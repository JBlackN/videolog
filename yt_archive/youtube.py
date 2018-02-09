"""YouTube module

This module contains application's methods for communicating with
    YouTube Data API.
"""

import flask
import google.oauth2.credentials
import googleapiclient.discovery
import googleapiclient.errors

from yt_archive.constants import API_SERVICE_NAME, API_VERSION
from yt_archive.db import get_db, db_get_archives, db_get_video
from yt_archive.helpers import build_resource

def yt_get_client():
    """Gets YouTube API client.

    Obtains client for communicating with YouTube Data API. Uses authenticated
        user's credentials.

    Returns:
        googleapiclient.discovery.Resource: YouTube Data API client.
    """

    credentials = google.oauth2.credentials.Credentials(
        **flask.session['credentials']
    )

    return googleapiclient.discovery.build(
        API_SERVICE_NAME, API_VERSION, credentials = credentials
    )

def yt_get_user():
    """Gets YouTube user information.

    Gets information about authenticated user from YouTube (id, name
        and thumbnail URL).

    Returns:
        dict: Information about authenticated YouTube user.
    """

    try:
        client = yt_get_client()
        response = client.channels().list(part = 'snippet', mine = True).execute()
        snippet = response['items'][0]['snippet']
        return {
            'thumbnail': snippet['thumbnails']['default']['url'],
            'name': snippet['title'],
            'id': response['items'][0]['id']
        }
    except googleapiclient.errors.Error:
        return {
            'thumbnail': '',
            'name': 'Unknown',
            'id': ''
        }

def yt_get_subscriptions(list_only = False):
    """Gets YouTube user's subscriptions.

    Gets YouTube channels to which is authenticated user subscribed, sorted
        alphabetically. Can obtain list (channel and subscription IDs) only.

    Args:
        list_only (bool): Whether to get list only.

    Returns:
        dict or list: Subscribed YouTube channels.
    """

    client = yt_get_client()
    kwargs = {
        'part': 'snippet', 'mine': True,
        'order': 'alphabetical', 'maxResults': 50
    }
    items = {} if list_only else []

    try:
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
    except googleapiclient.errors.Error:
        return {} if list_only else []

def yt_create_subscription(channel_id):
    """Creates YouTube subscription.

    Subscribes authenticated user to given YouTube channel.

    Args:
        channel_id (str): YouTube channel ID.

    Returns:
        bool: Whether operation was succesful.
    """

    try:
        yt_get_client().subscriptions().insert(
            body = build_resource({
                'snippet.resourceId.kind': 'youtube#channel',
                'snippet.resourceId.channelId': channel_id
            }),
            part = 'snippet'
        ).execute()
    except googleapiclient.errors.Error:
        return False

    return True

def yt_remove_subscription(subscription_id):
    """Removes YouTube subscription.

    Unsubscribes authenticated user from given YouTube channel.

    Args:
        subscription_id (str): YouTube subscription ID.

    Returns:
        bool: Whether operation was succesful.
    """

    try:
        client.subscriptions().delete(
            id = subscription_id
        ).execute()
    except googleapiclient.errors.Error:
        return False

    return True

def yt_get_channel(part, channel_id = None, user = None):
    """Gets YouTube channel.

    Gets YouTube channel by its ID or corresponding user name.

    Args:
        part (str): Comma separated list of parts which should YouTube Data API
            return. See `https://developers.google.com/youtube/v3/docs/channels/list#parameters <https://developers.google.com/youtube/v3/docs/channels/list#parameters>`_.
        channel_id (Optional[str]): YouTube channel ID.
        user (Optional[str]): YouTube user name.

    Returns:
        dict: YouTube channel.
    """

    client = yt_get_client()
    response = None

    try:
        if channel_id is not None:
            response = client.channels().list(
                part = part, id = channel_id
            ).execute()
        elif user is not None:
            response = client.channels().list(
                part = part, forUsername = user
            ).execute()
        else:
            return {}
    except googleapiclient.errors.Error:
        return {}

    return response['items'][0]

