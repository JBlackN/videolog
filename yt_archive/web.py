import datetime
import io
import json
import random
import re
import time
import urllib
import zipfile

import flask
import google_auth_oauthlib.flow
import requests

from yt_archive.constants import CLIENT_SECRETS_FILE, SCOPES
from yt_archive.db import get_db, update_db
from yt_archive.db import db_get_archived, db_get_archives, db_get_channels
from yt_archive.db import db_update_archives
from yt_archive.helpers import allowed_file, build_resource
from yt_archive.youtube import yt_get_client, yt_get_user
from yt_archive.youtube import yt_get_subscriptions, yt_get_tracks
from yt_archive.youtube import yt_get_channel_videos, yt_get_playlist_items
from yt_archive.youtube import yt_get_video, yt_get_comments
from yt_archive.youtube import yt_create_archive, yt_rename_playlist
from yt_archive.youtube import yt_insert_to_playlist, yt_remove_from_playlist

app = flask.Flask(__name__)
app.secret_key = b'\xfb\x04\x088E6\xff\xd2\x86\x93\xcef%\x1b\xe6F9`o\xb8\xbd\xc3\xf3['

@app.route('/')
def index():
    try:
        check_auth()
    except Exception as e:
        return flask.redirect(str(e))

    db_update_archives()

    return flask.redirect('videos')


@app.route('/videos')
@app.route('/videos/<channel>')
@app.route('/videos/<channel>/<video>')
def videos(user = None, tracks = [], subs = [], channel = None, video = None):
    try:
        check_auth()
    except Exception as e:
        return flask.redirect(str(e))

    tracks = yt_get_tracks(sort_by_played = True)

    if channel is None:
        if tracks:
            return flask.redirect(flask.url_for('videos', channel = tracks[0]['id']))
        else:
            return flask.render_template('index.html', user = flask.session['user'])
    else:
        if video is None:
            archived = flask.request.args.get('archived', 'null')
            played = flask.request.args.get('played', 'null')
            videos = []

            if channel == 'all':
                for tracked in tracks:
                    videos.append(yt_get_channel_videos(tracked['id']))
                videos = [
                    item
                    for sublist in videos
                    for item in sublist
                ]
            else:
                videos = yt_get_channel_videos(channel)

            if archived == 'true':
                videos = [
                    video
                    for video in videos
                    if video['archived'] is not None
                ]
            elif archived == 'false':
                videos = [
                    video
                    for video in videos
                    if video['archived'] is None
                ]

            if played == 'true':
                videos = [
                    video
                    for video in videos
                    if video['played'] is not None
                ]
            elif played == 'false':
                videos = [
                    video
                    for video in videos
                    if video['played'] is None
                ]

            return flask.render_template('index.html', user = flask.session['user'],
                tracks = tracks, channel = channel,
                videos = videos, archived = archived, played = played
            )
        elif video == 'random-unplayed':
            try:
                choice = random.choice([
                    video['snippet']['resourceId']['videoId']
                    for video in yt_get_channel_videos(channel)
                    if video['played'] is None
                ])
            except IndexError:
                return flask.redirect(flask.url_for('videos',
                    channel = channel
                ))

            return flask.redirect(flask.url_for('videos',
                channel = channel, video = choice
            ))
        elif video == 'next-unplayed':
            try:
                choice = sorted([
                    video
                    for video in yt_get_channel_videos(channel)
                    if video['played'] is None
                ], key = lambda video: video['snippet']['publishedAt'])[0]
            except IndexError:
                return flask.redirect(flask.url_for('videos',
                    channel = channel
                ))

            return flask.redirect(flask.url_for('videos',
                channel = channel, video = choice['snippet']['resourceId']['videoId']
            ))
        elif video == 'random-archived':
            try:
                choice = random.choice([
                    video['snippet']['resourceId']['videoId']
                    for video in yt_get_channel_videos(channel)
                    if video['archived'] is not None
                ])
            except IndexError:
                return flask.redirect(flask.url_for('videos',
                    channel = channel
                ))

            return flask.redirect(flask.url_for('videos',
                channel = channel, video = choice)
            )
        elif video == 'random-all':
            try:
                choice = random.choice([
                    video['snippet']['resourceId']['videoId']
                    for video in yt_get_channel_videos(channel)
                ])
            except IndexError:
                return flask.redirect(flask.url_for('videos',
                    channel = channel
                ))

            return flask.redirect(flask.url_for('videos',
                channel = channel, video = choice)
            )
        else:
            return flask.render_template('index.html', user = flask.session['user'],
                tracks = tracks, subs = yt_get_subscriptions(list_only = True),
                channel = channel, video = yt_get_video(video)
            )

