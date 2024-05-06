from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from datetime import datetime
from pytz import timezone  # Import pytz library for handling timezones
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from gapps import CardService
from gapps.cardservice import models
import pytz
from geopy.geocoders import Nominatim

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

def send_reminder(creds, user_location):
    unreplied_emails = get_unreplied_emails(creds)
    if unreplied_emails:
        # Build the card for unreplied emails
        card = build_unreplied_emails_card(unreplied_emails, user_location)
        return card
    else:
        # Return a card indicating no unreplied emails
        return CardService.newCardBuilder() \
            .setHeader(CardService.newCardHeader().setTitle('No Unreplied Emails')) \
            .build()

def get_user_timezone(user_location):
    geolocator = Nominatim(user_agent="email-not-replied-addon")
    location = geolocator.geocode(user_location)
    if location:
        timezone_str = pytz.timezone(location.timezone).zone
        return pytz.timezone(timezone_str)
    else:
        # Default to UTC timezone if location not found
        return pytz.utc

def get_unreplied_emails(creds, user_location):
    unreplied_emails = []
    user_timezone = get_user_timezone(user_location)
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
                message_date = datetime.fromtimestamp(int(message_details['internalDate'])/1000.0)
                # Convert message date to user's timezone
                message_date_with_timezone = message_date.replace(tzinfo=pytz.utc).astimezone(user_timezone).strftime('%Y-%m-%d %H:%M:%S %Z')
                # Check if the email is from the specified domain and not replied
                if sender and '@quytech.com' in sender and not has_been_replied_to(service, thread_id):
                    unreplied_emails.append({'sender': sender, 'subject': subject, 'date': message_date_with_timezone})
    return unreplied_emails

def build_unreplied_emails_card(emails, user_location):
    user_timezone = get_user_timezone(user_location)
    card = CardService.newCardBuilder().setHeader(CardService.newCardHeader().setTitle('Emails-Not-Replied'))
    # Add sections for each unreplied email
    for email in emails:
        section = CardService.newCardSection() \
            .setHeader(email['subject']) \
            .addWidget(CardService.newTextParagraph().setText(f'Sender: {email["sender"]}')) \
            .addWidget(CardService.newTextParagraph().setText(f'Date: {email["date"]}'))
        card.addSection(section)
    return card.build()

