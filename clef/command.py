import os
import re
import sys
import textwrap
import virtualenv
import webbrowser

import click
import colorama
import json
import jsonpickle
import requests

import clef.spotify as spotify

from colorama import Fore, Back, Style
from requests.auth import HTTPBasicAuth

from clef import app, mysql
from clef.user import User
from clef.playlist import Playlist, PlaylistSummaryView, PlaylistDetailsView
from clef.artist import Artist
from clef.album import Album
from clef.track import Track

colorama.init(autoreset=True)

module_path = os.path.dirname(os.path.realpath(__file__))
sql_path = os.path.abspath(module_path + '/../sql')
failed_checks = 0

@app.cli.command('bootstrap')
def bootstrap():
    pass

#
#  Database Commands
#

@app.cli.command()
def initdb():
    """Run the database DDL scripts to initialize the database."""
    app.config['MYSQL_USER'] = os.environ['MYSQL_ADMIN_DATABASE_USER']
    app.config['MYSQL_PASSWORD'] = os.environ['MYSQL_ADMIN_DATABASE_PASSWORD']

    script = 'create-database.sql'
    if app.config['MYSQL_DB'] != 'clef':
        script = 'create-database-%s.sql' % app.config['MYSQL_DB']
    else:
        return

    exec_sql_file(script)
    exec_sql_file('create-schema.sql', use=app.config['MYSQL_DB'])

    script = 'post-create-database.sql'
    if app.config['MYSQL_DB'] != 'clef':
        script = 'post-create-database-%s.sql' % app.config['MYSQL_DB']

    exec_sql_file(script, use=app.config['MYSQL_DB'])

@app.cli.command()
def migratedb():
    """Run migration scripts to update database schema and data."""
    if not 'MYSQL_DATABASE_USER' in os.environ:
        click.echo(Back.RED + colorama)
        app.config['MYSQL_USER'] = os.environ['MYSQL_ADMIN_DATABASE_USER']
        app.config['MYSQL_PASSWORD'] = os.environ['MYSQL_ADMIN_DATABASE_PASSWORD']
    for file in os.listdir(sql_path):
        if not re.match(r'^\d+_', file):
            continue

        exec_sql_file('%s/%s' % (sql_path, file))

@app.cli.command('get-user-playlists')
@click.option('--user-id')
def get_user_playlists(user_id):
    """Fetches all user playlists for a user from the clef database."""
    u = User.load(user_id)
    show_collection(Playlist.for_user(u))

@app.cli.command('get-user-playlists-summary')
@click.option('--user-id')
def get_user_playlists_summary(user_id):
    """Fetches a user's playlist summary view (what's shown on the user page)."""
    u = User.load(user_id)
    show_collection(PlaylistSummaryView.for_user(u))

#
# Website Commands
#

@app.cli.command('spotify-dashboard', with_appcontext=False)
def open_spotify_dashboard():
    """Open the spotify dashboard to for the application."""
    url = 'https://beta.developer.spotify.com/dashboard/applications/%s' % os.environ['SPOTIFY_CLIENT_ID']
    webbrowser.open(url)

@app.cli.command('prod', with_appcontext=False)
def open_prod():
    """Open the 'Production' version of the publically accessible app.."""
    url = 'https://clef2.azurewebsites.net/'
    webbrowser.open(url)

@app.cli.command('prod-kudu', with_appcontext=False)
def open_prod_kudu():
    """Open the 'Production' version of the publically accessible app.."""
    url = 'https://clef2.scm.azurewebsites.net/DebugConsole'
    webbrowser.open(url)

@app.cli.command('chris-test', with_appcontext=False)
def open_chris_test():
    """Open Chris's test deployment slot."""
    url = 'https://clef2-chris.azurewebsites.net/'
    webbrowser.open(url)

@app.cli.command('chris-test-kudu', with_appcontext=False)
def open_chris_test():
    """Open DebugConsole on Chris's test deployment slot."""
    url = 'https://clef2-chris.scm.azurewebsites.net/DebugConsole'
    webbrowser.open(url)

