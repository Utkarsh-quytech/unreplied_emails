import google.oauth2.credentials
from googleapiclient.discovery import build
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from gapps import CardService
from gapps.cardservice import models
from gapps.cardservice.utilities import decode_email
import asyncio
from functools import partial

app = FastAPI(title="Unreplied Emails Add-on")

# Function to authenticate and authorize the user
def get_gmail_service(access_token):
    creds = google.oauth2.credentials.Credentials(access_token)
    return build('gmail', 'v1', credentials=creds)

# Function to retrieve unreplied emails asynchronously
async def get_unreplied_emails_async(service):
    try:
        response = service.users().threads().list(userId='me').execute()
        threads = response.get('threads', [])
        unreplied_threads = []

        for thread in threads:
            thread_id = thread['id']
            messages = service.users().threads().get(userId='me', id=thread_id).execute()
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

        # Create card section with sender name and subject
        card_section1_decorated_text1 = CardService.newDecoratedText() \
            .setText(sender_name) \
            .setBottomLabel(subject)

        card_section1 = CardService.newCardSection() \
            .addWidget(card_section1_decorated_text1)

        # Create a card with the card section
        card = CardService.newCardBuilder() \
            .addSection(card_section1) \
            .build()
        
        cards.append(card)

    return cards

# Endpoint to trigger background task for retrieving emails
@app.post("/homepage", response_class=JSONResponse)
async def homepage(gevent: models.GEvent):
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
