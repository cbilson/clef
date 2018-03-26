import base64
import json
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
        app.logger.error('failed to renew access token: %s' % json)
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
    app.logger.debug('Spotify Request: %s, params: %s' % (url, params))
    resp = requests.get(url, headers=headers, params=params, data=data)
    if resp.status_code == 200:
        return 200, resp.json()

    app.logger.debug('Result: %s, %s' % (resp.status_code, resp.json()))
    json = resp.json()
    if 'error' in json and 'message' in json['error']:
      if 'The access token expired' == json['error']['message']:
          refresh_user_access_token(user)
          app.logger.debug('Spotify Request: %s, params: %s' % (url, params))
          return _get_json(user, url, params=params, data=data)

    return resp.status_code, json

#
# Methods below here use the User class from the user module.
#

def get_user_playlists(user):
    """Gets all of the current user's playlists (not including tracks).
       see: https://developer.spotify.com/web-api/get-a-list-of-current-users-playlists/
    """
    params = {'limit': 50, 'offset': 0}
    url = 'https://api.spotify.com/v1/users/%s/playlists' % user.id
    status, result = _get_json(user, url, params=params)
    if status != 200:
        app.logger.error('failed to retrieve playlists for %s' % user.id)
        return

    total = int(result['total'])
    for playlist in result['items']: yield playlist
    params['offset'] += params['limit']

    while params['offset'] < total:
        status, result = _get_json(user, url, params=params)
        if status != 200:
            app.logger.error('failed to retrieve playlists for %s' % user.id)
            return

        for playlist in result['items']: yield playlist
        params['offset'] += params['limit']

DEFAULT_PLAYLIST_FIELDS = ('collaborative,description,id,name,owner.id,public,snapshot_id,followers.total,images')
def get_playlist(user, id, owner=None, fields=DEFAULT_PLAYLIST_FIELDS):
    """Gets a specific playlist."""
    if owner is None: owner = user.id
    playlist_url = 'https://api.spotify.com/v1/users/%s/playlists/%s' % (owner, id)
    status, playlist = _get_json(user, playlist_url, params={'fields':fields})
    if status != 200:
        app.logger.error('Error fetching playlist %s/%s: %s, %s' % (owner, id, status, playlist))
        return None

    return playlist

DEFAULT_PLAYLIST_TRACK_FIELDS = ('items(added_at,added_by.id,total,'
                                 'track(id,name,type,disc_number,duration_ms,explicit,href,popularity,'
                                 'artists(id),'
                                 'album(id,artists(id))))')
def get_playlist_tracks(user, playlist, total=None, fields=DEFAULT_PLAYLIST_TRACK_FIELDS):
    """Gets the tracks associated with a playlist. NOTE: this only ever gives 100 tracks and doesn't page.
       We should probably just not use this method."""
    if total is None:
        pl = get_playlist(user, playlist.id, playlist.owner, fields='tracks.total')
        if 'tracks' in pl and 'total' in pl['tracks']:
            total = int(pl['tracks']['total'])
        else:
            app.logger.error('Failed to determine total tracks for %s.' % playlist)

    url = 'https://api.spotify.com/v1/users/%s/playlists/%s/tracks' % (playlist.owner, playlist.id)
    params = {'fields':fields, 'offset': 0, 'limit': 100}
    while params['offset'] < total:
        status, result = _get_json(user, url, params=params)
        if status != 200:
            app.logger.error('Failed to get tracks for playlist %s: %s' % (playlist.id, result))
            return

        for item in result['items']: yield item
        params['offset'] += params['limit']

DEFAULT_ALBUM_FIELDS = 'artists.id,genres,id,images(width,height,url),label,name,popularity,release_date,tracks.href'
def get_albums(user, album_ids, fields=DEFAULT_ALBUM_FIELDS):
    limit = 20
    queue = list(album_ids)
    url = 'https://api.spotify.com/v1/albums/'
    params = {'ids':','.join(queue[0:limit]), 'fields':fields}

    while len(queue) > 0:
        status, result = _get_json(user, url, params=params)
        if status != 200:
            app.logger.error('Failed to request albums.')
            return

        if len(queue) == 1:
            yield result['albums'][0]
            return

        for item in result['albums']: yield item
        del queue[0:limit]
        params['ids'] = ','.join(queue[0:limit])

def get_artists(user, artist_ids):
    limit = 20
    queue = list(artist_ids)
    url = 'https://api.spotify.com/v1/artists'
    params = {'ids':','.join(queue[0:limit])}

    while len(queue) > 0:
        status, result = _get_json(user, url, params=params)
        if status != 200:
            app.logger.error('Failed to request artists.')
            return

        for item in result['artists']: yield item
        del queue[0:limit]
        params['ids'] = ','.join(queue[0:limit])

def get_tracks(user, track_ids):
    limit = 50
    queue = list(track_ids)
    url = 'https://api.spotify.com/v1/tracks/'
    params = {'ids':','.join(queue[0:limit])}

    while len(queue) > 0:
        status, result = _get_json(user, url, params=params)
        if status != 200:
            app.logger.error('Failed to request tracks.')
            return

        for item in result['tracks']: yield item
        del queue[0:limit]
        params['ids'] = ','.join(queue[0:limit])

def get_audio_features(user, track_ids):
    limit = 100
    queue = list(track_ids)
    url = 'https://api.spotify.com/v1/audio-features/'
    params = {'ids':','.join(queue[0:limit])}

    while len(queue) > 0:
        status, result = _get_json(user, url, params=params)
        if status != 200:
            app.logger.error('Failed to request features.')
            return

        for item in result['audio_features']: yield item
        del queue[0:limit]
        params['ids'] = ','.join(queue[0:limit])

def get_audio_analysis(user, track_id):
    status, result = _get_json(user, 'https://api.spotify.com/v1/audio-analysis/%s' % track_id)
    if status != 200:
        app.logger.error('Failed to request analysis.')
        return

    return result
