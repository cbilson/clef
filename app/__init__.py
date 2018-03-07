from flask import Flask
import logging, os, sys
from logging import StreamHandler
from logging.handlers import RotatingFileHandler

app = Flask(__name__)

app.config.update(SESSION_COOKIE_NAME = 'clef_2_session')

if (os.getenv('DEBUG')):
    stdoutLogger = StreamHandler(sys.stdout)
    stdoutLogger.setLevel(logging.DEBUG)
    app.logger.addHandler(stdoutLogger)

    app.config.update(
        DEBUG = True,
        # just for running locally
        SECRET_KEY='P/5K82pTf0Gmx/DGvS/5s6S+XCy7133NUSm5kOAxKCH1xoK9oI/sDrmUJy1wsFfZcvVlu6QtEGuxyvlMP98YcQ==')
else:
    fileHandler = RotatingFileHandler('app.log', maxBytes=10*1024*1024, backupCount=100)
    fileHandler.setLevel(logging.INFO)
    app.logger.addHandler(fileHandler)

    app.config.update(
        SECRET_KEY = os.getenv('SECRET_KEY'),
        SESSION_COOKIE_SECURE = True)

if not app.config['SECRET_KEY']:
  raise Exception('Please specify a SECRET_KEY or DEBUG environment variable.')

from app import routes