def yt_get_channel_videos(channel_id):
    """Gets YouTube channel videos.

    Gets all uploaded videos for given YouTube channel. Includes information
        whether they were ``played`` or ``archived`` from the database.

    Args:
        channel_id (str): YouTube channel ID.

    Returns:
        list: YouTube videos uploaded by given channel.
    """

    db = get_db()
    client = yt_get_client()

    try:
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
                video_id = item['snippet']['resourceId']['videoId']

                item['played'] = db_get_video(video_id, channel_id, 'played')
                item['archived'] = db_get_video(video_id, channel_id, 'archived')

                items.append(item)

            if 'nextPageToken' not in response:
                return items
            else:
                kwargs['pageToken'] = response['nextPageToken']
    except googleapiclient.errors.Error:
        return []

def yt_get_video(video_id):
    """Gets YouTube video.

    Gets information about YouTube video including its rating, playlists,
        comments and data from the database (``played``, ``archived``).

    Args:
        video_id (str): YouTube video ID.

    Returns:
        dict: YouTube video.
    """

    db = get_db()
    client = yt_get_client()

    try:
        video = client.videos().list(
            part = 'snippet,contentDetails,statistics,status', id = video_id
        ).execute()['items'][0]
        channel_id = video['snippet']['channelId']

        video['played'] = db_get_video(video['id'], channel_id, 'played')
        video['archived'] = db_get_video(video['id'], channel_id, 'archived')

        video['playlists'] = {}
        video['rating'] = client.videos().getRating(
            id = video_id
        ).execute()['items'][0]['rating']

        for playlist_id, data in yt_get_playlists().items():
            video['playlists'][playlist_id] = {}
            video['playlists'][playlist_id]['title'] = data['title']
            if video['id'] in data['videos']:
                video['playlists'][playlist_id]['included'] = True
            else:
                video['playlists'][playlist_id]['included'] = False

        video['comments'] = yt_get_comments(video_id)
    except googleapiclient.errors.Error:
        return {}

    return video

def yt_get_comments(video_id):
    """Gets YouTube video comments.

    Gets all top level comments and their replies for given YouTube video.

    Args:
        video_id (str): YouTube video ID.

    Returns:
        list: YouTube video comments.

    See also:
        :func:`~yt_archive.youtube.yt_get_comment_replies()`
    """

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
                threads.sort(key = lambda thread: (
                    thread['snippet']['topLevelComment']['snippet']['publishedAt']
                ))
                break
            else:
                kwargs['pageToken'] = response['nextPageToken']

        for thread in threads:
            if thread['snippet']['totalReplyCount'] > 0:
                thread['replies'] = yt_get_comment_replies(
                    thread['snippet']['topLevelComment']['id']
                )
            else:
                thread['replies'] = { 'comments': [] }
    except googleapiclient.errors.Error:
        return []

    return threads

def yt_get_comment_replies(comment_id):
    """Gets YouTube video comment replies.

    Gets all replies to the given YouTube video's top level comment.

    Args:
        comment_id (str): YouTube top level comment ID.

    Returns:
        list: YouTube video comment replies.
    """

    client = yt_get_client()
    kwargs = {
        'part': 'snippet', 'maxResults': 100,
        'parentId': comment_id
    }
    replies = []

    while True:
        response = client.comments().list(**kwargs).execute()

        for reply in response['items']:
            replies.append(reply)

        if 'nextPageToken' not in response:
            return {
                'comments': sorted(
                    replies,
                    key = lambda reply: reply['snippet']['publishedAt']
                )
            }
            break
        else:
            kwargs['pageToken'] = response['nextPageToken']

