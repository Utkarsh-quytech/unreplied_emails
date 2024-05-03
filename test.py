from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from gapps import CardService
from gapps.cardservice import models
from gapps.cardservice.utilities import decode_email

app = FastAPI(title="Unreplied Emails Add-on")

@app.get("/")
async def root():
    return {"message": "Welcome to Unreplied Emails Add-on"}

@app.post("/homepage", response_class=JSONResponse)
async def homepage(gevent: models.GEvent):
    access_token = gevent.authorizationEventObject.userOAuthToken
    email = decode_email(gevent.authorizationEventObject.userIdToken)
    creds = Credentials(access_token)
    page = send_reminder(email, creds)
    return page

def send_reminder(email, creds):
    unreplied_emails = get_unreplied_emails(email, creds)
    if unreplied_emails:
        # Build the card for unreplied emails
        card = build_unreplied_emails_card(unreplied_emails)
        return card
    else:
        # Return a card indicating no unreplied emails
        return CardService.newCardBuilder() \
            .setHeader(CardService.newCardHeader().setTitle('No Unreplied Emails')) \
            .build()

def get_unreplied_emails(email, creds):
    unreplied_emails = []
    service = build('gmail', 'v1', credentials=creds)

    # Get unreplied incoming emails
    threads = service.users().threads().list(userId='me', q='-is:chats -is:sent -is:draft -in:trash', maxResults=50).execute()
    if 'threads' in threads:
        for thread in threads['threads']:
            thread_id = thread['id']
            thread_messages = service.users().threads().get(userId='me', id=thread_id).execute()
            for message in thread_messages['messages']:
                message_id = message['id']
                message_details = service.users().messages().get(userId='me', id=message_id).execute()
                sender = [header['value'] for header in message_details['payload']['headers'] if header['name'] == 'From']
                sender = sender[0] if sender else None
                subject = [header['value'] for header in message_details['payload']['headers'] if header['name'] == 'Subject']
                subject = subject[0] if subject else None
                message_date = datetime.fromtimestamp(int(message_details['internalDate'])/1000.0)
                # Check if the email is from the specified domain and not replied
                if sender and '@quytech.com' in sender and not has_been_replied_to(service, thread_id):
                    unreplied_emails.append({'sender': sender, 'subject': subject, 'date': message_date})
    return unreplied_emails

def has_been_replied_to(service, thread_id):
    thread = service.users().threads().get(userId='me', id=thread_id).execute()
    messages = thread['messages']
    return len(messages) > 1

def build_unreplied_emails_card(emails):
    card = CardService.newCardBuilder().setHeader(CardService.newCardHeader().setTitle('Unreplied Emails'))
    # Add sections for each unreplied email
    for email in emails:
        section = CardService.newCardSection() \
            .setHeader(email['subject']) \
            .addWidget(CardService.newTextParagraph().setText(f'Sender: {email["sender"]}')) \
            .addWidget(CardService.newTextParagraph().setText(f'Date: {email["date"]}'))
        card.addSection(section)
    return card.build()
