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
        # Implement your logic to fetch unreplied emails asynchronously
        # For example, you can use Gmail API's history.list() method to get recent messages
        # and check if they've been replied to.
        # Here's a simplified example using the threads.list() method:

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
        
        card_header = {
            "title": "Unreplied Emails",
            "subtitle": sender_name
        }

        card_sections = [
            {
                "header": "Subject",
                "widgets": [
                    {
                        "textParagraph": {"text": subject}
                    }
                ]
            }
        ]

        card = {
            "header": card_header,
            "sections": card_sections
        }

        cards.append(card)

    return cards

# Background task to retrieve and display unreplied emails from @quytech.com
async def background_task(gevent: models.GEvent, background_tasks: BackgroundTasks):
    access_token = gevent.authorizationEventObject.userOAuthToken
    service = get_gmail_service(access_token)

    # Retrieve unreplied emails asynchronously
    unreplied_threads = await get_unreplied_emails_async(service)

    if isinstance(unreplied_threads, str):
        return JSONResponse(status_code=500, content={"message": "Error occurred while fetching emails: " + unreplied_threads})

    # Filter emails from @quytech.com domain
    quytech_threads = filter_by_domain(unreplied_threads, "@quytech.com")

    # Build cards to display in the add-on
    cards = build_cards(quytech_threads)
    return cards

# Endpoint to trigger background task for retrieving emails
@app.post("/homepage", response_class=JSONResponse)
async def homepage(gevent: models.GEvent, background_tasks: BackgroundTasks):
    background_tasks.add_task(background_task, gevent, background_tasks)
    return {"message": "Background task initiated"}

# Handle 504 Gateway Timeout errors
@app.exception_handler(504)
async def gateway_timeout_exception_handler(request, exc):
    return JSONResponse(
        status_code=504,
        content={"message": "Gateway Timeout: The server did not receive a timely response from the upstream server."}
    )
