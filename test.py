import google.oauth2.credentials
from googleapiclient.discovery import build
from fastapi import FastAPI, BackgroundTasks
from fastapi.responses import JSONResponse
from gapps import CardService
from gapps.cardservice import models
from gapps.cardservice.utilities import decode_email
import asyncio

app = FastAPI(title="Unreplied Emails Add-on")

# Function to authenticate and authorize the user
def get_gmail_service(access_token):
    creds = google.oauth2.credentials.Credentials(access_token)
    return build('gmail', 'v1', credentials=creds)

# Function to retrieve unreplied emails asynchronously
async def get_unreplied_emails_async(service):
    try:
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, service.users().threads().list, userId='me')
        threads = response.get('threads', [])
        unreplied_threads = []

        for thread in threads:
            thread_id = thread['id']
            messages = await loop.run_in_executor(None, service.users().threads().get, userId='me', id=thread_id)
            if not any('INBOX' in msg['labelIds'] for msg in messages['messages']):
                unreplied_threads.append(thread)

        return unreplied_threads
    except Exception as e:
        return str(e)

# Function to filter emails by domain
def filter_by_domain(emails, domain):
    return [email for email in emails if email['sender'].endswith(domain)]

# Function to build cards to display in the add-on
def build_cards(emails):
    cards = []
    for email in emails:
        sender_name = email['sender']
        subject = email['subject']
        
        # Create an icon image
        icon_image = CardService.newIconImage().setIconUrl('https://www.google.com/url?sa=i&url=https%3A%2F%2Fwww.freepik.com%2Ffree-photos-vectors%2Fbutton&psig=AOvVaw11LaPqu_HGlFjKWw4qvcg1&ust=1714731332072000&source=images&cd=vfe&opi=89978449&ved=0CBIQjRxqFwoTCLDPiZHe7oUDFQAAAAAdAAAAABAE')

        # Create a decorated text widget for sender name
        sender_decorated_text = CardService.newDecoratedText() \
            .setText(sender_name) \
            .setBottomLabel('Sender')

        # Create a decorated text widget for subject
        subject_decorated_text = CardService.newDecoratedText() \
            .setText(subject) \
            .setBottomLabel('Subject')

        # Create a card section with sender and subject decorated texts
        card_section = CardService.newCardSection() \
            .setHeader('Unreplied Emails') \
            .addWidget(sender_decorated_text) \
            .addWidget(subject_decorated_text)

        # Create a card with the card section
        card = CardService.newCardBuilder() \
            .addSection(card_section) \
            .setHeader(icon_image) \
            .build()
        
        cards.append(card)

    return cards

# Background task to retrieve and display unreplied emails from @quytech.com
async def background_task(gevent: models.GEvent, background_tasks: BackgroundTasks):
    access_token = gevent.authorizationEventObject.userOAuthToken
    service = get_gmail_service(access_token)

    # Retrieve unreplied emails asynchronously
    unreplied_threads = await get_unreplied_emails_async(service)

    if isinstance(unreplied_threads, str):
        return JSONResponse(status_code=500, content={"error": {"message": "Error occurred while fetching emails: " + unreplied_threads}})

    # Filter emails from @quytech.com domain
    quytech_threads = filter_by_domain(unreplied_threads, "@quytech.com")

    # Build cards to display in the add-on
    cards = build_cards(quytech_threads)
    return {"renderActions": {"actions": cards}}

# Endpoint to trigger background task for retrieving emails
@app.post("/homepage", response_class=JSONResponse)
async def homepage(gevent: models.GEvent, background_tasks: BackgroundTasks):
    background_tasks.add_task(background_task, gevent, background_tasks)
    return JSONResponse(content={}, status_code=200)

# Handle 504 Gateway Timeout errors
@app.exception_handler(504)
async def gateway_timeout_exception_handler(request, exc):
    return JSONResponse(
        status_code=504,
        content={"error": {"message": "Gateway Timeout: The server did not receive a timely response from the upstream server."}}
    )
