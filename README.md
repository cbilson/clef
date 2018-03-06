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

In [1]: import db, user, spotify

In [2]:
```

3. Autheticate with Spotify:

``` python
In [2]: spotify.authorize_me()
```

   After you've authenticated, you will be redirected to a URL like
   "http://localhost:5000/authorized?code=...". Just copy this and use
   this function to get the token out:

``` python
In [3]: status, token_info = spotify.get_auth_token_from_redirect_url('<<paste in the URL from your browser>>')
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
In [5]: u = user.from_json(spotify_user, token_info)
In [6]: u.save()
```

6. Once you are saved in the database, we can reload you:

``` python
In [7]: u = user.load('cbilson')
```

7. And we can use that user to get your playlists from spotify:

``` python
In [8]: spotify.get_playlists(u)
```

Next I want to start saving playlists and the tracks they
contain. Also, I want to do this from the web application.

Tip: It's easier to work with the code if you set ipython to autreload
modules when you have made changes to them:

``` python
%load_ext autoreload
%autoreload 2
```
