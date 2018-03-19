import os
from logging import StreamHandler, Formatter
from logging.handlers import RotatingFileHandler
from flask import Flask
from flaskext.mysql import MySQL

app = Flask(__name__)
app.logger.info('App listening on port %s' % os.getenv('HTTP_PLATFORM_PORT'))

if (os.getenv('DEBUG')):
    app.config.update(DEBUG = True)

log_path = os.getenv('LOG_PATH')
if log_path:
    app.logger.info('Adding RotatingFileHandler logging to %s/app.log' % log_path)
    app.logger.addHandler(RotatingFileHandler(log_path + '/app.log', maxBytes = 1*1024*1024, backupCount = 100))

secret_key = os.getenv('SECRET_KEY')
if not secret_key:
    app.logger.warn('No SECRET_KEY environment variable found. Using default secret key.')
    secret_key = 'p/5K82pTf0Gmx/DGvS/5s6S+XCy7133NUSm5kOAxKCH1xoK9oI/sDrmUJy1wsFfZcvVlu6QtEGuxyvlMP98YcQ=='

app.config.update(
    SESSION_COOKIE_NAME = 'clef_2_session',
    SESSION_COOKIE_SECURE = False if app.config['DEBUG'] else False,
    SECRET_KEY = secret_key,
    MYSQL_DATABASE_HOST = os.getenv('MYSQL_DATABASE_HOST'),
    MYSQL_DATABASE_DB = os.getenv('MYSQL_DATABASE_DB'),
    MYSQL_DATABASE_USER = os.getenv('MYSQL_DATABASE_USER'),
    MYSQL_DATABASE_PASSWORD = os.getenv('MYSQL_DATABASE_PASSWORD'))

app.logger.info('Session cookie name: %s (Secure? %s)' % (app.config['SESSION_COOKIE_NAME'], app.config['SESSION_COOKIE_SECURE']))
app.logger.info('Initializing MySQL connection to %s, database %s, user %s' % (
    app.config['MYSQL_DATABASE_HOST'],
    app.config['MYSQL_DATABASE_DB'],
    app.config['MYSQL_DATABASE_USER']))
mysql = MySQL()
mysql.init_app(app)

from clef import routes
from clef import command
