import os
from tempfile import NamedTemporaryFile
from hashlib import sha256

from .index import Index
from .message import read_message, format_message


class Repo:

    def __init__(self, path):
        self.path = path
        os.makedirs(path, exist_ok=True)
        self.index = Index(self.full_path('index.sqlite'))
        os.makedirs(self.full_path('cur'), exist_ok=True)
        os.makedirs(self.full_path('new'), exist_ok=True)
        os.makedirs(self.full_path('tmp'), exist_ok=True)

    def full_path(self, *names):
        return os.path.join(self.path, *names)

    def tempfile(self):
        return NamedTemporaryFile(dir=self.full_path('tmp'), delete=False)

    def add_object(self, filename, hash=None):
        h = sha256()

        with open(filename, 'rb') as f:
            h.update(f.read())

        hex = h.hexdigest()

        if hash is not None:
            assert hash == hex

        os.rename(filename, self.full_path('new', hex))
        return hex

    def index_object(self, hash):
        with open(self.full_path('new', hash), 'rb') as f:
            message = read_message(f)

        header = message[0]
        if len(message) == 3:
            key = message[2]
            if header.get("type", None) == "feed":
                self.index.add_feed_item(key, hash, header["timestamp"])
                items = self.index.list_feed_items(key)

                with self.tempfile() as f:
                    f.write(format_message({"refs": items}))

                root =self.add_object(f.name)
                self.index_object(root)
                self.index.set_feed_root(key, hash)

        for ref in header.get("refs", ()):
            self.index.add_link(hash, ref)

        os.rename(self.full_path('new', hash), self.full_path('cur', hash))
        self.index.mark_finished(hash)
