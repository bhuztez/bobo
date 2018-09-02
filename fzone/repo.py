import os
from tempfile import NamedTemporaryFile
from hashlib import sha256
import sqlite3

from .index import create_table, add_channel_entry, add_link, mark_finished, set_channel_root, list_channel_entries
from .message import read_message, format_message


class Repo:

    def __init__(self, path):
        self.path = path
        os.makedirs(path, exist_ok=True)
        os.makedirs(self.full_path('cur'), exist_ok=True)
        os.makedirs(self.full_path('new'), exist_ok=True)
        os.makedirs(self.full_path('tmp'), exist_ok=True)

        with sqlite3.connect(self.index()) as conn:
            create_table(conn)

    def full_path(self, *names):
        return os.path.join(self.path, *names)

    def tempfile(self):
        return NamedTemporaryFile(dir=self.full_path('tmp'), delete=False)

    def index(self):
        return self.full_path('index.sqlite')

    def cur(self, name):
        return self.full_path('cur', name)

    def new(self, name):
        return self.full_path('new', name)

    def add_blob(self, filename, hash=None):
        h = sha256()

        with open(filename, 'rb') as f:
            h.update(f.read())

        hex = h.hexdigest()

        if hash is not None:
            assert hash == hex

        os.rename(filename, self.new(hex))
        return hex

    def index_blob(self, conn, hash):
        with open(self.full_path('new', hash), 'rb') as f:
            message = read_message(f)

        header = message[0]

        if len(message) == 3:
            sigheader = message[2]
            key = sigheader["k"]
            add_channel_entry(conn, key, hash, sigheader["t"])

        for ref in header.get("r", ()):
            add_link(conn, hash, ref)

        mark_finished(conn, hash)
        os.rename(self.new(hash), self.cur(hash))

    def update_channel(self, conn, key):
        entries = list_channel_entries(conn, key)

        with self.tempfile() as f:
            f.write(format_message({"r": entries}))

        root = self.add_blob(f.name)
        self.index_blob(conn, root)
        set_channel_root(conn, key, root)
