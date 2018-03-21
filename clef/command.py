import os
import re
import sys
import textwrap
import virtualenv
import webbrowser

import click
import colorama

from colorama import Fore, Back, Style
from clef import app, mysql
from clef.user import User
from clef.playlist import Playlist
from clef.artist import Artist
from clef.album import Album
from clef.track import Track
from clef.spotify import get_all_playlists, get_playlist_tracks

colorama.init(autoreset=True)

module_path = os.path.dirname(os.path.realpath(__file__))
sql_path = os.path.abspath(module_path + '/../sql')
failed_checks = 0

@app.cli.command('bootstrap')
def bootstrap():
    pass

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

@app.cli.command('load-playlists')
@click.option('--user-id')
def load_playlists(user_id):
    """Loads playlists for one user from spotify to the database."""
    user = User.load(user_id)
    playlists = [Playlist.from_json(json) for json in get_all_playlists(user)]
    for p in playlists:
        p.save()
        click.echo(p.name)

    mysql.connection.commit()
    click.echo(Style.DIM + '=' * 20)
    click.echo('Total %s for %s' % (len(playlists), user_id))

@app.cli.command('load-playlist-tracks')
@click.option('--user-id')
@click.option('--playlist-id')
def load_playlist_tracks(user_id, playlist_id):
    user = User.load(user_id)
    playlist = Playlist.load(playlist_id)
    status, json = get_playlist_tracks(user, playlist)
    if status != 200:
        click.echo('Failed to get playlist tracks. %s, %s' % status, json)
        return -1

    tracks_js = json['items']
    albums_js = dict()
    for album in [track['track']['album'] for track in tracks_js]:
        if album['id'] not in albums_js:
            albums_js[album['id']] = album

    click.echo('Found %s different albums...' % len(albums_js))

    artists_js = dict()
    for album in albums_js.values():
        for artist in album['artists']:
            if artist['id'] not in artists_js:
                artists_js[artist['id']] = artist

    for track in tracks_js:
        for artist in track['track']['artists']:
            if artist['id'] not in artists_js:
                artists_js[artist['id']] = artist

    click.echo('Found %s different artists...' % len(artists_js))

    artists = [Artist.from_json(x) for x in artists_js.values()]
    artists_dict = dict()
    click.echo()
    click.echo('Artists')
    click.echo('-------')
    for artist in artists:
        click.echo('%s' % artist)
        artist.save()
        artists_dict[artist.id] = artist

    click.echo(Style.DIM + '=' * 20)
    click.echo('Total %s artists' % len(artists))
    click.echo()

    albums = [Album.from_json(x) for x in albums_js.values()]
    albums_dict = dict()
    click.echo()
    click.echo('Albums')
    click.echo('------')
    for album in albums:
        click.echo('%s' % album)
        album.save()
        albums_dict[album.id] = album

        for artist_id in [artist['id'] for artist in albums_js[album.id]['artists']]:
            artist = artists_dict[artist_id]
            click.echo('\tadding artist %s' % artist.name)
            album.add_artist(artist)

        # TODO: link to images

    click.echo(Style.DIM + '=' * 20)
    click.echo('Total %s albums' % len(albums))
    click.echo()

    click.echo()
    click.echo('Tracks')
    click.echo('------')
    for track_js in tracks_js:
        track = Track.from_json(track_js['track'])
        click.echo('%s' % track)
        track.save()

        click.echo('\tadding to playlist %s' % playlist.name)
        playlist.add_track(track, track_js['added_at'], track_js['added_by']['id'])

        for artist_id in [artist['id'] for artist in track_js['track']['artists']]:
            artist = artists_dict[artist_id]
            click.echo('\tadding artist %s' % artist.name)
            track.add_artist(artist)

    click.echo(Style.DIM + '=' * 20)
    click.echo('Total %s tracks' % len(tracks_js))
    click.echo()

    mysql.connection.commit()

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
