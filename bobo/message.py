from datetime import datetime
from calendar import timegm
from nacl.signing import VerifyKey
from nacl.encoding import HexEncoder

from .bbencode import load, dump

def read_message(f):
    size = load(f)
    assert isinstance(size, int)
    size += f.tell()

    header = load(f)
    pos = f.tell()
    if pos < size:
        verify_key = VerifyKey(header["k"], encoder=HexEncoder)
        verify_key.verify(dump("t") + dump(header["t"]) + f.read(), HexEncoder.decode(header["s"]))
        f.seek(pos)
        header1 = load(f)
        pos = f.tell()
        assert pos == size
        return (header1, pos, header)
    else:
        assert pos == size
        return (header, pos)

def format_message(header, data=b'', signing_key=None, timestamp=None):
    header = dump(header)
    data = header + data

    if signing_key is not None:
        if timestamp is None:
            timestamp = timegm(datetime.utcnow().utctimetuple())
        signature = HexEncoder.encode(signing_key.sign(dump("t") + dump(timestamp) + data).signature)
        verify_key = encode_verify_key(signing_key.verify_key)
        sigheader = dump({"k": verify_key, "s": signature.decode(), "t": timestamp})
        header = sigheader + header
        data = sigheader + data
    return dump(len(header)) + data

def encode_verify_key(verify_key):
    return verify_key.encode(encoder=HexEncoder).decode()