@app.cli.command('portal', with_appcontext=False)
def open_portal():
    """Open the Azure Portal dashboard for Clef Notes."""
    url = 'https://portal.azure.com/#@chrisbilsoncalicoenergy.onmicrosoft.com/dashboard/private/60b7336f-622f-4867-943f-f37bbbe003cd'
    webbrowser.open(url)

#
# Raw Spotify Commands
#
@app.cli.command('get-spotify-playlist')
@click.option('--user-id')
@click.option('--playlist-id')
@click.option('--owner-id')
@click.option('--fields')
def get_spotify_playlist(user_id, playlist_id, owner_id, fields):
    """Get a Spotify playlist by id."""
    user = User.load(user_id)
    playlist = spotify.get_playlist(user, playlist_id, owner=owner_id, fields=fields)
    mysql.connection.commit()   # in case the user's token was refreshed
    click.echo('Result:')
    click.echo(json.dumps(playlist, indent=2, sort_keys=True))

@app.cli.command('get-spotify-user-playlists')
@click.option('--user-id')
def get_spotify_user_playlists(user_id):
    """Get all Spotify playlists for a user."""
    user = User.load(user_id)
    count = 0
    for playlist in spotify.get_user_playlists(user):
        click.echo(json.dumps(playlist, indent=2, sort_keys=True))
        click.echo(',')
        count += 1

    mysql.connection.commit() # in case user token changed
    click.echo('done. Total %s playlists' % count)

@app.cli.command('get-spotify-playlist-tracks')
@click.option('--user-id')
@click.option('--playlist-id')
def get_spotify_playlist_tracks(user_id, playlist_id):
    """Get tracks in a Spotify playlist."""
    user = User.load(user_id)
    playlist = Playlist.load(playlist_id)
    if playlist is None:
        status, result = get_playlist(user, pl_id)
        if status != 200:
            click.echo('failed to fetch playlist: %s, %s', (status, result))

        playlist = Playlist.from_json(result)

    count = 0
    for track in spotify.get_playlist_tracks(user, playlist):
        click.echo(json.dumps(track, indent=2, sort_keys=True))
        count += 1

    mysql.connection.commit() # in case user token changed
    click.echo('done. Total %s tracks' % count)

@app.cli.command('get-spotify-albums')
@click.option('--user-id')
@click.option('--album-ids', multiple=True)
def get_spotify_albums(user_id, album_ids):
    """Get Spotify albums by id."""
    user = User.load(user_id)
    count = 0
    for album in spotify.get_albums(user, album_ids):
        click.echo(json.dumps(album, indent=2, sort_keys=True))
        click.echo()
        count += 1

    mysql.connection.commit()   # in case the user's token was refreshed
    click.echo('done. Total %s albums' % count)

@app.cli.command('get-spotify-artists')
@click.option('--user-id')
@click.option('--artist-ids', multiple=True)
def get_spotify_artists(user_id, artist_ids):
    """Get Spotify artists by id."""
    user = User.load(user_id)
    count = 0
    for artist in spotify.get_artists(user, artist_ids):
        click.echo(json.dumps(artist, indent=2, sort_keys=True))
        click.echo()
        count += 1

    mysql.connection.commit()   # in case the user's token was refreshed
    click.echo('done. Total %s artists' % count)

@app.cli.command('get-spotify-tracks')
@click.option('--user-id')
@click.option('--track-ids', multiple=True)
def get_spotify_tracks(user_id, track_ids):
    """Get spotify tracks by id."""
    user = User.load(user_id)
    count = 0
    for track in spotify.get_tracks(user, track_ids):
        click.echo(json.dumps(track, indent=2, sort_keys=True))
        click.echo()
        count += 1

    mysql.connection.commit()   # in case the user's token was refreshed
    click.echo('done. Total %s tracks' % count)