@app.route('/channels')
def channels(user = None, subs = None, tracks = [], tracking = False, error = False):
    try:
        check_auth()
    except Exception as e:
        return flask.redirect(str(e))

    if 'channels_query_error' in flask.session:
        error = flask.session.pop('channels_query_error')

    return flask.render_template('channels.html', user = flask.session['user'],
        subs = yt_get_subscriptions(list_only = True), tracks = yt_get_tracks(),
        tracking = tracking, error = error)

@app.route('/channels-track')
def channels_track(user = None, subs = [], tracks = [], tracking = True, error = False):
    try:
        check_auth()
    except Exception as e:
        return flask.redirect(str(e))

    return flask.render_template('channels.html', user = flask.session['user'],
        subs = yt_get_subscriptions(), tracks = db_get_channels(),
        tracking = tracking, error = error)

@app.route('/channels-update')
def channels_update():
    try:
        check_auth()
    except Exception as e:
        return flask.redirect(str(e))

    db = get_db()
    tracks = flask.request.args.get('tracks', None)
    query = flask.request.args.get('query', None)

    if tracks is not None:
        for channel_id, tracked in json.loads(urllib.parse.unquote(tracks)).items():
            if tracked:
                if channel_id not in db[flask.session['user']['id']]:
                    db[flask.session['user']['id']][channel_id] = {
                        'played': {}, 'archived': {}
                    }
            else:
                if channel_id in db[flask.session['user']['id']]:
                    db[flask.session['user']['id']].pop(channel_id)

    if query is not None:
        client = yt_get_client()
        query_data = json.loads(urllib.parse.unquote(query))

        try:
            if query_data['type'] == 'url':
                url = query_data['value']
                if '/user/' in url:
                    user = re.search('^.+\/user\/([^\/]+)(\/.*|$)', url, re.IGNORECASE).group(1)
                    response = client.channels().list(
                        part = 'snippet', forUsername = user
                    ).execute()
                    db[flask.session['user']['id']][response['items'][0]['id']] = {
                        'played': {}, 'archived': {}
                    }
                elif '/channel/' in url:
                    channel_id = url.rsplit('/', 1)[-1]
                    response = client.channels().list(
                        part = 'snippet', id = channel_id
                    ).execute()
                    db[flask.session['user']['id']][response['items'][0]['id']] = {
                        'played': {}, 'archived': {}
                    }
                else:
                    raise
            elif query_data['type'] == 'user':
                response = client.channels().list(
                    part = 'snippet', forUsername = query_data['value']
                ).execute()
                db[flask.session['user']['id']][response['items'][0]['id']] = {
                    'played': {}, 'archived': {}
                }
            elif query_data['type'] == 'id':
                response = client.channels().list(
                    part = 'snippet', id = query_data['value']
                ).execute()
                db[flask.session['user']['id']][response['items'][0]['id']] = {
                    'played': {}, 'archived': {}
                }
        except:
            flask.session['channels_query_error'] = True
            return flask.redirect('channels')

    update_db(db)

    return flask.redirect('channels')

@app.route('/channels-subscriptions')
def channels_subscriptions():
    try:
        check_auth()
    except Exception as e:
        return flask.redirect(str(e))

    client = yt_get_client()
    update = flask.request.args.get('update', None)

    if update is not None:
        update_data = json.loads(urllib.parse.unquote(update))

        if update_data['subscribe']:
            client.subscriptions().insert(
                body = build_resource({
                    'snippet.resourceId.kind': 'youtube#channel',
                    'snippet.resourceId.channelId': update_data['id']
                }),
                part = 'snippet'
            ).execute()
        else:
            client.subscriptions().delete(
                id = update_data['id']
            ).execute()

        time.sleep(10)
        return flask.redirect(update_data['redirect'])

    return flask.redirect('channels')

