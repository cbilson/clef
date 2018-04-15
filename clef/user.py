import json
from datetime import datetime, timedelta
from clef import mysql, app

class User:
    def __init__(self, id, name='', email='', joined=None, average_dancability=0.0, access_token=None,
                 token_expiration=None, refresh_token=None, status=None):
        self.id = id
        self.name = name
        self.email = email
        self.joined = joined
        self.average_dancability = average_dancability
        self.access_token = access_token
        self.token_expiration = token_expiration
        self.refresh_token = refresh_token
        self.status = status
        self.is_admin = id in {'1228285312', 'hannparkk', 'cbilson'}

    def __repr__(self):
        ctor_args = [
            'id="%s"' % self.id,
            'name="%s"' % self.name,
            'email="%s"' % self.email,
            'joined=None' if not self.joined else 'joined=%s' % repr(self.joined),
            'average_dancability=%s' % self.average_dancability,
            'access_token=None' if not self.access_token else 'access_token="%s"' % self.access_token,
            'token_expiration=None' if not self.token_expiration else 'token_expiration=%s' % repr(self.token_expiration),
            'refresh_token=None' if not self.refresh_token else 'refresh_token="%s"' % self.refresh_token,
            'status=None' if not self.status else 'status="%s"' % self.status]
        return 'User(%s)' % ', '.join(ctor_args)

    def load(id):
        cursor = mysql.connection.cursor()
        cursor.execute("""
        select   name, email, joined, average_dancability,
                 access_token, token_expiration, refresh_token, status
        from     User
        where    id = %s
        """, (id,))

        if cursor.rowcount == 0:
            return None

        row = cursor.fetchone()
        user = User(id)
        user.name = row[0]
        user.email = row[1]
        user.joined = row[2]
        user.average_dancability = row[3]
        user.access_token = row[4]
        user.token_expiration = row[5]
        user.refresh_token = row[6]
        user.status = row[7]
        app.logger.debug('Loaded user %s' % (user.id))
        return user

    def from_json(json, auth_info = None):
        u = User(json['id'])
        u.name = json['display_name']
        u.email = json['email']

        if auth_info:
            u.access_token = auth_info['access_token']
            u.token_expiration = datetime.utcnow() + timedelta(seconds=auth_info['expires_in'])
            u.refresh_token = auth_info['refresh_token']

        return u

    def token_refreshed(self, response_json):
        self.access_token = response_json['access_token']
        self.token_expiration = datetime.utcnow() + timedelta(seconds=response_json['expires_in'])
        app.logger.debug('user %s token refreshed, token_expiration: %s' % (self.id, self.token_expiration))

        if 'refresh_token' in response_json.keys():
            app.logger.debug('refresh_token updated')
            self.refresh_token = response_json['refresh_token']

        self.save()

    # TODO: rename 'follow_playlist'
    def add_playlist(self, playlist):
        self.follow_playlist_id(playlist.id)

    def follow_playlist_id(self, playlist_id):
        app.logger.debug("User %s following playlist %s." % (self.id, playlist_id))
        cursor = mysql.connection.cursor()
        cursor.execute('insert into PlaylistFollow(playlist_id, user_id) '
                       'values(%s, %s) '
                       'on duplicate key update playlist_id=%s',
                       (playlist_id, self.id, playlist_id))

    def remove_playlist(self, playlist):
        self.unfollow_playlist_id(playlist.id)

    def unfollow_playlist_id(self, playlist_id):
        app.logger.debug("User %s unfollowing playlist %s." % (self.id, playlist_id))
        cursor = mysql.connection.cursor()
        cursor.execute('delete from PlaylistFollow '
                       'where playlist_id=%s and user_id=%s',
                       (playlist_id, self.id))

    def save(self):
        cursor = mysql.connection.cursor()
        cursor.execute("""
        insert into User(id, name, email, joined, average_dancability, access_token,
                    token_expiration, refresh_token, status)
                    values(%s, %s, %s, %s, %s, %s, %s, %s, %s)
        on duplicate key
        update      name=%s, email=%s, joined=%s, average_dancability=%s, access_token=%s,
                    token_expiration=%s, refresh_token=%s, status=%s""",
                       (self.id, self.name, self.email,
                        self.joined, self.average_dancability,
                        self.access_token, self.token_expiration,
                        self.refresh_token, self.status,
                        self.name, self.email,
                        self.joined, self.average_dancability,
                        self.access_token, self.token_expiration,
                        self.refresh_token, self.status))
        app.logger.info('User %s updated' % self.id)

    def display_name(self):
        if self.name is not None:
            return self.name

        return self.email

class UserArtistOverview:
    def for_user(user):
        cursor = mysql.connection.cursor()
        cursor.execute("""
        SELECT T6.Users_Artists AS Users_Artists, COUNT(*) - 1 AS Number_of_Songs_by_the_Artist
                       FROM (
                       SELECT DISTINCT artist.name AS Users_Artists
                       FROM albumartist, artist
                       WHERE album_id IN (
                       SELECT album_id
                       FROM track
                       WHERE track.id IN (
                       SELECT DISTINCT track_id
                       FROM playlisttrack
                       WHERE playlisttrack.playlist_id IN (
                       SELECT DISTINCT id AS playlist_id
                       FROM playlist
                       WHERE playlist.owner = %s))) AND albumartist.artist_id = artist.id
                       UNION ALL
                       SELECT artist.name AS Users_Artists
                       FROM albumartist, artist
                       WHERE album_id IN (
                       SELECT album_id
                       FROM track
                       WHERE track.id IN (
                       SELECT track_id
                       FROM playlisttrack
                       WHERE playlisttrack.playlist_id IN (
                       SELECT DISTINCT id AS playlist_id
                       FROM playlist
                       WHERE playlist.owner = %s))) AND albumartist.artist_id = artist.id
                       ) AS T6
                       GROUP BY T6.Users_Artists""",
                       (user.id, user.id))
        return [(row[0], row[1]) for row in cursor]

class UserListEntry:
    def __init__(self, row):
        self.id = row[0]
        self.name = row[1]
        self.joined = row[2]
        self.email = row[3]
        self.status = row[4]
        self.playlist_count = row[5]

    def get(user_id):
        cursor = mysql.connection.cursor()
        cursor.execute("""
        select    u.id, u.name, u.joined, u.email, u.status, count(pf.user_id)
        from      User u
                  left outer join PlaylistFollow pf on u.id = pf.user_id
        where     user_id = %s
        group by  u.id, u.name, u.joined, u.email, u.status;
        """, (user_id,))
        row = cursor.fetchone()
        return UserListEntry(row)

class UserList:
    def __init__(self):
        cursor = mysql.connection.cursor()
        cursor.execute("""
        select    u.id, u.name, u.joined, u.email, u.status, count(pf.user_id)
        from      User u
                  left outer join PlaylistFollow pf on u.id = pf.user_id
        group by  u.id, u.name, u.joined, u.email, u.status;
        """)
        self.users = [UserListEntry(row) for row in cursor]
        self.total = len(self.users)
        self.total_new = len([u for u in self.users if u.status == 'New' or u.playlist_count == 0])
