from flask import app, request, redirect, session, jsonify, render_template, url_for, abort, current_app
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import logging
from datetime import datetime, timedelta
import pytz
from oauthlib.oauth2.rfc6749.errors import OAuth2Error
from utils import create_message, credentials_to_dict, get_credentials
import json
import os
from email_manager_agent import email_manager_agent
from langchain_core.messages import HumanMessage, AIMessage

def index():
    return render_template('index.html')

def check_login():
    return jsonify({'logged_in': 'credentials' in session})

def login(app):
    flow = Flow.from_client_config(
        client_config=app.config['CLIENT_CONFIG'],
        scopes=app.config['SCOPES']
    )
    flow.redirect_uri = 'http://127.0.0.1:5000/oauth2callback'
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='false',
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
        creds_file_path = os.path.join(current_app.config['CREDENTIALS_DIR'], f'{user_id}_creds.json')
        os.makedirs(os.path.dirname(creds_file_path), exist_ok=True)
        with open(creds_file_path, 'w') as f:
            json.dump(creds_dict, f)
        
        logging.debug(f"Stored credentials in file: {creds_file_path}")

        # Check if all required scopes are present
        granted_scopes = set(credentials.scopes)
        required_scopes = set(current_app.config['SCOPES'])
        
        if not required_scopes.issubset(granted_scopes):
            missing_scopes = required_scopes - granted_scopes
            logging.error(f"Missing required scopes: {missing_scopes}")
            return jsonify({'error': 'Insufficient permissions granted. Please try logging in again.'}), 400

        # Redirect to calendar_events page
        return redirect(url_for('main.calendar_events'))

    except OAuth2Error as e:
        logging.error(f"OAuth2 error in oauth2callback: {str(e)}")
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logging.error(f"Error in oauth2callback: {str(e)}")
        return jsonify({'error': 'An unexpected error occurred. Please try again.'}), 500

def calendar_events():
    credentials = get_credentials(current_app, session)
    if not credentials:
        return jsonify({'error': 'Not logged in'}), 401

    # Get month and year from query parameters, default to current month if not provided
    month = request.args.get('month', datetime.now().month)
    year = request.args.get('year', datetime.now().year)

    # Convert to integers
    month = int(month)
    year = int(year)

    # Calculate start and end of the month
    start_of_month = datetime(year, month, 1).isoformat() + 'Z'
    if month == 12:
        end_of_month = datetime(year + 1, 1, 1) - timedelta(seconds=1)
    else:
        end_of_month = datetime(year, month + 1, 1) - timedelta(seconds=1)
    end_of_month = end_of_month.isoformat() + 'Z'

    service = build('calendar', 'v3', credentials=credentials)

    events_result = service.events().list(calendarId='primary', 
                                          timeMin=start_of_month,
                                          timeMax=end_of_month,
                                          maxResults=1000,  # Increased to ensure all month's events are retrieved
                                          singleEvents=True, 
                                          orderBy='startTime').execute()
    events = events_result.get('items', [])

    formatted_events = [
        {
            'id': event.get('id'),
            'start': event['start'].get('dateTime', event['start'].get('date')),
            'end': event['end'].get('dateTime', event['end'].get('date')),
            'organizer': event.get('organizer', {}).get('displayName'),
            'description': event.get('description', 'No description'),
            'location': event.get('location', 'No location specified'),
            'status': event.get('status', 'unknown'),
            'summary': event.get('summary', 'No summary')
        }
        for event in events
    ]

    return jsonify(formatted_events)

def availabilities():
    credentials = get_credentials(current_app, session)
    if not credentials:
        return jsonify({'error': 'Not logged in'}), 401

    # Get the current month and year
    now = datetime.now()
    year = now.year
    month = now.month

    # Calculate start and end of the month
    start_of_month = datetime(year, month, 1, tzinfo=pytz.UTC)
    if month == 12:
        end_of_month = datetime(year + 1, 1, 1, tzinfo=pytz.UTC) - timedelta(seconds=1)
    else:
        end_of_month = datetime(year, month + 1, 1, tzinfo=pytz.UTC) - timedelta(seconds=1)

    credentials = Credentials(**session['credentials'])
    service = build('calendar', 'v3', credentials=credentials)

    events_result = service.events().list(calendarId='primary', 
                                          timeMin=start_of_month.isoformat(),
                                          timeMax=end_of_month.isoformat(),
                                          singleEvents=True, 
                                          orderBy='startTime').execute()
    events = events_result.get('items', [])

    # Convert events to datetime objects
    busy_times = []
    for event in events:
        start = event['start'].get('dateTime', event['start'].get('date'))
        end = event['end'].get('dateTime', event['end'].get('date'))
        start = datetime.fromisoformat(start.replace('Z', '+00:00'))
        end = datetime.fromisoformat(end.replace('Z', '+00:00'))
        busy_times.append((start, end))
    # Sort busy times
    busy_times.sort(key=lambda x: x[0])
    # Calculate available times
    available_times = []
    current_time = start_of_month
    for busy_start, busy_end in busy_times:
        if current_time < busy_start:
            available_times.append({
                'start': current_time.isoformat(),
                'end': busy_start.isoformat()
            })
        current_time = max(current_time, busy_end)
    if current_time < end_of_month:
        available_times.append({
            'start': current_time.isoformat(),
            'end': end_of_month.isoformat()
          })
    return jsonify(available_times)

