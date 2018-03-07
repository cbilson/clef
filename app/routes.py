import base64, json, os, requests
from urllib.parse import unquote
from flask import render_template, request, session, redirect
from app import app
import app.db
import app.user

@app.route('/')
def index():
  if 'user_id' in session:
      connection = db.connect()
      try:
          user = user.load(session['user_id'], connection)
          if user:
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
  with db.connect() as connection:
      if 'error' in request.args:
          error = request.args.get('error')
          app.logger.error('Error response from authorize: %s', error)
          return render_template('error.html', error=error)

      auth_code = request.args.get('code')
      state = unquote(request.args.get('state'))
      app.logger.info('authorized state: %s', state)

      # TODO: verify state matches

      status, token = spotify.get_auth_token(auth_code)
      if status != 200:
          return render_template('auth-error.html', error=token)

      # TODO: if user is already in our database, look for changes

      # Otherwise, create a new record for them and populate their data
      status, spotify_user = spotify.get_user(token)
      if status != 200:
          return render_template('error.html', error = user)

      user = user.from_json(spotify_user, token)
      user.save(connection)

      users[user.id] = user
      session['user_id'] = user.id
      return redirect('/')

if __name__ == '__main__':
  app.run()
