from flask import request, session
from clef import app
from clef.user import User
from clef.track import Track
from clef.playlist import Playlist
from clef.spotify import get_all_playlists

def dump_session(msg):
    content = '\n'.join(['%s: %s' % (k,session[k]) for k in session.keys()])
    app.logger.debug('%s. Session:\n%s' % (msg, content))

