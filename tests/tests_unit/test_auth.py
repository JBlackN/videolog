import flask
import flexmock
import pytest
import requests

from videolog.app import app
from videolog.auth import auth_check

def test_auth_check_credentials():
    import videolog.auth
    with app.test_client() as client:
        with client.session_transaction() as session:
            session.clear()
        client.get('/')

        with pytest.raises(Exception) as e:
            auth_check()
        assert str(e.value) == 'authorize'

def test_auth_check_grant():
    import videolog.auth
    flexmock(requests, get = flexmock(status_code = 400))
    with app.test_client() as client:
        with client.session_transaction() as session:
            session['credentials'] = {
                'token': 'test_token'
            }
        client.get('/')

        with pytest.raises(Exception) as e:
            auth_check()
        assert str(e.value) == 'logout'

def test_auth_check_token():
    import videolog.auth
    with app.test_client() as client:
        with client.session_transaction() as session:
            session['credentials'] = {}
        client.get('/')

        with pytest.raises(Exception) as e:
            auth_check()
        assert str(e.value) == 'logout'