@app.cli.command('get-spotify-audio-features')
@click.option('--user-id')
@click.option('--track-ids', multiple=True)
def get_spotify_audio_features(user_id, track_ids):
    """Get Spotify's audio features for a track.
    See: https://beta.developer.spotify.com/documentation/web-api/reference/tracks/get-audio-features/"""
    user = User.load(user_id)
    count = 0
    for features in spotify.get_audio_features(user, track_ids):
        click.echo(json.dumps(features, indent=2, sort_keys=True))
        click.echo()
        count += 1

    mysql.connection.commit()   # in case the user's token was refreshed
    click.echo('done. Total %s tracks' % count)

@app.cli.command('get-spotify-audio-analysis')
@click.option('--user-id')
@click.option('--track-id')
def get_spotify_audio_analysis(user_id, track_id):
    """Get Spotify's audio analysis for a track. See: https://beta.developer.spotify.com/documentation/web-api/reference/tracks/get-audio-analysis/"""
    user = User.load(user_id)
    count = 0
    analysis = spotify.get_audio_analysis(user, track_id)
    click.echo('{')

    click.echo('"bars": [')
    for bar in analysis['bars']:
        click.echo('\t%s' % json.dumps(bar))
    click.echo('],')

    click.echo('"beats": [')
    for beat in analysis['beats']:
        click.echo('\t%s' % json.dumps(beat))
    click.echo('],')

    click.echo('"sections": [')
    for section in analysis['sections']:
        click.echo('\t%s' % json.dumps(section))
    click.echo('],')

    click.echo('"segments": [')
    for segment in analysis['segments']:
        click.echo('\t%s' % json.dumps(segment))
    click.echo('],')

    click.echo('"tatums": [')
    for tatum in analysis['tatums']:
        click.echo('\t%s' % json.dumps(tatum))
    click.echo('],')

    click.echo('"track": %s,' % json.dumps(analysis['track'], indent=2, sort_keys=True))
    click.echo()
    click.echo('"meta": %s,' % json.dumps(analysis['meta'], indent=2, sort_keys=True))

    click.echo('}')

    mysql.connection.commit()   # in case the user's token was refreshed

#
# Import Commands
#

@app.cli.command('import-user-playlists')
@click.option('--user-id')
def import_user_playlists(user_id):
    """Imports all of a user's playlists from spotify, regardless if they have been changed or not."""
    user = User.load(user_id)
    t, al, ar = Playlist.import_user_playlists(user)
    mysql.connection.commit()
    click.echo('done. %s tracks, %s albums, %s artists.' % (t, al, ar))

#-------------------------------------------------------------------------------
#  Web Jobs
#  see: https://github.com/projectkudu/kudu/wiki/WebJobs-API
#-------------------------------------------------------------------------------
@app.cli.command('invoke-webjob')
@click.option('--job')
@click.option('--args')
def invoke_webjob(job, args):
    url = 'https://clef2.scm.azurewebsites.net/api/triggeredwebjobs/%s/run?arguments=%s' % (job, args)
    resp = requests.post(url, auth=HTTPBasicAuth(os.environ['WEBJOBS_USER_NAME'], os.environ['WEBJOBS_PASSWORD']))
    if resp.status_code == 200:
        click.echo('job complete.')
    elif resp.status_code == 202:
        click.echo('job submitted.')
        click.echo('Location: %s' % resp.headers['Location'])
    else:
        click.echo('%s. failed. %s' % (resp.status_code, resp.content))

@app.cli.command('webjob')
@click.option('--job')
def webjob(job):
    """Gets summary information for a webjob."""
    url = 'https://clef2.scm.azurewebsites.net/api/triggeredwebjobs/%s' % job
    resp = requests.get(url, auth=HTTPBasicAuth(os.environ['WEBJOBS_USER_NAME'], os.environ['WEBJOBS_PASSWORD']))
    if resp.status_code == 200:
        result = jsonpickle.decode(resp.content)
        click.echo()
        click.echo('WebJob')
        click.echo('------')
        for prop in ['name', 'type', 'error', 'url', 'run_command', 'history_url', 'extra_info_url']:
            click.echo('%s:\t%s' % (prop, result[prop]))
        click.echo('latest_run:')
        latest_run = result['latest_run']
        for prop in ['id', 'name', 'status', 'start_time', 'end_time', 'duration', 'output_url', 'error_url', 'url', 'trigger']:
            click.echo('\t%s:\t%s' % (prop, latest_run[prop]))
    elif resp.status_code == 404:
        click.echo('Job does not exist.')
    else:
        click.echo('%s. failed. %s' % (resp.status_code, resp.content))

