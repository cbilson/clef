import json
from datetime import datetime, timedelta
from clef import mysql, app

class User:
    def __init__(self, id, name='', email='', joined=None,
                 average_dancability=0.0, access_token=None,
                 token_expiration=None, refresh_token=None):
        self.id = id
        self.name = name
        self.email = email
        self.joined = joined
        self.average_dancability = average_dancability
        self.access_token = access_token
        self.token_expiration = token_expiration
        self.refresh_token = refresh_token

    def __repr__(self):
        ctor_args = [
            'id="%s"' % self.id,
            'name="%s"' % self.name,
            'email="%s"' % self.email,
            'joined=None' if not self.joined else 'joined=%s' % repr(self.joined),
            'average_dancability=%s' % self.average_dancability,
            'access_token=None' if not self.access_token else 'access_token="%s"' % self.access_token,
            'token_expiration=None' if not self.token_expiration else 'token_expiration=%s' % repr(self.token_expiration),
            'refresh_token=None' if not self.refresh_token else 'refresh_token="%s"' % self.refresh_token]
        return 'User(%s)' % ', '.join(ctor_args)

    def load(id):
        cursor = mysql.connection.cursor()
        cursor.execute('select name, email, joined, average_dancability, '
                       'access_token, token_expiration, refresh_token '
                       'from User '
                       'where id = %s',
                       (id,))

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

    def add_playlist(self, playlist):
        cursor = mysql.connection.cursor()
        cursor.execute('insert into PlaylistFollow(playlist_id, user_id) '
                       'values(%s, %s) '
                       'on duplicate key update playlist_id=%s',
                       (playlist.id, self.id, playlist.id))

    def remove_playlist(self, playlist):
        cursor = mysql.connection.cursor()
        cursor.execute('delete from PlaylistFollow '
                       'where playlist_id=%s and user_id=%s',
                       (playlist.id, self.id))

    def save(self):
        cursor = mysql.connection.cursor()
        cursor.execute('insert into User(id, name, email, '
                       'joined, average_dancability, access_token, '
                       'token_expiration, refresh_token) '
                       'values(%s, %s, %s, %s, %s, %s, %s, %s) '
                       'on duplicate key update '
                       'name=%s, email=%s, joined=%s, average_dancability=%s, '
                       'access_token=%s, token_expiration=%s, '
                       'refresh_token=%s',
                       (self.id, self.name, self.email,
                        self.joined, self.average_dancability,
                        self.access_token, self.token_expiration,
                        self.refresh_token, self.name, self.email,
                        self.joined, self.average_dancability,
                        self.access_token, self.token_expiration,
                        self.refresh_token))
        app.logger.info('User %s updated' % self.id)

    def display_name(self):
        if self.name is not None:
            return self.name

        return self.email

class UserArtistOverview:
    def for_user(user):
        cursor = mysql.connection.cursor()
        cursor.execute('SELECT T6.Users_Artists AS Users_Artists, COUNT(*) - 1 AS Number_of_Songs_by_the_Artist '
                       'FROM ('
                       'SELECT DISTINCT artist.name AS Users_Artists '
                       'FROM albumartist, artist '
                       'WHERE album_id IN ( '
                       'SELECT album_id '
                       'FROM track '
                       'WHERE track.id IN ( '
                       'SELECT DISTINCT track_id '
                       'FROM playlisttrack '
                       'WHERE playlisttrack.playlist_id IN ( '
                       'SELECT DISTINCT id AS playlist_id '
                       'FROM playlist '
                       'WHERE playlist.owner = %s))) AND albumartist.artist_id = artist.id '
                       'UNION ALL '
                       'SELECT artist.name AS Users_Artists '
                       'FROM albumartist, artist '
                       'WHERE album_id IN ( '
                       'SELECT album_id '
                       'FROM track '
                       'WHERE track.id IN ( '
                       'SELECT track_id '
                       'FROM playlisttrack '
                       'WHERE playlisttrack.playlist_id IN ( '
                       'SELECT DISTINCT id AS playlist_id '
                       'FROM playlist '
                       'WHERE playlist.owner = %s))) AND albumartist.artist_id = artist.id '
                       ') AS T6 '
                       'GROUP BY T6.Users_Artists',
                       (user.id, user.id))

        return [(row[0], row[1]) for row in cursor]
