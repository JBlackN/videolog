import io
import json

import builtins
import flexmock
import pytest

from videolog.db import get_db, update_db
from videolog.db import db_get_tracks

DB_FIXTURE_PATH = './tests/fixtures/db.json'

@pytest.fixture
def testapp():
    from videolog.app import app
    app.config['TESTING'] = True
    return app.test_client()

def test_get_db():
    flexmock(builtins, open = open(DB_FIXTURE_PATH))
    assert get_db() == {
      'user_id': {
        'channel_id': {
          'archived': {
            'video_id': 'playlist_id'
          },
          'played': {
            'video_id': 'timestamp'
          }
        }
      }
    }

def test_update_db():
    db = json.load(open(DB_FIXTURE_PATH))
    storage = io.StringIO()

    flexmock(builtins, open = storage)
    flexmock(storage, close = True)

    db['user_id']['channel_id']['played']['video_id'] = 'modified'
    update_db(db)

    assert json.loads(storage.getvalue()) == {
      'user_id': {
        'channel_id': {
          'archived': {
            'video_id': 'playlist_id'
          },
          'played': {
            'video_id': 'modified'
          }
        }
      }
    }
    storage.close()

def test_db_get_tracks():
    with testapp() as client:
        with client.session_transaction() as session:
            session['user'] = { 'id': 'user_id' }

        #assert session['user']['id'] == 'user_id2'
        client.get('/')
        import videolog.db
        flexmock(videolog.db, get_db = json.load(open(DB_FIXTURE_PATH)))
        assert db_get_tracks() == db_get_tracks(sort_by_played = None)

        #with app.app_context():
        #    assert db_get_tracks() == True
    #assert db_get_tracks() == db_get_tracks(sort_by_played = None)
