from datetime import datetime, timedelta
from clef import mysql
from clef import app

class Track:
    def __init__(self, id, name=None, type=None, album_id=None, disc_number=None, duration_ms=None,
                 explicit=None, popularity=None, preview_url=None, acousticness=None, danceability=None,
                 energy=None, instrumentalness=None, key=None, liveness=None, loudness=None, mode=None,
                 speechiness=None, tempo=None, time_signature=None, valence=None):

        self.id = id
        self.name = name
        self.type = type
        self.album_id = album_id
        self.disc_number = disc_number
        self.duration_ms = duration_ms
        self.explicit = explicit
        self.popularity = popularity
        self.preview_url = preview_url
        self.acousticness = acousticness
        self.danceability = danceability
        self.energy = energy
        self.instrumentalness = instrumentalness
        self.key= key
        self.liveness = liveness
        self.loudness = loudness
        self.mode = mode
        self.speechiness = speechiness
        self.tempo = tempo
        self.time_signature = time_signature
        self.valence = valence

    def _from_row(row):
        return Track(row[0], row[1], row[2], row[3], row[4], row[5], row[6], row[7], row[8], row[9],
                     row[10], row[11], row[12], row[13], row[14], row[15], row[16], row[17], row[18],
                     row[19], row[20])

    def load(id):
        app.logger.debug('fetching track %s' % id)
        cursor = mysql.connection.cursor()
        cursor.execute("""
        select id, name, type, album_id, disc_number, duration_ms, explicit, popularity, preview_url,
               acousticness, danceability, energy, instrumentalness, `key`, liveness, loudness,
               mode, speechiness, tempo, time_signature, valence
        from   Track
        where  id = %s
        """, (id,))

        if cursor.rowcount == 0:
            return None

        return Track._from_row(cursor.fetchone())

    def load_many(ids):
        if len(ids) < 1: return {}
        params = ','.join(['%s'] * len(ids))
        cursor = mysql.connection.cursor()
        cursor.execute("""
        select id, name, type, album_id, disc_number, duration_ms, explicit, popularity, preview_url,
               acousticness, danceability, energy, instrumentalness, `key`, liveness, loudness,
               mode, speechiness, tempo, time_signature, valence
        from   Track
        where  id in (%s)
        """ % params, tuple(ids))
        tracks = [Track._from_row(row) for row in cursor]
        return {track.id:track for track in tracks}

    def for_playlist(playlist):
        return Track.for_playlist_id(playlist.id)

    def for_playlist_id(id):
        cursor = mysql.connection.cursor()
        cursor.execute("""
        select t.id, t.name, t.type, t.album_id, t.disc_number, t.duration_ms, t.explicit, t.popularity, t.preview_url,
               t.acousticness, t.danceability, t.energy, t.instrumentalness, t.`key`, t.liveness, t.loudness,
               t.mode, t.speechiness, t.tempo, t.time_signature, t.valence
        from   Track t
               inner join PlaylistTrack pt on t.id = pt.track_id
        where  pt.playlist_id = %s
        """, (id,))
        return [Track._from_row(row) for row in cursor]

    def save(self):
        cursor = mysql.connection.cursor()
        cursor.execute("""
        insert into Track (
               id, name, type, album_id, disc_number, duration_ms, explicit, popularity, preview_url,
               acousticness, danceability, energy, instrumentalness, `key`, liveness, loudness,
               mode, speechiness, tempo, time_signature, valence)
        values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        on duplicate key
        update name=%s, type=%s, album_id=%s, disc_number=%s, duration_ms=%s, explicit=%s, popularity=%s, preview_url=%s,
               acousticness=%s, danceability=%s, energy=%s, instrumentalness=%s, `key`=%s, liveness=%s, loudness=%s,
               mode=%s, speechiness=%s, tempo=%s, time_signature=%s, valence=%s
        """, (self.id, self.name, self.type, self.album_id, self.disc_number, self.duration_ms,
              self.explicit, self.popularity, self.preview_url, self.acousticness, self.danceability,
              self.energy, self.instrumentalness, self.key, self.liveness, self.loudness, self.mode,
              self.speechiness, self.tempo, self.time_signature, self.valence,
              self.name, self.type, self.album_id, self.disc_number, self.duration_ms,
              self.explicit, self.popularity, self.preview_url, self.acousticness, self.danceability,
              self.energy, self.instrumentalness, self.key, self.liveness, self.loudness, self.mode,
              self.speechiness, self.tempo, self.time_signature, self.valence))

    def save_many(tracks):
        for track in tracks:
            if not isinstance(track, Track):
                raise Exception("save_many tracks must be Track: %s" % track)

        cursor = mysql.connection.cursor()
        cursor.executemany("""
        insert into Track (
               id, name, type, album_id, disc_number, duration_ms, explicit, popularity, preview_url,
               acousticness, danceability, energy, instrumentalness, `key`, liveness, loudness,
               mode, speechiness, tempo, time_signature, valence)
        values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        on duplicate key
        update name=values(name), type=values(type), album_id=values(album_id),
               disc_number=values(disc_number), duration_ms=values(duration_ms),
               explicit=values(explicit), popularity=values(popularity),
               preview_url=values(preview_url), acousticness=values(acousticness),
               danceability=values(danceability), energy=values(energy),
               instrumentalness=values(instrumentalness), `key`=values(`key`),
               liveness=values(liveness), loudness=values(loudness),
               mode=values(mode), speechiness=values(speechiness), tempo=values(tempo),
               time_signature=values(time_signature), valence=values(valence)
        """, [(track.id, track.name, track.type, track.album_id, track.disc_number, track.duration_ms,
              track.explicit, track.popularity, track.preview_url, track.acousticness, track.danceability,
              track.energy, track.instrumentalness, track.key, track.liveness, track.loudness, track.mode,
              track.speechiness, track.tempo, track.time_signature, track.valence) for track in tracks])

    def add_artist(self, artist):
        cursor = mysql.connection.cursor()
        cursor.execute("""
        insert into TrackArtist(track_id, artist_id)
        values      (%s, %s)
        on duplicate key
        update track_id=values(track_id)
        """, (self.id, artist.id))

    def link_many_to_many_artists(track_id_artist_ids):
        cursor = mysql.connection.cursor()
        cursor.executemany("""
        insert into TrackArtist(track_id, artist_id)
        values      (%s, %s)
        on duplicate key
        update track_id=values(track_id)
        """, [(track_id, artist_id) for track_id, artist_id in track_id_artist_ids])

    def from_json(json):
        if json['id'] is None: raise ValueError('Track has no id: %s' % json)
        return Track(json['id'], json['name'], json['type'], json['album']['id'],
                     json['disc_number'], json['duration_ms'], json['explicit'],
                     json['popularity'], json['preview_url'])

    def update_features(self, json):
        self.acousticness = json['acousticness']
        self.danceability = json['danceability']
        self.energy = json['energy']
        self.instrumentalness = json['instrumentalness']
        self.key = json['key']
        self.liveness = json['liveness']
        self.loudness = json['loudness']
        self.mode = json['mode']
        self.speechiness = json['speechiness']
        self.tempo = json['tempo']
        self.time_signature = json['time_signature']
        self.valence = json['valence']

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
        if self.preview_url is not None: ctor_args.append('preview_url="%s"' % self.preview_url)
        if self.acousticness is not None: ctor_args.append('acousticness=%s' % self.acousticness)
        if self.danceability is not None: ctor_args.append('danceability=%s' % self.danceability)
        if self.energy is not None: ctor_args.append('energy=%s' % self.energy)
        if self.instrumentalness is not None: ctor_args.append('instrumentalness=%s' % self.instrumentalness)
        if self.key is not None: ctor_args.append('key=%s' % self.key)
        if self.liveness is not None: ctor_args.append('liveness=%s' % self.liveness)
        if self.loudness is not None: ctor_args.append('loudness=%s' % self.loudness)
        if self.mode is not None: ctor_args.append('mode=%s' % self.mode)
        if self.speechiness is not None: ctor_args.append('speechiness=%s' % self.speechiness)
        if self.tempo is not None: ctor_args.append('tempo=%s' % self.tempo)
        if self.time_signature is not None: ctor_args.append('time=%s' % self.time)
        if self.valence is not None: ctor_args.append('valence=%s' % self.valence)
        return 'Track(%s)' % ', '.join(ctor_args)
