import sqlite3


def create_table(cur):
    cur.execute(
'''
CREATE TABLE IF NOT EXISTS object (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  hash TEXT UNIQUE,
  state INTEGER
)
''')

    cur.execute(
'''
CREATE TABLE IF NOT EXISTS reference (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  from_id INTEGER REFERENCES object (id),
  to_id INTEGER REFERENCES object (id),
  UNIQUE(from_id, to_id)
)
''')

    cur.execute(
'''
CREATE TABLE IF NOT EXISTS feed (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  key TEXT UNIQUE,
  root_id INTEGER REFERENCES object (id)
)
''')

    cur.execute(
'''
CREATE TABLE IF NOT EXISTS item (
  id INTEGER PRIMARY KEY REFERENCES object (id),
  feed_id INTEGER REFERENCES feed (id),
  timestamp INTEGER NOT NULL
)
''')


class Index:

    def __init__(self, path=':memory:'):
        self.conn = sqlite3.connect(path)
        self.conn.execute('''PRAGMA foreign_keys = ON''')
        with self.conn:
            create_table(self.conn.cursor())

    def get_feed_id(self, key):
        with self.conn:
            self.conn.execute('''INSERT OR IGNORE INTO feed(key) VALUES (?)''', (key,))

        with self.conn:
            return self.conn.execute('''SELECT id FROM feed WHERE key=?''', (key,)).fetchone()[0]

    def get_object_id(self, hash):
        with self.conn:
            self.conn.execute('''INSERT OR IGNORE INTO object(hash, state) VALUES (?, ?)''', (hash,0))

        with self.conn:
            return self.conn.execute('''SELECT id FROM object WHERE hash=?''', (hash,)).fetchone()[0]

    def add_link(self, from_hash, to_hash):
        from_id = self.get_object_id(from_hash)
        to_id = self.get_object_id(to_hash)

        with self.conn:
            self.conn.execute('''INSERT OR IGNORE INTO reference(from_id, to_id) VALUES (?, ?)''', (from_id, to_id))

    def find_objects_to_fetch(self, root_hashes):
        root_ids = [self.get_object_id(h) for h in root_hashes]

        with self.conn:
            results = self.conn.execute(
'''
WITH RECURSIVE ancestor(object_id, ancestor_id) AS (
  SELECT id, id FROM object WHERE state=0
  UNION ALL
  SELECT ancestor.object_id, reference.from_id
  FROM ancestor JOIN reference ON ancestor.ancestor_id = reference.to_id
)
SELECT object.hash FROM ancestor JOIN object on ancestor.object_id = object.id
WHERE NOT EXISTS(SELECT 1 FROM reference WHERE ancestor.ancestor_id = reference.to_id)
AND ancestor.ancestor_id IN (%s)''' % (','.join('?' * len(root_ids))), root_ids).fetchall()
        return [r[0] for r in results]

    def add_feed_item(self, key, hash, timestamp):
        feed_id = self.get_feed_id(key)
        object_id = self.get_object_id(hash)

        with self.conn:
            self.conn.execute('''INSERT OR IGNORE INTO item(id, feed_id, timestamp) VALUES (?, ?, ?)''', (object_id, feed_id, timestamp))

    def list_feed_items(self, key):
        with self.conn:
            results = self.conn.execute('''SELECT object.hash FROM item JOIN object ON item.id = object.id JOIN feed ON item.feed_id = feed.id WHERE feed.key=? ORDER BY object.hash''', (key,)).fetchall()
        return [r[0] for r in results]

    def list_feed_keys(self):
        with self.conn:
            results = self.conn.execute('''SELECT key FROM feed''').fetchall()
        return [r[0] for r in results]

    def get_feed_root(self, key):
        with self.conn:
            result = self.conn.execute('''SELECT object.hash FROM feed JOIN object ON feed.root_id = object.id WHERE key=?''', (key,)).fetchone()

        if result:
            return result[0]

    def set_feed_root(self, key, hash):
        object_id = self.get_object_id(hash)

        with self.conn:
            self.conn.execute('''UPDATE feed set root_id=? WHERE key=?''', (object_id, key))

    def mark_finished(self, hash):
        object_id = self.get_object_id(hash)
        with self.conn:
            self.conn.execute('''UPDATE object SET state=1 WHERE id=?''', (object_id,))
