from datetime import datetime, timedelta
from clef import mysql, app
from clef.spotify import get_playlist_tracks
from clef.artist import Artist
from clef.track import Track
from clef.album import Album

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

    def refresh(user):
        """Refreshes playlists in our database with data from spotify."""
        original_playlists = {pl.id:pl for pl in Playlists.for_user(user)}
        current_playlists = {pl.id:pl for pl in Playlist.from_json(json) for json in get_all_playlists(user)}
        deleted_playlists = [pl for pl in original_playlists if pl.id not in current_playlists]
        keep_playlists = [pl for pl in original_playlists if pl.id in current_playlists]
        updated_playlists = [pl for pl in keep_playlists if pl.snapshot_id != current_playlists[pl.id].snapshot_id]
        new_playlists = [pl for pl in current_playlists if pl.id not in original_playlists]

        for pl in deleted_playlists:
            user.remove_playlist(pl)

        for pl in updated_playlists + new_playlists:
            status, json = get_playlist_tracks(user, pl)
            if status != 200:
                app.logger.error('Failed to get playlist tracks. %s, %s' % status, json)
                abort(status)

            tracks_js = [item for item in json['items'] if item['track']['id'] is not None]
            albums_js = dict()
            for album in [track['track']['album'] for track in tracks_js]:
                if album['id'] is None: continue
                if album['id'] not in albums_js:
                    albums_js[album['id']] = album

            artists_js = dict()
            for album in albums_js.values():
                for artist in album['artists']:
                    if artist['id'] is None: continue
                    if artist['id'] not in artists_js:
                        artists_js[artist['id']] = artist

            for track in tracks_js:
                for artist in track['track']['artists']:
                    if artist['id'] is None: continue
                    if artist['id'] not in artists_js:
                        artists_js[artist['id']] = artist

            artists = [Artist.from_json(x) for x in artists_js.values()]
            artists_dict = dict()
            for artist in artists:
                artist.save()
                artists_dict[artist.id] = artist

            albums = [Album.from_json(x) for x in albums_js.values()]
            albums_dict = dict()

            for album in albums:
                album.save()
                albums_dict[album.id] = album

            for artist_id in [artist['id'] for artist in albums_js[album.id]['artists'] if id in artist]:
                artist = artists_dict[artist_id]
                album.add_artist(artist)

            # TODO: link to images

            tracks = list()
            for track_js in tracks_js:
                track = Track.from_json(track_js['track'])
                track.save()
                tracks.append(track)

                if 'added_by' in track_js and track_js['added_by'] is not None:
                    added_by = track_js['added_by']['id']
                    playlist.add_track(track, track_js['added_at'], added_by)

                for artist_id in [artist['id'] for artist in track_js['track']['artists'] if id in artist]:
                    artist = artists_dict[artist_id]
                    track.add_artist(artist)

        # TODO: return deleted, updated, new playlist ids and stats about tracks, artists, albums.
        return {}

class PlaylistSummaryView:
    def __init__(self, id, name, track_count, is_new=False, is_deleted=False, is_updated=False):
        self.id = id
        self.name = name
        self.track_count = track_count
        self.is_new = False
        self.is_deleted = False
        self.is_updated = False

    def __repr__(self):
        return ('PlaylistSummaryView(id="%s", name="%s", track_count=%s, is_new=%s, is_deleted=%s, is_updated=%s)'
                % (self.id, self.name, self.track_count, self.is_new, self.is_deleted, self.is_updated))

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
