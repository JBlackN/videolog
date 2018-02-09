import json
import flask

def get_db():
    return json.load(open('db.json'))

def update_db(db):
    with open('db.json', 'w') as f:
        json.dump(db, f, indent = 2, sort_keys = True)

def db_get_tracks(sort_by_played = None):
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
    db = get_db()

    return set([
        video_id
        for channel in db[flask.session['user']['id']].values()
        for video_id in channel['archived'].keys()
    ])

def db_get_video(video_id, channel_id, field = 'played'):
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
