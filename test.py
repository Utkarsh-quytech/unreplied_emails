from typing import List
from gapps.cardservice import models
from fastapi.responses import JSONResponse
from google.oauth2 import service_account
from googleapiclient.discovery import build
from fastapi import FastAPI, HTTPException

app = FastAPI()

# Define your service account credentials file path
SERVICE_ACCOUNT_FILE = 'service_account.json'

# Define your Gmail API version
GMAIL_API_VERSION = 'v1'

@app.get("/")
async def root():
    return {"message": "Welcome to Simple Demo App example"}

class EmailInfo:
    def __init__(self, sender_name: str, subject: str):
        self.sender_name = sender_name
        self.subject = subject

def get_unreplied_emails(credentials) -> List[EmailInfo]:
    try:
        # Build the Gmail service
        gmail_service = build('gmail', GMAIL_API_VERSION, credentials=credentials)

        # Fetch unreplied emails
        response = gmail_service.users().messages().list(userId='me', q="is:unread -in:sent from:me").execute()
        messages = response.get('messages', [])

        unreplied_emails = []
        for message in messages:
            msg_id = message['id']
            msg = gmail_service.users().messages().get(userId='me', id=msg_id).execute()
            sender_name = next((header['value'] for header in msg['payload']['headers'] if header['name'] == 'From'), None)
            subject = next((header['value'] for header in msg['payload']['headers'] if header['name'] == 'Subject'), None)
            unreplied_emails.append(EmailInfo(sender_name=sender_name, subject=subject))
        
        return unreplied_emails

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")

@app.post("/homepage", response_class=JSONResponse)
async def homepage(gevent: models.GEvent):
    try:
        # Authenticate using service account credentials
        credentials = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE)

        # Fetch unreplied emails
        unreplied_emails = get_unreplied_emails(credentials)

        # Convert EmailInfo objects to dictionaries
        email_dicts = [{"sender_name": email.sender_name, "subject": email.subject} for email in unreplied_emails]

        return email_dicts
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="Internal Server Error: Service account credentials file not found.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")
