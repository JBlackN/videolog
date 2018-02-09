import flask

from yt_archive.api import api_video_play, api_video_unplay
from yt_archive.api import api_video_archive, api_video_unarchive
from yt_archive.api import api_video_rate, api_video_playlists, api_video_comments
from yt_archive.api import api_video_subscribe, api_video_unsubscribe
from yt_archive.auth import auth_authorize, auth_oauth2callback
from yt_archive.auth import auth_check, auth_logout
from yt_archive.web import web_index
from yt_archive.web import web_videos
from yt_archive.web import web_channels, web_channels_track
from yt_archive.web import web_channels_update, web_channels_subscriptions
from yt_archive.web import web_archive, web_archive_insert_rename
from yt_archive.web import web_archive_batch, web_archive_comments
from yt_archive.web import web_archive_config

app = flask.Flask(__name__)
app.secret_key = b'\xfb\x04\x088E6\xff\xd2\x86\x93\xcef%\x1b\xe6F9`o\xb8\xbd\xc3\xf3['

@app.route('/')
def index():
    return web_index()

@app.route('/videos')
@app.route('/videos/<channel>')
@app.route('/videos/<channel>/<video>')
def videos(user = None, tracks = [], subs = [], channel = None, video = None):
    return web_videos(user, tracks, subs, channel, video)

@app.route('/channels')
def channels(user = None, subs = None, tracks = [], tracking = False, error = False):
    return web_channels(user, subs, tracks, tracking, error)

@app.route('/channels-track')
def channels_track(user = None, subs = [], tracks = [], tracking = True, error = False):
    return web_channels_track(user, subs, tracks, tracking, error)

@app.route('/channels-update')
def channels_update():
    return web_channels_update()

@app.route('/channels-subscriptions')
def channels_subscriptions():
    return web_channels_subscriptions()

@app.route('/archive')
def archive():
    return web_archive()

@app.route('/archive/<type>/<id>')
def archive_insert_rename(type = None, id = None):
    return web_archive_insert_rename(type, id)

@app.route('/archive/batch', methods = ['POST'])
def archive_batch():
    return web_archive_batch()

@app.route('/archive/comments')
def archive_comments():
    return web_archive_comments()

@app.route('/archive/config')
def archive_config():
    return web_archive_config()

@app.route('/api/videos/<channel>/<video>/play')
def video_play(channel = None, video = None):
    return api_video_play(channel, video)

@app.route('/api/videos/<channel>/<video>/unplay')
def video_unplay(channel = None, video = None):
    return api_video_unplay(channel, video)

@app.route('/api/videos/<channel>/<video>/archive')
def video_archive(channel = None, video = None):
    return api_video_archive(channel, video)

@app.route('/api/videos/<channel>/<video>/unarchive')
def video_unarchive(channel = None, video = None):
    return api_video_unarchive(channel, video)

@app.route('/api/videos/<channel>/<video>/rate')
def video_rate(channel = None, video = None):
    return api_video_rate(channel, video)

@app.route('/api/videos/<channel>/<video>/playlists')
def video_playlists(channel = None, video = None):
    return api_video_playlists(channel, video)

@app.route('/api/videos/<channel>/<video>/subscribe')
def video_subscribe(channel = None, video = None):
    return api_video_subscribe(channel, video)

@app.route('/api/videos/<channel>/<video>/unsubscribe')
def video_unsubscribe(channel = None, video = None):
    return api_video_unsubscribe(channel, video)

@app.route('/api/videos/<channel>/<video>/comments')
def video_comments(channel = None, video = None):
    return api_video_comments(channel, video)

@app.route('/authorize')
def authorize():
    return auth_authorize()

@app.route('/oauth2callback')
def oauth2callback():
    return auth_oauth2callback()

@app.route('/logout')
def logout():
    return auth_logout()
