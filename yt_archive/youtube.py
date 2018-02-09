import flask
import google.oauth2.credentials
import googleapiclient.discovery

from yt_archive.constants import API_SERVICE_NAME, API_VERSION
from yt_archive.db import get_db, db_get_archives, db_get_channels
from yt_archive.helpers import build_resource

def yt_get_user():
    client = yt_get_client()
    response = client.channels().list(part = 'snippet', mine = True).execute()
    snippet = response['items'][0]['snippet']
    return {
        'thumbnail': snippet['thumbnails']['default']['url'],
        'name': snippet['title'],
        'id': response['items'][0]['id']
    }

def yt_get_subscriptions(list_only = False):
    client = yt_get_client()
    kwargs = {
        'part': 'snippet', 'mine': True,
        'order': 'alphabetical', 'maxResults': 50
    }

    if list_only:
        items = {}
    else:
        items = []

    while True:
        response = client.subscriptions().list(**kwargs).execute()

        for item in response['items']:
            if list_only:
                items[item['snippet']['resourceId']['channelId']] = item['id']
            else:
                items.append(item)

        if 'nextPageToken' not in response:
            return items
        else:
            kwargs['pageToken'] = response['nextPageToken']

def yt_get_tracks(sort_by_played = False):
    db = get_db()
    tracks = []

    for channel_id in db_get_channels():
        client = yt_get_client()
        response = client.channels().list(
            part = 'snippet,statistics', id = channel_id
        ).execute()

        response['items'][0]['statistics']['videoCount'] = int(
            response['items'][0]['statistics']['videoCount']
        )
        response['items'][0]['statistics']['playedCount'] = len(
            db[flask.session['user']['id']][channel_id]['played']
        )
        response['items'][0]['statistics']['playedPercentage'] = (
            response['items'][0]['statistics']['playedCount'] /
            response['items'][0]['statistics']['videoCount']
        ) * 100
        tracks.append(response['items'][0])

    if sort_by_played:
        return sorted(tracks,
            key = lambda item: (
                -item['statistics']['playedPercentage'],
                item['snippet']['title']
            )
        )
    else:
        return sorted(tracks, key = lambda item: item['snippet']['title'])

def yt_get_channel_videos(channel_id):
    db = get_db()
    client = yt_get_client()
    uploaded_id = client.channels().list(
        part = 'contentDetails', id = channel_id
    ).execute()['items'][0]['contentDetails']['relatedPlaylists']['uploads']

    kwargs = {
        'part': 'snippet', 'playlistId': uploaded_id,
        'maxResults': 50
    }
    items = []

    while True:
        response = client.playlistItems().list(**kwargs).execute()

        for item in response['items']:
            if item['snippet']['resourceId']['videoId'] in db[flask.session['user']['id']][channel_id]['played']:
                item['played'] = db[flask.session['user']['id']][channel_id]['played'][item['snippet']['resourceId']['videoId']]
            else:
                item['played'] = None

            if item['snippet']['resourceId']['videoId'] in db[flask.session['user']['id']][channel_id]['archived']:
                item['archived'] = db[flask.session['user']['id']][channel_id]['archived'][item['snippet']['resourceId']['videoId']]
            else:
                item['archived'] = None

            items.append(item)

        if 'nextPageToken' not in response:
            return items
        else:
            kwargs['pageToken'] = response['nextPageToken']

def yt_get_video(video_id):
    db = get_db()
    client = yt_get_client()
    response = client.videos().list(
        part = 'snippet,contentDetails,statistics,status', id = video_id
    ).execute()

    video = response['items'][0]
    channel_id = video['snippet']['channelId']

    try:
        if video['id'] in db[flask.session['user']['id']][channel_id]['played']:
            video['played'] = db[flask.session['user']['id']][channel_id]['played'][video['id']]
        else:
            video['played'] = None
    except KeyError:
        video['played'] = None

    try:
        if video['id'] in db[flask.session['user']['id']][channel_id]['archived']:
            video['archived'] = db[flask.session['user']['id']][channel_id]['archived'][video['id']]
        else:
            video['archived'] = None
    except KeyError:
        video['archived'] = None

    response2 = client.videos().getRating(
        id = video_id
    ).execute()
    video['rating'] = response2['items'][0]['rating']

    video['playlists'] = {}
    for playlist_id, data in yt_get_playlists().items():
        video['playlists'][playlist_id] = {}
        video['playlists'][playlist_id]['title'] = data['title']
        if video['id'] in data['videos']:
            video['playlists'][playlist_id]['included'] = True
        else:
            video['playlists'][playlist_id]['included'] = False

    video['comments'] = yt_get_comments(video_id)

    return video

