"""WSGI entry-point for gunicorn / uWSGI."""
import os
from stemquest import create_app

app = create_app(os.environ.get("FLASK_ENV", "production"))
