#!/usr/bin/env python3

import os
import random
import sqlite3

from nacl.signing import SigningKey
from nacl.encoding import HexEncoder

from bobo import Repo, encode_verify_key, format_message
from bobo.index import get_chan_id

ROOT = os.path.dirname(__file__)

def init_server(private_keys):
    repo = Repo(os.path.join(ROOT, 'server'))

    for key in private_keys:
        message = format_message({}, b'', key)
        with repo.tempfile() as f:
            f.write(message)

        with sqlite3.connect(repo.index()) as conn:
            repo.index_blob(conn, repo.add_blob(f.name))
            repo.update_channel(conn, encode_verify_key(key.verify_key))

def init_client(verify_keys):
    repo = Repo(os.path.join(ROOT, 'client'))
    verify_key = random.choice(verify_keys)

    with sqlite3.connect(repo.index()) as conn:
        get_chan_id(conn, encode_verify_key(verify_key))

def init():
    private_keys = [SigningKey.generate() for _ in range(5)]
    init_server(private_keys)
    init_client([key.verify_key for key in private_keys])

if __name__ == '__main__':
    init()
