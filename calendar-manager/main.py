from flask import Flask
import logging

from flask_cors import CORS
from config import configure_app
from routes import register_routes


# Set up logging
logging.basicConfig(level=logging.DEBUG)

def create_app():
    app = Flask(__name__)
    CORS(app)
    configure_app(app)
    register_routes(app)
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=True)