from flask import Blueprint
import email_management_handlers
import calendar_management_handlers

import main_handlers

bp = Blueprint('main', __name__)

def register_routes(app):

    ###### main routes ######
    bp.route('/', endpoint='index')(main_handlers.index)
    bp.route('/check_login', endpoint='check_login')(main_handlers.check_login)
    bp.route('/login', endpoint='login')(lambda: main_handlers.login(app))
    bp.route('/oauth2callback', endpoint='oauth2callback')(lambda: main_handlers.oauth2callback(app))
    bp.route('/super_manager', methods=['POST'], endpoint='super_manager')(lambda: main_handlers.super_manager(app))


    ###### calender management routes ######
    bp.route('/calendar_events', endpoint='calendar_events')(calendar_management_handlers.get_calendar_events)
    bp.route('/availabilities', endpoint='availabilities')(calendar_management_handlers.get_availabilities)
    bp.route('/create_event', methods=['POST'], endpoint='create_event')(calendar_management_handlers.create_event)
    bp.route('/calendar_manager', methods=['POST'], endpoint='calendar_manager')(calendar_management_handlers.handle_calendar_manager)


    ###### email management routes ######
    bp.route('/todays_emails', endpoint='todays_emails')(email_management_handlers.todays_emails)
    bp.route('/send_email', methods=['POST'], endpoint='send_email')(email_management_handlers.send_email)
    bp.route('/reply_email', methods=['POST'], endpoint='reply_email')(email_management_handlers.reply_email)
    bp.route('/email_manager', methods=['POST'], endpoint='email_manager')(email_management_handlers.handle_email_manager)
    bp.route('/contacts', endpoint='contacts')(email_management_handlers.contacts)

    app.register_blueprint(bp)
