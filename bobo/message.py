import json
from nacl.signing import VerifyKey
from nacl.encoding import HexEncoder

def read_header(f):
    return json.loads(f.read(int(f.read(int(f.read(1))))))

def read_signed(f):
    header = read_header(f)
    pos = f.tell()
    public_key = VerifyKey(header["key"], encoder=HexEncoder)
    public_key.verify(f.read(), HexEncoder.decode(header["sig"]))
    f.seek(pos)
    return read_message(f) + (header["key"],)

def read_message(f):
    t = f.read(1)

    if t == b'S':
        return read_signed(f)

    assert t == b'P'
    header = read_header(f)
    pos = f.tell()
    return (header, pos)

def format_header(header):
    header = json.dumps(header, sort_keys=True, separators=(',',':')) + '\n'
    size = str(len(header))
    return (str(len(size)) + size + header).encode()

def sign_message(private_key, data):
    signature = HexEncoder.encode(private_key.sign(data).signature)
    public_key = encode_public_key(private_key.verify_key)
    header = {"key": public_key, 'sig': signature.decode()}
    return b'S' + format_header(header) + data

def format_message(header, data=b''):
    return b'P' + format_header(header) + data

def encode_public_key(public_key):
    return public_key.encode(encoder=HexEncoder).decode()
