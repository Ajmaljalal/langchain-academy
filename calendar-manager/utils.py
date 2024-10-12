from datetime import datetime
import logging
import base64
from email.mime.text import MIMEText
import json
from google.oauth2.credentials import Credentials
import os

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

def get_credentials_from_session(session):
    if 'credentials' not in session:
        return None
    
    credentials_dict = session['credentials']
    
    # Ensure all values are strings
    credentials_dict = {k: str(v) if v is not None else None for k, v in credentials_dict.items()}
    
    # Handle 'scopes' conversion
    if 'scopes' in credentials_dict:
        try:
            if isinstance(credentials_dict['scopes'], str):
                credentials_dict['scopes'] = json.loads(credentials_dict['scopes'])
        except json.JSONDecodeError:
            # If 'scopes' is not a valid JSON string, assume it's already a list
            if isinstance(credentials_dict['scopes'], str):
                credentials_dict['scopes'] = [s.strip() for s in credentials_dict['scopes'].split(',')]
    
    return Credentials(
        token=credentials_dict.get('token'),
        refresh_token=credentials_dict.get('refresh_token'),
        token_uri=credentials_dict.get('token_uri'),
        client_id=credentials_dict.get('client_id'),
        client_secret=credentials_dict.get('client_secret'),
        scopes=credentials_dict.get('scopes')
    )

def get_credentials(app, session):
    if 'credentials' in session:
        return get_credentials_from_session(session)
    user_id = session.get('user_id', 'default_user')
    creds_file_path = os.path.join(app.config['CREDENTIALS_DIR'], f'{user_id}_creds.json')
    if os.path.exists(creds_file_path):
        try:
            with open(creds_file_path, 'r') as f:
                creds_dict = json.load(f)
                session['credentials'] = creds_dict # Update session with file contents
                return get_credentials_from_session(session)
        except (IOError, json.JSONDecodeError) as e:
            logging.error(f"Error reading credentials file {creds_file_path}: {e}")
            return None
    return None