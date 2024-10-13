from datetime import datetime
import logging
import base64
from email.mime.text import MIMEText
import json
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
import os
from flask import session, redirect, url_for

def create_message(sender, to, subject, message_text):
    message = MIMEText(message_text)
    message['to'] = to
    message['from'] = sender
    message['subject'] = subject
    raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
    return {'raw': raw_message}

def to_rfc3339(datetime_str):
    try:
        dt = datetime.strptime(datetime_str, "%Y-%m-%dT%H:%M:%SZ")
        return dt.isoformat()
    except ValueError:
        try:
            dt = datetime.strptime(datetime_str, "%Y-%m-%dT%H:%M:%S")
            return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        except ValueError as ve:
            logging.error(f"Invalid datetime format: {ve}")
            return None

def credentials_to_dict(credentials):
    return {
        'token': credentials.token,
        'refresh_token': credentials.refresh_token,
        'token_uri': credentials.token_uri,
        'client_id': credentials.client_id,
        'client_secret': credentials.client_secret,
        'scopes': credentials.scopes
    }

def get_credentials(app, session):
    logging.info("Attempting to get credentials")
    
    # First, try to get credentials from the local file
    user_id = session.get('user_id', 'default_user')
    creds_file_path = os.path.join(app.config['CREDENTIALS_DIR'], f'{user_id}_creds.json')
    
    if os.path.exists(creds_file_path):
        logging.info(f"Found credentials file: {creds_file_path}")
        with open(creds_file_path, 'r') as f:
            credentials_dict = json.load(f)
        credentials = Credentials(**credentials_dict)
    elif 'credentials' in session:
        logging.info("Using credentials from session")
        credentials_dict = session['credentials']
        credentials = Credentials(**credentials_dict)
    else:
        logging.warning("No credentials found in file or session")
        return redirect(url_for('main.login'))

    if credentials and credentials.expired and credentials.refresh_token:
        logging.info("Credentials expired. Attempting to refresh.")
        try:
            credentials.refresh(Request())
            updated_creds_dict = credentials_to_dict(credentials)
            
            # Update both file and session
            with open(creds_file_path, 'w') as f:
                json.dump(updated_creds_dict, f)
            session['credentials'] = updated_creds_dict
            
            logging.info("Credentials refreshed successfully")
        except Exception as e:
            logging.error(f"Error refreshing credentials: {str(e)}")
            # Clear invalid credentials and redirect to login
            if os.path.exists(creds_file_path):
                os.remove(creds_file_path)
            if 'credentials' in session:
                del session['credentials']
            return redirect(url_for('main.login'))

    if not credentials or not credentials.valid:
        logging.warning("Credentials are not valid")
        # Clear invalid credentials and redirect to login
        if os.path.exists(creds_file_path):
            os.remove(creds_file_path)
        if 'credentials' in session:
            del session['credentials']
        return redirect(url_for('main.login'))

    # Ensure the session has the most up-to-date credentials
    session['credentials'] = credentials_to_dict(credentials)
    return credentials
