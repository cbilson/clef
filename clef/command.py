import glob
import os
import re
import sys
import webbrowser

import click
import colorama

from clef import app, mysql

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
                click.echo(colorama.Style.DIM + "Executing SQL statement:")
                click.echo(statement)
                cursor.execute(statement)
                click.echo(colorama.Fore.GREEN + 'done.')
                statement = ""

module_path = os.path.dirname(os.path.realpath(__file__))
sql_path = os.path.abspath(module_path + '/../sql')

@app.cli.command()
def initdb():
    """Run the database DDL scripts to initialize the database."""
    colorama.init(autoreset=True)
    app.config['MYSQL_DATABASE_USER'] = os.environ['MYSQL_ADMIN_DATABASE_USER']
    app.config['MYSQL_DATABASE_PASSWORD'] = os.environ['MYSQL_ADMIN_DATABASE_PASSWORD']
    exec_sql_file(sql_path + '/create-database.sql')

@app.cli.command()
def migratedb():
    """Run migration scripts to update database schema and data."""
    colorama.init(autoreset=True)
    for file in os.listdir(sql_path):
        if not re.match(r'^\d+_', file):
            continue

        exec_sql_file('%s/%s' % (sql_path, file))

@app.cli.command('spotify-dashboard')
def spotify_dashboard():
    webbrowser.open('https://beta.developer.spotify.com/dashboard/applications/7cab843edcd8494b939924f28d347d91').start()

failed_checks = 0

def passed(msg):
    click.echo(colorama.Fore.GREEN + '+ ' + msg)

def failed(msg):
    click.echo(colorama.Fore.WHITE + colorama.Back.RED + '- ' + msg)
    failed_checks += 1

@app.cli.command('preflight-check')
def preflight_check():
    """Validate application configuration."""
    colorama.init(autoreset=True)
    click.echo()
    click.echo(colorama.Style.DIM + '=' * 80)
    click.echo(colorama.Style.DIM + 'Checking environment...')

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

    click.echo()
    click.echo(colorama.Style.DIM + '=' * 80)

    if failed_checks == 0:
        click.echo(colorama.Fore.GREEN + 'Everything looks good!')
    else:
        click.echo(colorama.Fore.WHITE + colorama.Back.RED + '%s problems found.' % failed_checks)

    click.echo(colorama.Style.DIM + '=' * 80)
    click.echo()
