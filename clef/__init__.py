import os, sys, logging
import clef.ver
from logging import StreamHandler, Formatter
from logging.handlers import RotatingFileHandler
from flask import Flask
from flask_mysqldb import MySQL
from traitlets.config import Config

app = Flask(__name__)

@app.context_processor
def inject_build_ver():
    return dict(build_ver=clef.ver.version, build_message=clef.ver.message, last_updated=clef.ver.last_updated)

app.logger.handlers.clear()

console = StreamHandler(sys.stdout)
console.setLevel(logging.DEBUG)
console.setFormatter(Formatter('%(levelname)s: %(message)s -- %(module)s L%(lineno)s'))
app.logger.addHandler(console)

#if (os.getenv('DEBUG')):
app.config.update(DEBUG = True)

log_path = os.getenv('LOG_PATH')
log_name = os.getenv('LOG_NAME') or 'clef.log'
if log_path:
    file_handler = RotatingFileHandler(log_path + '/clef.log', maxBytes = 1*1024*1024, backupCount = 100)
    file_handler.setFormatter(Formatter('%(asctime)s %(levelname)s: %(message)s -- %(module)s L%(lineno)s'))
    app.logger.addHandler(file_handler)

app.logger.info('App listening on port %s' % os.getenv('HTTP_PLATFORM_PORT'))

secret_key = os.getenv('SECRET_KEY')
if not secret_key:
    app.logger.warn('No SECRET_KEY environment variable found. Using default secret key.')
    secret_key = 'p/5K82pTf0Gmx/DGvS/5s6S+XCy7133NUSm5kOAxKCH1xoK9oI/sDrmUJy1wsFfZcvVlu6QtEGuxyvlMP98YcQ=='

app.config.update(
    SESSION_COOKIE_NAME = 'clef_2_session',
    SESSION_COOKIE_SECURE = False if app.config['DEBUG'] else False,
    SECRET_KEY = secret_key,
    MYSQL_HOST = os.getenv('MYSQL_DATABASE_HOST'),
    MYSQL_DB = os.getenv('MYSQL_DATABASE_DB'),
    MYSQL_USER = os.getenv('MYSQL_DATABASE_USER'),
    MYSQL_PASSWORD = os.getenv('MYSQL_DATABASE_PASSWORD'))

mysql = MySQL(app)

# ipython initialization, for `flask shell`
ipy_cfg = Config()
ipy_cfg.InteractiveShellApp.exec_lines = [
    'import clef',
    'from clef.spotify import *',
    'from clef.user import User',
    'from clef.playlist import Playlist',
    'from clef.track import Track',
    'from clef.artist import Artist',
    'from clef.helpers import *']
app.config['IPYTHON_CONFIG'] = ipy_cfg

from clef import command
from clef import routes
