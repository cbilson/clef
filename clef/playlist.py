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
        app.logger.debug('Adding track %s to playlist %s, added_at=%s, added_by=%s'
                         % (track.id, self.id, added_at, added_by))
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

    def import_playlist(user, pl_id, owner_id, albums,  artists, tracks):
        new_track_count = 0
        new_album_count = 0
        new_artist_count = 0
        playlist_js = spotify.get_playlist(user, pl_id, owner_id)

        pl = Playlist.from_json(playlist_js)
        pl.save()

        new_track_ids = set()
        new_artist_ids = set()
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
                if artist_js['id'] not in artists: new_artist_ids.add(artist_js['id'])
                track_artists.append((track_js['id'], artist_js['id']))

        app.logger.debug('%s new tracks' % len(new_track_ids))
        new_track_count += len(new_track_ids)

        new_album_ids = set()
        album_artists = []
        albums_js = [track['album'] for track in tracks_js]
        album_ids = [album['id'] for album in albums_js if album['id'] not in albums]
        albums.update(Album.load_many(album_ids))
        for album_js in albums_js:
            for artist_js in album_js['artists']:
                album_artists.append((album_js['id'], artist_js['id']))

            if album_js['id'] in albums: continue
            new_album_ids.add(album_js['id'])

        app.logger.debug('%s new albums' % len(new_album_ids))
        new_album_count += len(new_album_ids)

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
        for item_js in items_js:
            added_by = None if 'added_by' not in items_js or item_js['added_by'] is None else item_js['added_by']['id']
            pl.add_track(tracks[item_js['track']['id']], item_js['added_at'], added_by)

        return pl, new_track_count, new_album_count, new_artist_count

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
            app.logger.debug('playlist item: %s' % json.dumps(playlist_item_js))
            pl_id = playlist_item_js['id']
            if playlist_id != None and pl_id != playlist_id:
                app.logger.debug('skipping playlist %s because it was not requested.' % pl_id)
            else:
                owner_id = playlist_item_js['owner']['id']
                snapshot_id = playlist_item_js['snapshot_id']
                pl = Playlist.load(pl_id)
                if pl is not None and pl.snapshot_id == snapshot_id and not force_reimport:
                    app.logger.debug('playlist unchanged (snapshot_id: %s). Force re-importing.' % pl.snapshot_id)
                else:
                    if pl is None:
                        app.logger.debug('new playlist %s' % pl_id)
                    elif pl.snapshot_id != snapshot_id:
                        app.logger.debug('stale: old snapshot_id %s, new snapshot_id %s' % (pl.snapshot_id, snapshot_id))
                    else:
                        app.logger.debug('force_reimport')

                    pl, tc, alc, arc = Playlist.import_playlist(user, pl_id, owner_id, albums,  artists, tracks)
                    new_track_count += tc
                    new_album_count += alc
                    new_artist_count += arc

                    # try:
                    #     pl, tc, alc, arc = Playlist.import_playlist(user, pl_id, owner_id, albums,  artists, tracks)
                    #     new_track_count += tc
                    #     new_album_count += alc
                    #     new_artist_count += arc
                    # except:
                    #     e = sys.exc_info()[0]
                    #     app.logger.error('Failed to import playlist %s: %s' % (pl_id, e))

                app.logger.debug('adding follow of %s to user %s' % (pl.id, user.id))
                user.add_playlist(pl)

        app.logger.debug('total tracks: %s, albums: %s, artists: %s' % (len(tracks), len(albums), len(artists)))
        return new_track_count, new_album_count, new_artist_count

    def import_user_playlist(user, playlist_id, force_reimport=False):
        """
        Import a single user playlist from spotify.
        This is mostly for testing, so I don't go over the spotify
        limits.
        """
        return Playlist._import_user_playlists(user, playlist_id=playlist_id, force_reimport=force_reimport)

    def import_user_playlists(user, force_reimport=False):
        """
        Reloads all of a users playlists from spotify.
        Returns the count of tracks, albums, and artists.
        """
        return Playlist._import_user_playlists(user, force_reimport=force_reimport)

    def remove_playlists(user, playlist_id=None):
        cursor = mysql.connection.cursor()
        cursor.execute(
            'delete from PlaylistFollow where playlist_id = %s',
            (playlist_id,))
        cursor.execute(
            'delete from PlaylistImage where playlist_id = %s',
            (playlist_id,))
        cursor.execute(
            'delete from Playlist where id = %s',
            (playlist_id,))

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
