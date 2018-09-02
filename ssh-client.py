#!/usr/bin/env python3

import os
from bobo import Repo
ROOT = os.path.dirname(__file__)
repo = Repo(os.path.join(ROOT, 'client'))

from twisted.enterprise.adbapi import ConnectionPool
dbpool = ConnectionPool("sqlite3", repo.index(), check_same_thread=False)

from twisted.conch.ssh.transport import SSHClientTransport
from twisted.internet.defer import succeed
from bobo.ssh import BoboConnection

class BoboClientConnection(BoboConnection):

    def serviceStarted(self):
        super().serviceStarted()
        self.pull()

class BoboClientTransport(SSHClientTransport):
    def verifyHostKey(self, hostKey, fingerprint):
        return succeed(True)

    def connectionSecure(self):
        self.requestService(BoboClientConnection())


from twisted.internet.protocol import ClientFactory
class BoboClientFactory(ClientFactory):
    protocol = BoboClientTransport

    def getRepo(self):
        return repo

    def getDBPool(self):
        return dbpool

factory = BoboClientFactory()


from twisted.python import log
import sys
log.startLogging(sys.stdout)

from twisted.internet import reactor
from twisted.internet.endpoints import clientFromString

endpoint = clientFromString(reactor, 'tcp:127.0.0.1:13013')
endpoint.connect(factory)

reactor.run()
