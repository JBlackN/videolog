"""App module

This module contains the Flask application and its routes.

Attributes:
    app (flask.Flask): Flask application.
"""

import flask

from videolog.api import api_video_play, api_video_unplay
from videolog.api import api_video_archive, api_video_unarchive
from videolog.api import api_video_rate, api_video_playlists, api_video_comments
from videolog.api import api_video_subscribe, api_video_unsubscribe
from videolog.auth import auth_authorize, auth_oauth2callback
from videolog.auth import auth_check, auth_logout
from videolog.web import web_index
from videolog.web import web_videos
from videolog.web import web_channels, web_channels_track
from videolog.web import web_channels_update, web_channels_subscriptions
from videolog.web import web_archive, web_archive_insert_rename
from videolog.web import web_archive_batch, web_archive_comments
from videolog.web import web_archive_config

app = flask.Flask(__name__)
app.secret_key = b'\xfb\x04\x088E6\xff\xd2\x86\x93\xcef%\x1b\xe6F9`o\xb8\xbd\xc3\xf3['

@app.route('/')
def index():
    """Index route.

    Returns index page.

    See also:
        :func:`~videolog.web.web_index()`
    """

    return web_index()

@app.route('/videos')
@app.route('/videos/<channel>')
@app.route('/videos/<channel>/<video>')
def videos(user = None, tracks = [], subs = [], channel = None, video = None):
    """Videos route.

    Renders video list or detail view.

    See also:
        :func:`~videolog.web.web_videos()`
    """

    return web_videos(user, tracks, subs, channel, video)

@app.route('/channels')
def channels(user = None, subs = None, tracks = [], tracking = False, error = False):
    """Channels route.

    Renders channel management page.

    See also:
        :func:`~videolog.web.web_channels()`
    """

    return web_channels(user, subs, tracks, tracking, error)

@app.route('/channels-track')
def channels_track(user = None, subs = [], tracks = [], tracking = True, error = False):
    """Channels track route.

    Renders tracking using connected YouTube account page.

    See also:
        :func:`~videolog.web.web_channels_track()`
    """

    return web_channels_track(user, subs, tracks, tracking, error)

@app.route('/channels-update')
def channels_update():
    """Channels update route.

    Handles channel tracking updates.

    See also:
        :func:`~videolog.web.web_channels_update()`
    """

    return web_channels_update()

@app.route('/channels-subscriptions')
def channels_subscriptions():
    """Channels subscriptions route.

    Handles updates to channel subscriptions.

    See also:
        :func:`~videolog.web.web_channels_subscriptions()`
    """

    return web_channels_subscriptions()

@app.route('/archive')
def archive():
    """Archive route.

    Renders archive management page.

    See also:
        :func:`~videolog.web.web_archive()`
    """

    return web_archive()

@app.route('/archive/<type>/<id>')
def archive_insert_rename(type = None, id = None):
    """Archive insert or rename route.

    Handles archive management.

    See also:
        :func:`~videolog.web.web_archive_insert_rename()`
    """

    return web_archive_insert_rename(type, id)

@app.route('/archive/batch', methods = ['POST'])
def archive_batch():
    """Archive batch route.

    Handles archive batch file for youtube-dl generation.

    See also:
        :func:`~videolog.web.web_archive_batch()`
    """

    return web_archive_batch()

@app.route('/archive/comments')
def archive_comments():
    """Archive comments route.

    Handles archived videos comments download.

    See also:
        :func:`~videolog.web.web_archive_comments()`
    """

    return web_archive_comments()

@app.route('/archive/config')
def archive_config():
    """Archive configuration route.

    Handles youtube-dl configuration generation.

    See also:
        :func:`~videolog.web.web_archive_config()`
    """

    return web_archive_config()

@app.route('/api/videos/<channel>/<video>/play')
def video_play(channel = None, video = None):
    """API play video route.

    Handles marking video as played.

    See also:
        :func:`~videolog.api.api_video_play()`
    """

    return api_video_play(channel, video)

@app.route('/api/videos/<channel>/<video>/unplay')
def video_unplay(channel = None, video = None):
    """API unplay video route.

    Handles marking video as unplayed.

    See also:
        :func:`~videolog.api.api_video_unplay()`
    """

    return api_video_unplay(channel, video)

@app.route('/api/videos/<channel>/<video>/archive')
def video_archive(channel = None, video = None):
    """API archive video route.

    Handles video archiving.

    See also:
        :func:`~videolog.api.api_video_archive()`
    """

    return api_video_archive(channel, video)

@app.route('/api/videos/<channel>/<video>/unarchive')
def video_unarchive(channel = None, video = None):
    """API unarchive video route.

    Handles video unarchiving.

    See also:
        :func:`~videolog.api.api_video_unarchive()`
    """

    return api_video_unarchive(channel, video)

@app.route('/api/videos/<channel>/<video>/rate')
def video_rate(channel = None, video = None):
    """API rate video route.

    Handles video rating.

    See also:
        :func:`~videolog.api.api_video_rate()`
    """

    return api_video_rate(channel, video)

@app.route('/api/videos/<channel>/<video>/playlists')
def video_playlists(channel = None, video = None):
    """API video playlists route.

    Handles updating video's playlists.

    See also:
        :func:`~videolog.api.api_video_playlists()`
    """

    return api_video_playlists(channel, video)

@app.route('/api/videos/<channel>/<video>/subscribe')
def video_subscribe(channel = None, video = None):
    """API video subscribe route.

    Handles subscribing to video's channel.

    See also:
        :func:`~videolog.api.api_video_subscribe()`
    """

    return api_video_subscribe(channel, video)

@app.route('/api/videos/<channel>/<video>/unsubscribe')
def video_unsubscribe(channel = None, video = None):
    """API video unsubscribe route.

    Handles unsubscribing from video's channel.

    See also:
        :func:`~videolog.api.api_video_unsubscribe()`
    """

    return api_video_unsubscribe(channel, video)

@app.route('/api/videos/<channel>/<video>/comments')
def video_comments(channel = None, video = None):
    """API video comments route.

    Returns video's comments.

    See also:
        :func:`~videolog.api.api_video_comments()`
    """

    return api_video_comments(channel, video)

@app.route('/authorize')
def authorize():
    """Authorization route.

    Redirects to Google authorization page.

    See also:
        :func:`~videolog.auth.auth_authorize()`
    """

    return auth_authorize()

@app.route('/oauth2callback')
def oauth2callback():
    """OAuth 2.0 callback route.

    Completes authorization process and redirects to index.

    See also:
        :func:`~videolog.auth.auth_oauth2callback()`
    """

    return auth_oauth2callback()

@app.route('/logout')
def logout():
    """Logout route.

    Logs user out of the application.

    See also:
        :func:`~videolog.auth.auth_logout()`
    """

    return auth_logout()
