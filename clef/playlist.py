import sys
import json
import clef.spotify as spotify

from datetime import datetime, timedelta
from flask import abort
from clef import mysql, app
from clef.artist import Artist
from clef.track import Track
from clef.album import Album

class Playlist:
    def __init__(self, id, owner=None, name=None, description=None, public=False, snapshot_id=None):
        self.id = id
        self.owner = owner
        self.name = name
        self.description = description
        self.public = False
        self.snapshot_id = snapshot_id

    def __repr__(self):
        ctor_args = [
            'id="%s"' % self.id,
            'owner="%s"' % self.owner,
            'name=None' if not self.name else 'name="%s"' % self.name,
            'description=None' if not self.description else 'description="%s"' % self.description,
            'public=%s' % self.public,
            'snapshot_id=None' if not self.snapshot_id else 'snapshot_id="%s"' % self.snapshot_id]
        return 'Playlist(%s)' % ', '.join(ctor_args)

    def _from_row(row):
        if row: return Playlist(row[0], row[1], row[2], row[3], row[4], row[5])

    def load(id):
        cursor = mysql.connection.cursor()
        cursor.execute('select id, owner, name, description, public, snapshot_id '
                       'from Playlist '
                       'where id = %s',
                       (id,))

        row = cursor.fetchone()
        return Playlist._from_row(row)

    def for_user(user):
        cursor = mysql.connection.cursor()
        cursor.execute('select p.id, p.owner, p.name, p.description, p.public, p.snapshot_id '
                       'from Playlist p '
                       '  inner join PlaylistFollow pf on p.id = pf.playlist_id '
                       'where pf.user_id = %s',
                       (user.id,))
        return [Playlist._from_row(row) for row in cursor]

    def from_json(json):
        return Playlist(json['id'], json['owner']['id'], json['name'], json['description'],
                        json['public'], json['snapshot_id'])

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
            'insert into Playlist(id, owner, name, description, public, snapshot_id) '
            'values (%s, %s, %s, %s, %s, %s) '
            'on duplicate key update '
            'owner=%s, name=%s, description=%s, public=%s, snapshot_id=%s',
            (self.id, self.owner, self.name, self.description, self.public, self.snapshot_id,
             self.owner, self.name, self.description, self.public, self.snapshot_id))

    def _import_user_playlists(user, playlist_id=None, force_reimport=False):
        """
        Imports a set of playlists for a user.
        Returns the number of tracks, albums, and artists added.
        """
        new_track_count = 0
        new_album_count = 0
        new_artist_count = 0

        # cache albums, artists, and tracks by id
        albums = {}
        artists = {}
        tracks = {}

        for playlist_item_js in spotify.get_user_playlists(user):
            pl_id = playlist_item_js['id']
            if playlist_id != None and pl_id != playlist_id: continue
            owner_id = playlist_item_js['owner']['id']
            snapshot_id = playlist_item_js['snapshot_id']
            app.logger.debug("loading playlist %s/%s..." % (owner_id, pl_id))
            pl = Playlist.load(pl_id)
            if pl is not None:
                if pl.snapshot_id == snapshot_id:
                    app.logger.debug('playlist unchanged (snapshot_id: %s)' % pl.snapshot_id)
                    if not force_reimport:
                        continue

                    app.logger.debug('reimporting unchanged playlist, due to force_reimport')
                else:
                    app.logger.debug('playlist has changed, refreshing. old snapshot_id: %s, new snapshot_id: %s' %
                                     (pl.snapshot_id, snapshot_id))
            else:
                app.logger.debug('importing new playlist %s' % pl_id)

            playlist_js = spotify.get_playlist(user, pl_id, owner_id)
            pl = Playlist.from_json(playlist_js)
            pl.save()

            new_track_ids = set()
            track_albums = []
            track_artists = []
            items_js = [item for item in spotify.get_playlist_tracks(user, pl)]
            tracks_js = [item['track'] for item in items_js]
            track_ids = [track['id'] for track in tracks_js if track['id'] not in tracks]
            tracks.update(Track.load_many(track_ids))
            for track_js in tracks_js:
                if track_js['id'] in tracks: continue
                new_track_ids.add(track_js['id'])
                track_albums.append((track_js['id'], track_js['album']['id']))
                for artist_js in track_js['artists']:
                    track_artists.append((track_js['id'], artist_js['id']))

            app.logger.debug('%s new tracks' % len(new_track_ids))
            new_track_count += len(new_track_ids)

            new_album_ids = set()
            albums_js = [track['album'] for track in tracks_js]
            album_ids = [album['id'] for album in albums_js if album['id'] not in albums]
            albums.update(Album.load_many(album_ids))
            for album_id in album_ids:
                if album_id in albums: continue
                new_album_ids.add(album_id)

            app.logger.debug('%s new albums' % len(new_album_ids))
            new_album_count += len(new_album_ids)

            # assumption: track.artists \subset track.album.artists
            new_artist_ids = set()
            artists_js = [artist for album in albums_js for artist in album['artists']]
            artist_ids = [artist['id'] for artist in artists_js if artist['id'] not in artists]
            artists.update(Artist.load_many(artist_ids))
            for artist_id in artist_ids:
                if artist_id in artists: continue
                new_artist_ids.add(artist_id)

            app.logger.debug('%s new artists' % len(new_artist_ids))
            new_artist_count += len(new_artist_ids)

            # import new artists
            for artist_js in spotify.get_artists(user, new_artist_ids):
                artist = Artist.import_json(artist_js)
                artists[artist.id] = artist

            for album_js in spotify.get_albums(user, new_album_ids):
                album = Album.import_json(album_js)
                albums[album.id] = album

            for track_js in spotify.get_tracks(user, new_track_ids):
                track = Track.import_json(track_js)
                tracks[track.id] = track

            app.logger.debug("linking artists and tracks")
            for track_id, artist_id in track_artists:
                tracks[track_id].add_artist(artists[artist_id])

            app.logger.debug("linking artists and albums")
            for album_id, artist_id in album_artists:
                albums[album_id].add_artist(artists[artist_id])

            app.logger.debug("linking tracks and playlists")
            for track_id in new_track_ids:
                pl.add_track(tracks[track_id])

        return new_track_count, new_album_count, new_artist_count

    def import_user_playlist(user, playlist_id):
        """
        Import a single user playlist from spotify.
        This is mostly for testing, so I don't go over the spotify
        limits.
        """
        return Playlist._import_user_playlists(user, playlist_id=playlist_id)

    def import_user_playlists(user):
        """
        Reloads all of a users playlists from spotify.
        Returns the count of tracks, albums, and artists.
        """
        owner_playlist_ids = [(pl.owner, pl.id) for pl in Playlist.for_user(user)]
        return Playlist._import_user_playlists(user, owner_playlist_ids)

    def refresh(user):
        """Refreshes playlists in our database with data from spotify."""
        original_playlists = {pl.id:pl for pl in Playlist.for_user(user)}
        spotify_playlists = [Playlist.from_json(js) for js in get_all_playlists(user)]
        current_playlists = {pl.id:pl for pl in spotify_playlists}
        deleted_playlists = [pl for pl in original_playlists.values() if pl.id not in current_playlists]
        keep_playlists = [pl for pl in original_playlists.values() if pl.id in current_playlists]
        updated_playlists = [pl for pl in keep_playlists if pl.snapshot_id != current_playlists[pl.id].snapshot_id]
        new_playlists = [pl for pl in current_playlists.values() if pl.id not in original_playlists]
        result = PlaylistRefreshResults(
            [pl.id for pl in new_playlists],
            [pl.id for pl in updated_playlists],
            [pl.id for pl in deleted_playlists])

        app.logger.debug('original: %s, current: %s, deleted: %s, updated: %s, new: %s',
                         len(original_playlists), len(current_playlists), len(deleted_playlists),
                         len(updated_playlists), len(new_playlists))

        for pl in deleted_playlists:
            app.logger.debug('removing %s' % pl)
            user.remove_playlist(pl)

        t, al, ar = Playlist._import_user_playlists(user, result.updated_playlists + result.new_playlists)
        result.track_count = t
        result.artist_count = ar
        result.album_count = al

        return result

class PlaylistRefreshResults:
    def __init__(self, new=[], updated=[], deleted=[], track_count=0, artist_count=0, album_count=0):
        self.new = new
        self.updated = updated
        self.deleted = deleted
        self.track_count = track_count
        self.artist_count = artist_count
        self.album_count = album_count

    def __repr__(self):
        new = '[]' if len(self.new) == 0 else "['%s']" % "', '".join(self.new)
        updated = '[]' if len(self.updated) == 0 else "['%s']" % "', '".join(self.updated)
        deleted = '[]' if len(self.deleted) == 0 else "['%s']" % "', '".join(self.deleted)
        return ('PlaylistRefreshResults(new=%s, updated=%s, deleted=%s, track_count=%s, artist_count=%s, album_count=%s)'
                % (new, updated, deleted, self.track_count, self.artist_count, self.album_count))

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