def todays_emails():
    # print('todays_emails start')
    credentials = get_credentials(current_app, session)
    # print('todays_emails credentials', credentials)
    if not credentials:
        return jsonify({'error': 'Not logged in'}), 401

    try:
        # # Convert credentials dict to JSON string, then back to dict
        # credentials_dict = json.loads(json.dumps(session['credentials']))
        # credentials = Credentials(**credentials_dict)

        service = build('gmail', 'v1', credentials=credentials)

        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        now = datetime.now()

        after = int(today_start.timestamp())
        before = int(now.timestamp())

        query = f'after:{after} before:{before}'

        results = service.users().messages().list(userId='me', q=query).execute()
        messages = results.get('messages', [])
        
        emails = []
        for message in messages:
            msg = service.users().messages().get(userId='me', id=message['id']).execute()
            headers = msg['payload']['headers']
            subject = next((header['value'] for header in headers if header['name'].lower() == 'subject'), 'No Subject')
            sender = next((header['value'] for header in headers if header['name'].lower() == 'from'), 'Unknown Sender')
            date = next((header['value'] for header in headers if header['name'].lower() == 'date'), 'Unknown Date')
            internal_date = datetime.fromtimestamp(int(msg['internalDate']) / 1000).isoformat()
            emails.append({
                'id': msg['id'],
                'subject': subject,
                'sender': sender,
                'date': date,
                'internal_date': internal_date,
                'snippet': msg['snippet']
            })

        return jsonify({
            'query': query,
            'total_results': results['resultSizeEstimate'],
            'emails': emails
        })

    except HttpError as error:
        logging.error(f"An HTTP error occurred: {error}")
        return jsonify({'error': str(error)}), 500
    except Exception as e:
        logging.error(f"Error fetching emails: {str(e)}")
        return jsonify({'error': str(e)}), 500
    
def contacts():
    credentials = get_credentials(current_app, session)
    if not credentials:
        return jsonify({'error': 'Not logged in'}), 401
    service = build('gmail', 'v1', credentials=credentials)
    results = service.users().messages().list(userId='me', maxResults=500).execute()
    messages = results.get('messages', [])
    contacts = set()
    for message in messages:
        msg = service.users().messages().get(userId='me', id=message['id']).execute()
        headers = msg['payload']['headers']
        for header in headers:
            if header['name'] in ['From', 'To', 'Cc', 'Bcc']:
                emails = header['value'].split(',')
                for email in emails:
                    contacts.add(email.strip())
    return jsonify(list(contacts))

def send_email():
    credentials = get_credentials(current_app, session)
    if not credentials:
        return jsonify({'error': 'Not logged in'}), 401

    try:
        # Convert credentials dict to JSON string, then back to dict
        # credentials_dict = json.loads(json.dumps(session['credentials']))
        # credentials = Credentials(**credentials_dict)

        service = build('gmail', 'v1', credentials=credentials)

        data = request.json
        to = data.get('to')
        subject = data.get('subject')
        body = data.get('body')

        if not all([to, subject, body]):
            return jsonify({'error': 'Missing required fields'}), 400

        message = create_message('me', to, subject, body)
        sent_message = service.users().messages().send(userId='me', body=message).execute()
        return jsonify({'message': 'Email sent successfully', 'id': sent_message['id']})

    except HttpError as error:
        logging.error(f"An HTTP error occurred: {error}")
        return jsonify({'error': str(error)}), 500
    except Exception as e:
        logging.error(f"Error sending email: {str(e)}")
        return jsonify({'error': str(e)}), 500
    
def create_event():
    credentials = get_credentials(current_app, session)
    if not credentials:
        return jsonify({'error': 'Not logged in'}), 401

    try:
        service = build('calendar', 'v3', credentials=credentials)

        data = request.json
        summary = data.get('summary', '').strip()
        start = data.get('start')
        end = data.get('end')
        description = data.get('description', '').strip()
        location = data.get('location', '').strip()
        time_zone = data.get('timeZone', 'UTC')

        if not all([summary, start, end]):
            logging.error(f"Missing required fields. Received: summary={summary}, start={start}, end={end}")
            return jsonify({'error': 'Missing required fields: summary, start, end.'}), 400

        event = {
            'summary': summary,
            'location': location,
            'description': description,
            'start': {'dateTime': start, 'timeZone': time_zone},
            'end': {'dateTime': end, 'timeZone': time_zone},
        }

        logging.debug(f"Attempting to create event with payload: {event}")
        created_event = service.events().insert(calendarId='primary', body=event).execute()
        logging.info(f"Event created successfully: {created_event['id']}")
        return jsonify({'message': 'Event created successfully', 'id': created_event['id']}), 200

    except HttpError as error:
        error_content = error.content.decode()
        logging.error(f"Google Calendar API error: {error_content}")
        return jsonify({'error': error_content}), error.resp.status

    except Exception as e:
        logging.error(f"Unexpected error in create_event: {str(e)}")
        return jsonify({'error': 'An unexpected error occurred.'}), 500
    
def handle_email_manager():
    try:
        data = request.json
        user_input = data.get('input')

        if not user_input:
            return jsonify({'error': 'No input provided'}), 400

        result = email_manager_agent.invoke({
            "messages": [HumanMessage(content=user_input)]
        })

        # Extract the AI's response
        ai_responses = [msg.content for msg in result['messages'] if isinstance(msg, AIMessage)]
        print('ai_responses', ai_responses)
        # Create a serializable version of the result
        serializable_result = {
            'messages': [
                {
                    'type': type(msg).__name__,
                    'content': msg.content
                } for msg in result['messages']
            ]
        }

        return jsonify({
            'response': ai_responses,
            'full_result': serializable_result
        })

    except Exception as e:
        logging.error(f"Error in handle_email_manager: {str(e)}")
        return jsonify({'error': str(e)}), 500
    