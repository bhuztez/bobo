def create_table(cur):
    cur.execute(
'''
CREATE TABLE IF NOT EXISTS blob (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  hash TEXT UNIQUE,
  state INTEGER
)
''')

    cur.execute(
'''
CREATE TABLE IF NOT EXISTS reference (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  from_id INTEGER REFERENCES blob (id),
  to_id INTEGER REFERENCES blob (id),
  UNIQUE(from_id, to_id)
)
''')

    cur.execute(
'''
CREATE TABLE IF NOT EXISTS channel (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  key TEXT UNIQUE,
  root_id INTEGER REFERENCES blob (id)
)
''')

    cur.execute(
'''
CREATE TABLE IF NOT EXISTS entry (
  id INTEGER PRIMARY KEY REFERENCES blob (id),
  channel_id INTEGER REFERENCES channel (id),
  timestamp INTEGER NOT NULL
)
''')


def get_chan_id(cur, key):
    cur.execute('''INSERT OR IGNORE INTO channel(key) VALUES (?)''', (key,))
    return cur.execute('''SELECT id FROM channel WHERE key=?''', (key,)).fetchone()[0]


def get_blob_id(cur, hash):
    cur.execute('''INSERT OR IGNORE INTO blob(hash, state) VALUES (?, ?)''', (hash,0))
    return cur.execute('''SELECT id FROM blob WHERE hash=?''', (hash,)).fetchone()[0]


def add_link(cur, from_hash, to_hash):
    from_id = get_blob_id(cur, from_hash)
    to_id = get_blob_id(cur, to_hash)
    cur.execute('''INSERT OR IGNORE INTO reference(from_id, to_id) VALUES (?, ?)''', (from_id, to_id))


def find_blobs_to_fetch(cur, root_hashes):
    root_ids = [get_blob_id(cur, h) for h in root_hashes]
    results = cur.execute(
'''
WITH RECURSIVE ancestor(blob_id, ancestor_id) AS (
  SELECT id, id FROM blob WHERE state=0
  UNION ALL
  SELECT ancestor.blob_id, reference.from_id
  FROM ancestor JOIN reference ON ancestor.ancestor_id = reference.to_id
)
SELECT blob.hash FROM ancestor JOIN blob on ancestor.blob_id = blob.id
WHERE NOT EXISTS(SELECT 1 FROM reference WHERE ancestor.ancestor_id = reference.to_id)
AND ancestor.ancestor_id IN (%s)''' % (','.join('?' * len(root_ids))), root_ids).fetchall()
    return [r[0] for r in results]


def add_channel_entry(cur, key, hash, timestamp):
    channel_id = get_chan_id(cur, key)
    blob_id = get_blob_id(cur, hash)
    cur.execute('''INSERT OR IGNORE INTO entry(id, channel_id, timestamp) VALUES (?, ?, ?)''', (blob_id, channel_id, timestamp))


def list_channel_entries(cur, key):
    results = cur.execute('''
SELECT blob.hash FROM entry
JOIN blob ON entry.id = blob.id
JOIN channel ON entry.channel_id = channel.id
WHERE channel.key=?
ORDER BY blob.hash''', (key,)).fetchall()
    return [r[0] for r in results]


def list_channels(cur):
    results = cur.execute('''SELECT key FROM channel''').fetchall()
    return [r[0] for r in results]


def get_channel_root(cur, key):
    result = cur.execute('''
SELECT blob.hash FROM channel
JOIN blob ON channel.root_id = blob.id
WHERE key=?''', (key,)).fetchone()

    if result:
        return result[0]


def set_channel_root(cur, key, hash):
    blob_id = get_blob_id(cur, hash)
    cur.execute('''UPDATE channel set root_id=? WHERE key=?''', (blob_id, key))


def mark_finished(cur, hash):
    blob_id = get_blob_id(cur, hash)
    cur.execute('''UPDATE blob SET state=1 WHERE id=?''', (blob_id,))
