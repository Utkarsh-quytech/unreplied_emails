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
            unreplied_threads.append(thread)

        return unreplied_threads
    except Exception as e:
        return []

# Function to build cards to display in the add-on
def build_cards(emails):
    cards = []
    for email in emails:
        card_section = CardService.newCardSection()
        card_section.set_header('Unreplied Email')
        card_section.set_widgets([CardService.newTextParagraph().setText(email['snippet'])])

        card = CardService.newCardBuilder()
        card.add_section(card_section)
        cards.append(card.build())

    return cards

# Background task to retrieve and display unreplied emails
async def background_task(gevent: models.GEvent, background_tasks: BackgroundTasks):
    access_token = gevent.authorizationEventObject.userOAuthToken
    service = get_gmail_service(access_token)

    # Retrieve unreplied emails asynchronously
    unreplied_threads = await get_unreplied_emails_async(service)

    # Build cards to display in the add-on
    if unreplied_threads:
        cards = build_cards(unreplied_threads)
        return {"cards": cards}
    else:
        return {"cards": []}

# Endpoint to trigger background task for retrieving emails
@app.post("/homepage", response_class=JSONResponse)
async def homepage(gevent: models.GEvent, background_tasks: BackgroundTasks):
    background_tasks.add_task(background_task, gevent, background_tasks)
    return JSONResponse(content={}, status_code=200)
