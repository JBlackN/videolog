import pytest
from videolog.helpers import build_resource, allowed_file

def test_build_resource():
    assert build_resource({}) == {}
    assert build_resource({
        'snippet.playlistId': 'playlist_id',
        'snippet.resourceId.kind': 'youtube#video',
        'snippet.resourceId.videoId': 'video_id'
    }) == {
        'snippet': {
            'playlistId': 'playlist_id',
            'resourceId': {
                'kind': 'youtube#video',
                'videoId': 'video_id'
            }
        }
    }

@pytest.mark.parametrize('filename', (
    'a', 'b.txt', 'c.html', 'd.htm', 'e.xhtml', 'f.php'
))
def test_allowed_file(filename):
    if filename in ['a', 'b.txt']:
        assert allowed_file(filename) == True
    else:
        assert allowed_file(filename) == False
