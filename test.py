from gapps.cardservice import models
import google.oauth2.credentials
from googleapiclient.discovery import build
from fastapi import FastAPI, BackgroundTasks
from fastapi.responses import JSONResponse
from gapps import CardService

app = FastAPI(title="Unreplied Emails Add-on")

@app.get("/")
async def root():
    return {"message": "Welcome to Simple Demo App example"}

# Function to retrieve unreplied emails from users with domain @quytech.com
def get_unreplied_emails(service):
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
                if sender.endswith('@quytech.com'):
                    unreplied_emails.append({'sender': sender, 'subject': subject})

        return unreplied_emails
    except Exception as e:
        return str(e)

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

# Endpoint to retrieve unreplied emails with domain @quytech.com
@app.post("/homepage", response_class=JSONResponse)
def homepage(gevent: models.GEvent):
    access_token = gevent.authorizationEventObject.userOAuthToken
    service = get_gmail_service(access_token)

    # Retrieve unreplied emails from users with domain @quytech.com
    unreplied_emails = get_unreplied_emails(service)

    if unreplied_emails:
        # Build cards to display in the add-on
        cards = build_cards(unreplied_emails)
        return JSONResponse(status_code=200, content={"renderActions": {"actions": cards}})
    
    # If no unreplied emails found, return an empty list
    return JSONResponse(status_code=200, content={"message": "No unreplied emails found"})