@app.route('/archive')
def archive():
    try:
        check_auth()
    except Exception as e:
        return flask.redirect(str(e))

    return flask.render_template('archive.html', user = flask.session['user'],
        archives = db_get_archives())

@app.route('/archive/<type>/<id>')
def archive_insert_rename(type = None, id = None):
    try:
        check_auth()
    except Exception as e:
        return flask.redirect(str(e))

    db = get_db()

    if id is not None:
        if type == 'video':
            video_id = id
            video = yt_get_video(video_id)

            archive = None
            for playlist in db_get_archives():
                if playlist['contentDetails']['itemCount'] < 5000:
                    archive = playlist
                    break

            if archive is None:
                archive = yt_create_archive()

            if yt_insert_to_playlist(video_id, archive['id']):
                if video['snippet']['channelId'] not in db[flask.session['user']['id']]:
                    db[flask.session['user']['id']][video['snippet']['channelId']] = {
                        'played': {}, 'archived': {}
                    }
                db[flask.session['user']['id']][video['snippet']['channelId']]['archived'][video_id] = archive['id']
                update_db(db)
        elif type == 'playlist':
            for item in yt_get_playlist_items(id):
                video_id = item['snippet']['resourceId']['videoId']
                video = yt_get_video(video_id)

                archive = None
                for playlist in db_get_archives():
                    if playlist['contentDetails']['itemCount'] < 5000:
                        archive = playlist
                        break

                if archive is None:
                    archive = yt_create_archive()

                if yt_insert_to_playlist(video_id, archive['id']):
                    if video['snippet']['channelId'] not in db[flask.session['user']['id']]:
                        db[flask.session['user']['id']][video['snippet']['channelId']] = {
                            'played': {}, 'archived': {}
                        }
                    db[flask.session['user']['id']][video['snippet']['channelId']]['archived'][video_id] = archive['id']
                    update_db(db)
        elif type == 'rename':
            name = flask.request.args.get('name', None)
            if name is not None:
                yt_rename_playlist(id, name)
                time.sleep(5)

    return flask.redirect(flask.url_for('archive'))

@app.route('/archive/batch', methods = ['POST'])
def archive_batch():
    try:
        check_auth()
    except Exception as e:
        return flask.redirect(str(e))

    batch = set()

    if 'archiveFile' in flask.request.files:
        file = flask.request.files['archiveFile']
        if file.filename != '':
            if file and allowed_file(file.filename):
                downloaded = [
                    line.decode('utf-8').rstrip('\n').split(' ')[1]
                    for line in file.readlines()
                ]
                archived = db_get_archived()

                for video_id in archived:
                    if video_id not in downloaded:
                        batch.add(video_id)
    else:
        archived = db_get_archived()

        for video_id in archived:
            batch.add(video_id)

    return flask.Response('\n'.join(list(batch)),
        mimetype = 'text/plain',
        headers = { 'Content-Disposition': 'attachment;filename=batch.txt' }
    )

@app.route('/archive/comments')
def archive_comments():
    try:
        check_auth()
    except Exception as e:
        return flask.redirect(str(e))

    archive_comments = io.BytesIO()

    with zipfile.ZipFile(archive_comments, 'w') as zf:
        for video_id in db_get_archived():
            video = yt_get_video(video_id)
            comments = yt_get_comments(video_id)

            zf.writestr(
                video['snippet']['channelId'] + '/' + video_id + '.comments.json',
                json.dumps(comments, indent = 2, sort_keys = True)
              )

    archive_comments.seek(0)
    return flask.send_file(archive_comments, mimetype = 'application/zip', as_attachment = True, attachment_filename = 'archive_comments.zip')

