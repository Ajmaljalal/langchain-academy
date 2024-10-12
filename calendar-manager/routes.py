from flask import Blueprint
import handlers

bp = Blueprint('main', __name__)

def register_routes(app):
    bp.route('/', endpoint='index')(handlers.index)
    bp.route('/check_login', endpoint='check_login')(handlers.check_login)
    bp.route('/login', endpoint='login')(lambda: handlers.login(app))
    bp.route('/oauth2callback', endpoint='oauth2callback')(lambda: handlers.oauth2callback(app))
    bp.route('/calendar_events', endpoint='calendar_events')(handlers.calendar_events)
    bp.route('/availabilities', endpoint='availabilities')(handlers.availabilities)
    bp.route('/todays_emails', endpoint='todays_emails')(handlers.todays_emails)
    bp.route('/contacts', endpoint='contacts')(handlers.contacts)
    bp.route('/send_email', methods=['POST'], endpoint='send_email')(handlers.send_email)
    bp.route('/create_event', methods=['POST'], endpoint='create_event')(handlers.create_event)
    # bp.route('/email_manager', methods=['POST'], endpoint='email_manager')(handlers.handle_email_manager)

    app.register_blueprint(bp)
