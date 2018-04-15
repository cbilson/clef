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
    def __init__(self, id, owner=None, name=None, description=None, public=False, snapshot_id=None, status='New'):
        self.id = id
        self.owner = owner
        self.name = name
        self.description = description
        self.public = False
        self.snapshot_id = snapshot_id
        self.status = status

    def __repr__(self):
        ctor_args = [
            'id="%s"' % self.id,
            'owner="%s"' % self.owner,
            'name=None' if not self.name else 'name="%s"' % self.name,
            'description=None' if not self.description else 'description="%s"' % self.description,
            'public=%s' % self.public,
            'snapshot_id=None' if not self.snapshot_id else 'snapshot_id="%s"' % self.snapshot_id,
            'status="%s"' % self.status]
        return 'Playlist(%s)' % ', '.join(ctor_args)

    def _from_row(row):
        if row: return Playlist(row[0], row[1], row[2], row[3], row[4], row[5], row[6])

    def load(id):
        cursor = mysql.connection.cursor()
        cursor.execute('select id, owner, name, description, public, snapshot_id, status '
                       'from Playlist '
                       'where id = %s',
                       (id,))

        row = cursor.fetchone()
        return Playlist._from_row(row)

    def for_user(user):
        cursor = mysql.connection.cursor()
        cursor.execute('select p.id, p.owner, p.name, p.description, p.public, p.snapshot_id, status '
                       'from Playlist p '
                       '  inner join PlaylistFollow pf on p.id = pf.playlist_id '
                       'where pf.user_id = %s',
                       (user.id,))
        return [Playlist._from_row(row) for row in cursor]

    def from_json(json):
        return Playlist(json['id'], json['owner']['id'], json['name'], json.get('description'),
                        json['public'], json['snapshot_id'])

    def delete(self):
        mysql.connection.cursor().execute('delete from Playlist where id = %s', (self.id,))

    def mark_stale(id):
        app.logger.debug('Playlist %s is stale' % id)
        mysql.connection.cursor().execute("update Playlist set status='Stale' where id = %s", (id,))

    def add_track(self, track, added_at, added_by):
        app.logger.debug('Adding track %s to playlist %s, added_at=%s, added_by=%s'
                         % (track.id, self.id, added_at, added_by))
        cursor = mysql.connection.cursor()
        cursor.execute('insert into PlaylistTrack(playlist_id, track_id, added_at, added_by) '
                       'values(%s,%s,%s,%s) '
                       'on duplicate key update '
                       'added_at=%s, added_by=%s',
                       (self.id, track.id, added_at, added_by, added_at, added_by))

    def remove_track(self, track):
        app.logger.debug('Removing track %s to playlist %s' % (track.id, self.id))
        cursor = mysql.connection.cursor()
        cursor.execute('delete from PlaylistTrack '
                       'where playlist_id = %s and track_id = %s ',
                       (self.id, track.id))

    def add_image(self, width, height, url):
        cursor = mysql.connection.cursor()
        cursor.execute('insert into PlaylistImage(playlist_id, width, height, url) '
                       'values(%s,%s,%s,%s) '
                       'on duplicate key update '
                       'width=%s, height=%s, url=%s',
                       (self.id, width, height, url,
                        width, height, url))

    def save(self):
        cursor = mysql.connection.cursor()
        cursor.execute(
            'insert into Playlist(id, owner, name, description, public, snapshot_id, status) '
            'values (%s, %s, %s, %s, %s, %s, %s) '
            'on duplicate key update '
            'owner=%s, name=%s, description=%s, public=%s, snapshot_id=%s, status=%s',
            (self.id, self.owner, self.name, self.description, self.public, self.snapshot_id, self.status,
             self.owner, self.name, self.description, self.public, self.snapshot_id, self.status))

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
        track_ids = {track['id'] for track in tracks_js if track['id'] not in tracks}

        # remove any tracks no longer in the playlist
        existing_tracks = list(Track.for_playlist(pl))
        app.logger.debug("existing tracks in %s: %s" % (pl.id, len(existing_tracks)))
        for existing_track in Track.for_playlist(pl):
            if existing_track.id not in track_ids:
                app.logger.debug('removing %s from %s' % (existing_track.id, pl.id))
                pl.remove_track(existing_track)

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

        pl.status = 'Ready'
        pl.save()

        return pl, new_track_count, new_album_count, new_artist_count

    def _import_user_playlists(user, playlist_id=None, force_reimport=False, continue_on_error=True):
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
                    app.logger.debug('playlist unchanged (snapshot_id: %s).' % pl.snapshot_id)
                else:
                    if pl is None:
                        app.logger.debug('new playlist %s' % pl_id)
                    elif pl.snapshot_id != snapshot_id:
                        app.logger.debug('stale: old snapshot_id %s, new snapshot_id %s' % (pl.snapshot_id, snapshot_id))
                    else:
                        app.logger.debug('force_reimport')
                    try:
                        pl, tc, alc, arc = Playlist.import_playlist(user, pl_id, owner_id, albums,  artists, tracks)
                        new_track_count += tc
                        new_album_count += alc
                        new_artist_count += arc
                    except:
                        e = sys.exc_info()[0]
                        app.logger.error('Failed to import playlist %s: %s' % (pl_id, e))
                        if not continue_on_error: raise

                if pl is None:
                    app.logger.warn('no playlist %s loaded, so not adding follow for user %s' % (pl_id, user.id))
                elif user is None:
                    app.logger.warn('no user loaded, so not adding follow of playlist %s' % (pl.id))
                else:
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
        result = Playlist._import_user_playlists(user, force_reimport=force_reimport)
        app.logger.debug('Setting user status to Ready')
        user.status = 'Ready'
        user.save()
        return result

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
    """Gets a summary of a user's playlists - data shown on the /user/{id}."""
    def __init__(self, id, name, track_count, image_width, image_height, image_url):
        self.id = id
        self.name = name
        self.track_count = track_count
        self.image_width = image_width
        self.image_height = image_height
        self.image_url = image_url

    def __repr__(self):
        return ('PlaylistSummaryView(id="%s", name="%s", track_count=%s, image_width=%s, image_height=%s, image_url="%s")'
                % (self.id, self.name, self.track_count, self.image_width, self.image_height, self.image_url))

    def for_user(user):
        cursor = mysql.connection.cursor()
        cursor.execute(
            'select          pf.playlist_id, p.name, pi.width, pi.height, pi.width * pi.height as img_area, pi.url, count(*) '
            'from            PlaylistFollow pf '
            '                inner join Playlist p on pf.playlist_id = p.id '
            '                inner join PlaylistTrack pt on p.id = pt.playlist_id '
            '                left outer join PlaylistImage pi on p.id = pi.playlist_id '
            'where           pf.user_id=%s '
            'group by        p.id '
            'having          img_area is null or img_area = max(img_area);',
            (user.id,))
        return [PlaylistSummaryView(id=row[0], name=row[1], image_width=row[2], image_height=row[3],
                                    image_url=row[5], track_count=row[6]) for row in cursor]