@app.cli.command('webjob-history')
@click.option('--job')
def webjob_history(job):
    """Gets a specific run of a web job."""
    url = 'https://clef2.scm.azurewebsites.net/api/triggeredwebjobs/%s/history' % (job)
    auth = HTTPBasicAuth(os.environ['WEBJOBS_USER_NAME'], os.environ['WEBJOBS_PASSWORD'])
    resp = requests.get(url, auth=auth)
    if resp.status_code == 200:
        result = jsonpickle.decode(resp.content)
        for entry in result['runs']:
            print(entry)
            # for prop in ['id', 'name', 'status', 'start_time', 'end_time', 'duration',
            #              'output_url', 'error_url', 'url', 'trigger']:
            #     click.echo('\t%s:\t%s' % (prop, result[prop]))
    elif resp.status_code == 404:
        click.echo('Not run or job does not exist.')
    else:
        click.echo('%s. failed. %s' % (resp.status_code, resp.content))

@app.cli.command('webjob-run')
@click.option('--job')
@click.option('--run')
def webjob_run(job, run):
    """Gets a specific run of a web job."""
    url = 'https://clef2.scm.azurewebsites.net/api/triggeredwebjobs/%s/history/%s' % (job, run)
    auth = HTTPBasicAuth(os.environ['WEBJOBS_USER_NAME'], os.environ['WEBJOBS_PASSWORD'])
    resp = requests.get(url, auth=auth)
    if resp.status_code == 200:
        result = jsonpickle.decode(resp.content)
        for prop in ['job_name', 'id', 'name', 'status', 'start_time', 'end_time', 'duration',
                     'output_url', 'error_url', 'url', 'trigger']:
            click.echo('\t%s:\t%s' % (prop, result[prop]))
        resp = requests.get(result['output_url'], auth=auth)
        if resp.status_code == 200:
            click.echo('-------')
            click.echo('output:')
            click.echo('-------')
            click.echo(resp.content)
            click.echo('-------')
        else:
            click.echo('failed to fetch output. %s. %s' % (resp.status_code, resp.content))
    elif resp.status_code == 404:
        click.echo('Not run or job does not exist.')
    else:
        click.echo('%s. failed. %s' % (resp.status_code, resp.content))

#-------------------------------------------------------------------------------
# Import Commands
#-------------------------------------------------------------------------------
@app.cli.command('import-playlist-images')
@click.option('--user-id')
def import_playlist_images(user_id):
    """Imports images for all of a user's playlists. This is to mitigate an issue with the normal import process."""
    user = User.load(user_id)
    image_count = 0
    playlist_count = 0
    for playlist in Playlist.for_user(user):
        playlist_count += 1
        spotify_playlist = spotify.get_playlist(user, playlist.id, playlist.owner, fields='id,images')
        for image in spotify_playlist['images']:
            playlist.add_image(image['width'], image['height'], image['url'])
            image_count += 1

    mysql.connection.commit()
    click.echo('done. %s playlists, %s images.' % (playlist_count, image_count))

@app.cli.command('import-user-playlist')
@click.option('--user-id')
@click.option('--playlist-id')
@click.option('--force')
def import_user_playlist(user_id, playlist_id, force=False):
    """Imports a single user playlist from spotify, regardless if it has been changed or not."""
    user = User.load(user_id)
    t, al, ar = Playlist.import_user_playlist(user, playlist_id, force)
    mysql.connection.commit()
    click.echo('done. %s tracks, %s albums, %s artists.' % (t, al, ar))

