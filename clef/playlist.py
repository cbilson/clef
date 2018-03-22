from datetime import datetime, timedelta
from clef import mysql, app

class Playlist:
    def __init__(self, id, href=None, owner=None, name=None, public=False, snapshot_id=None, tracks_url=None):
        self.id = id
        self.href = href
        self.owner = owner
        self.name = name
        self.public = False
        self.snapshot_id = snapshot_id
        self.tracks_url = tracks_url

    def __repr__(self):
        ctor_args = [
            'id="%s"' % self.id,
            'href="%s"' % self.href,
            'owner="%s"' % self.owner,
            'name=None' if not self.name else 'name="%s"' % self.name,
            'public=%s' % self.public,
            'snapshot_id=None' if not self.snapshot_id else 'snapshot_id="%s"' % self.snapshot_id,
            'tracks_url=None' if not self.tracks_url else 'tracks_url="%s"' % self.tracks_url]
        return 'Playlist(%s)' % ', '.join(ctor_args)

    def _from_row(row):
        return Playlist(row[0], row[1], row[2], row[3], row[4], row[5], row[6])

    def load(id):
        cursor = mysql.connection.cursor()
        cursor.execute('select id, href, owner, name, public, snapshot_id, tracks_url '
                       'from Playlist '
                       'where id = %s',
                       (id,))

        row = cursor.fetchone()
        return Playlist._from_row(row)

    def for_user(user):
        cursor = mysql.connection.cursor()
        cursor.execute('select p.id, p.href, p.owner, p.name, p.public, p.snapshot_id, p.tracks_url '
                       'from Playlist p '
                       '  inner join PlaylistFollow pf on p.id = pf.playlist_id '
                       'where pf.user_id = %s',
                       (user.id,))
        return [Playlist._from_row(row) for row in cursor]

    def from_json(json):
        return Playlist(json['id'], json['href'], json['owner']['id'], json['name'],
                        json['public'], json['snapshot_id'], json['tracks']['href'])

    def delete(self):
        mysql.connection.cursor().execute('delete from Playlist where id = %s', (self.id,))

    def add_track(self, track, added_at, added_by):
        cursor = mysql.connection.cursor()
        cursor.execute('insert into PlaylistTrack(playlist_id, track_id, added_at, added_by) '
                       'values(%s,%s,%s,%s) '
                       'on duplicate key update '
                       'added_at=%s, added_by=%s',
                       (self.id, track.id, added_at, added_by, added_at, added_by))

    def save(self):
        cursor = mysql.connection.cursor()
        cursor.execute(
            'insert into Playlist(id, href, owner, name, public, snapshot_id, tracks_url) '
            'values (%s, %s, %s, %s, %s, %s, %s) '
            'on duplicate key update '
            'href=%s, owner=%s, name=%s, public=%s, snapshot_id=%s, tracks_url=%s',
            (self.id, self.href, self.owner,
             self.name, self.public,
             self.snapshot_id, self.tracks_url,
             self.href, self.owner,
             self.name, self.public,
             self.snapshot_id, self.tracks_url))

class PlaylistSummaryView:
    def __init__(self, id, name, track_count):
        self.id = id
        self.name = name
        self.track_count = track_count

    def __repr__(self):
        return 'PlaylistSummaryView(id="%s", name="%s", track_count=%s)' % (self.id, self.name, self.track_count)

    def for_user(user):
        cursor = mysql.connection.cursor()
        cursor.execute(
            'select p.id, p.name, count(*) '
            'from Playlist p '
            '  inner join PlaylistFollow pf on p.id = pf.playlist_id '
            '  inner join PlaylistTrack pt on p.id = pt.playlist_id '
            'where pf.user_id=%s '
            'group by p.id',
            (user.id,))
        return [PlaylistSummaryView(row[0], row[1], row[2]) for row in cursor]
