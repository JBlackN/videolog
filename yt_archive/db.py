"""DB module

This module contains methods to work with application's simple JSON database.
"""

import json
import flask

def get_db():
    """Gets database.

    Loads database from JSON file.

    Returns:
        dict: JSON database object.
    """

    return json.load(open('db.json'))

def update_db(db):
    """Updates database.

    Saves database updates back to the JSON file.

    Args:
        dict: JSON database object.
    """
    with open('db.json', 'w') as f:
        json.dump(db, f, indent = 2, sort_keys = True)

def db_get_tracks(sort_by_played = None):
    """Gets tracked channels.

    Gets tracked channels from the database, either list of YouTube channel IDs
        or list of entire objects with optional sorting by played percentage and
        channel title.

    Args:
        sort_by_played (bool): Whether to sort by played percentage. Can also
            be ``None``: then return list of IDs only.

    Returns:
        list: Tracked channels or their IDs.
    """

    from yt_archive.youtube import yt_get_channel
    db = get_db()

    if sort_by_played is None:
        return list(db[flask.session['user']['id']].keys())
    else:
        tracks = []

        for channel_id in db_get_tracks(sort_by_played = None):
            channel = yt_get_channel('snippet,statistics', channel_id = channel_id)

            channel['statistics']['videoCount'] = int(
                channel['statistics']['videoCount']
            )
            channel['statistics']['playedCount'] = len(
                db[flask.session['user']['id']][channel_id]['played']
            )
            channel['statistics']['playedPercentage'] = (
                channel['statistics']['playedCount'] /
                channel['statistics']['videoCount']
            ) * 100

            tracks.append(channel)

        if sort_by_played:
            return sorted(tracks,
                key = lambda item: (
                    -item['statistics']['playedPercentage'],
                    item['snippet']['title']
                )
            )
        else:
            return sorted(tracks, key = lambda item: item['snippet']['title'])

def db_get_archives():
    """Gets archives.

    Gets list of archives from the database sorted by date and time created.

    Returns:
        list: YouTube archives (playlist objects).
    """

    from yt_archive.youtube import yt_get_playlist
    db = get_db()
    archive_ids = set()
    archives = []

    for channel in db[flask.session['user']['id']].values():
        archive_ids.update(channel['archived'].values())

    for archive_id in archive_ids:
        archives.append(yt_get_playlist(archive_id))

    if archives:
        return sorted(archives,
            key = lambda archive: archive['snippet']['publishedAt']
        )
    else:
        return archives

def db_update_archives():
    """Synchronizes archives with YouTube.

    Synchronizes archives in the database with respective YouTube playlists.
        Works bidirectionally.
    """

    from yt_archive.youtube import yt_get_playlist_items, yt_get_video
    db = get_db()
    user_id = flask.session['user']['id']

    archived_video_ids_local = db_get_archived()
    archived_video_ids_remote = []
    unarchive_videos = []

    for archive in db_get_archives():
        for video in yt_get_playlist_items(archive['id']):
            video_id = video['snippet']['resourceId']['videoId']
            if video_id not in archived_video_ids_local:
                video = yt_get_video(video_id)
                channel_id = video['snippet']['channelId']
                archived_video_ids_remote.append(video['id'])

                if channel_id not in db[user_id]:
                    db[user_id][channel_id] = {
                        'played': {}, 'archived': {}
                    }

                if video['id'] not in db[user_id][channel_id]['archived']:
                    db[user_id][channel_id]['archived'][video['id']] = archive['id']
            else:
                archived_video_ids_remote.append(video_id)

    for channel_id, channel in db[user_id].items():
        for video_id in channel['archived'].keys():
            if video_id not in archived_video_ids_remote:
                unarchive_videos.append((channel_id, video_id))

    for item in unarchive_videos:
        db[user_id][item[0]]['archived'].pop(item[1])

    update_db(db)

def db_get_archived():
    """Gets archived video IDs.

    Gets archived YouTube video IDs from the database.

    Returns:
        set: Archived YouTube video IDs.
    """

    db = get_db()

    return set([
        video_id
        for channel in db[flask.session['user']['id']].values()
        for video_id in channel['archived'].keys()
    ])

def db_get_video(video_id, channel_id, field = 'played'):
    """Gets video metadata.

    Gets information whether (when, where) video was played or archived
        from the database.

    Args:
        video_id (str): YouTube video ID.
        channel_id (str): YouTube channel ID.
        field (Optional[str]): ``played`` or ``archived``.

    Returns:
        str: ISO8601 timestamp, YouTube playlist ID or ``None``.
    """

    db = get_db()
    user_id = flask.session['user']['id']

    if field == 'played' or field == 'archived':
        try:
            if video_id in db[user_id][channel_id][field]:
                return db[user_id][channel_id][field][video_id]
            else:
                return None
        except KeyError:
            return None