@app.route('/archive/config')
def archive_config():
    try:
        check_auth()
    except Exception as e:
        return flask.redirect(str(e))

    socket_timeout = flask.request.args.get('ytdl-socket-timeout', '120')
    retries = flask.request.args.get('ytdl-retries', 'infinite')
    output = flask.request.args.get('ytdl-output', '%(uploader_id)s/%(id)s.%(ext)s')
    overwrites = flask.request.args.get('ytdl-overwrites', 'false') == 'true'
    info_json = flask.request.args.get('ytdl-info-json', 'true') == 'true'
    thumbnail = flask.request.args.get('ytdl-thumbnail', 'true') == 'true'
    format = flask.request.args.get('ytdl-format', 'bestvideo[vcodec^=vp]' +
             '+bestaudio[acodec=opus]/bestvideo+bestaudio[acodec=opus]' +
             '/bestvideo+bestaudio/best')
    merge_format = flask.request.args.get('ytdl-merge-format', 'mkv')
    all_subs = flask.request.args.get('ytdl-all-subs', 'true') == 'true'
    sub_format = flask.request.args.get('ytdl-sub-format', 'srt/best')
    convert_subs = flask.request.args.get('ytdl-convert-subs', 'srt')

    config = io.BytesIO()

    config.write(('--socket-timeout ' + socket_timeout + '\n').encode('utf-8'))
    config.write(('--retries ' + retries + '\n').encode('utf-8'))
    config.write(('--output ' + output + '\n').encode('utf-8'))
    if not overwrites:
        config.write('--no-overwrites\n'.encode('utf-8'))
    if info_json:
        config.write('--write-info-json\n'.encode('utf-8'))
    if thumbnail:
        config.write('--write-thumbnail\n'.encode('utf-8'))
    config.write(('--format ' + format + '\n').encode('utf-8'))
    config.write(('--merge-output-format ' + merge_format + '\n').encode('utf-8'))
    if all_subs:
        config.write('--all-subs\n'.encode('utf-8'))
    config.write(('--sub-format ' + sub_format + '\n').encode('utf-8'))
    config.write(('--convert-subs ' + convert_subs + '\n').encode('utf-8'))

    config.seek(0)

    return flask.Response(config,
        mimetype = 'text/plain',
        headers = { 'Content-Disposition': 'attachment;filename=config.txt' }
    )

@app.route('/api/videos/<channel>/<video>/play')
def video_play(channel = None, video = None):
    try:
        check_auth()
    except Exception as e:
        return flask.jsonify(False)

    if channel is not None and video is not None:
        db = get_db()
        if video not in db[flask.session['user']['id']][channel]['played']:
            db[flask.session['user']['id']][channel]['played'][video] = datetime.datetime.utcnow().replace(microsecond = 0, tzinfo = datetime.timezone.utc).isoformat();
            update_db(db)

        return flask.jsonify(True)

@app.route('/api/videos/<channel>/<video>/unplay')
def video_unplay(channel = None, video = None):
    try:
        check_auth()
    except Exception as e:
        return flask.jsonify(False)

    if channel is not None and video is not None:
        db = get_db()
        if video in db[flask.session['user']['id']][channel]['played']:
            db[flask.session['user']['id']][channel]['played'].pop(video)
            update_db(db)

        return flask.jsonify(True)

@app.route('/api/videos/<channel>/<video>/archive')
def video_archive(channel = None, video = None):
    try:
        check_auth()
    except Exception as e:
        return flask.jsonify(False)

    if channel is not None and video is not None:
        db = get_db()
        archive = None
        for playlist in db_get_archives():
            if playlist['contentDetails']['itemCount'] < 5000:
                archive = playlist
                break

        if archive is None:
            archive = yt_create_archive()

        if yt_insert_to_playlist(video, archive['id']):
            db[flask.session['user']['id']][channel]['archived'][video] = archive['id']
            update_db(db)
            return flask.jsonify(True)
        else:
            return flask.jsonify(False)

