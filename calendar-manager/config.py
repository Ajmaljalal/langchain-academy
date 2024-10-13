import os
import json
from oauthlib.oauth2 import WebApplicationClient

def configure_app(app):
    app.secret_key = 'your_secret_key'  # Set this to a random secret string

    # Load client secrets from file
    CLIENT_SECRETS_FILE = "client_secret.json"

    # Ensure the client secrets file exists
    if not os.path.exists(CLIENT_SECRETS_FILE):
        raise FileNotFoundError(f"Please place your {CLIENT_SECRETS_FILE} file in the same directory as this script.")

    with open(CLIENT_SECRETS_FILE) as client_secret_file:
        CLIENT_CONFIG = json.load(client_secret_file)

    # Update the SCOPES variable to match the granted scopes
    SCOPES = [
        'https://www.googleapis.com/auth/gmail.compose',
        'https://www.googleapis.com/auth/contacts.readonly',
        'https://www.googleapis.com/auth/calendar.readonly',
        'https://www.googleapis.com/auth/calendar',
        'https://www.googleapis.com/auth/gmail.modify'
    ]

    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
    client = WebApplicationClient(CLIENT_CONFIG['web']['client_id'])

    # Add these to app.config for easy access in routes
    app.config['CLIENT_CONFIG'] = CLIENT_CONFIG
    app.config['SCOPES'] = SCOPES
    app.config['CLIENT'] = client
    app.config['CREDENTIALS_DIR'] = os.path.join(app.root_path, 'user_credentials')