def yt_get_playlists():
    """Gets YouTube playlists.

    Gets all authenticated user's YouTube playlists in form of
        ``id``: ``{ 'title': ..., 'videos': ... }``.

    Returns:
        dict: YouTube playlists.
    """

    client = yt_get_client()
    kwargs = {
        'part': 'snippet', 'mine': True, 'maxResults': 50
    }
    playlists = {}

    try:
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
            playlists[playlist_id]['videos'] = (
                yt_get_playlist_items(playlist_id, video_ids_only = True)
            )
    except googleapiclient.errors.Error:
        return {}

    return playlists

def yt_get_playlist(playlist_id):
    """Gets YouTube playlist.

    Gets information about single YouTube playlist.

    Returns:
        dict: YouTube playlist.
    """

    client = yt_get_client()

    try:
        response = client.playlists().list(
            part = 'snippet,contentDetails', id = playlist_id, maxResults = 50
        ).execute()
    except googleapiclient.errors.Error:
        return {}

    return response['items'][0]

def yt_get_playlist_items(playlist_id, video_ids_only = False):
    """Gets YouTube playlist's videos.

    Gets videos contained in given YouTube playlist. Can obtain IDs only.

    Args:
        playlist_id (str): YouTube playlist ID.
        video_ids_only (bool): Whether to get IDs only.

    Returns:
        list: YouTube playlist videos or video IDs.
    """

    part = 'contentDetails' if video_ids_only else 'snippet'
    kwargs = {
        'part': part, 'maxResults': 50,
        'playlistId': playlist_id
    }
    items = []

    try:
        while True:
            response = yt_get_client().playlistItems().list(**kwargs).execute()

            for item in response['items']:
                if video_ids_only:
                    items.append(item['contentDetails']['videoId'])
                else:
                    items.append(item)

            if 'nextPageToken' not in response:
                return items
            else:
                kwargs['pageToken'] = response['nextPageToken']
    except googleapiclient.errors.Error:
        return []

def yt_insert_to_playlist(video_id, playlist_id):
    """Inserts YouTube video to playlist.

    Inserts given YouTube video to YouTube playlist.

    Args:
        video_id (str): YouTube video ID.
        playlist_id (str): YouTube playlist ID.

    Returns:
        bool: Whether operation was succesful.
    """

    try:
        yt_get_client().playlistItems().insert(
            body = build_resource({
                'snippet.playlistId': playlist_id,
                'snippet.resourceId.kind': 'youtube#video',
                'snippet.resourceId.videoId': video_id
            }),
            part = 'snippet'
        ).execute()
    except googleapiclient.errors.Error:
        return False

    return True

def yt_remove_from_playlist(video_id, playlist_id):
    """Removes YouTube video from playlist.

    Removes given YouTube video from YouTube playlist.

    Args:
        video_id (str): YouTube video ID.
        playlist_id (str): YouTube playlist ID.

    Returns:
        bool: Whether operation was succesful.
    """

    client =  yt_get_client()
    kwargs = {
        'part': 'snippet', 'maxResults': 50,
        'playlistId': playlist_id
    }

    try:
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
    except googleapiclient.errors.Error:
        return False

def yt_create_playlist():
    """Creates YouTube playlist.

    Creates new YouTube private playlist to be used as application's archive.
        Names it using template: *User's Archive #N*.

    Returns:
        dict: Created YouTube playlist.
    """

    try:
        return yt_get_client().playlists().insert(
            body = build_resource({
                'snippet.title': (
                    flask.session['user']['name'] +
                    '\'s Archive #' +
                    str(len(db_get_archives()) + 1)
                ),
                'status.privacyStatus': 'private'
            }),
            part = 'snippet,status'
        ).execute()
    except googleapiclient.errors.Error:
        return {}

def yt_rename_playlist(playlist_id, name):
    """Renames YouTube playlist.
    """

    try:
        yt_get_client().playlists().update(
            body = build_resource({
                'id': playlist_id,
                'snippet.title': name
            }),
            part = 'snippet'
        ).execute()
    except googleapiclient.errors.Error:
        return {}