@app.cli.command('remove-playlist')
@click.option('--user-id')
@click.option('--playlist-id')
def remove_playlist(user_id, playlist_id):
    """Deletes playlists."""
    user = User.load(user_id)
    Playlist.remove_playlists(user, playlist_id)
    mysql.connection.commit()

@app.cli.command('refresh-all-tracks')
@click.option('--user-id')
def refresh_all_tracks(user_id):
    user = User.load(user_id)
    cursor = mysql.connection.cursor()
    cursor.execute('select id from Track')
    spotify_tracks = spotify.get_tracks(user, [row[0] for row in cursor])
    for track in [Track.from_json(js) for js in spotify_tracks]:
        track.save()

    mysql.connection.commit()

@app.cli.command('refresh-track-audio-features')
@click.option('--user-id')
@click.option('--track-ids', multiple=True)
@click.option('--limit', default=1000)
def refresh_track_audio_features(user_id, track_ids, limit):
    user = User.load(user_id)
    if len(track_ids) < 1:
        cursor = mysql.connection.cursor()
        cursor.execute('select id from Track where danceability is null limit %s', (limit,))
        track_ids = [row[0] for row in cursor]

    features = spotify.get_audio_features(user, track_ids)
    by_track_id = {f['id']:f for f in features if f != None}
    if len(by_track_id) < 1:
        click.echo('No features available for these tracks.')
        return

    tracks = Track.load_many(by_track_id.keys()).values()
    for track in tracks:
        track.update_features(by_track_id[track.id])
        track.save()

    mysql.connection.commit()

@app.cli.command('refresh-all-albums')
@click.option('--user-id')
@click.option('--album-id', multiple=True)
@click.option('--limit')
def refresh_all_albums(user_id, album_ids=None, limit=1000):
    user = User.load(user_id)
    if album_ids is None:
        cursor = mysql.connection.cursor()
        cursor.execute('select id from Album limit %s' % limit)
        album_ids = [row[0] for row in cursor]

    spotify_albums = spotify.get_albums(user, album_ids)
    for album in [Album.import_json(js) for js in spotify_albums]:
        album.save()
        click.echo('Updated album %s (%s)' % (album.id, album.name))

    mysql.connection.commit()

@app.cli.command('refresh-artists')
@click.option('--user-id')
@click.option('--artist-ids', multiple=True)
@click.option('--limit')
def refresh_artists(user_id, artist_ids=[], limit=1000):
    user = User.load(user_id)
    if len(artist_ids) < 1:
        cursor = mysql.connection.cursor()
        cursor.execute('''
        select distinct a.id
        from   Artist a
               left outer join ArtistGenre ag on a.id = ag.artist_id
        where  isnull(ag.genre)
        limit %s''' % limit)
        artist_ids = [row[0] for row in cursor]

    for artist in [Artist.import_json(sa) for sa in spotify.get_artists(user, artist_ids)]:
        artist.save()
        click.echo('Updated artist %s (%s)' % (artist.id, artist.name))

    mysql.connection.commit()

#
# "Raw" Commands: commands that exercise the same APIs as the web site
# but return JSON.
#
@app.cli.command('get-playlist-details')
@click.option('--user-id')
@click.option('--playlist-id')
def get_playlist_details(user_id, playlist_id):
    view = PlaylistDetailsView.get(user_id, playlist_id)
    mysql.connection.commit()

    click.echo('result:')
    click.echo(jsonpickle.encode(view, unpicklable=True))

#
# Testing Commands
#

