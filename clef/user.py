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

        if 'refresh_token' in response_json.keys():
            self.refresh_token = response_json['refresh_token']
            self.save()

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
