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
            for genre in js['genres']:
                artist.add_genre(genre)

        if 'images' in js:
            for image in js['images']:
                artist.add_image(image['width'], image['height'], image['url'])

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
        params = ','.join(['%s'] * len(ids))
        app.logger.debug('Artist.load_many: %s artists, [%s]' % (len(ids), ids))
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

    def add_genre(self, genre):
        app.logger.debug('adding genre for artist %s (id:%s): %s' % (self.name, self.id, genre))
        cursor = mysql.connection.cursor()
        cursor.execute('insert into ArtistGenre(artist_id, genre) '
                       'values(%s, %s) '
                       'on duplicate key update '
                       'genre=%s',
                       (self.id, genre, genre))

    def add_image(self, width, height, url):
        app.logger.debug('adding image for artist %s (id:%s): %s' % (self.name, self.id, url))
        cursor = mysql.connection.cursor()
        cursor.execute('insert into ArtistImage(artist_id, width, height, url) '
                       'values(%s, %s, %s, %s) '
                       'on duplicate key update '
                       'width=%s, height=%s, url=%s',
                       (self.id, width, height, url, width, height, url))
