# Using the Python REPL

1. Set environment variables to the values in cred.txt.

For example, on windows, I do this:
```shell
set DB_HOST=clefdb.mysql.database.azure.com
set DB_NAME=clef
set DB_USER=***
set DB_PASSWORD=***
set SPOTIFY_CLIENT_ID=***
set SPOTIFY_CLIENT_SECRET=***
```
2. Start a python REPL in the root of the git repository and load modules:
```shell
C:\src\clef>ipython
Python 3.6.4 (v3.6.4:d48eceb, Dec 19 2017, 06:54:40) [MSC v.1900 64 bit (AMD64)]
Type 'copyright', 'credits' or 'license' for more information
IPython 6.2.1 -- An enhanced Interactive Python. Type '?' for help.

In [1]: from clef.user import User

In [2]: from clef.playlist import Playlist

In [3]: import clef.spotify

```

3. Autheticate with Spotify:

``` python
In [2]: clef.spotify.authorize_me()
```

   After you've authenticated, you will be redirected to a URL like
   "http://localhost:5000/authorized?code=...". Just copy this and use
   this function to get the token out:

``` python
In [3]: status, token_info = clef.spotify.get_auth_token_from_redirect_url('<<paste in the URL from your browser>>')
```

   If =status= is 200, =token_info= will contain an access_token, good
   for 1 hour, and a refresh token we can use to refresh the access
   token. 

4. From this, we can get the rest of your spotify user info:

``` python
In [4]: status, spotify_user = spotify.get_user(token_info['access_token'])
```

5. From this, we can create our user object and save it in the
   database:

``` python
In [5]: u = User.from_json(spotify_user, token_info)
In [6]: u.save()
```

6. Once you are saved in the database, we can reload you:

``` python
In [7]: u = User.load('cbilson')
```

7. And we can use that user to get your playlists from spotify:

``` python
In [8]: clef.spotify.get_playlists(u)
```

Next I want to start saving playlists and the tracks they
contain. Also, I want to do this from the web application.

Tip: It's easier to work with the code if you set ipython to autreload
modules when you have made changes to them:

``` python
%load_ext autoreload
%autoreload 2
```

# Spotify Messages

## get_playlists

``` json
{'href': 'https://api.spotify.com/v1/users/cbilson/playlists?offset=0&limit=20',
 'items': [{'collaborative': False,
   'external_urls': {'spotify': 'https://open.spotify.com/user/cbilson/playlist/4fIts6ifuNaB6ueuxToWun'},
   'href': 'https://api.spotify.com/v1/users/cbilson/playlists/4fIts6ifuNaB6ueuxToWun',
   'id': '4fIts6ifuNaB6ueuxToWun',
   'images': [{'height': 640,
     'url': 'https://mosaic.scdn.co/640/0d56ada22e1185b1764ea4060eb3dc24addc6f736c6086f6922b9a44920310b34ef98161bd7adf78767fff2bd704862cc0b7865d2365f67a269a4cbaa77fedfc4a62a3e23f02e4dab7e926e5577566cd',
     'width': 640},
    {'height': 300,
     'url': 'https://mosaic.scdn.co/300/0d56ada22e1185b1764ea4060eb3dc24addc6f736c6086f6922b9a44920310b34ef98161bd7adf78767fff2bd704862cc0b7865d2365f67a269a4cbaa77fedfc4a62a3e23f02e4dab7e926e5577566cd',
     'width': 300},
    {'height': 60,
     'url': 'https://mosaic.scdn.co/60/0d56ada22e1185b1764ea4060eb3dc24addc6f736c6086f6922b9a44920310b34ef98161bd7adf78767fff2bd704862cc0b7865d2365f67a269a4cbaa77fedfc4a62a3e23f02e4dab7e926e5577566cd',
     'width': 60}],
   'name': 'My Shazam Tracks',
   'owner': {'display_name': 'Chris Bilson',
    'external_urls': {'spotify': 'https://open.spotify.com/user/cbilson'},
    'href': 'https://api.spotify.com/v1/users/cbilson',
    'id': 'cbilson',
    'type': 'user',
    'uri': 'spotify:user:cbilson'},
   'public': True,
   'snapshot_id': 'lQPZYLNntvmcDPPdDaUxZB8GC4gOP7o0chTRYo6OuylPSYZ4dRY1cdYUHjo/DiBv',
   'tracks': {'href': 'https://api.spotify.com/v1/users/cbilson/playlists/4fIts6ifuNaB6ueuxToWun/tracks',
    'total': 5},
   'type': 'playlist',
   'uri': 'spotify:user:cbilson:playlist:4fIts6ifuNaB6ueuxToWun'}, ...],
 'limit': 20,
 'next': 'https://api.spotify.com/v1/users/cbilson/playlists?offset=20&limit=20',
 'offset': 0,
 'previous': None,
 'total': 88}
```

`
