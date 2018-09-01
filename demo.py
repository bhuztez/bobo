#!/usr/bin/env python3

import os
import random
from datetime import datetime
from calendar import timegm
from argparse import ArgumentParser
from urllib.request import urlopen, Request

from nacl.signing import SigningKey
from nacl.encoding import HexEncoder

from bobo import Repo, encode_verify_key, format_message

ROOT = os.path.dirname(__file__)

def init_server(private_keys):
    repo = Repo(os.path.join(ROOT, 'server'))

    for key in private_keys:
        message = format_message({}, b'', key)
        with repo.tempfile() as f:
            f.write(message)
        repo.index_object(repo.add_object(f.name))

def init_client(verify_keys):
    repo = Repo(os.path.join(ROOT, 'client'))
    verify_key = random.choice(verify_keys)
    repo.index.get_channel_id(encode_verify_key(verify_key))

def demo_app():
    from wsgiref.util import FileWrapper
    repo = Repo(os.path.join(ROOT, 'server'))
    sessions = {}

    def application(environ, start_response):
        path = environ["PATH_INFO"]

        if path.startswith("/chan/"):
            key = path[6:]
            root = repo.index.get_channel_root(key)
            if root:
                start_response('200 OK', [('Content-type', 'application/octet-stream')])
                return [root.encode()]
        elif path.startswith("/blob/"):
            try:
                f = open(repo.full_path('cur', path[6:]), 'rb')
                start_response('200 OK', [('Content-type', 'application/octet-stream')])
                return FileWrapper(f)
            except FileNotFoundError:
                pass

        start_response('404 Not Found', [('Content-type', 'text/plain; charset=utf-8')])
        return [b"404 Not Found"]

    return application


def sync():
    repo = Repo(os.path.join(ROOT, 'client'))
    SERVER = 'http://127.0.0.1:8000'

    def fetch_channel_root(key):
        response = urlopen(SERVER + '/chan/' + key)
        return response.read().decode()

    def fetch_blob(hash):
        response = urlopen(SERVER + '/blob/' + hash)
        with repo.tempfile() as f:
            f.write(response.read())
        repo.index_object(repo.add_object(f.name, hash))

    def pull():
        roots = [fetch_channel_root(key)
                 for key in repo.index.list_channel_keys()]

        while True:
            hashes = repo.index.find_objects_to_fetch(roots)
            if not hashes:
                break
            fetch_blob(hashes[0])

    pull()

def argument(*args, **kwargs):
    return lambda parser: parser.add_argument(*args, **kwargs)

class Command(object):

    def __init__(self):
        self._parser = ArgumentParser()
        self._subparsers = self._parser.add_subparsers(dest="COMMAND")
        self._commands = {}

    def __call__(self, *arguments):
        def decorator(func):
            name = func.__name__.replace("_", "-")
            subparser = self._subparsers.add_parser(name, help = func.__doc__)
            dests = [arg(subparser).dest for arg in arguments]
            def wrapper(args):
                return func(**{d:getattr(args, d, None) for d in dests})
            self._commands[name] = wrapper
            return func
        return decorator

    def run(self):
        args = self._parser.parse_args()
        return self._commands[args.COMMAND or "help"](args)


command = Command()

@command()
def init():
    private_keys = [SigningKey.generate() for _ in range(5)]
    init_server(private_keys)
    init_client([key.verify_key for key in private_keys])

@command()
def server():
    from wsgiref.simple_server import make_server
    with make_server('', 8000, demo_app()) as httpd:
        print("Serving on port 8000...")
        httpd.serve_forever()

@command()
def client():
    sync()

@command()
def help():
    command._parser.print_help()


if __name__ == '__main__':
    command.run()
