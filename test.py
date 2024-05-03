import asyncio
from aiogoogle import Aiogoogle
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
    page = await send_reminder(email, access_token)
    return page

async def send_reminder(email, access_token):
    unreplied_emails = await get_unreplied_emails(email, access_token)
    if unreplied_emails:
        # Build the card for unreplied emails
        card = build_unreplied_emails_card(unreplied_emails)
        return card
    else:
        # Return a card indicating no unreplied emails
        return CardService.newCardBuilder() \
            .setHeader(CardService.newCardHeader().setTitle('No Unreplied Emails')) \
            .build()

async def get_unreplied_emails(email, access_token):
    unreplied_emails = []
    async with Aiogoogle() as aiogoogle:
        gmail = await aiogoogle.discover('gmail', 'v1')
        # Get unreplied incoming emails
        next_page_token = None
        while True:
            params = {
                'userId': 'me',
                'q': '-is:chats -is:sent -is:draft -in:trash',
                'maxResults': 100,
                'pageToken': next_page_token
            }
            response = await aiogoogle.as_service_account(
                gmail.users().threads().list(**params),
                credentials=access_token
            )
            threads = response.get('threads', [])
            for thread in threads:
                thread_id = thread['id']
                thread_details = await aiogoogle.as_service_account(
                    gmail.users().threads().get(userId='me', id=thread_id),
                    credentials=access_token
                )
                messages = thread_details.get('messages', [])
                for message in messages:
                    message_id = message['id']
                    message_details = await aiogoogle.as_service_account(
                        gmail.users().messages().get(userId='me', id=message_id),
                        credentials=access_token
                    )
                    sender = next((header['value'] for header in message_details['payload']['headers'] if header['name'] == 'From'), None)
                    subject = next((header['value'] for header in message_details['payload']['headers'] if header['name'] == 'Subject'), None)
                    message_date = datetime.fromtimestamp(int(message_details['internalDate'])/1000.0)
                    # Check if the email is from the specified domain and not replied
                    if sender and '@quytech.com' in sender and not await has_been_replied_to(gmail, access_token, thread_id):
                        unreplied_emails.append({'sender': sender, 'subject': subject, 'date': message_date})
            # Check if there are more pages
            next_page_token = response.get('nextPageToken')
            if not next_page_token:
                break  # No more pages, exit the loop
    return unreplied_emails

async def has_been_replied_to(gmail, access_token, thread_id):
    response = await aiogoogle.as_service_account(
        gmail.users().threads().get(userId='me', id=thread_id),
        credentials=access_token
    )
    messages = response.get('messages', [])
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
