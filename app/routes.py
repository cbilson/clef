import base64, json, os, requests
from urllib.parse import unquote
from flask import render_template, request, session, redirect, url_for
from app.spotify import get_auth_url, get_auth_token, get_user
from app.user import User

from app import app

@app.route('/')
def index():
    if 'user_id' in session:
        user = User.load(session['user_id'])
        if user:
            return render_template('user.html', user=user)

    session.clear()
    state = base64.b64encode(os.urandom(64)).decode('ascii')
    authorize_callback_url = request.url_root + 'authorized'
    authorize_url = get_auth_url(authorize_callback_url, state)
    app.logger.info('Redirecting to authorize, state = %s', state)
    app.logger.info('url: %s', authorize_url)
    return redirect(authorize_url)

@app.route('/authorized')
def authorized():
    if 'error' in request.args:
        error = request.args.get('error')
        app.logger.error('Error response from authorize: %s', error)
        return render_template('error.html', error=error)

    auth_code = request.args.get('code')
    state = unquote(request.args.get('state'))
    app.logger.info('authorized state: %s', state)

    # TODO: verify state matches

    authorize_callback_url = request.url_root + 'authorized'
    status, token = get_auth_token(auth_code, authorize_callback_url)
    if status != 200:
        return render_template('error.html', error=token)

    # TODO: if user is already in our database, look for changes
    status, spotify_user = get_user(token['access_token'])
    if status != 200:
        return render_template('error.html', error = spotify_user)

    user = User.load(spotify_user['id'])
    if not user:
        user = User.from_json(spotify_user, token)
        user.save()

    session['user_id'] = user.id
    return redirect('/')
