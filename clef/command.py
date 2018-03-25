import os
import re
import sys
import textwrap
import virtualenv
import webbrowser

import click
import colorama
import json

import clef.spotify

from colorama import Fore, Back, Style
from clef import app, mysql
from clef.user import User
from clef.playlist import Playlist, PlaylistSummaryView
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
    if not 'MYSQL_DATABASE_USER' in os.environ:
        click.echo(Back.RED + colorama)
        app.config['MYSQL_USER'] = os.environ['MYSQL_ADMIN_DATABASE_USER']
        app.config['MYSQL_PASSWORD'] = os.environ['MYSQL_ADMIN_DATABASE_PASSWORD']
        exec_sql_file(sql_path + '/create-database.sql')

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
    playlist = clef.spotify.get_playlist(user, playlist_id, owner=owner, fields=fields)
    mysql.connection.commit()   # in case the user's token was refreshed
    click.echo('Result:')
    click.echo(json.dumps(playlist, indent=2, sort_keys=True))

@app.cli.command('get-spotify-user-playlists')
@click.option('--user-id')
def get_spotify_user_playlist(user_id):
    """Get all Spotify playlists for a user."""
    user = User.load(user_id)
    count = 0
    for playlist in clef.spotify.get_user_playlists(user):
        click.echo(json.dumps(playlist, indent=2, sort_keys=True))
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
    for track in clef.spotify.get_playlist_tracks(user, playlist):
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
    for album in clef.spotify.get_albums(user, album_ids):
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
    for artist in clef.spotify.get_artists(user, artist_ids):
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
    for track in clef.spotify.get_tracks(user, track_ids):
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
    for features in clef.spotify.get_audio_features(user, track_ids):
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
    analysis = clef.spotify.get_audio_analysis(user, track_id)
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

@app.cli.command('import-user-playlist')
@click.option('--user-id')
@click.option('--playlist-id')
@click.option('--force')
def import_user_playlist(user_id, playlist_id, force=False):
    """Imports a single user playlist from spotify, regardless if it has been changed or not."""
    user = User.load(user_id)
    t, al, ar = Playlist.import_user_playlist(user, playlist_id)
    mysql.connection.commit()
    click.echo('done. %s tracks, %s albums, %s artists.' % (t, al, ar))

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

    try:
        with mysql.get_db().cursor() as cursor:
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

def exec_sql_file(sql_file):
    click.echo('Executing SQL script file: %s' % sql_file)
    statement = ""

    cursor = mysql.connection.cursor()
    for line in open(sql_file):
        if re.match(r'^--', line):  # ignore sql comment lines
            continue
        if not re.search(r'[^-;]+;', line):  # keep appending lines that don't end in ';'
            statement = statement + line
        else:  # when you get a line ending in ';' then exec statement and reset for next statement
            statement = statement + line
            click.echo(Style.DIM + "Executing SQL statement:")
            click.echo(statement)
            cursor.execute(statement)
            click.echo(Fore.GREEN + 'done.')
            statement = ""
