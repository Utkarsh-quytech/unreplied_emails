from typing import List
from gapps.cardservice import models
from fastapi.responses import JSONResponse
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from google.auth import default
import requests
from fastapi import FastAPI, HTTPException

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Welcome to Simple Demo App example"}

class EmailInfo:
    def __init__(self, sender_name: str, subject: str):
        self.sender_name = sender_name
        self.subject = subject

def get_unreplied_emails() -> List[EmailInfo]:
    try:
        # Fetch access token using application default credentials (ADC)
        credentials, project_id = default()
        access_token = credentials.token
        
        # Fetch unreplied emails
        response = requests.get(
            "https://gmail.googleapis.com/gmail/v1/users/me/messages",
            params={"q": "is:unread -in:sent from:me"},
            headers={"Authorization": f"Bearer {access_token}"}
        )
        response.raise_for_status()
        
        messages = response.json().get('messages', [])

        unreplied_emails = []
        for message in messages:
            msg_id = message['id']
            msg_response = requests.get(
                f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{msg_id}",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            msg_response.raise_for_status()
            msg = msg_response.json()
            sender_name = next((header['value'] for header in msg['payload']['headers'] if header['name'] == 'From'), None)
            subject = next((header['value'] for header in msg['payload']['headers'] if header['name'] == 'Subject'), None)
            unreplied_emails.append(EmailInfo(sender_name=sender_name, subject=subject))
        
        return unreplied_emails

    except requests.HTTPError as e:
        raise HTTPException(status_code=e.response.status_code, detail=f"Failed to fetch unreplied emails: {e.response.text}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")

@app.post("/homepage", response_class=JSONResponse)
async def homepage():
    # Fetch unreplied emails
    unreplied_emails = get_unreplied_emails()

    # Convert EmailInfo objects to dictionaries
    email_dicts = [{"sender_name": email.sender_name, "subject": email.subject} for email in unreplied_emails]

    return email_dicts

