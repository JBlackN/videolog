import io
import json
import random
import re
import time
import urllib
import zipfile

import flask

from yt_archive.auth import auth_check
from yt_archive.db import get_db, update_db
from yt_archive.db import db_get_archived, db_get_archives, db_get_tracks
from yt_archive.db import db_update_archives
from yt_archive.helpers import allowed_file
from yt_archive.youtube import yt_get_subscriptions
from yt_archive.youtube import yt_create_subscription, yt_remove_subscription
from yt_archive.youtube import yt_get_channel, yt_get_channel_videos, yt_get_playlist_items
from yt_archive.youtube import yt_get_video, yt_get_comments
from yt_archive.youtube import yt_create_playlist, yt_rename_playlist
from yt_archive.youtube import yt_insert_to_playlist

def web_index():
    try:
        auth_check()
    except Exception as e:
        return flask.redirect(str(e))

    db_update_archives()

    return flask.redirect('videos')


def web_videos(user = None, tracks = [], subs = [], channel = None, video = None):
    try:
        auth_check()
    except Exception as e:
        return flask.redirect(str(e))

    tracks = db_get_tracks(sort_by_played = True)

    if channel is None:
        if tracks:
            return flask.redirect(flask.url_for('videos', channel = tracks[0]['id']))
        else:
            return flask.render_template('index.html', user = flask.session['user'])
    else:
        if video is None:
            archived = flask.request.args.get('archived', 'null')
            played = flask.request.args.get('played', 'null')
            videos = web_videos_filter(channel, tracks, archived, played)

            return flask.render_template('index.html', user = flask.session['user'],
                tracks = tracks, channel = channel,
                videos = videos, archived = archived, played = played
            )
        elif video == 'random-unplayed':
            return web_videos_random_unplayed(channel)
        elif video == 'next-unplayed':
            return web_videos_next_unplayed(channel)
        elif video == 'random-archived':
            return web_videos_random_archived(channel)
        elif video == 'random-all':
            return web_videos_random_all(channel)
        else:
            return flask.render_template('index.html', user = flask.session['user'],
                tracks = tracks, subs = yt_get_subscriptions(list_only = True),
                channel = channel, video = yt_get_video(video)
            )

def web_videos_filter(channel, tracks, archived, played):
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

    return videos

def web_videos_random_unplayed(channel):
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

def web_videos_next_unplayed(channel):
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

def web_videos_random_archived(channel):
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

def web_videos_random_all(channel):
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

def web_channels(user = None, subs = None, tracks = [], tracking = False, error = False):
    try:
        auth_check()
    except Exception as e:
        return flask.redirect(str(e))

    if 'channels_query_error' in flask.session:
        error = flask.session.pop('channels_query_error')

    return flask.render_template('channels.html', user = flask.session['user'],
        subs = yt_get_subscriptions(list_only = True),
        tracks = db_get_tracks(sort_by_played = False),
        tracking = tracking, error = error)

def web_channels_track(user = None, subs = [], tracks = [], tracking = True, error = False):
    try:
        auth_check()
    except Exception as e:
        return flask.redirect(str(e))

    return flask.render_template('channels.html', user = flask.session['user'],
        subs = yt_get_subscriptions(),
        tracks = db_get_tracks(sort_by_played = None),
        tracking = tracking, error = error)

def web_channels_update():
    try:
        auth_check()
    except Exception as e:
        return flask.redirect(str(e))

    tracks = flask.request.args.get('tracks', None)
    query = flask.request.args.get('query', None)

    if tracks is not None:
        web_channels_update_tracks(tracks)

    if query is not None:
        try:
            web_channels_update_query(query)
        except:
            flask.session['channels_query_error'] = True
            return flask.redirect('channels')

    return flask.redirect('channels')

def web_channels_update_tracks(tracks):
    db = get_db()
    user_id = flask.session['user']['id']

    for channel_id, tracked in json.loads(urllib.parse.unquote(tracks)).items():
        if tracked:
            if channel_id not in db[user_id]:
                db[user_id][channel_id] = {
                    'played': {}, 'archived': {}
                }
        else:
            if channel_id in db[user_id]:
                db[user_id].pop(channel_id)

    update_db(db)

