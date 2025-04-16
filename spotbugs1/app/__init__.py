"""
SpotBugs1 - A Java Bug Analysis Tool
"""

from app.routes import register_routes
from flask import Flask
__version__ = "0.1.0"

from dotenv import load_dotenv

# Load environment variables at the very beginning
load_dotenv()

# Import function to register blueprints


def create_app():
    """Initialize the Flask app and register all routes."""
    app = Flask(__name__)
    register_routes(app)  # Register blueprints from routes/
    return app


app = create_app()
