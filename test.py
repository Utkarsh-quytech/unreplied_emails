from typing import List
import requests
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from gapps.cardservice import models

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Welcome to Simple Demo App example"}

class EmailInfo:
    def __init__(self, sender_name: str, subject: str):
        self.sender_name = sender_name
        self.subject = subject

def get_unreplied_emails(authorization_token: str) -> List[EmailInfo]:
    headers = {"Authorization": f"Bearer {authorization_token}"}
    params = {"q": "is:unread -in:sent from:me"}

    try:
        response = requests.get("https://www.googleapis.com/gmail/v1/users/me/messages", headers=headers, params=params)
        response.raise_for_status()
        messages = response.json().get('messages', [])

        unreplied_emails = []
        for message in messages:
            msg_id = message['id']
            msg_response = requests.get(f"https://www.googleapis.com/gmail/v1/users/me/messages/{msg_id}", headers=headers)
            msg_response.raise_for_status()
            msg = msg_response.json()

            sender_name = next((header['value'] for header in msg['payload']['headers'] if header['name'] == 'From'), None)
            subject = next((header['value'] for header in msg['payload']['headers'] if header['name'] == 'Subject'), None)
            unreplied_emails.append(EmailInfo(sender_name=sender_name, subject=subject))
        
        return unreplied_emails

    except requests.HTTPError as e:
        raise HTTPException(status_code=500, detail="Failed to fetch unreplied emails.")

@app.post("/homepage", response_class=JSONResponse)
async def homepage(gevent: models.GEvent):
    try:
        # Fetch unreplied emails
        unreplied_emails = get_unreplied_emails(gevent.authorizationEventObject.userIdToken)

        # Convert EmailInfo objects to dictionaries
        email_dicts = [{"sender_name": email.sender_name, "subject": email.subject} for email in unreplied_emails]

        return email_dicts
    
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to process request.")
