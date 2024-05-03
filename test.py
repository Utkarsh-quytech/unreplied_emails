from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from datetime import datetime
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.responses import JSONResponse
from gapps import CardService
from gapps.cardservice import models
from gapps.cardservice.utilities import decode_email
import asyncio
import aiohttp

app = FastAPI(title="Unreplied Emails Add-on")

@app.get("/")
async def root():
    return {"message": "Welcome to Unreplied Emails Add-on"}

@app.post("/homepage", response_class=JSONResponse)
async def homepage(gevent: models.GEvent, background_tasks: BackgroundTasks):
    access_token = gevent.authorizationEventObject.userOAuthToken
    email = decode_email(gevent.authorizationEventObject.userIdToken)
    creds = Credentials(access_token)
    background_tasks.add_task(send_reminder, email, creds)
    return {"message": "Processing request in the background"}

async def send_reminder(email, creds):
    unreplied_emails = await get_unreplied_emails(email, creds)
    if unreplied_emails:
        # Build the card for unreplied emails
        card = build_unreplied_emails_card(unreplied_emails)
        # Now you can send this card to the user or do further processing
    else:
        # No unreplied emails found
        print("No unreplied emails")

async def get_unreplied_emails(email, creds):
    unreplied_emails = []
    service = build('gmail', 'v1', credentials=creds)

    # Get unreplied incoming emails
    next_page_token = None
    async with aiohttp.ClientSession() as session:
        while True:
            async with session.get(f'https://www.googleapis.com/gmail/v1/users/me/threads?q=-is:chats -is:sent -is:draft -in:trash&maxResults=100&pageToken={next_page_token}', headers={'Authorization': f'Bearer {creds.token}'}) as response:
                if response.status == 200:
                    threads = await response.json()
                    if 'threads' in threads:
                        for thread in threads['threads']:
                            thread_id = thread['id']
                            async with session.get(f'https://www.googleapis.com/gmail/v1/users/me/threads/{thread_id}', headers={'Authorization': f'Bearer {creds.token}'}) as msg_response:
                                if msg_response.status == 200:
                                    thread_messages = await msg_response.json()
                                    for message in thread_messages['messages']:
                                        message_id = message['id']
                                        async with session.get(f'https://www.googleapis.com/gmail/v1/users/me/messages/{message_id}', headers={'Authorization': f'Bearer {creds.token}'}) as msg_detail_response:
                                            if msg_detail_response.status == 200:
                                                message_details = await msg_detail_response.json()
                                                sender = [header['value'] for header in message_details['payload']['headers'] if header['name'] == 'From']
                                                sender = sender[0] if sender else None
                                                subject = [header['value'] for header in message_details['payload']['headers'] if header['name'] == 'Subject']
                                                subject = subject[0] if subject else None
                                                message_date = datetime.fromtimestamp(int(message_details['internalDate'])/1000.0)
                                                # Check if the email is from the specified domain and not replied
                                                if sender and '@quytech.com' in sender and not await has_been_replied_to(service, thread_id, creds):
                                                    unreplied_emails.append({'sender': sender, 'subject': subject, 'date': message_date})
                        # Check if there are more pages
                        next_page_token = threads.get('nextPageToken')
                        if not next_page_token:
                            break  # No more pages, exit the loop
                    else:
                        break  # No threads found, exit the loop
                else:
                    raise HTTPException(status_code=response.status, detail=await response.text())
    return unreplied_emails

async def has_been_replied_to(service, thread_id, creds):
    async with aiohttp.ClientSession() as session:
        async with session.get(f'https://www.googleapis.com/gmail/v1/users/me/threads/{thread_id}', headers={'Authorization': f'Bearer {creds.token}'}) as response:
            if response.status == 200:
                thread = await response.json()
                messages = thread['messages']
                return len(messages) > 1
            else:
                raise HTTPException(status_code=response.status, detail=await response.text())

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
