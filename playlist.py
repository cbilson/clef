from datetime import datetime, timedelta
import db

def load(id, db = db.connect()):
    cursor = db.cursor()
    cursor.execute('select user_id, name, description, is_public '
                   'from Playlist '
                   'where id = %s',
                   (id,))

    row = cursor.fetchone()

    playlist = Playlist(id)
    playlist.user_id = row[0]
    playlist.name = row[1]
    playlist.description = row[2]
    playlist.is_public = row[3]
    playlist.created = row[4]
    playlist.snapshot_id = row[5]
    return playlist

def from_json(json):
    pass

class Playlist:
    def __init__(self, id):
        self.id = id
        self.user_id = None
        self.name = None
        self.description = None
        self.is_public = False
        self.created = None
        self.snapshot_id = None

    def save(self, db = None)
        db.do(db,
              lambda cursor:
              if self.created:
                cursor.execute(
                    'update Playlist '
                    'set user_id = %s,'
                    'name = %s,'
                    'description = %s,'
                    'is_public = %s,'
                    'created = %s,'
                    'snapshot_id = %s '
                    'where id = %s',
                (self.user_id, self.name, self.description,
                 self.is_public, self.created, self.snapshot_id))
              else:
                self.created = datetime.utcnow()
                cursor.execute(
                    'insert into Playlist('
                    'id, user_id, name, description, is_public,'
                    'created, snapshot_id)'
                    'values(%s, %s, %s, %s, %s, %s, %s)',
                (self.id, self.user_id, self.name, self.description,
                 self.is_public, self.created, self.snapshot_id))
