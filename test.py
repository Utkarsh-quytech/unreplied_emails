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
        response = service.users().messages().list(userId='me', maxResults=10).execute()
        messages = response.get('messages', [])
        unreplied_emails = []

        for message in messages:
            message_id = message['id']
            msg = service.users().messages().get(userId='me', id=message_id).execute()
            if not any('INBOX' in label for label in msg['labelIds']):
                sender = next((header['value'] for header in msg['payload']['headers'] if header['name'] == 'From'), '')
                subject = next((header['value'] for header in msg['payload']['headers'] if header['name'] == 'Subject'), '')
                unreplied_emails.append({'sender': sender, 'subject': subject})

        return unreplied_emails
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

        card_section1_decorated_text1 = CardService.newDecoratedText() \
            .setText(sender_name) \
            .setBottomLabel(subject)

        card_section1 = CardService.newCardSection() \
            .addWidget(card_section1_decorated_text1)

        card = CardService.newCardBuilder() \
            .addSection(card_section1) \
            .build()
        
        cards.append(card)

    return cards

# Background task to retrieve and display unreplied emails from @quytech.com
async def background_task(gevent: models.GEvent, background_tasks: BackgroundTasks):
    access_token = gevent.authorizationEventObject.userOAuthToken
    service = get_gmail_service(access_token)

    unreplied_emails = await get_unreplied_emails_async(service)

    if isinstance(unreplied_emails, str):
        return JSONResponse(status_code=500, content={"error": {"message": "Error occurred while fetching emails: " + unreplied_emails}})

    quytech_emails = filter_by_domain(unreplied_emails, "@quytech.com")

    cards = build_cards(quytech_emails)
    return cards

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
