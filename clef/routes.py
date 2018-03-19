import base64, json, os, requests
from urllib.parse import unquote
from flask import render_template, request, session, redirect, url_for
from clef.spotify import get_auth_url, get_auth_token, get_user, get_playlists
from clef.user import User
from clef.playlist import Playlist
from clef.helpers import dump_session
from clef import app

@app.route('/')
def default():
    return render_template('index.html')

@app.route('/login')
def login():
    session.clear()
    state = base64.b64encode(os.urandom(64)).decode('ascii')
    authorize_callback_url = request.url_root + 'authorized'
    authorize_url = get_auth_url(authorize_callback_url, state)
    app.logger.info('Redirecting to authorize, state = %s', state)
    app.logger.info('url: %s', authorize_url)
    return redirect(authorize_url)

@app.route('/user/<id>')
def user(id):
    app.logger.debug('/user/%s' % id)
    if 'user_id' in session:
        user_id = session['user_id']
        app.logger.debug('Session user: %s' % user_id)
        app.logger.info('Loading user %s' % id)
        user = User.load(session['user_id'])
        if user:
            app.logger.info('User %s is logged in.' % user.id)

            target_user = user if id == user.id else User.load(id)

            playlists = list(Playlist.for_user(target_user))

            # TODO: if the user has no playlists, or we haven't
            # refreshed them in a while, do that now.
            if len(playlists) == 0:
                status, res = get_playlists(target_user)
                if status == 200:
                    for p in res['items']:
                        playlist = Playlist.from_json(p)
                        playlist.save()
                        playlists.append(playlist)

            if target_user == user:
                return render_template('user.html', user=user, target_user=target_user, playlists=playlists)
            else:
                # TODO: show the current user some information about
                # another user
                pass

        app.logger.warn('User %s not found in database.' % user_id)
    else:
        dump_session('No user_id in current session')

    return login()

@app.route('/authorized')
def authorized():
    if 'error' in request.args:
        error = request.args.get('error')
        app.logger.error('Error response from authorize: %s', error)
        return render_template('error.html', error=error)

    auth_code = request.args.get('code')
    state = unquote(request.args.get('state'))
    app.logger.debug('authorized state: %s', state)

    # TODO: verify state matches

    authorize_callback_url = request.url_root + 'authorized'
    status, token = get_auth_token(auth_code, authorize_callback_url)
    if status != 200:
        app.logger.error('Failed to get auth_token. Status=%s, response = %s' % (status, token))
        return render_template('error.html', error=token)

    # TODO: if user is already in our database, look for changes
    status, spotify_user = get_user(token['access_token'])
    if status != 200:
        app.logger.error('Failed to get user. Status=%s, response = %s' % (status, spotify_user))
        return render_template('error.html', error = spotify_user)

    user = User.load(spotify_user['id'])
    if not user:
        app.logger.info('Creating new user record for user id %s' % spotify_user['id'])
        user = User.from_json(spotify_user, token)
        user.save()

    user_url = '/user/%s' % user.id
    session['user_id'] = user.id
    session.modified = True
    app.logger.info('redirecting to %s with session set to user_id %s' % (user_url, session['user_id']))
    return redirect(user_url)
