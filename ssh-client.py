#!/usr/bin/env python3

import os
from fzone import Repo
ROOT = os.path.dirname(__file__)
repo = Repo(os.path.join(ROOT, 'client'))

from twisted.enterprise.adbapi import ConnectionPool
dbpool = ConnectionPool("sqlite3", repo.index(), check_same_thread=False)

from twisted.conch.ssh.transport import SSHClientTransport
from twisted.internet.defer import succeed
from fzone.ssh import FZoneConnection

class FZoneClientConnection(FZoneConnection):

    def serviceStarted(self):
        super().serviceStarted()
        self.pull()

class FZoneClientTransport(SSHClientTransport):
    def verifyHostKey(self, hostKey, fingerprint):
        return succeed(True)

    def connectionSecure(self):
        self.requestService(FZoneClientConnection())


from twisted.internet.protocol import ClientFactory
class FZoneClientFactory(ClientFactory):
    protocol = FZoneClientTransport

    def getRepo(self):
        return repo

    def getDBPool(self):
        return dbpool

factory = FZoneClientFactory()


from twisted.python import log
import sys
log.startLogging(sys.stdout)

from twisted.internet import reactor
from twisted.internet.endpoints import clientFromString

endpoint = clientFromString(reactor, 'tcp:127.0.0.1:13013')
endpoint.connect(factory)

reactor.run()
