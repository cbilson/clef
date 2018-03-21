from datetime import datetime, timedelta
from clef import mysql, app

class Artist:
    def __init__(self, id, name, type, href):
        self.id = id
        self.name = name
        self.type = type
        self.href = href

    def __repr__(self):
        ctor_args = [
            'id="%s"' % self.id,
            'name="%s"' % self.name,
            'type="%s"' % self.type,
            'href="%s"' % self.href]

        return 'Artist(%s)' % ', '.join(ctor_args)

    def from_json(json):
        return Artist(json['id'], json['name'], json['type'], json['href'])

    def _from_row(row):
        return Artist(row[0], row[1], row[2], row[3])

    def load(id):
        cursor = mysql.connection.cursor()
        cursor.execute('select id, name, type, href '
                       'from Artist '
                       'where id = %s',
                       (id,))

        if cursor.rowcount == 0:
            return None

        return _from_row(cursor.fetchone())

    def save(self):
        cursor = mysql.connection.cursor()
        cursor.execute('insert into Artist(id, name, type, href) '
                       'values(%s, %s, %s, %s) '
                       'on duplicate key update '
                       'name=%s, type=%s, href=%s',
                       (self.id, self.name, self.type, self.href,
                        self.name, self.type, self.href))
