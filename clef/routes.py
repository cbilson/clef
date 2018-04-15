import base64, json, os, requests
import jsonpickle
from datetime import datetime, timedelta
from requests.auth import HTTPBasicAuth
from urllib.parse import unquote, urlparse
from flask import render_template, get_template_attribute, request, session, redirect, url_for, jsonify
from clef.spotify import get_auth_url, get_auth_token, get_user, get_user_playlists
from clef.user import User, UserArtistOverview, UserList
from clef.playlist import Playlist, PlaylistSummaryView, PlaylistDetailsView
from clef.helpers import dump_session
from clef import app, mysql

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

@app.route('/user/<id>/playlists')
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
            return render_template('playlists.html', user=user, playlists=playlists)

        app.logger.warn('User %s not found in database.' % user_id)
    else:
        dump_session('No user_id in current session')

    return login()

# TODO: expose a way to update user-email address
# when adding a new user, copy e-mail from spotify then save that in our database.

@app.route('/user/<user_id>/refresh', methods=['POST'])
def refresh(user_id):
    # Adding this light-weight "refresh" so I can test without waiting 10 minutes to reload my playlists
    if 'user_id' not in session: abort(401)
    if session['user_id'] != user_id: abort(403)
    user = User.load(user_id)
    mysql.connection.commit()
    playlists = PlaylistSummaryView.for_user(user)
    return jsonify([p.__dict__ for p in playlists])

@app.route('/user/<user_id>/full-refresh', methods=['POST'])
def full_refresh(user_id):
    if 'user_id' not in session: abort(401)
    if session['user_id'] != user_id: abort(403)
    user = User.load(user_id)
    refresh_result = Playlist.import_user_playlists(user)
    mysql.connection.commit()
    playlists = PlaylistSummaryView.for_user(user)
    return jsonify([p.__dict__ for p in playlists])

@app.route('/user/<user_id>/artists')
def artists(user_id):
    if 'user_id' not in session: abort(401)
    if session['user_id'] != user_id: abort(403)
    user = User.load(user_id)
    artists = list(UserArtistOverview.for_user(user))
    return render_template('artists.html', user=user, artists=artists)

@app.route('/user/<user_id>/save', methods=['POST'])
def user_save(user_id):
    if 'user_id' not in session: abort(401)
    if session['user_id'] != user_id: abort(403)
    user = User.load(user_id)
    user.name = request.json['displayName']
    user.save()
    mysql.connection.commit()
    return jsonify(dict(id=user.id, email=user.email, name=user.name, joined=user.joined))

@app.route('/user/<user_id>/playlist/<playlist_id>/details')
def user_playlist_details(user_id, playlist_id):
    if 'user_id' not in session: abort(401)
    if session['user_id'] != user_id: abort(403)
    return jsonpickle.encode(PlaylistDetailsView.get(user_id, playlist_id), unpicklable=False)

@app.route('/admin/users')
def admin():
    if 'user_id' not in session: abort(403)
    user = User.load(session['user_id'])
    if not user.is_admin: abort(403)
    user_list = UserList.get()
    return render_template('admin.html', user=user, user_list=user_list)

def webjobs_auth():
    return HTTPBasicAuth(os.environ['WEBJOBS_USER_NAME'], os.environ['WEBJOBS_PASSWORD'])

@app.route('/admin/import/user/<user_id>', methods=['POST'])
def admin_import_user(user_id):
    if 'user_id' not in session: abort(403)
    user = User.load(session['user_id'])
    if not user.is_admin: abort(403)

    url = 'https://clef2.scm.azurewebsites.net/api/triggeredwebjobs/import-user-playlists/run?arguments=%s' % user_id
    app.logger.info('staring import for user_id %s' % user_id)
    resp = requests.post(url, auth=webjobs_auth())
    if resp.status_code != 202: abort(resp.status_code)
    location = resp.headers['Location']
    url = urlparse(location)
    job_id = url.path.split('/')[-1]
    app.logger.info('import for user_id %s -> job_id %s' % (user_id, job_id))
    return jsonify(dict(status='started', jobId=job_id)), resp.status_code

@app.route('/admin/import/user/<user_id>/job/<job_id>', methods=['GET'])
def admin_import_job(user_id, job_id):
    if 'user_id' not in session: abort(403)
    user = User.load(session['user_id'])
    if not user.is_admin: abort(403)

    url = 'https://clef2.scm.azurewebsites.net/api/triggeredwebjobs/import-user-playlists/history/%s' % job_id
    resp = requests.get(url, auth=webjobs_auth())
    if resp.status_code != 200: abort(resp.status_code)
    job_info = jsonpickle.decode(resp.content)
    app.logger.debug('job %s, status %s, duration: %s' % (id, job_info['status'], job_info['duration']))
    if job_info['status'] == 'Success':
        user = UserListEntry.get(user_id)
        job_info['userInfo'] = jsonpickle.encode(user, unpicklable=True)
    return jsonify(job_info)

@app.route('/admin/import/job/<job_id>/results', methods=['GET'])
def admin_import_job_results(job_id):
    if 'user_id' not in session: abort(403)
    user = User.load(session['user_id'])
    if not user.is_admin: abort(403)

    url = 'https://clef2.scm.azurewebsites.net/vfs/data/jobs/triggered/import-user-playlists/%s/output_log.txt' % job_id
    resp = requests.get(url, auth=webjobs_auth())
    return resp.content, resp.status_code, {'Content-Type': 'text/plain; charset=utf-8'}

@app.route('/search')
def search():
    cursor = mysql.connection.cursor()
    cursor.execute("""
select e.id, e.type, e.name
from SearchTerm t
inner join SearchEntity e
on t.entity_id = e.id
where t.term like %s
limit 20
    """, (('%' + request.args.get('term') + '%',)))
    return jsonify([dict(id=row[0], type=row[1], name=row[2]) for row in cursor])

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
        user.status = 'New'
    else:
        user.access_token = token['access_token']
        user.token_expiration = datetime.utcnow() + timedelta(seconds=token['expires_in'])
        user.refresh_token = token['refresh_token']

    user.save()
    mysql.connection.commit()

    user_url = '/user/%s/playlists' % user.id
    session['user_id'] = user.id
    session.modified = True
    app.logger.info('redirecting to %s with session set to user_id %s' % (user_url, session['user_id']))
    return redirect(user_url)
