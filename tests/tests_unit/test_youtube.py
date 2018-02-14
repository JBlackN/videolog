import json

import flask
import flexmock
import google.oauth2.credentials
import googleapiclient.discovery
import pytest

from yt_archive.app import app
from yt_archive.constants import API_SERVICE_NAME, API_VERSION
from yt_archive.helpers import build_resource
from yt_archive.youtube import yt_get_client
from yt_archive.youtube import yt_get_user, yt_get_subscriptions
from yt_archive.youtube import yt_get_channel, yt_get_channel_videos

DB_FIXTURE_PATH = './tests/fixtures/db.json'

def test_yt_get_client():
    import yt_archive.youtube
    (flexmock(yt_archive.youtube)
        .should_call('googleapiclient.discovery.build')
        .with_args(API_SERVICE_NAME, API_VERSION, credentials =
            google.oauth2.credentials.Credentials)
        .and_return(googleapiclient.discovery.Resource))

    with app.test_client() as client:
        with client.session_transaction() as session:
            session['credentials'] = {
                'token': 'test_token'
            }
        client.get('/')
        yt_get_client()

def test_yt_get_user():
    import yt_archive.youtube
    flexmock(yt_archive.youtube, yt_get_client = flexmock(
        channels = lambda: flexmock(
            list = lambda *args, **kwargs: flexmock(
                execute = lambda: json.load(open(
                    './tests/fixtures/youtube/get_user.json'
                ))
            )
        )
    ))

    assert yt_get_user() == {
        'thumbnail': 'https://yt3.ggpht.com/-Fgp8KFpgQqE/AAAAAAAAAAI' +
                     '/AAAAAAAAAAA/Wyh1vV5Up0I/s88-c-k-no-mo-rj-c0xffffff' +
                     '/photo.jpg',
        'name': 'Google Developers',
        'id': 'UC_x5XG1OV2P6uZZ5FSM9Ttw'
    }

def test_yt_get_subscriptions():
    import yt_archive.youtube
    flexmock(yt_archive.youtube, yt_get_client = flexmock(
        subscriptions = lambda: flexmock(
            list = lambda *args, **kwargs: flexmock(
                execute = lambda: (
                    json.load(open('./tests/fixtures/youtube/get_subscriptions_1.json'))
                    if 'pageToken' not in kwargs
                    else json.load(open('./tests/fixtures/youtube/get_subscriptions_2.json'))
                )
            )
        )
    ))

    assert len(yt_get_subscriptions()) == 4
    assert yt_get_subscriptions() == yt_get_subscriptions(list_only = False)
    assert yt_get_subscriptions()[0]['snippet']['resourceId']['channelId'] == (
        'UC1EXoqvR9VrmWnM9S47SfVA')
    assert yt_get_subscriptions(list_only = True) == {
        'UC1EXoqvR9VrmWnM9S47SfVA': 'MpajmvGNexIkHC8F7y2fiSTLzSRwLzqiDEJZG8lxZNQ',
        'UCGg-UqjRgzhYDPJMr-9HXCg': 'MpajmvGNexIo-VllBd2eTP0cR2c_IK9tKnN-JMChPWE',
        'UCH7xyou6RXO8PKwMZ4nQ64Q': 'MpajmvGNexIkHC8F7y2fiVn_Hu_lfY-ZLzRKqVI4dGo',
        'UC1l7wYrva1qCH-wgqcHaaRg': 'MpajmvGNexIkHC8F7y2fiaLMDN6JNxp1K4Jl2GuLQnA'
    }

def test_yt_get_channel():
    import yt_archive.youtube
    flexmock(yt_archive.youtube, yt_get_client = flexmock(
        channels = lambda: flexmock(
            list = lambda *args, **kwargs: flexmock(
                execute = lambda: (
                    json.load(open('./tests/fixtures/youtube/get_channel_id.json'))
                    if 'forUsername' not in kwargs
                    else json.load(open('./tests/fixtures/youtube/get_channel_user.json'))
                )
            )
        )
    ))

    assert (yt_get_channel('snippet', channel_id = 'UC_x5XG1OV2P6uZZ5FSM9Ttw') ==
        yt_get_channel('snippet', user = 'Google Developers')
    )

def test_yt_get_channel_videos():
    import yt_archive.youtube
    flexmock(yt_archive.youtube, yt_get_client = flexmock(
        channels = lambda: flexmock(
            list = lambda *args, **kwargs: flexmock(
                execute = lambda: json.load(open(
                    './tests/fixtures/youtube/get_channel_videos_1.json'
                ))
            )
        ),
        playlistItems = lambda: flexmock(
            list = lambda *args, **kwargs: flexmock(
                execute = lambda: (
                    json.load(open('./tests/fixtures/youtube/get_channel_videos_2.json'))
                    if 'pageToken' not in kwargs
                    else json.load(open('./tests/fixtures/youtube/get_channel_videos_3.json'))
                )
            )
        )
    ))
    flexmock(yt_archive.youtube, db_get_video = None)
    flexmock(yt_archive.youtube, get_db = json.load(open(DB_FIXTURE_PATH)))

    result = yt_get_channel_videos('UC_x5XG1OV2P6uZZ5FSM9Ttw')

    assert len(result) == 4
    for item in result:
        assert item['archived'] is None
        assert item['played'] is None
