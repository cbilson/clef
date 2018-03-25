from datetime import datetime, timedelta
from clef import mysql
from clef import app

class Track:
    def __init__(self, id, name=None, type=None, album_id=None,
                 disc_number=None, duration_ms=None, explicit=None,
                 popularity=None):
        self.id = id
        self.name = name
        self.type = type
        self.album_id = album_id
        self.disc_number = disc_number
        self.duration_ms = duration_ms
        self.explicit = explicit
        self.popularity = popularity

    def _from_row(row):
        return Track(row[0], row[1], row[2], row[3], row[4], row[5], row[6], row[7])

    def load(id):
        app.logger.debug('fetching track %s' % id)
        cursor = mysql.connection.cursor()
        cursor.execute('select id, name, type, '
                       'album_id, disc_number, duration_ms, '
                       'explicit, popularity '
                       'from Track '
                       'where id = %s',
                       (id,))

        if cursor.rowcount == 0:
            return None

        return Track._from_row(cursor.fetchone())

    def load_many(ids):
        params = ','.join(['%s'] * len(ids))
        cursor = mysql.connection.cursor()
        cursor.execute('select id, name, type, '
                       'album_id, disc_number, duration_ms, '
                       'explicit, popularity '
                       'from Track '
                       'where id in (%s)' % params,
                       tuple(ids))
        tracks = [Track._from_row(row) for row in cursor]
        return {track.id:track for track in tracks}

    def for_playlist(playlist):
        cursor = mysql.connection.cursor()
        cursor.execute('select id, name, type, '
                       'album_id, disc_number, duration_ms, '
                       'explicit, popularity '
                       'from Track '
                       ' inner join PlaylistTrack pt on track_id = pt.track_id '
                       'where pt.playlist_id = %s',
                       (playlist.id,))
        return [Track._from_row(row) for row in cursor]

    def save(self):
        cursor = mysql.connection.cursor()
        cursor.execute('insert into Track(id, name, type, '
                       'album_id, disc_number, duration_ms, '
                       'explicit, popularity) '
                       'values(%s,%s,%s,%s,%s,%s,%s,%s) '
                       'on duplicate key update '
                       'name=%s, type=%s, '
                       'album_id=%s, disc_number=%s, duration_ms=%s, '
                       'explicit=%s, popularity=%s',
                       (self.id, self.name, self.type,
                        self.album_id, self.disc_number, self.duration_ms,
                        self.explicit, self.popularity,
                        self.name, self.type,
                        self.album_id, self.disc_number, self.duration_ms,
                        self.explicit, self.popularity))

    def add_artist(self, artist):
        cursor = mysql.connection.cursor()
        cursor.execute('insert into TrackArtist(track_id, artist_id) '
                       'values(%s, %s) '
                       'on duplicate key update '
                       'track_id = %s',
                       (self.id, artist.id, self.id))

    def from_json(json):
        if json['id'] is None: raise ValueError('Track has no id: %s' % json)
        return Track(json['id'], json['name'], json['type'], json['album']['id'],
                     json['disc_number'], json['duration_ms'], json['explicit'],
                     json['popularity'])

    def import_json(js):
        """Imports a track and any child objects, saving them into the database."""
        track = Track.from_json(js)
        track.save()

        # it looks like tracks don't have images or genre, althought I thougt I saw they had images at least...
        return track

    def __repr__(self):
        ctor_args = list()
        ctor_args.append('id="%s"' % self.id)
        if self.name is not None: ctor_args.append('name="%s"' % self.name)
        if self.type is not None: ctor_args.append('type="%s"' % self.type)
        if self.album_id is not None: ctor_args.append('album_id="%s"' % self.album_id)
        if self.disc_number is not None: ctor_args.append('disc_number="%s"' % self.disc_number)
        if self.duration_ms is not None: ctor_args.append('duration_ms="%s"' % self.duration_ms)
        if self.explicit is not None: ctor_args.append('explicit="%s"' % self.explicit)
        if self.popularity is not None: ctor_args.append('popularity="%s"' % self.popularity)
        return 'Track(%s)' % ', '.join(ctor_args)
