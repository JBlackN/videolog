import json
import os

import flask
import google.oauth2.credentials
import google_auth_oauthlib.flow
import googleapiclient.discovery
import requests

API_SERVICE_NAME = 'youtube'
API_VERSION = 'v3'
CLIENT_SECRETS_FILE = 'client_secret.json'
SCOPES = ['https://www.googleapis.com/auth/youtube.force-ssl']

app = flask.Flask(__name__)
app.secret_key = b'\xfb\x04\x088E6\xff\xd2\x86\x93\xcef%\x1b\xe6F9`o\xb8\xbd\xc3\xf3['

@app.route('/')
def index(user = None):
    if 'credentials' not in flask.session:
        return flask.redirect('authorize')

    return flask.render_template('index.html', user = flask.session['user'])

@app.route('/channels')
def channels(user = None, items = []):
    if 'credentials' not in flask.session:
        return flask.redirect('authorize')

    return flask.render_template('channels.html', user = flask.session['user'],
        items = yt_get_subscriptions())

def get_db():
    return json.load(open('db.json'))

def update_db(db):
    with open('db.json', 'w') as f:
        json.dump(db, f, indent = 2, sort_keys = True)

def yt_get_user():
    client = yt_get_client()
    response = client.channels().list(part = 'snippet', mine = True).execute()
    snippet = response['items'][0]['snippet']
    return {
        'thumbnail': snippet['thumbnails']['default']['url'],
        'name': snippet['title'],
        'id': response['items'][0]['id']
    }

def yt_get_subscriptions():
    client = yt_get_client()
    kwargs = {
        'part': 'snippet', 'mine': True,
        'order': 'alphabetical', 'maxResults': 50
    }
    items = []
    while True:
        response = client.subscriptions().list(**kwargs).execute()

        for item in response['items']:
            items.append(item)

        if 'nextPageToken' not in response:
            return items
        else:
            kwargs['pageToken'] = response['nextPageToken']

def yt_get_client():
    credentials = google.oauth2.credentials.Credentials(
        **flask.session['credentials']
    )

    return googleapiclient.discovery.build(
        API_SERVICE_NAME, API_VERSION, credentials = credentials
    )

@app.route('/authorize')
def authorize():
    flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE, scopes = SCOPES
    )
    flow.redirect_uri = flask.url_for('oauth2callback', _external = True)

    authorization_url, state = flow.authorization_url(
        access_type = 'offline',
        include_granted_scopes = 'true'
    )

    flask.session['state'] = state

    return flask.redirect(authorization_url)

@app.route('/oauth2callback')
def oauth2callback():
    state = flask.session['state']

    flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE, scopes = SCOPES, state = state
    )
    flow.redirect_uri = flask.url_for('oauth2callback', _external = True)

    authorization_response = flask.request.url
    flow.fetch_token(authorization_response = authorization_response)

    credentials = flow.credentials
    flask.session['credentials'] = {
        'token': credentials.token,
        'refresh_token': credentials.refresh_token,
        'token_uri': credentials.token_uri,
        'client_id': credentials.client_id,
        'client_secret': credentials.client_secret,
        'scopes': credentials.scopes
    }
    flask.session['user'] = yt_get_user()

    db = get_db()
    if flask.session['user']['id'] not in db:
        db[flask.session['user']['id']] = {}
    update_db(db)

    return flask.redirect(flask.url_for('index'))

@app.route('/logout')
def logout():
    flask.session.clear()
    return flask.redirect('')

if __name__ == '__main__':
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1' # TODO: rm in production
    if not os.path.isfile('db.json'):
        with open('db.json', 'w') as f:
            json.dump({}, f, indent = 2, sort_keys = True)
    app.run('localhost', 8090, debug = True)
