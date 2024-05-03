from google.oauth2 import credentials
from googleapiclient.discovery import build
from fastapi import FastAPI, BackgroundTasks
from fastapi.responses import JSONResponse

app = FastAPI(title="Unreplied Emails Add-on")

@app.get("/")
async def root():
    return {"message": "Welcome to Email add-on test"}

# Function to authenticate and authorize the user
def get_gmail_service(access_token):
    creds = credentials.Credentials(access_token)
    return build('gmail', 'v1', credentials=creds)

# Function to check if the email is from the quytech.com domain
def is_quytech_email(sender):
    return '@quytech.com' in sender

# Function to retrieve unreplied emails asynchronously
async def get_unreplied_emails_async(service):
    try:
        response = service.users().messages().list(userId='me', q='is:unread').execute()
        messages = response.get('messages', [])
        unreplied_emails = []

        for message in messages:
            msg_details = service.users().messages().get(userId='me', id=message['id']).execute()
            sender = msg_details['payload']['headers'][3]['value']  # Assuming 'From' header is at index 3
            subject = next(header['value'] for header in msg_details['payload']['headers'] if header['name'] == 'Subject')
            date = msg_details['internalDate']  # Adjust as needed
            if is_quytech_email(sender) and not has_been_replied_to(service, msg_details):
                unreplied_emails.append({'sender': sender, 'subject': subject, 'date': date})
        
        return unreplied_emails
    except Exception as e:
        return []

# Function to check if the email has been replied to
def has_been_replied_to(service, message):
    thread_id = message['threadId']
    response = service.users().threads().get(userId='me', id=thread_id).execute()
    return len(response['messages']) > 1

# Function to build cards to display in the add-on
def build_cards(emails):
    cards = []
    for email in emails:
        card = {
            "header": email['subject'],
            "sections": [
                {"text": f"Sender: {email['sender']}"},
                {"text": f"Date: {email['date']}"}
            ]
        }
        cards.append(card)
    return cards

# Background task to retrieve and display unreplied emails
async def background_task(gevent, background_tasks):
    access_token = gevent.authorizationEventObject.userOAuthToken
    service = get_gmail_service(access_token)

    # Retrieve unreplied emails asynchronously
    unreplied_emails = await get_unreplied_emails_async(service)

    if not unreplied_emails:
        # If no unreplied emails found, return a response with an appropriate message
        return JSONResponse(content={"message": "No unreplied emails found"}, status_code=200)
    
    # Build cards to display in the add-on
    cards = build_cards(unreplied_emails)
    return {"cards": cards}

# Endpoint to trigger background task for retrieving emails
@app.post("/homepage", response_class=JSONResponse)
async def homepage(gevent: models.GEvent, background_tasks: BackgroundTasks):
    background_tasks.add_task(background_task, gevent, background_tasks)
    return JSONResponse(content={}, status_code=200)
