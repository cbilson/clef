from datetime import datetime, timedelta
from clef import mysql

class Album:
    def __init__(self, id, name, album_type, href):
        self.id = id
        self.name = name
        self.album_type = album_type
        self.href = href

    def from_json(json):
        return Album(json['id'], json['name'], json['album_type'], json['href'])

    def save(self):
        cursor = mysql.connection.cursor()
        cursor.execute('insert into Album(id, name, album_type, href) '
                       'values(%s, %s, %s, %s) '
                       'on duplicate key update '
                       'name=%s, album_type=%s, href=%s',
                       (self.id, self.name, self.album_type, self.href,
                        self.name, self.album_type, self.href))

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
            'album_type="%s"' % self.album_type,
            'href=%s' % self.href]
        return 'Album(%s)' % ', '.join(ctor_args)
