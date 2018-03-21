import base64
import os
import requests
import uritools
import webbrowser

from urllib.parse import urlencode, unquote, urlparse
from clef import app

CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
if not CLIENT_ID:
  raise Exception('SPOTIFY_CLIENT_ID environment variable not set.')

CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
if not CLIENT_SECRET:
  raise Exception('SPOTIFY_CLIENT_SECRET environment variable not set.')

ENCODED_AUTHENTICATION = base64.b64encode(bytes(CLIENT_ID + ':' + CLIENT_SECRET, 'utf-8')).decode('ascii')

SCOPE = "playlist-read-private user-library-read user-read-email user-read-playback-state user-modify-playback-state user-read-currently-playing user-read-recently-played"

def get_auth_url(auth_callback_uri, state = None):
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

def authorize_me(auth_callback_uri = 'http://localhost:5000/authorized'):
    auth_url = get_auth_url(auth_callback_uri)
    webbrowser.open(auth_url).start()

def get_auth_token_from_redirect_url(url):
    """Utility function that gets an auth token from a url that spotify
    redirected to after the above get_auth_url was pasted into a
    browser. This makes it easier to play with interactively. Just call
    this with the url in your browser after the redirect."""
    result = uritools.urisplit(url)
    parsed = urlparse(url)
    auth_callback_uri = '%s://%s%s' % (parsed.scheme, parsed.netloc, parsed.path)
    code = result.getquerydict()['code'][0]
    return get_auth_token(code, auth_callback_uri)

def get_auth_token(auth_code, auth_callback_uri):
    """Given a Spotify Auth Code, get a token to use in Spotify API calls.
       Returns (HTTP response code, result).
    """
    app.logger.info('requesting token for authorization code %s, callback %s' % (auth_code, auth_callback_uri))
    headers = {'Authorization': 'Basic ' + ENCODED_AUTHENTICATION}
    data = {'grant_type': 'authorization_code',
            'code': auth_code,
            'redirect_uri': auth_callback_uri}
    resp = requests.post('https://accounts.spotify.com/api/token', headers=headers, data=data)
    json = resp.json()
    result = None

    if resp.status_code != 200:
        app.logger.error('failed to get token: %s' % json)
        # TODO: Need a refresh_access_token that doesn't use a User instance
        #        if json['error_description'] == 'Authorization code expired':
        #            refresh_access_token
        result = 'Failed to get token.'
        if 'error_description' in json:
            result = json['error_description']
    else:
        result = json

    return resp.status_code, result

def refresh_user_access_token(user):
    """Call this after an access token has expired to renew it."""
    headers = {'Authorization': 'Basic ' + ENCODED_AUTHENTICATION}
    data = {'grant_type': 'refresh_token',
            'refresh_token': user.refresh_token}
    app.logger.debug('Refreshing token for %s' % user.id)
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

def _get_json(user, url, params={}, data = {}):
    """Generic GET using the spotify API."""
    headers = {'Authorization': 'Bearer ' + user.access_token}
    app.logger.debug('Spotify Request: %s' % url)
    resp = requests.get(url, headers=headers, params=params, data=data)
    if resp.status_code == 200:
        return 200, resp.json()

    json = resp.json()
    if 'error' in json and 'message' in json['error']:
      if 'The access token expired' == json['error']['message']:
          refresh_user_access_token(user)
          app.logger.debug('Spotify Request: %s' % url)
          return _get_json(user, url, data)

    return resp.status_code, json

#
# Methods below here use the User class from the user module.
#

def get_playlists(user, offset=0, limit=20):
    """Gets all of the current user's playlists (not including tracks).
       see: https://developer.spotify.com/web-api/get-a-list-of-current-users-playlists/
    """

    # TODO: Automatically page these using yield - spotify limits you
    # to 20 playlists per page. This would be a lot easier to use if
    # it just did the paging for you, using yield.
    params = {'limit': str(limit), 'offset': str(offset)}
    app.logger.debug("limit: %s, offset: %s" % (limit, offset))
    return _get_json(user, 'https://api.spotify.com/v1/users/%s/playlists' % user.id, params=params)

def get_all_playlists(user):
    offset = 0
    limit = 20
    status, json = get_playlists(user, 0, limit)
    if status != 200: return []

    app.logger.debug("Next page: %s" % json['next'])
    accum = list(json['items'])
    total = json['total']
    while status == 200:
        offset += limit
        if offset > total: break
        count = min(total-offset, limit)
        app.logger.debug("requesting playlists %s - %s" % (offset, offset+count))
        status, json = get_playlists(user, offset, count)
        app.logger.debug("Next page: %s" % json['next'])
        if status == 200: accum += json['items']

    return accum

def get_playlist(user, playlist_url):
    """Gets a specific playlist.
       see: https://developer.spotify.com/web-api/get-a-list-of-current-users-playlists/
    """
    return _get_json(user, playlist_url)

def get_playlist_tracks(user, playlist):
    """Gets the tracks associated with a playlist."""
    url = playlist.tracks_url
    code, json = _get_json(user, url)
    return code, json

def get_all_playlist_tracks(user, playlist):
    offset = 0
    limit = 20
    status, json = get_playlists(user, 0, limit)
    if status != 200: return []

    app.logger.debug("Next page: %s" % json['next'])
    accum = list(json['items'])
    total = json['total']
    while status == 200:
        offset += limit
        if offset > total: break
        count = min(total-offset, limit)
        app.logger.debug("requesting playlists %s - %s" % (offset, offset+count))
        status, json = get_playlists(user, offset, count)
        app.logger.debug("Next page: %s" % json['next'])
        if status == 200: accum += json['items']

    return accum
