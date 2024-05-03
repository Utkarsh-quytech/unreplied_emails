import aiohttp
import asyncio
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
    headers = {"Authorization": f"Bearer {access_token}"}
    params = {
        'q': '-is:chats -is:sent -is:draft -in:trash',
        'maxResults': 100
    }
    base_url = "https://gmail.googleapis.com/gmail/v1/users/me/threads"
    async with aiohttp.ClientSession() as session:
        next_page_token = None
        while True:
            if next_page_token:
                params['pageToken'] = next_page_token
            async with session.get(base_url, params=params, headers=headers) as response:
                data = await response.json()
                threads = data.get('threads', [])
                for thread in threads:
                    thread_id = thread['id']
                    async with session.get(f"{base_url}/{thread_id}", headers=headers) as thread_response:
                        thread_data = await thread_response.json()
                        messages = thread_data.get('messages', [])
                        for message in messages:
                            message_id = message['id']
                            async with session.get(f"{base_url}/{thread_id}/messages/{message_id}", headers=headers) as message_response:
                                message_data = await message_response.json()
                                sender = next((header['value'] for header in message_data['payload']['headers'] if header['name'] == 'From'), None)
                                subject = next((header['value'] for header in message_data['payload']['headers'] if header['name'] == 'Subject'), None)
                                message_date = datetime.fromtimestamp(int(message_data['internalDate'])/1000.0)
                                # Check if the email is from the specified domain and not replied
                                if sender and '@quytech.com' in sender and not await has_been_replied_to(access_token, thread_id):
                                    unreplied_emails.append({'sender': sender, 'subject': subject, 'date': message_date})
                # Check if there are more pages
                next_page_token = data.get('nextPageToken')
                if not next_page_token:
                    break  # No more pages, exit the loop
    return unreplied_emails

async def has_been_replied_to(access_token, thread_id):
    async with aiohttp.ClientSession() as session:
        headers = {"Authorization": f"Bearer {access_token}"}
        async with session.get(f"https://gmail.googleapis.com/gmail/v1/users/me/threads/{thread_id}", headers=headers) as response:
            data = await response.json()
            messages = data.get('messages', [])
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
