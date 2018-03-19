import os
import re
import sys
import webbrowser

import click
import colorama

from colorama import Fore, Back, Style
from clef import app, mysql

colorama.init(autoreset=True)

module_path = os.path.dirname(os.path.realpath(__file__))
sql_path = os.path.abspath(module_path + '/../sql')
failed_checks = 0

@app.cli.command()
def initdb():
    """Run the database DDL scripts to initialize the database."""
    if not 'MYSQL_DATABASE_USER' in os.environ:
        click.echo(Back.RED + colorama)
    app.config['MYSQL_DATABASE_USER'] = os.environ['MYSQL_ADMIN_DATABASE_USER']
    app.config['MYSQL_DATABASE_PASSWORD'] = os.environ['MYSQL_ADMIN_DATABASE_PASSWORD']
    exec_sql_file(sql_path + '/create-database.sql')

@app.cli.command()
def migratedb():
    """Run migration scripts to update database schema and data."""
    for file in os.listdir(sql_path):
        if not re.match(r'^\d+_', file):
            continue

        exec_sql_file('%s/%s' % (sql_path, file))

@app.cli.command('spotify-dashboard')
def spotify_dashboard():
    """Open the spotify dashboard to for the application."""
    url = 'https://beta.developer.spotify.com/dashboard/applications/%s' % os.environ['SPOTIFY_CLIENT_ID']
    webbrowser.open(url)

@app.cli.command('prod')
def spotify_dashboard():
    """Open the 'Production' version of the publically accessible app.."""
    url = 'https://clef2.azurewebsites.net/'
    webbrowser.open(url)

@app.cli.command('chris-test')
def spotify_dashboard():
    """Open Chris's test version of the publically accessible app (deployed by pushing to a local repo)."""
    url = 'https://clef2-chris.azurewebsites.net/'
    webbrowser.open(url)

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
    click.echo(Fore.WHITE + Back.RED + '- ' + msg)
    failed_checks += 1

def exec_sql_file(sql_file):
    click.echo('Executing SQL script file: %s' % sql_file)
    statement = ""

    with mysql.get_db().cursor() as cursor:
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

