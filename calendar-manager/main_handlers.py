from flask import request, redirect, session, jsonify, render_template, url_for, abort
from google_auth_oauthlib.flow import Flow
import logging
from oauthlib.oauth2.rfc6749.errors import OAuth2Error
from utils import credentials_to_dict, get_credentials
import json
import os
from super_manager import run_super_manager
def index():
    return render_template('index.html')

def check_login():
    return jsonify({'logged_in': 'credentials' in session})

def login(app):
    if 'credentials' in session:
        # Check if credentials are still valid
        credentials = get_credentials(app, session)
        if not isinstance(credentials, redirect):
            return redirect(url_for('main.calendar_events'))

    flow = Flow.from_client_config(
        client_config=app.config['CLIENT_CONFIG'],
        scopes=app.config['SCOPES']
    )
    flow.redirect_uri = 'http://127.0.0.1:5000/oauth2callback'
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt='consent'  # Forces the consent screen to appear
    )
    session['state'] = state
    return redirect(authorization_url)

def oauth2callback(app):
    logging.debug(f"Received callback at URL: {request.url}")

    if 'error' in request.args:
        logging.error(f"Error in OAuth callback: {request.args['error']}")
        return jsonify({'error': request.args['error']}), 400

    if 'state' not in session:
        logging.error("No state found in session")
        abort(400, description="No state found in session")

    try:
        state = session['state']
        flow = Flow.from_client_config(
            client_config=app.config['CLIENT_CONFIG'],
            scopes=app.config['SCOPES'],
            state=state
        )
        flow.redirect_uri = 'http://127.0.0.1:5000/oauth2callback'

        # Fetch the token
        flow.fetch_token(authorization_response=request.url)

        # Get credentials
        credentials = flow.credentials
        creds_dict = credentials_to_dict(credentials)
        
        # Store credentials in session
        session['credentials'] = creds_dict
        
        # Save credentials to a local file
        user_id = session.get('user_id', 'default_user')  # You might want to implement user identification
        creds_file_path = os.path.join(app.config['CREDENTIALS_DIR'], f'{user_id}_creds.json')
        os.makedirs(os.path.dirname(creds_file_path), exist_ok=True)
        with open(creds_file_path, 'w') as f:
            json.dump(creds_dict, f)
        
        logging.debug(f"Stored credentials in file: {creds_file_path}")
        logging.debug(f"Granted scopes: {credentials.scopes}")

        # Check if all required scopes are present
        granted_scopes = set(credentials.scopes)
        required_scopes = set(app.config['SCOPES'])
        
        if not required_scopes.issubset(granted_scopes):
            missing_scopes = required_scopes - granted_scopes
            logging.error(f"Missing required scopes: {missing_scopes}")
            return jsonify({'error': 'Insufficient permissions granted. Please try logging in again.'}), 400

        # Redirect to calendar_events page
        return redirect(url_for('main.index'))

    except OAuth2Error as e:
        logging.error(f"OAuth2 error in oauth2callback: {str(e)}")
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logging.error(f"Error in oauth2callback: {str(e)}")
        return jsonify({'error': 'An unexpected error occurred. Please try again.'}), 500

def super_manager(app):
    credentials = get_credentials(app, session)
    if not credentials:
        return jsonify({'error': 'Not logged in'}), 401
    
    if not request.json or 'input' not in request.json or 'thread_id' not in request.json:
        return jsonify({'error': 'Invalid request, user_input and thread_id are required'}), 400
    
    try:
        user_input = request.json.get('input')
        thread_id = request.json.get('thread_id')
        result = run_super_manager(user_input, thread_id)
        if not result:
            ai_response = "Was not able to get a information, sorry!"
        else:
            ai_response = result[-1].content if hasattr(result[-1], 'content') else "No response generated."
        return jsonify({'response': [ai_response]})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

