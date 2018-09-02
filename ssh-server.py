#!/usr/bin/env python3

import os
from fzone import Repo
ROOT = os.path.dirname(__file__)
repo = Repo(os.path.join(ROOT, 'server'))

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric.rsa import generate_private_key

PRIVATE_KEY = generate_private_key(public_exponent=65537, key_size=1024, backend=default_backend())

from twisted.enterprise.adbapi import ConnectionPool
dbpool = ConnectionPool("sqlite3", repo.index(), check_same_thread=False)

from twisted.conch.ssh.keys import Key
from fzone.ssh import FZoneServerFactory

class ServerFactory(FZoneServerFactory):
    publicKeys = {
        b'ssh-rsa': Key(PRIVATE_KEY.public_key())
    }
    privateKeys = {
        b'ssh-rsa': Key(PRIVATE_KEY)
    }

    def getRepo(self):
        return repo

    def getDBPool(self):
        return dbpool

from twisted.python import log
import sys
log.startLogging(sys.stdout)

from twisted.internet import reactor
reactor.listenTCP(13013, ServerFactory())
reactor.run()