@app.route('/api/videos/<channel>/<video>/unarchive')
def video_unarchive(channel = None, video = None):
    try:
        check_auth()
    except Exception as e:
        return flask.jsonify(False)

    if channel is not None and video is not None:
        db = get_db()
        if video in db[flask.session['user']['id']][channel]['archived']:
            if yt_remove_from_playlist(video, db[flask.session['user']['id']][channel]['archived'][video]):
                db[flask.session['user']['id']][channel]['archived'].pop(video)
                update_db(db)
            else:
                return flask.jsonify(False)

        return flask.jsonify(True)

@app.route('/api/videos/<channel>/<video>/rate')
def video_rate(channel = None, video = None):
    try:
        check_auth()
    except Exception as e:
        return flask.jsonify(False)

    rating = flask.request.args.get('rating', None)

    if channel is not None and video is not None and (
        rating == 'like' or rating == 'dislike' or rating == 'none'
    ):
        yt_get_client().videos().rate(id = video, rating = rating).execute()
        return flask.jsonify(True)

@app.route('/api/videos/<channel>/<video>/playlists')
def video_playlists(channel = None, video = None):
    try:
        check_auth()
    except Exception as e:
        return flask.jsonify(False)

    data = flask.request.args.get('data', None)

    if channel is not None and video is not None and data is not None:
        client = yt_get_client()

        for playlist_id, include in json.loads(urllib.parse.unquote(data)).items():
            if include:
                client.playlistItems().insert(
                    body = build_resource({
                        'snippet.playlistId': playlist_id,
                        'snippet.resourceId.kind': 'youtube#video',
                        'snippet.resourceId.videoId': video
                    }),
                    part = 'snippet'
                ).execute()
            else:
                kwargs = {
                    'part': 'snippet', 'maxResults': 50,
                    'playlistId': playlist_id
                }

                while True:
                    response = client.playlistItems().list(**kwargs).execute()

                    for item in response['items']:
                        if item['snippet']['resourceId']['videoId'] == video:
                            client.playlistItems().delete(id = item['id']).execute()
                            break

                    if 'nextPageToken' not in response:
                        break
                    else:
                        kwargs['pageToken'] = response['nextPageToken']

        return flask.jsonify(True)

@app.route('/api/videos/<channel>/<video>/subscribe')
def video_subscribe(channel = None, video = None):
    try:
        check_auth()
    except Exception as e:
        return flask.jsonify(False)

    if channel is not None and video is not None:
        yt_get_client().subscriptions().insert(
            body = build_resource({
                'snippet.resourceId.kind': 'youtube#channel',
                'snippet.resourceId.channelId': channel
            }),
            part = 'snippet'
        ).execute()

        return flask.jsonify(True)

@app.route('/api/videos/<channel>/<video>/unsubscribe')
def video_unsubscribe(channel = None, video = None):
    try:
        check_auth()
    except Exception as e:
        return flask.jsonify(False)

    if channel is not None and video is not None:
        for subscription in yt_get_subscriptions():
            if subscription['snippet']['resourceId']['channelId'] == channel:
                yt_get_client().subscriptions().delete(
                    id = subscription['id']
                ).execute()

        return flask.jsonify(True)

@app.route('/api/videos/<channel>/<video>/comments')
def video_comments(channel = None, video = None):
    try:
        check_auth()
    except Exception as e:
        return flask.jsonify(False)

    if channel is not None and video is not None:
        comments = yt_get_comments(video)

        return flask.Response(json.dumps(comments, indent = 2, sort_keys = True),
            mimetype = 'application/json',
            headers = { 'Content-Disposition': 'attachment;filename=' + video + '.comments.json' }
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

def check_auth():
    if 'credentials' not in flask.session:
        raise Exception('authorize')
    else:
        if 'token' in flask.session['credentials']:
            base_url = 'https://www.googleapis.com/oauth2/v3/tokeninfo?access_token='
            response = requests.get(base_url + flask.session['credentials']['token'])
            if response.status_code == 400:
                raise Exception('logout')
        else:
            raise Exception('logout')

@app.route('/logout')
def logout():
    flask.session.clear()
    return flask.redirect('')
