import collections
import json
import os
import pathlib


class Encode:
    def __init__(self, *, encode_fn, decode_fn):
        self.encode = encode_fn
        self.decode = decode_fn


def list_encode(encode: 'Encode'):
    return Encode(
        encode_fn=lambda x: list(map(encode.encode, x)),
        decode_fn=lambda x: list(map(encode.decode, x)))


def union_with_none_encode(encode: 'Encode'):
    return Encode(
        encode_fn=lambda x: x if x is None else encode.encode(x),
        decode_fn=lambda x: x if x is None else encode.decode(x))


def namedtuple_encode(_type, **encodes_by_field):
    def encode_fn(x):
        result = x._asdict()
        result.update({k: v.encode(result[k]) for k, v in encodes_by_field.items()})

        return result

    def decode_fn(x):
        updates = {k: v.decode(x[k]) for k, v in encodes_by_field.items()}

        return _type(**dict(x, **updates))

    return Encode(encode_fn=encode_fn, decode_fn=decode_fn)


pathlib_path_encode = Encode(encode_fn=str, decode_fn=pathlib.Path)


# TODO: It is certainly a stupid idea that the store itself exports a list interface, but it also creates some problems. E.g. <store-instance> + <some other list> does not work.
class Store(collections.UserList):
    """
    Used to store a list of Python values in a file and access it as a Python
    sequence.

    Each item is individually converted between a Python and a JSON value
    using `self._encode_item()` and `self._decode_item()`, encoded as
    JSON and written to a separate line in the file.
    """

    def __init__(self, path: pathlib.Path, encode: Encode):
        super().__init__()

        self._path = path
        self._encode = encode

        with self._path.open('r', encoding='utf-8') as file:
            for line in file:
                self.append(self._encode.decode(json.loads(line)))

    def save(self):
        temp_path = self._path.with_name(self._path.name + '~')

        with temp_path.open('w', encoding='utf-8') as file:
            for i in self:
                print(json.dumps(self._encode.encode(i)), file=file)

            file.flush()
            os.fsync(file.fileno())

        temp_path.rename(self._path)
