# from typing import List
# from gapps.cardservice import models
# from fastapi import FastAPI, HTTPException
# from fastapi.responses import JSONResponse
# from google.oauth2 import id_token
# from google.auth.transport import requests
# from googleapiclient.discovery import build
# from googleapiclient.errors import HttpError

# app = FastAPI()

# @app.get("/")
# async def root():
#     return {"message": "Welcome to Simple Demo App example"}

# class EmailInfo:
#     def __init__(self, sender_name: str, subject: str):
#         self.sender_name = sender_name
#         self.subject = subject

# def get_unreplied_emails(gevent) -> List[EmailInfo]:
#     # Authenticate with Gmail API
#     credentials = id_token.fetch_id_token(requests.Request(), gevent.authorizationEventObject.userIdToken)
#     service = build('gmail', 'v1', credentials=credentials)

#     try:
#         # Fetch unreplied emails
#         response = service.users().messages().list(userId='me', q="is:unread -in:sent from:me").execute()
#         messages = response.get('messages', [])

#         unreplied_emails = []
#         for message in messages:
#             msg_id = message['id']
#             msg = service.users().messages().get(userId='me', id=msg_id).execute()
#             sender_name = next((header['value'] for header in msg['payload']['headers'] if header['name'] == 'From'), None)
#             subject = next((header['value'] for header in msg['payload']['headers'] if header['name'] == 'Subject'), None)
#             unreplied_emails.append(EmailInfo(sender_name=sender_name, subject=subject))
        
#         return unreplied_emails

#     except HttpError as e:
#         raise HTTPException(status_code=e.resp.status, detail=e._get_reason())

# @app.post("/homepage", response_class=JSONResponse)
# async def homepage(gevent: models.GEvent):
#     # email = decode_email(gevent.authorizationEventObject.userIdToken)
    
#     # Fetch unreplied emails
#     unreplied_emails = get_unreplied_emails(gevent)

#     return unreplied_emails


from typing import List
from gapps.cardservice import models
from fastapi.responses import JSONResponse
from google.oauth2 import id_token
from google.auth.transport import requests
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from fastapi import FastAPI, HTTPException

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Welcome to Simple Demo App example"}

class EmailInfo:
    def __init__(self, sender_name: str, subject: str):
        self.sender_name = sender_name
        self.subject = subject

def get_unreplied_emails(gevent) -> List[EmailInfo]:
    # Authenticate with Gmail API
    credentials = id_token.fetch_id_token(requests.Request(), gevent.authorizationEventObject.userIdToken)
    service = build('gmail', 'v1', credentials=credentials)

    try:
        # Fetch unreplied emails
        response = service.users().messages().list(userId='me', q="is:unread -in:sent from:me").execute()
        messages = response.get('messages', [])

        unreplied_emails = []
        for message in messages:
            msg_id = message['id']
            msg = service.users().messages().get(userId='me', id=msg_id).execute()
            sender_name = next((header['value'] for header in msg['payload']['headers'] if header['name'] == 'From'), None)
            subject = next((header['value'] for header in msg['payload']['headers'] if header['name'] == 'Subject'), None)
            unreplied_emails.append(EmailInfo(sender_name=sender_name, subject=subject))
        
        return unreplied_emails

    except HttpError as e:
        raise HTTPException(status_code=500, detail="Failed to fetch unreplied emails.")

@app.post("/homepage", response_class=JSONResponse, response_model=None)
async def homepage(gevent: models.GEvent) -> List[EmailInfo]:
    # Fetch unreplied emails
    unreplied_emails = get_unreplied_emails(gevent)

    return unreplied_emails


