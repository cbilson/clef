import json
import re
from datetime import datetime, timedelta
from clef import app, mysql

class Album:
    def __init__(self, id, name, label, album_type, popularity, release_date):
        if (len(id) > 32): raise Exception("album_id too long: %s" % id)

        if isinstance(release_date, str):
            if (re.match(r'^\d{4}$', release_date)): release_date = release_date + '-01-01'
            elif (re.match(r'^\d{4}-\d{1,2}$', release_date)): release_date = release_date + '-01'
            elif (re.match(r'^\d{4}\d{1,2}$', release_date)): release_date = release_date + '01'
            elif (re.match(r'^\d{4}\d{2}-\d{2}$', release_date)):
                release_date = release_date[:6] + release_date[7:9]
            elif (re.match(r'^\d{4}-\d{1,2}-\d{1,2}$', release_date)): pass
            else:
                raise Exception("Bad release date: %s" % release_date)

        self.id = id
        self.name = name
        self.label = label
        self.album_type = album_type
        self.popularity = popularity
        self.release_date = release_date

    def from_json(json):
        if 'id' not in json or json['id'] is None: raise ValueError('Album has no id: %s' % json)
        return Album(json['id'], json['name'], json['label'], json['album_type'],
                     json['popularity'], json['release_date'])

    def import_json(js):
        """Creates and saves an Album object from JSON, including any child images or genres."""
        album = Album.from_json(js)
        album.save()

        if 'genres' in js:
            for genre in js['genres']:
                album.add_genre(genre)

        if 'images' in js:
            for image in js['images']:
                album.add_image(image['width'], image['height'], image['url'])

        return album

    def add_genre(self, genre):
        cursor = mysql.connection.cursor()
        cursor.execute('insert into AlbumGenre(album_id, genre) '
                       'values(%s, %s) '
                       'on duplicate key update '
                       'genre=%s',
                       (self.id, genre, genre))

    def add_image(self, width, height, url):
        cursor = mysql.connection.cursor()
        cursor.execute('insert into AlbumImage(album_id, width, height, url) '
                       'values(%s, %s, %s, %s) '
                       'on duplicate key update '
                       'url=%s',
                       (self.id, width, height, url, url))

    def _from_row(row):
        return Album(row[0], row[1], row[2], row[3], row[4], row[5])

    def load(id):
        cursor = mysql.connection.cursor()
        cursor.execute('select id, name, label, album_type, popularity, release_date '
                       'from Album '
                       'where id = %s',
                       (id,))

        if cursor.rowcount == 0: return None

        return Album._from_row(cursor.fetchone())

    def load_many(ids):
        if len(ids) < 1: return {}
        params = ','.join(['%s'] * len(ids))
        cursor = mysql.connection.cursor()
        cursor.execute("""
            select    id, name, label, album_type, popularity, release_date
            from      Album
            where id in (%s)
        """ % params, tuple(ids))
        albums = [Album._from_row(row) for row in cursor]
        return {album.id:album for album in albums}

    def save(self):
        cursor = mysql.connection.cursor()
        try:
            cursor.execute('insert into Album(id, name, label, album_type, popularity, release_date) '
                           'values(%s, %s, %s, %s, %s, %s) '
                           'on duplicate key update '
                           'name=%s, label=%s, album_type=%s, popularity=%s, release_date=%s',
                           (self.id, self.name, self.label, self.album_type, self.popularity, self.release_date,
                            self.name, self.label, self.album_type, self.popularity, self.release_date))
        except:
            app.logger.error("Failed to save Album: %s" % self)
            raise

    def save_many(albums):
        cursor = mysql.connection.cursor()
        cursor.executemany("""
        insert into   Album(id, name, label, album_type, popularity, release_date)
        values        (%s, %s, %s, %s, %s, %s)
        on duplicate key
        update        name=values(name), label=values(label), album_type=values(album_type),
                      popularity=values(popularity), release_date=values(release_date)
        """, [(album.id, album.name, album.label, album.album_type, album.popularity, album.release_date)
              for album in albums])

    def link_many_to_many_artists(album_artist_id_tuples):
        for album_id, artist_id in album_artist_id_tuples:
            if not isinstance(album_id, str): raise Exception("album_id must be a string: %s" % album_id)
            if len(album_id) > 32:
                raise Exception("album_id too long: %s" % album_id)
            if not isinstance(artist_id, str): raise Exception("artist_id must be a string: %s" % artist_id)
            if len(artist_id) > 32:
                raise Exception("artist_id too long: %s" % artist_id)

        cursor = mysql.connection.cursor()
        cursor.executemany("""
        insert into   AlbumArtist(album_id, artist_id)
        values        (%s, %s)
        on duplicate key update album_id=values(album_id)
        """, album_artist_id_tuples)

    def add_artist(self, artist):
        cursor = mysql.connection.cursor()
        cursor.execute('insert into AlbumArtist(album_id, artist_id) '
                       'values(%s, %s) '
                       'on duplicate key update album_id=%s',
                       (self.id, artist.id, self.id))

    def __repr__(self):
        ctor_args = [
            'id="%s"' % self.id,
            'name="%s"' % self.name,
            'label="%s"' % self.label,
            'album_type="%s"' % self.album_type,
            'popularity=%s' % self.popularity,
            'release_date=%s' % self.release_date]
        return 'Album(%s)' % ', '.join(ctor_args)
