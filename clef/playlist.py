from datetime import datetime, timedelta
from clef import mysql

class Playlist:
    def __init__(self, id):
        self.id = id
        self.user_id = None
        self.name = None
        self.is_public = False
        self.created = None
        self.snapshot_id = None

    def _from_row(row):
        playlist = Playlist(row[0])
        playlist.user_id = row[1]
        playlist.name = row[2]
        playlist.is_public = row[3]
        playlist.created = row[3]
        playlist.snapshot_id = row[5]
        return playlist

    def load(id):
        with mysql.get_db().cursor() as cursor:
            cursor.execute('select id, user_id, name, is_public, created, snapshot_id '
                           'from Playlist '
                           'where id = %s',
                           (id,))

            row = cursor.fetchone()
            return Playlist._from_row(row)

    def for_user(user):
        with mysql.get_db().cursor() as cursor:
            cursor.execute('select id, user_id, name, is_public, created, snapshot_id '
                           'from Playlist '
                           'where user_id = %s',
                           (user.id,))
            for row in cursor:
                yield Playlist._from_row(row)

    def from_json(json):
        playlist = Playlist(json['id'])
        playlist.user_id = json['owner']['id']
        playlist.name = json['name']
        playlist.is_public = json['public']
        playlist.snapshot_id = json['snapshot_id']
        return playlist

    def delete(self):
        with mysql.get_db().cursor() as cursor:
            cursor.execute('delete from Playlist where id = %s', (self.id,))

    def save(self):
        with mysql.get_db().cursor() as cursor:
            if self.created:
                cursor.execute(
                    'update Playlist '
                    'set user_id = %s,'
                    'name = %s,'
                    'is_public = %s,'
                    'created = %s,'
                    'snapshot_id = %s '
                    'where id = %s',
                    (self.user_id, self.name,
                     self.is_public, self.created, self.snapshot_id,
                     self.id))
            else:
                self.created = datetime.utcnow()
                cursor.execute(
                    'insert into Playlist('
                    'id, user_id, name, is_public,'
                    'created, snapshot_id)'
                    'values(%s, %s, %s, %s, %s, %s)',
                    (self.id, self.user_id, self.name,
                     self.is_public, self.created, self.snapshot_id))
