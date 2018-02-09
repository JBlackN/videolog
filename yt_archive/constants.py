"""Constants module

This module contains constants for use by other modules.

Attributes:
    API_SERVICE_NAME (str): YouTube Data API service name.
    API_VERSION (str): YouTube Data API version.
    CLIENT_SECRETS_FILE (str): Name of the file containing Google application
        client secret.
    SCOPES (str): YouTube Data API scopes used by the application.
"""

API_SERVICE_NAME = 'youtube'
API_VERSION = 'v3'
CLIENT_SECRETS_FILE = 'client_secret.json'
SCOPES = ['https://www.googleapis.com/auth/youtube.force-ssl']
