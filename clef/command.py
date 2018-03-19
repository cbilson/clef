import colorama
import os, sys
import webbrowser
from flask import Flask
from clef import app, mysql

@app.cli.command()
def initdb():
    """Run the database DDL scripts to initialize the database."""
    click.echo('TODO: run the SQL scripts to initialize the database.')

@app.cli.command()
def migratedb():
    """Run migration scripts to update database schema and data."""
    click.echo('TODO: run migration scripts to update database.')

@app.cli.command('spotify-dashboard')
def spotify_dashboard():
    webbrowser.open('https://beta.developer.spotify.com/dashboard/applications/7cab843edcd8494b939924f28d347d91').start()

failed_checks = 0

def passed(msg):
    print(colorama.Fore.GREEN + '+ ' + msg)

def failed(msg):
    print(colorama.Fore.WHITE + colorama.Back.RED + '- ' + msg)
    failed_checks += 1

@app.cli.command('preflight-check')
def preflight_check():
    """Validate application configuration."""
    colorama.init(autoreset=True)
    print()
    print(colorama.Style.DIM + '=' * 80)
    print(colorama.Style.DIM + 'Checking environment...')

    passed('Log path found') if 'LOG_PATH' in os.environ else failed('LOG_PATH missing')
    passed('HTTP port found') if 'HTTP_PLATFORM_PORT' in os.environ else failed('HTTP_PLATFORM_PORT missing')
    passed('Secret Key found') if 'SECRET_KEY' in os.environ else failed('SECRET_KEY missing')
    passed('Database host found') if 'MYSQL_DATABASE_HOST' in os.environ else failed('MYSQL_DATABASE_HOST missing')
    passed('Database name found') if 'MYSQL_DATABASE_DB' in os.environ else failed('MYSQL_DATABASE_DB missing')
    passed('Database user found') if 'MYSQL_DATABASE_USER' in os.environ else failed('MYSQL_DATABASE_USER missing')
    passed('Database password found') if 'MYSQL_DATABASE_PASSWORD' in os.environ else failed('MYSQL_DATABASE_PASSWORD missing')

    try:
        with mysql.get_db().cursor() as cursor:
            cursor.execute('select 1')
            if cursor.rowcount == 1:
                passed('Can connect to database and execute queries')
            else:
                failed('"SELECT 1" returned unexected %s rows (expected: 1)' % cursor.rowcount)
    except:
        failed('"SELECT 1" resulted in error: %s' % sys.exc_info()[0])

    print()
    print(colorama.Style.DIM + '=' * 80)

    if failed_checks == 0:
        print(colorama.Fore.GREEN + 'Everything looks good!')
    else:
        print(colorama.Fore.WHITE + colorama.Back.RED + '%s problems found.' % failed_checks)

    print(colorama.Style.DIM + '=' * 80)
    print()
