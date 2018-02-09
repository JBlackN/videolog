import datetime
import json
import urllib

import flask

from yt_archive.auth import auth_check
from yt_archive.db import get_db, update_db
from yt_archive.db import db_get_archives
from yt_archive.youtube import yt_get_client
from yt_archive.youtube import yt_get_subscriptions
from yt_archive.youtube import yt_get_comments
from yt_archive.youtube import yt_create_playlist
from yt_archive.youtube import yt_insert_to_playlist, yt_remove_from_playlist

def api_video_play(channel = None, video = None):
    try:
        auth_check()
    except Exception as e:
        return flask.jsonify(False)

    if channel is not None and video is not None:
        db = get_db()
        user_id = flask.session['user']['id']

        if video not in db[user_id][channel]['played']:
            db[user_id][channel]['played'][video] = (
                datetime.datetime.utcnow().replace(
                    microsecond = 0, tzinfo = datetime.timezone.utc
                ).isoformat()
            )
            update_db(db)

        return flask.jsonify(True)

def api_video_unplay(channel = None, video = None):
    try:
        auth_check()
    except Exception as e:
        return flask.jsonify(False)

    if channel is not None and video is not None:
        db = get_db()
        if video in db[flask.session['user']['id']][channel]['played']:
            db[flask.session['user']['id']][channel]['played'].pop(video)
            update_db(db)

        return flask.jsonify(True)

def api_video_archive(channel = None, video = None):
    try:
        auth_check()
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
            archive = yt_create_playlist()

        if yt_insert_to_playlist(video, archive['id']):
            db[flask.session['user']['id']][channel]['archived'][video] = archive['id']
            update_db(db)
            return flask.jsonify(True)
        else:
            return flask.jsonify(False)

def api_video_unarchive(channel = None, video = None):
    try:
        auth_check()
    except Exception as e:
        return flask.jsonify(False)

    if channel is not None and video is not None:
        db = get_db()
        user_id = flask.session['user']['id']
        if video in db[user_id][channel]['archived']:
            if yt_remove_from_playlist(
                video, db[user_id][channel]['archived'][video]
            ):
                db[user_id][channel]['archived'].pop(video)
                update_db(db)
            else:
                return flask.jsonify(False)

        return flask.jsonify(True)

def api_video_rate(channel = None, video = None):
    try:
        auth_check()
    except Exception as e:
        return flask.jsonify(False)

    rating = flask.request.args.get('rating', None)

    if channel is not None and video is not None and (
        rating == 'like' or rating == 'dislike' or rating == 'none'
    ):
        yt_get_client().videos().rate(id = video, rating = rating).execute()
        return flask.jsonify(True)

def api_video_playlists(channel = None, video = None):
    try:
        auth_check()
    except Exception as e:
        return flask.jsonify(False)

    data = flask.request.args.get('data', None)

    if channel is not None and video is not None and data is not None:
        for playlist_id, include in json.loads(urllib.parse.unquote(data)).items():
            if include:
                yt_insert_to_playlist(video, playlist_id)
            else:
                yt_remove_from_playlist(video, playlist_id)

        return flask.jsonify(True)

def api_video_subscribe(channel = None, video = None):
    try:
        auth_check()
    except Exception as e:
        return flask.jsonify(False)

    if channel is not None and video is not None:
        if yt_create_subscription(channel):
            return flask.jsonify(True)
        else:
            return flask.jsonify(False)

    return flask.jsonify(False)

def api_video_unsubscribe(channel = None, video = None):
    try:
        auth_check()
    except Exception as e:
        return flask.jsonify(False)

    if channel is not None and video is not None:
        for subscription in yt_get_subscriptions():
            if subscription['snippet']['resourceId']['channelId'] == channel:
                if yt_remove_subscription(subscription['id']):
                    return flask.jsonify(True)
                else:
                    return flask.jsonify(False)

    return flask.jsonify(False)

def api_video_comments(channel = None, video = None):
    try:
        auth_check()
    except Exception as e:
        return flask.jsonify(False)

    if channel is not None and video is not None:
        comments = yt_get_comments(video)

        return flask.Response(json.dumps(comments, indent = 2, sort_keys = True),
            mimetype = 'application/json',
            headers = { 'Content-Disposition': 'attachment;filename=' + video + '.comments.json' }
        )
