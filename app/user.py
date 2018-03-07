from datetime import datetime, timedelta
import app.db

def load(id, connection = None):
    close_connection = False
    if not connection:
        connection = db.connect()
        close_connection = True

    cursor = connection.cursor()
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

    if close_connection:
        connection.close()

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

class User:
    def __init__(self, id):
        self.id = id
        self.name = ''
        self.email = ''
        self.joined = None
        self.average_dancability = 0.0
        self.access_token = None
        self.token_expiration = None
        self.refresh_token = None

    def token_refreshed(self, response_json):
        self.access_token = response_json['access_token']
        self.token_expiration = datetime.utcnow() + timedelta(seconds=response_json['expires_in'])

        if 'refresh_token' in response_json.keys():
            self.refresh_token = response_json['refresh_token']

    def save(self, db_connection = None):
        close_connection = False
        if not db_connection:
            db_connection = db.connect()
            close_connection = True

        cursor = db_connection.cursor()

        # use joined to determine if it's new?
        if not self.joined:
            self.joined = datetime.utcnow()
            cursor.execute('insert into User(id, name, email, '
                           'joined, average_dancability, access_token, '
                           'token_expiration, refresh_token) '
                           'values(%s, %s, %s, %s, %s, %s, %s, %s)',
                           (self.id, self.name, self.email,
                            self.joined, self.average_dancability,
                            self.access_token, self.token_expiration,
                            self.refresh_token))
        else:
            cursor.execute('update User '
                           'set name = %s, '
                           'email = %s, '
                           'joined = %s, '
                           'average_dancability = %s, '
                           'access_token = %s, '
                           'token_expiration = %s, '
                           'refresh_token = %s '
                           'where id = %s',
                           (self.name, self.email, self.joined,
                            self.average_dancability,
                            self.access_token, self.token_expiration, self.refresh_token,
                            self.id))

        db_connection.commit()
        if close_connection:
            db_connection.close()
