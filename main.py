import base64, json, logging, os, requests, sys, threading, webbrowser
from urllib.parse import urlencode, unquote
from flask import Flask, render_template, request, session, redirect
from datetime import datetime
from logging import StreamHandler
from logging.handlers import RotatingFileHandler

import db
import user

app = Flask(__name__)
app.logger.setLevel(logging.DEBUG)
app.config.update(
    SESSION_COOKIE_NAME = 'clef_2_session')

if (os.getenv('DEBUG')):
    stdoutLogger = StreamHandler(sys.stdout)
    stdoutLogger.setLevel(logging.DEBUG)
    app.logger.addHandler(stdoutLogger)

  app.config.update(
      DEBUG = True,
      # just for running locally
      SECRET_KEY='P/5K82pTf0Gmx/DGvS/5s6S+XCy7133NUSm5kOAxKCH1xoK9oI/sDrmUJy1wsFfZcvVlu6QtEGuxyvlMP98YcQ==')
else:
    fileHandler = RotatingFileHandler('app.log', maxBytes=10*1024*1024, backupCount=100)
    fileHandler.setLevel(logging.DEBUG)
    app.logger.addHandler(fileHandler)

    app.config.update(
        SECRET_KEY = os.getenv('SECRET_KEY'),
        SESSION_COOKIE_SECURE = True)

if not app.config['SECRET_KEY']:
  raise Exception('Please specify a SECRET_KEY or DEBUG environment variable.')

@app.route('/')
def index():
  if 'user_id' in session:
      connection = get_db_connection()
      try:
          user = User(connection, session['user_id'])
          return render_template('user.html', user=user)
      except:
          connection.close()
          return render_template('error.html', error='Failed to connect to database.')

  session.clear()
  app.logger.info('Redirecting to authorize, state = %s', state)
  state = base64.b64encode(os.urandom(64)).decode('ascii')
  authorize_url = spotify.get_auth_url(request.url_root + 'authorized', state)
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

  code, token = spotify.get_auth_token(auth_code)
  if code != 200:
      return render_template('auth-error.html', error=token)

  # TODO: if user is already in our database, look for changes

  # Otherwise, create a new record for them and populate their data
  code, user = spotify.get_user(token)
  if code != 200:
      return render_template('error.html', error = user)

  app.logger.info('Requesting user playlists')
  resp = requests.get('https://api.spotify.com/v1/me/playlists', headers=headers)
  playlists_json = resp.json()
  app.logger.debug('User playlists: %s', json.dumps(playlists_json))

  user = User(token_json, user_json, playlists_json)
  users[user.id] = user
  session['user_id'] = user.id
  return redirect('/')
