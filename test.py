from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from datetime import datetime
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from gapps import CardService
from gapps.cardservice import models
from pytz import timezone, UnknownTimeZoneError

app = FastAPI(title="Emails-Not-Replied Add-on")

@app.get("/")
async def root():
    return {"message": "Welcome to Unreplied Emails Add-on"}

@app.post("/homepage", response_class=JSONResponse)
async def homepage(gevent: models.GEvent):
    access_token = gevent.authorizationEventObject.userOAuthToken
    creds = Credentials(access_token)
    page = send_reminder(creds)
    return page

def send_reminder(creds):
    unreplied_emails = get_unreplied_emails(creds)
    if unreplied_emails:
        # Build the card for unreplied emails
        card = build_unreplied_emails_card(unreplied_emails)
        return card
    else:
        # Return a card indicating no unreplied emails
        return CardService.newCardBuilder() \
            .setHeader(CardService.newCardHeader().setTitle('No Unreplied Emails')) \
            .build()

def get_unreplied_emails(creds):
    unreplied_emails = []
    service = build('gmail', 'v1', credentials=creds)

    # Get unreplied incoming emails
    threads = service.users().threads().list(userId='me', q='-is:chats -is:sent -is:draft -in:trash', maxResults=20).execute()
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
                message_date = int(message_details['internalDate'])
                # Get the time zone information from the headers
                time_zone = [header['value'] for header in message_details['payload']['headers'] if header['name'] == 'Date']
                time_zone = time_zone[0][-6:] if time_zone else None  # Extracting time zone from the Date header
                unreplied_emails.append({'sender': sender, 'subject': subject, 'date': message_date, 'time_zone': time_zone})
    return unreplied_emails

def build_unreplied_emails_card(emails):
    card = CardService.newCardBuilder().setHeader(CardService.newCardHeader().setTitle('Emails-Not-Replied '))
    # Add sections for each unreplied email
    for email in emails:
        try:
            message_date_with_timezone = datetime.fromtimestamp(email['date'] / 1000.0, timezone(email['time_zone'])).strftime('%Y-%m-%d %H:%M:%S %Z')
        except UnknownTimeZoneError:
            message_date_with_timezone = "Unknown Time Zone"
        section = CardService.newCardSection() \
            .setHeader(email['subject']) \
            .addWidget(CardService.newTextParagraph().setText(f'Sender: {email["sender"]}')) \
            .addWidget(CardService.newTextParagraph().setText(f'Date: {message_date_with_timezone}'))
        card.addSection(section)
    return card.build()
