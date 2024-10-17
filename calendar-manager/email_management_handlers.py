from flask import request, session, jsonify, current_app
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import logging
from datetime import datetime
from utils import create_message, create_reply_to_email_message, get_credentials
from email_manager_agent import run_email_manager
from werkzeug.wrappers import Response


def todays_emails():
    credentials = get_credentials(current_app, session)
    if credentials is None or isinstance(credentials, Response):
        return jsonify({'error': 'Not logged in'}), 401

    try:
        service = build('gmail', 'v1', credentials=credentials)

        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        now = datetime.now()

        after = int(today_start.timestamp())
        before = int(now.timestamp())

        query = f'after:{after} before:{before} -in:sent'

        results = service.users().messages().list(userId='me', q=query).execute()
        messages = results.get('messages', [])
        
        emails = []
        for message in messages:
            msg = service.users().messages().get(userId='me', id=message['id']).execute()
            headers = msg['payload']['headers']
            subject = next((header['value'] for header in headers if header['name'].lower() == 'subject'), 'No Subject')
            sender = next((header['value'] for header in headers if header['name'].lower() == 'from'), 'Unknown Sender')
            date = next((header['value'] for header in headers if header['name'].lower() == 'date'), 'Unknown Date')
            thread_id = msg['threadId']
            emails.append({
                'message_id': msg['id'],
                'subject': subject,
                'sender': sender,
                'date': date,
                'snippet': msg['snippet'],
                'thread_id': thread_id
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

def reply_email():
    credentials = get_credentials(current_app, session)
    if not credentials:
        return jsonify({'error': 'Not logged in'}), 401

    data = request.json
    thread_id = data.get('thread_id')
    body = data.get('body')
    subject = data.get('subject')
    sender = data.get('sender')
    message_id = data.get('message_id')
    if not all([thread_id, body, subject, sender, message_id]):
        return jsonify({'error': 'Missing required fields'}), 400

    try:
        service = build('gmail', 'v1', credentials=credentials)
        message = create_reply_to_email_message(sender, subject, body, message_id, thread_id)
        sent_message = service.users().messages().send(userId="me", body=message).execute()
        return jsonify({'message': 'Email sent successfully', 'id': sent_message['id']})

    except HttpError as error:
        logging.error(f"An HTTP error occurred: {error}")
        return jsonify({'error': str(error)}), 500
    except Exception as e:
        logging.error(f"Error sending email: {str(e)}")
        return jsonify({'error': str(e)}), 500    

def handle_email_manager():
    credentials = get_credentials(current_app, session)
    if not credentials:
        return jsonify({'error': 'Not logged in'}), 401
    
    data = request.json
    user_input = data.get('input')  # Ensure we're retrieving the correct key
    thread_id = data.get('thread_id', 'default_thread-id')

    if not user_input:
        return jsonify({"error": "User input is required"}), 400

    try:
        result = run_email_manager(user_input, thread_id)
        # Assuming the last message in the result is the AI's response
        if not result:
            logging.warning("No messages returned from email_manager_agent.")
            ai_response = "No response generated."
        else:
            ai_response = result[-1].content if hasattr(result[-1], 'content') else "No response generated."
        
        return jsonify({"response": [ai_response]})  # Wrap response in a list
    except Exception as e:
        return jsonify({"error": str(e)}), 500