import json
import flask

def get_db():
    return json.load(open('db.json'))

def update_db(db):
    with open('db.json', 'w') as f:
        json.dump(db, f, indent = 2, sort_keys = True)

def db_get_channels():
    db = get_db()
    return list(db[flask.session['user']['id']].keys())

def db_get_archives():
    from yt_archive.youtube import yt_get_archive
    db = get_db()
    archive_ids = set()
    archives = []

    for channel in db[flask.session['user']['id']].values():
        archive_ids.update(channel['archived'].values())

    for archive_id in archive_ids:
        archives.append(yt_get_archive(archive_id))

    if archives:
        return sorted(archives,
            key = lambda archive: archive['snippet']['publishedAt']
        )
    else:
        return archives

def db_update_archives():
    from yt_archive.youtube import yt_get_playlist_items, yt_get_video
    db = get_db()
    archived_video_ids_local = db_get_archived()
    archived_video_ids_remote = []
    unarchive_videos = []

    for archive in db_get_archives():
        for video in yt_get_playlist_items(archive['id']):
            if video['snippet']['resourceId']['videoId'] not in archived_video_ids_local:
                video = yt_get_video(video['snippet']['resourceId']['videoId'])
                archived_video_ids_remote.append(video['id'])

                if video['snippet']['channelId'] not in db[flask.session['user']['id']]:
                    db[flask.session['user']['id']][video['snippet']['channelId']] = {
                        'played': {}, 'archived': {}
                    }

                if video['id'] not in db[flask.session['user']['id']][video['snippet']['channelId']]['archived']:
                    db[flask.session['user']['id']][video['snippet']['channelId']]['archived'][video['id']] = archive['id']
            else:
                archived_video_ids_remote.append(video['snippet']['resourceId']['videoId'])

    for channel_id, channel in db[flask.session['user']['id']].items():
        for video_id in channel['archived'].keys():
            if video_id not in archived_video_ids_remote:
                unarchive_videos.append((channel_id, video_id))

    for item in unarchive_videos:
        db[flask.session['user']['id']][item[0]]['archived'].pop(item[1])

    update_db(db)

def db_get_archived():
    db = get_db()

    return set([
        video_id
        for channel in db[flask.session['user']['id']].values()
        for video_id in channel['archived'].keys()
    ])