def web_channels_update_query(query):
    db = get_db()
    query_data = json.loads(urllib.parse.unquote(query))
    user_id = flask.session['user']['id']

    if query_data['type'] == 'url':
        url = query_data['value']
        if '/user/' in url:
            user = re.search('^.+\/user\/([^\/]+)(\/.*|$)', url,
                re.IGNORECASE).group(1)
            channel = yt_get_channel('snippet', user = user)
            db[user_id][channel['id']] = {
                'played': {}, 'archived': {}
            }
        elif '/channel/' in url:
            channel_id = url.rsplit('/', 1)[-1]
            channel = yt_get_channel('snippet', channel_id = channel_id)
            db[user_id][channel['id']] = {
                'played': {}, 'archived': {}
            }
        else:
            raise
    elif query_data['type'] == 'user':
        channel = yt_get_channel('snippet', user = query_data['value'])
        db[user_id][channel['id']] = {
            'played': {}, 'archived': {}
        }
    elif query_data['type'] == 'id':
        channel = yt_get_channel('snippet', id = query_data['value'])
        db[user_id][channel['id']] = {
            'played': {}, 'archived': {}
        }

    update_db(db)

def web_channels_subscriptions():
    try:
        auth_check()
    except Exception as e:
        return flask.redirect(str(e))

    update = flask.request.args.get('update', None)

    if update is not None:
        update_data = json.loads(urllib.parse.unquote(update))

        if update_data['subscribe']:
            yt_create_subscription(update_data['id'])
            time.sleep(10)
        else:
            yt_remove_subscription(update_data['id'])
            time.sleep(10)

        return flask.redirect(update_data['redirect'])

    return flask.redirect('channels')

def web_archive():
    try:
        auth_check()
    except Exception as e:
        return flask.redirect(str(e))

    return flask.render_template('archive.html', user = flask.session['user'],
        archives = db_get_archives())

def web_archive_insert_rename(type = None, id = None):
    try:
        auth_check()
    except Exception as e:
        return flask.redirect(str(e))

    if id is not None:
        if type == 'video':
            web_archive_insert_video(id)
        elif type == 'playlist':
            web_archive_import_playlist(id)
        elif type == 'rename':
            web_archive_rename(id, flask.request.args.get('name', None))

    return flask.redirect(flask.url_for('archive'))

def web_archive_insert_video(id):
    db = get_db()
    user_id = flask.session['user']['id']

    video_id = id
    video = yt_get_video(video_id)
    channel_id = video['snippet']['channelId']

    archive = None
    for playlist in db_get_archives():
        if playlist['contentDetails']['itemCount'] < 5000:
            archive = playlist
            break

    if archive is None:
        archive = yt_create_playlist()

    if yt_insert_to_playlist(video_id, archive['id']):
        if channel_id not in db[user_id]:
            db[user_id][channel_id] = {
                'played': {}, 'archived': {}
            }
        db[user_id][channel_id]['archived'][video_id] = archive['id']
        update_db(db)

def web_archive_import_playlist(id):
    db = get_db()
    user_id = flask.session['user']['id']

    for item in yt_get_playlist_items(id):
        video_id = item['snippet']['resourceId']['videoId']
        video = yt_get_video(video_id)
        channel_id = video['snippet']['channelId']

        archive = None
        for playlist in db_get_archives():
            if playlist['contentDetails']['itemCount'] < 5000:
                archive = playlist
                break

        if archive is None:
            archive = yt_create_playlist()

        if yt_insert_to_playlist(video_id, archive['id']):
            if channel_id not in db[user_id]:
                db[user_id][channel_id] = {
                    'played': {}, 'archived': {}
                }
            db[user_id][channel_id]['archived'][video_id] = archive['id']
            update_db(db)

def web_archive_rename(id, name):
    if name is not None:
        yt_rename_playlist(id, name)
        time.sleep(5)

def web_archive_batch():
    try:
        auth_check()
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

def web_archive_comments():
    try:
        auth_check()
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
    return flask.send_file(
        archive_comments, mimetype = 'application/zip',
        as_attachment = True, attachment_filename = 'archive_comments.zip'
    )

def web_archive_config():
    try:
        auth_check()
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
