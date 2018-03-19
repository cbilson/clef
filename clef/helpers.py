from flask import request, session
from clef import app

def dump_session(msg):
    content = '\n'.join(['%s: %s' % (k,session[k]) for k in session.keys()])
    app.logger.debug('%s. Session:\n%s' % (msg, content))
