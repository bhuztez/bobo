from string import ascii_letters, digits


def load(f):
    c = f.read(1).decode()
    if c in ascii_letters:
        return c
    i = 0
    while c in digits:
        i = i * 10 + int(c)
        c = f.read(1).decode()
    if c == 'n':
        return -i
    elif c == 'i':
        return i
    elif c == '"':
        return f.read(i).decode()
    elif c == '[':
        return [load(f) for _ in range(i)]
    elif c == '{':
        d = {}
        for _ in range(i):
            k = load(f)
            v = load(f)
            d[k] = v
        return d

    raise ValueError()


def encode(o):
    if isinstance(o, int):
        if o < 0:
            return "{}n".format(-o)
        else:
            return "{}i".format(o)
    elif isinstance(o, str):
        if len(o) == 1 and o in ascii_letters:
            return o
        else:
            return '{}"{}'.format(len(o), o)
    elif isinstance(o, list):
        return '{}[{}'.format(len(o), ''.join(encode(e) for e in o))
    elif isinstance(o, dict):
        keys = sorted(o.keys())
        return '{}{{{}'.format(len(keys), ''.join(encode(k) + encode(o[k]) for k in keys))

    raise TypeError("Object of type {} is not bbencode serializable".format(repr(type(o))))


def dump(o):
    return encode(o).encode()
