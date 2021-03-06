import json
from datetime import datetime, timedelta
from clef import mysql, app

class Artist:
    def __init__(self, id, name, type, followers, popularity):
        self.id = id
        self.name = name
        self.type = type
        self.followers = followers
        self.popularity = popularity

    def __repr__(self):
        ctor_args = [
            'id="%s"' % self.id,
            'name="%s"' % self.name,
            'type="%s"' % self.type,
            'followers=%s' % self.followers,
            'popularity=%s' % self.popularity]

        return 'Artist(%s)' % ', '.join(ctor_args)

    def from_json(js):
        if 'id' not in js:
            raise ValueError('No ID for artist: %s' % js)

        return Artist(js['id'], js['name'], js['type'], js['followers']['total'], js['popularity'])

    def import_json(js):
        """Create an Artist from JSON, save it, and create child objects as well."""
        artist = Artist.from_json(js)
        artist.save()

        if 'genres' in js:
            artist.add_genres(js['genres'])

        if 'images' in js:
            artist.add_images([(image['width'], image['height'], image['url']) for image in js['images']])

        return artist

    def _from_row(row):
        return Artist(row[0], row[1], row[2], row[3], row[4])

    def load(id):
        cursor = mysql.connection.cursor()
        cursor.execute('select id, name, type, followers, popularity '
                       'from Artist '
                       'where id = %s',
                       (id,))

        if cursor.rowcount == 0:
            return None

        return Artist._from_row(cursor.fetchone())

    def load_many(ids):
        if len(ids) < 1: return {}
        params = ','.join(['%s'] * len(ids))
        cursor = mysql.connection.cursor()
        cursor.execute('select id, name, type, followers, popularity '
                       'from Artist '
                       'where id in (%s)' % params,
                       tuple(ids))
        artists = [Artist._from_row(row) for row in cursor]
        return {artist.id:artist for artist in artists}

    def save(self):
        cursor = mysql.connection.cursor()
        cursor.execute('insert into Artist(id, name, type, followers, popularity) '
                       'values(%s, %s, %s, %s, %s) '
                       'on duplicate key update '
                       'name=%s, type=%s, followers=%s, popularity=%s',
                       (self.id, self.name, self.type, self.followers, self.popularity,
                        self.name, self.type, self.followers, self.popularity))

    def save_many(artists):
        cursor = mysql.connection.cursor()
        cursor.executemany("""
        insert into   Artist(id, name, type, followers, popularity)
        values        (%s, %s, %s, %s, %s)
        on duplicate key update
                      name=values(name), type=values(type), followers=values(followers), popularity=values(popularity)
        """, [(artist.id, artist.name, artist.type, artist.followers, artist.popularity) for artist in artists])

    def add_genres(self, genres):
        cursor = mysql.connection.cursor()
        cursor.executemany("""
            insert into ArtistGenre(artist_id, genre)
            values      (%s, %s)
            on duplicate key
            update genre=values(genre)""",
                       [(self.id, genre) for genre in genres])

    def add_images(self, images):
        cursor = mysql.connection.cursor()
        cursor.executemany("""
            insert into ArtistImage(artist_id, width, height, url)
            values(%s, %s, %s, %s)
            on duplicate key update
            width=values(width), height=values(height), url=values(url)""",
                           [(self.id, w, h, u) for w, h, u in images])
