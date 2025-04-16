from flask import Blueprint

from .routes import api_bp


# List of Blueprints
blueprints = [api_bp]


def register_routes(app):
    """Register all blueprints (route handlers) with the Flask app."""
    for bp in blueprints:
        app.register_blueprint(bp)