def yt_get_playlists():
    client = yt_get_client()
    kwargs = {
        'part': 'snippet', 'mine': True, 'maxResults': 50
    }
    playlists = {}

    while True:
        response = client.playlists().list(**kwargs).execute()

        for playlist in response['items']:
            playlists[playlist['id']] = {
                'title': playlist['snippet']['title'], 'videos': []
            }

        if 'nextPageToken' not in response:
            break
        else:
            kwargs['pageToken'] = response['nextPageToken']

    for playlist_id in playlists.keys():
        kwargs2 = {
            'part': 'contentDetails', 'playlistId': playlist_id,
            'maxResults': 50
        }
        videos = []

        while True:
            response2 = client.playlistItems().list(**kwargs2).execute()

            for video in response2['items']:
                videos.append(video['contentDetails']['videoId'])

            if 'nextPageToken' not in response:
                playlists[playlist_id]['videos'] = videos
                break
            else:
                kwargs2['pageToken'] = response['nextPageToken']

    return playlists

def yt_get_comments(video_id):
    client = yt_get_client()
    kwargs = {
        'part': 'snippet', 'videoId': video_id, 'maxResults': 100
    }
    threads = []

    try:
        while True:
            response = client.commentThreads().list(**kwargs).execute()

            for thread in response['items']:
                threads.append(thread)

            if 'nextPageToken' not in response:
                threads.sort(key = lambda thread: thread['snippet']['topLevelComment']['snippet']['publishedAt'])
                break
            else:
                kwargs['pageToken'] = response['nextPageToken']

        for thread in threads:
            if thread['snippet']['totalReplyCount'] > 0:
                kwargs2 = {
                    'part': 'snippet', 'maxResults': 100,
                    'parentId': thread['snippet']['topLevelComment']['id']
                }
                replies = []

                while True:
                    response2 = client.comments().list(**kwargs2).execute()

                    for reply in response2['items']:
                        replies.append(reply)

                    if 'nextPageToken' not in response:
                        thread['replies'] = {
                            'comments': sorted(replies, key = lambda reply: reply['snippet']['publishedAt'])
                        }
                        break
                    else:
                        kwargs2['pageToken'] = response['nextPageToken']
            else:
                thread['replies'] = { 'comments': [] }
    except:
        return []

    return threads

def yt_get_archive(playlist_id):
    client = yt_get_client()
    response = client.playlists().list(
        part = 'snippet,contentDetails', id = playlist_id, maxResults = 50
    ).execute()

    return response['items'][0]

def yt_create_archive():
    return yt_get_client().playlists().insert(
        body = build_resource({
            'snippet.title': flask.session['user']['name'] + '\'s Archive #' + str(len(db_get_archives()) + 1),
            'status.privacyStatus': 'private'
        }),
        part = 'snippet,status'
    ).execute()

def yt_insert_to_playlist(video_id, playlist_id):
    try:
        yt_get_client().playlistItems().insert(
            body = build_resource({
                'snippet.playlistId': playlist_id,
                'snippet.resourceId.kind': 'youtube#video',
                'snippet.resourceId.videoId': video_id
            }),
            part = 'snippet'
        ).execute()
    except:
        return False

    return True

def yt_remove_from_playlist(video_id, playlist_id):
    client =  yt_get_client()
    kwargs = {
        'part': 'snippet', 'maxResults': 50,
        'playlistId': playlist_id
    }

    while True:
        response = client.playlistItems().list(**kwargs).execute()

        for item in response['items']:
            if item['snippet']['resourceId']['videoId'] == video_id:
                client.playlistItems().delete(id = item['id']).execute()
                return True

        if 'nextPageToken' not in response:
            return False
        else:
            kwargs['pageToken'] = response['nextPageToken']

def yt_get_playlist_items(playlist_id):
    kwargs = {
        'part': 'snippet', 'maxResults': 50,
        'playlistId': playlist_id
    }
    items = []

    while True:
        response = yt_get_client().playlistItems().list(**kwargs).execute()

        for item in response['items']:
            items.append(item)

        if 'nextPageToken' not in response:
            return items
        else:
            kwargs['pageToken'] = response['nextPageToken']

def yt_rename_playlist(playlist_id, name):
    yt_get_client().playlists().update(
        body = build_resource({
            'id': playlist_id,
            'snippet.title': name
        }),
        part = 'snippet'
    ).execute()

def yt_get_client():
    credentials = google.oauth2.credentials.Credentials(
        **flask.session['credentials']
    )

    return googleapiclient.discovery.build(
        API_SERVICE_NAME, API_VERSION, credentials = credentials
    )
