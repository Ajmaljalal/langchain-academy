from flask import request, session, jsonify, current_app
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import logging
from datetime import datetime
import pytz
from utils import get_credentials
from calendar_manager_agent import run_calendar_manager

def get_calendar_events():
    credentials = get_credentials(current_app, session)
    if not credentials:
        return jsonify({'error': 'Not logged in'}), 401

    try:
        now = datetime.now()
        day = request.args.get('day', type=int)
        month = request.args.get('month', type=int)
        year = request.args.get('year', type=int)

        if day is None:
            day = now.day
        if month is None:
            month = now.month
        if year is None:
            year = now.year

        # Define user's local timezone (modify as needed)
        user_timezone = pytz.timezone('America/New_York')  # Replace with user's actual timezone

        start_of_day = user_timezone.localize(datetime(year, month, day, 0, 0, 0))
        end_of_day = user_timezone.localize(datetime(year, month, day, 23, 59, 59))

        # Convert to ISO 8601 format with timezone information
        start_of_day_iso = start_of_day.isoformat()
        end_of_day_iso = end_of_day.isoformat()

        logging.debug(f"Fetching events from {start_of_day_iso} to {end_of_day_iso}")

        service = build('calendar', 'v3', credentials=credentials)

        events_result = service.events().list(
            calendarId='primary',
            timeMin=start_of_day_iso,
            timeMax=end_of_day_iso,
            maxResults=1000,
            singleEvents=True,
            orderBy='startTime'
        ).execute()

        events = events_result.get('items', [])
        print('events:', events)
        if not events:
            logging.info("No events found for the specified date.")
            return jsonify({'message': 'No events found for the specified date.'}), 200

        formatted_events = [
            {
                'id': event.get('id'),
                'start': event['start'].get('dateTime', event['start'].get('date')),
                'end': event['end'].get('dateTime', event['end'].get('date')),
                'organizer': event.get('organizer', {}).get('email'),
                'creator': event.get('creator', {}).get('email'),
                'am_i_organizing': event.get('creator', {}).get('self'),
                'location': event.get('location', 'No location specified'),
                'status': event.get('status', 'unknown'),
                'summary': event.get('summary', 'No summary')
            }
            for event in events
        ]

        logging.info(f"Retrieved {len(formatted_events)} events.")
        return jsonify(formatted_events), 200

    except HttpError as error:
        error_content = error.content.decode() if error.content else str(error)
        logging.error(f"Google Calendar API error: {error_content}")
        return jsonify({'error': f'Google Calendar API error: {error_content}'}), error.resp.status

    except Exception as e:
        logging.error(f"Unexpected error in get_calendar_events: {str(e)}")
        return jsonify({'error': 'An unexpected error occurred.'}), 500

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

def get_availabilities():
    credentials = get_credentials(current_app, session)
    if not credentials:
        return jsonify({'error': 'Not logged in'}), 401

    try:

        day = request.args.get('day', type=int)
        month = request.args.get('month', type=int)
        year = request.args.get('year', type=int)

        now = datetime.now()

        if day is None:
            day = now.day
        if month is None:
            month = now.month
        if year is None:
            year = now.year

        # Define user's local timezone (modify as needed)
        user_timezone = pytz.timezone('America/New_York')  # Replace with user's actual timezone

        # Create timezone-aware datetime objects for start and end of the day
        start_of_day = user_timezone.localize(datetime(year, month, day, 0, 0, 0))
        end_of_day = user_timezone.localize(datetime(year, month, day, 23, 59, 59))

        # Convert to ISO 8601 format with timezone information
        start_of_day_iso = start_of_day.isoformat()
        end_of_day_iso = end_of_day.isoformat()

        service = build('calendar', 'v3', credentials=credentials)

        events_result = service.events().list(
            calendarId='primary',
            timeMin=start_of_day_iso,
            timeMax=end_of_day_iso,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        events = events_result.get('items', [])

        # Convert events to datetime objects
        busy_times = []
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            end = event['end'].get('dateTime', event['end'].get('date'))
            start = datetime.fromisoformat(start.replace('Z', '+00:00')).astimezone(user_timezone)
            end = datetime.fromisoformat(end.replace('Z', '+00:00')).astimezone(user_timezone)
            busy_times.append((start, end))

        # Sort busy times
        busy_times.sort(key=lambda x: x[0])

        # Calculate available times
        available_times = []
        current_time = start_of_day
        for busy_start, busy_end in busy_times:
            if current_time < busy_start:
                available_times.append({
                    'start': current_time.isoformat(),
                    'end': busy_start.isoformat()
                })
            current_time = max(current_time, busy_end)
        if current_time < end_of_day:
            available_times.append({
                'start': current_time.isoformat(),
                'end': end_of_day.isoformat()
            })

        return jsonify(available_times), 200

    except HttpError as error:
        error_content = error.content.decode() if error.content else str(error)
        logging.error(f"Google Calendar API error: {error_content}")
        return jsonify({'error': f'Google Calendar API error: {error_content}'}), error.resp.status

    except Exception as e:
        logging.error(f"Unexpected error in get_availabilities: {str(e)}")
        return jsonify({'error': 'An unexpected error occurred.'}), 500

def handle_calendar_manager():
    credentials = get_credentials(current_app, session)
    if not credentials:
        return jsonify({'error': 'Not logged in'}), 401

    data = request.json
    user_input = data.get('input')
    thread_id = data.get('thread_id', 'default_thread')

    if not user_input:
        return jsonify({"error": "User input is required"}), 400

    try:
        result = run_calendar_manager(user_input, thread_id)
        if not result:
            logging.warning("No messages returned from calendar_manager_agent.")
            ai_response = "No response generated."
        else:
            ai_response = result[-1].content if hasattr(result[-1], 'content') else "No response generated."
        
        return jsonify({"response": [ai_response]})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
