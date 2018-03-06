import base64
import os
import requests
import uritools
import webbrowser

from urllib.parse import urlencode, unquote

CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
if not CLIENT_ID:
  raise Exception('SPOTIFY_CLIENT_ID environment variable not set.')

CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
if not CLIENT_SECRET:
  raise Exception('SPOTIFY_CLIENT_SECRET environment variable not set.')

ENCODED_AUTHENTICATION = base64.b64encode(bytes(CLIENT_ID + ':' + CLIENT_SECRET, 'utf-8')).decode('ascii')

SCOPE = "playlist-read-private user-library-read user-read-email user-read-playback-state user-modify-playback-state user-read-currently-playing user-read-recently-played"

auth_callback_uri = 'http://localhost:5000/authorized'

def get_auth_url(state = None):
    """Gets the url to redirect a user to, in order to login to spotify
    and give us access."""
    if not state:
        state = base64.b64encode(os.urandom(64)).decode('ascii')

    params = urlencode({'client_id': CLIENT_ID,
                        'response_type': 'code',
                        'redirect_uri': auth_callback_uri,
                        'state': state,
                        'scope': SCOPE})

    return 'https://accounts.spotify.com/authorize/?' + params

def authorize_me():
    auth_url = get_auth_url()
    webbrowser.open(auth_url).start()

def get_auth_token_from_redirect_url(url):
    """Utility function that gets an auth token from a url that spotify
    redirected to after the above get_auth_url was pasted into a
    browser. This makes it easier to play with interactively. Just call
    this with the url in your browser after the redirect."""
    result = uritools.urisplit(url)
    code = result.getquerydict()['code'][0]
    return get_auth_token(code)

def get_auth_token(auth_code):
    """Given a Spotify Auth Code, get a token to use in Spotify API calls.
       Returns (HTTP response code, result).
    """
    headers = {'Authorization': 'Basic ' + ENCODED_AUTHENTICATION}
    data = {'grant_type': 'authorization_code',
            'code': auth_code,
            'redirect_uri': auth_callback_uri}
    resp = requests.post('https://accounts.spotify.com/api/token', headers=headers, data=data)
    json = resp.json()
    result = None

    if resp.status_code != 200:
        result = 'Failed to get token.'
        if 'error_description' in json:
            result = json['error_description']
    else:
        result = json

    return resp.status_code, result

def refresh_access_token(user):
    """Call this after an access token has expired to renew it."""
    headers = {'Authorization': 'Basic ' + ENCODED_AUTHENTICATION}
    data = {'grant_type': 'refresh_token',
            'refresh_token': user.refresh_token}
    resp = requests.post('https://accounts.spotify.com/api/token', headers=headers, data=data)
    json = resp.json()
    result = None

    if resp.status_code != 200:
        result = 'Failed to get token.'
        if 'error_description' in json:
            result = json['error_description']
    else:
        result = json
        user.token_refreshed(result)

    return resp.status_code, result

def get_user(token):
    headers = {'Authorization': 'Bearer ' + token}
    resp = requests.get('https://api.spotify.com/v1/me', headers=headers)
    result = None
    if resp.status_code != 200:
        result = 'Failed'
    else:
        result = resp.json()

    return resp.status_code, result

def _get_json(user, url, data = {}):
    """Generic GET using the spotify API."""
    headers = {'Authorization': 'Bearer ' + user.access_token}
    resp = requests.get(url, headers=headers, data=data)
    if resp.status_code == 200:
        return 200, resp.json()

    return resp.status_code, resp

def get_playlists(user, limit=50, offset=0):
    """Gets all of the current user's playlists (not including tracks).
       see: https://developer.spotify.com/web-api/get-a-list-of-current-users-playlists/
    """
    data={'limit': str(limit), 'offset': str(offset)}
    return _get_json(user, 'https://api.spotify.com/v1/me/playlists', data)

def get_playlist(user, playlist_url):
    """Gets a specific playlist.
       see: https://developer.spotify.com/web-api/get-a-list-of-current-users-playlists/
    """
    return _get_json(user, playlist_url)