class PlaylistDetailsView:
    """Gets details about a particular playlist for a user - data for /user/{uid}/playlist/{pid}."""
    def __init__(self):
        self.user_id = None
        self.playlist_id = None
        self.owner_id = None
        self.name = None
        self.explicitness = None
        self.popularity = None
        self.acousticness = None
        self.danceability = None
        self.energy = None
        self.instrumentalness = None
        self.liveness = None
        self.loudness = None
        self.speechiness = None
        self.tempo = None
        self.valence = None
        self.previews = None
        self.genres = None

    def get(user_id, playlist_id):
        cursor = mysql.connection.cursor()
        cursor.execute("""
        -- playlist summary metrics
        select          p.id, p.owner, p.name,
                        avg(acousticness) as acousticness,
                        avg(danceability) as danceability,
                        avg(energy) as energy,
                        avg(instrumentalness) as instrumentalness,
                        avg(liveness) as liveness,
                        avg(loudness) as loudness,
                        avg(speechiness) as speechiness,
                        avg(tempo) as tempo,
                        avg(valence) as valence
        from            Playlist p
                        inner join PlaylistTrack pt on p.id = pt.playlist_id
                        inner join Track t on pt.track_id = t.id
        where           p.id = %s
        group by        p.id;

        -- track previews
        select          t.preview_url
        from            PlaylistTrack pt
                        inner join Track t on pt.track_id = t.id
        where           pt.playlist_id = %s
                        and t.preview_url is not null
        order by        t.popularity desc
        limit           10;

        -- genre analysis
        select          ag.genre, count(*)
        from            PlaylistTrack pt
                        inner join TrackArtist ta on pt.track_id = ta.track_id
                        inner join ArtistGenre ag on ta.artist_id = ag.artist_id
        where           pt.playlist_id = %s
        group by        ag.genre
        order by        count(*) desc
        limit           10;
        """,
                       (playlist_id, playlist_id, playlist_id))

        view = PlaylistDetailsView()

        row = cursor.fetchone()
        view.id = row[0]
        view.owner = row[1]
        view.name = row[2]
        view.acousticness = row[3]
        view.danceability = row[4]
        view.energy = row[5]
        view.instrumentalness = row[6]
        view.liveness = row[7]
        view.loudness = row[8]
        view.speechiness = row[9]
        view.tempo = row[10]
        view.valence = row[11]

        cursor.nextset()
        view.previews = [row[0] for row in cursor]

        cursor.nextset()
        view.genres = {row[0]:row[1] for row in cursor}

        return view

class AdminPlaylistSummaryViewEntry:
    def __init__(self, row):
        self.id = row[0]
        self.owner = row[1]
        self.name = row[2]
        self.description = row[3]
        self.track_count = row[4]
        self.follower_count = None
        self.genres = []

class AdminPlaylistSummaryView:
    def __init__(self, offset=0, limit=100):
        self.offset = 0
        self.limit = 100
        cursor = mysql.connection.cursor()
        cursor.execute("""
        select count(*) from Playlist;

        select          p.id, p.owner, p.name, p.description, count(pt.playlist_id)
        from            Playlist p
                        left outer join PlaylistTrack pt on p.id = pt.playlist_id
        group by        p.id, p.owner, p.name, p.description
        order by        p.name
        limit           %s, %s;

        select          p.id, count(pf.user_id)
        from            Playlist p
                        left outer join PlaylistFollow pf on p.id = pf.playlist_id
        group by        p.id
        order by        p.name
        limit           %s, %s;
        """, (self.offset, self.limit, self.offset, self.limit))
        row = cursor.fetchone()
        self.total_playlists = row[0]
        self.has_more = self.total_playlists > (self.offset + self.limit)

        cursor.nextset()
        playlists = {row[0]:AdminPlaylistSummaryViewEntry(row) for row in cursor}

        cursor.nextset()
        for row in cursor:
            if row[0] in playlists:
                playlists[row[0]].follower_count = row[1]

        self.playlists = playlists.values()
