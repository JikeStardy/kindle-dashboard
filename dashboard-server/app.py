"""Flask app entry point for Gunicorn (app:app)."""
from app import create_app

app = create_app()