@app.cli.command('preflight-check')
def preflight_check():
    """Validate application configuration."""
    click.echo()
    click.echo(Style.DIM + '=' * 80)
    click.echo(Style.DIM + 'Checking environment...')

    passed('Log path found') if 'LOG_PATH' in os.environ else failed('LOG_PATH environment variable missing')
    passed('Log path exists') if os.path.isdir(os.environ['LOG_PATH']) else failed('LOG_PATH %s does not exist' % os.environ['LOG_PATH'])
    passed('HTTP port found') if 'HTTP_PLATFORM_PORT' in os.environ else failed('HTTP_PLATFORM_PORT environment variable missing')
    passed('Spotify Client ID found') if 'SPOTIFY_CLIENT_ID' in os.environ else failed('SPOTIFY_CLIENT_ID environment variable missing')
    passed('Spotify Client Secret found') if 'SPOTIFY_CLIENT_SECRET' in os.environ else failed('SPOTIFY_CLIENT_SECRET environment variable missing')
    passed('Secret Key found') if 'SECRET_KEY' in os.environ else failed('SECRET_KEY environment variable missing')
    passed('Database host found') if 'MYSQL_DATABASE_HOST' in os.environ else failed('MYSQL_DATABASE_HOST environment variable missing')
    passed('Database name found') if 'MYSQL_DATABASE_DB' in os.environ else failed('MYSQL_DATABASE_DB environment variable missing')
    passed('Database user found') if 'MYSQL_DATABASE_USER' in os.environ else failed('MYSQL_DATABASE_USER environment variable missing')
    passed('Database password found') if 'MYSQL_DATABASE_PASSWORD' in os.environ else failed('MYSQL_DATABASE_PASSWORD environment variable missing')
    passed('WebJobs user found') if 'WEBJOBS_USER_NAME' in os.environ else failed('WEBJOBS_USER_NAME environment variable missing')
    passed('WebJobs password found') if 'WEBJOBS_PASSWORD' in os.environ else failed('WEBJOBS_PASSWORD environment variable missing')

    try:
        with mysql.connection.cursor() as cursor:
            cursor.execute('select 1')
            if cursor.rowcount == 1:
                passed('Can connect to database and execute queries')
            else:
                failed('"SELECT 1" returned unexected %s rows (expected: 1)' % cursor.rowcount)
    except:
        failed('"SELECT 1" resulted in error: %s' % sys.exc_info()[0])

    click.echo()
    click.echo(Style.DIM + '=' * 80)

    if failed_checks == 0:
        click.echo(Fore.GREEN + 'Everything looks good!')
    else:
        click.echo(Fore.WHITE + Back.RED + '%s problems found.' % failed_checks)

    click.echo(Style.DIM + '=' * 80)
    click.echo()
    if failed_checks != 0:
        sys.exit(-1)

def passed(msg):
    click.echo(Fore.GREEN + '+ ' + msg)

def failed(msg):
    global failed_checks
    click.echo(Fore.WHITE + Back.RED + '- ' + msg)
    failed_checks += 1

def show_collection(things):
    click.echo()

    if len(things) < 1:
        click.echo('None')
        return

    name = str(things[0].__class__)
    click.echo(name)
    click.echo('-' * len(name))
    for thing in things:
        click.echo('%s' % thing)

    click.echo(Style.DIM + '=' * 20)
    click.echo('Total %s %s' % (len(things), name))
    click.echo()

def exec_sql_file(sql_file, use=None):
    full_path = '%s/%s' % (sql_path, sql_file)
    if not os.path.isfile(full_path):
        click.echo('Not executing non-existant script %s' % sql_file)
        return

    click.echo('Executing SQL script file: %s' % sql_file)
    statement = ""
    if use is not None:
        statement = "use %s;" %use

    connection = mysql.connect
    cursor = connection.cursor()
    for line in open(full_path):
        if re.match(r'^--', line):  # ignore sql comment lines
            continue
        if not re.search(r'[^-;]+;', line):  # keep appending lines that don't end in ';'
            statement = statement + line
        else:  # when you get a line ending in ';' then exec statement and reset for next statement
            statement = statement + line

            # replace 'macros'
            statement = statement.replace('__DB_USER__', os.environ['MYSQL_DATABASE_USER'])
            statement = statement.replace('__DB_PASSWORD__', os.environ['MYSQL_DATABASE_PASSWORD'])
            click.echo(Style.DIM + "Executing SQL statement:")
            click.echo(statement)
            cursor.execute(statement)
            click.echo(Fore.GREEN + 'done.')
            statement = ""

    cursor.close()
    connection.close()
