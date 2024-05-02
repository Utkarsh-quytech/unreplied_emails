import google.oauth2.credentials
from googleapiclient.discovery import build
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from gapps import CardService
from gapps.cardservice import models
from gapps.cardservice.utilities import decode_email

app = FastAPI(title="Unreplied Emails Add-on")

# Function to authenticate and authorize the user
def get_gmail_service(access_token):
    creds = google.oauth2.credentials.Credentials(access_token)
    return build('gmail', 'v1', credentials=creds)

# Function to retrieve unreplied emails with domain @quytech.com
def get_unreplied_emails(service):
    try:
        # Retrieve latest 100 messages
        response = service.users().messages().list(userId='me', maxResults=100).execute()
        messages = response.get('messages', [])

        unreplied_emails = []
        for message in messages:
            message_id = message['id']
            msg = service.users().messages().get(userId='me', id=message_id).execute()
            # Check if the email is unreplied
            if not any('INBOX' in label for label in msg['labelIds']):
                # Extract sender's email
                sender = next((header['value'] for header in msg['payload']['headers'] if header['name'] == 'From'), '')
                # Extract subject
                subject = next((header['value'] for header in msg['payload']['headers'] if header['name'] == 'Subject'), '')
                unreplied_emails.append({'sender': sender, 'subject': subject})
        return unreplied_emails
    except Exception as e:
        return str(e)

# Function to filter emails by domain
def filter_by_domain(emails, domain):
    return [email for email in emails if email['sender'].endswith(domain)]

# Function to build cards to display in the add-on
def build_cards(emails):
    cards = []
    for email in emails:
        sender_name = email['sender']
        subject = email['subject']

        # Create card section with sender name and subject
        card_section1_decorated_text1 = CardService.newDecoratedText() \
            .setText(sender_name) \
            .setBottomLabel(subject)

        card_section1 = CardService.newCardSection() \
            .addWidget(card_section1_decorated_text1)

        # Create a card with the card section
        card = CardService.newCardBuilder() \
            .addSection(card_section1) \
            .build()
        
        cards.append(card)

    return cards

# Endpoint to retrieve unreplied emails with domain @quytech.com
@app.post("/homepage", response_class=JSONResponse)
def homepage(gevent: models.GEvent):
    access_token = gevent.authorizationEventObject.userOAuthToken
    service = get_gmail_service(access_token)

    # Retrieve unreplied emails
    unreplied_emails = get_unreplied_emails(service)

    if isinstance(unreplied_emails, str):
        return JSONResponse(status_code=500, content={"error": {"message": "Error occurred while fetching emails: " + unreplied_emails}})

    # Filter emails from @quytech.com domain
    quytech_emails = filter_by_domain(unreplied_emails, "@quytech.com")

    # Build cards to display in the add-on
    cards = build_cards(quytech_emails)
    return {"renderActions": {"actions": cards}}
