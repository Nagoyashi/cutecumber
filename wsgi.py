"""WSGI entrypoint.

Dev:   flask --app wsgi run --debug
Prod:  gunicorn -w 1 'wsgi:app'
"""

from app import create_app

app = create_app()
