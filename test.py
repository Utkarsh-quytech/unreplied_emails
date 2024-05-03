from fastapi import FastAPI, BackgroundTasks
from fastapi.responses import JSONResponse
from gapps import CardService
from gapps.cardservice import models
from gapps.cardservice.utilities import decode_email
import google.oauth2.credentials
from googleapiclient.discovery import build

app = FastAPI(title="Unreplied Emails Add-on")

@app.get("/")
async def root():
    return {"message": "Welcome to Email add-on test"}

# Function to authenticate and authorize the user
def get_gmail_service(access_token):
    creds = google.oauth2.credentials.Credentials(access_token)
    return build('gmail', 'v1', credentials=creds)

# Function to retrieve unreplied emails asynchronously
async def get_unreplied_emails_async(service):
    try:
        response = service.users().threads().list(userId='me', q='is:unread').execute()
        threads = response.get('threads', [])
        unreplied_threads = []

        for thread in threads:
            thread_id = thread['id']
            messages = service.users().threads().get(userId='me', id=thread_id).execute()
            if len(messages['messages']) == 1:  # Only one message means it hasn't been replied to
                message = messages['messages'][0]
                sender = message['payload']['headers'][1]['value']  # Assuming sender's email is the second header
                subject = next(item['value'] for item in message['payload']['headers'] if item['name'] == 'Subject')
                date = message['payload']['headers'][2]['value']  # Assuming date is the third header
                if sender.endswith('@quytech.com'):
                    unreplied_threads.append({'sender': sender, 'subject': subject, 'date': date})
        
        return unreplied_threads
    except Exception as e:
        return []

# Function to build cards to display in the add-on
def build_cards(emails):
    cards = []
    for email in emails:
        card = CardService.newCardBuilder()
        card.set_header_text(email['subject'])
        card.add_section(CardService.newCardSection()
            .add_widget(CardService.newDecoratedText().set_text(email['sender']).set_bottom_label(email['date'])))
        cards.append(card.build())

    return cards

# Background task to retrieve and display unreplied emails
async def background_task(gevent: models.GEvent, background_tasks: BackgroundTasks):
    access_token = gevent.authorizationEventObject.userOAuthToken
    service = get_gmail_service(access_token)

    # Retrieve unreplied emails asynchronously
    unreplied_threads = await get_unreplied_emails_async(service)

    if not unreplied_threads:
        # If no unreplied emails found, return a response with an appropriate message
        return JSONResponse(content={"message": "No unreplied emails found"}, status_code=200)
    
    # Build cards to display in the add-on
    cards = build_cards(unreplied_threads)
    return {"cards": cards}

# Endpoint to trigger background task for retrieving emails
@app.post("/homepage", response_class=JSONResponse)
async def homepage(gevent: models.GEvent, background_tasks: BackgroundTasks):
    background_tasks.add_task(background_task, gevent, background_tasks)
    return JSONResponse(content={}, status_code=200)

