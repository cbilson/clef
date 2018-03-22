import base64, json, os, requests
from urllib.parse import unquote
from flask import render_template, request, session, redirect, url_for
from clef.spotify import get_auth_url, get_auth_token, get_user, get_playlists
from clef.user import User
from clef.playlist import Playlist, PlaylistSummaryView
from clef.helpers import dump_session
from clef import app

@app.errorhandler(401)
def custom_401(error):
    return render_template('error.html', error='You must be logged.'), 401

@app.errorhandler(403)
def custom_401(error):
    return render_template('error.html', error='You do not have permision to view that.'), 401

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
            if id != user.id: abort(403)
            app.logger.info('User %s is logged in.' % user.id)
            playlists = PlaylistSummaryView.for_user(user)
            # Check to see if the user profile is stale
            return render_template('user.html', user=user, target_user=target_user, playlists=playlists)

        app.logger.warn('User %s not found in database.' % user_id)
    else:
        dump_session('No user_id in current session')

    return login()

@app.route('/user/<user_id>/refresh', methods=['POST'])
def refresh(user_id):
    if 'user_id' not in session: abort(401)
    if session['user_id'] != user_id: abort(403)

    # TODO: this should just return a token that the page can poll for
    # status changes, or use a web socket. When the work is complete the
    # page could then highlight the changed playlists.
    user = User.load(user_id)
    result = Playlist.refresh(user)

    playlists = PlaylistSummaryView.for_user(user)

    # TODO: update the is_deleted, is_... for playlists based on result
    
    # TODO: should render a widget with just the list items for the new
    # set of playlists
    return render_template('user.html')

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
