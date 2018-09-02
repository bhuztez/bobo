from twisted.conch.avatar import ConchUser
from twisted.conch.ssh.connection import SSHConnection
from twisted.conch.ssh.channel import SSHChannel
from twisted.conch.ssh.factory import SSHFactory
from twisted.internet.defer import Deferred, inlineCallbacks, gatherResults
import os
from io import BytesIO
from hashlib import sha256

from .bbencode import dump, load
from .index import get_channel_root, list_channels, find_blobs_to_fetch


class BoboClientChannel(SSHChannel):

    def openFailed(self, reason):
        self.deferred.errback(reason)

    def closed(self):
        if not self.deferred.called:
            self.deferred.errback(Exception("remote closed"))

class BoboChanClientChannel(BoboClientChannel):
    name = b'bobo-chan'

    def dataReceived(self, data):
        self.remote_data += data

    def eofReceived(self):
        self.deferred.callback(self.remote_data)

class BoboBlobClientChannel(BoboClientChannel):
    name = b'bobo-blob'

    def dataReceived(self, data):
        self.f.write(data)
        self.h.update(data)

    def eofReceived(self):
        self.f.close()
        self.deferred.callback(self.h.hexdigest())

class BoboChanServerChannel(SSHChannel):
    name = b'bobo-chan'

    def channelOpen(self, key):
        self.write_channel_root(key.decode())

    @inlineCallbacks
    def write_channel_root(self, key):
        root = yield self.avatar.db.runInteraction(get_channel_root, key)
        if root is None:
            header = {'r': []}
        else:
            header = {'r': [root]}
        self.write(dump(header))
        self.conn.sendEOF(self)


class BoboBlobServerChannel(SSHChannel):
    name = b'bobo-blob'

    def channelOpen(self, hash):
        try:
            f = open(self.avatar.repo.cur(hash.decode()), 'rb')
            with f:
                self.write(f.read())
        except FileNotFoundError:
            pass
        self.conn.sendEOF(self)


class BoboUser(ConchUser):

    def __init__(self, repo, db):
        ConchUser.__init__(self)
        self.repo = repo
        self.db = db
        self.channelLookup.update(
            {b'bobo-chan': BoboChanServerChannel,
             b'bobo-blob': BoboBlobServerChannel})

class BoboConnection(SSHConnection):

    def serviceStarted(self):
        self.transport.avatar = BoboUser(
            self.transport.factory.getRepo(),
            self.transport.factory.getDBPool())
        self.transport.logoutFunction = lambda: None

    @inlineCallbacks
    def pull(self):
        channels = yield self.transport.avatar.db.runInteraction(list_channels)
        roots = yield gatherResults([self.fetch_channel_root(chan) for chan in channels])
        roots = sum(roots,[])

        while True:
            hashes = yield self.transport.avatar.db.runInteraction(find_blobs_to_fetch, roots)
            if not hashes:
                break

            yield self.fetch_blob(hashes[0])

    def fetch_channel_root(self, key):
        d = Deferred()
        chan = BoboChanClientChannel()
        chan.remote_data = b''
        chan.deferred = d
        d.addCallback(lambda data: load(BytesIO(data))["r"])

        self.openChannel(chan, key.encode())
        return d

    def fetch_blob(self, hash):
        d = Deferred()
        chan = BoboBlobClientChannel()
        repo = self.transport.avatar.repo
        chan.f = repo.tempfile()
        chan.h = sha256()
        chan.deferred = d

        def add_blob(hex):
            assert hash == hex
            os.rename(chan.f.name, repo.new(hex))
            return self.transport.avatar.db.runInteraction(repo.index_blob, hex)
        d.addCallback(add_blob)
        self.openChannel(chan, hash.encode())
        return d


class BoboServerFactory(SSHFactory):
    services = {b'ssh-connection': BoboConnection}

    def getService(self, transport, service):
        return self.services[service]

    def getRepo(self):
        raise NotImplementedError
