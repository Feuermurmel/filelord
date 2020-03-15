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


_no_value_token = object()


class Store:
    """
    Used to store a Python value in a file encoded as JSON, which can be
    atomically updated.
    """

    def __init__(self, path: pathlib.Path, encode: Encode):
        """
        The file at the specified  path is only opened for reading when the
        value is read the first time with `get()`.

        :param path:
            The path where the file containing the encoded value is stored.
        :param encode:
            Used to convert between a Python and JSON value when writing to or
            reading from the file.
        """

        self._path = path
        self._encode = encode
        self._current_value = _no_value_token

    def get(self):
        if self._current_value is _no_value_token:
            with self._path.open('r', encoding='utf-8') as file:
                self._current_value = self._encode.decode(json.load(file))

        return self._current_value

    def set(self, new_value):
        temp_path = self._path.with_name(self._path.name + '~')

        with temp_path.open('w', encoding='utf-8') as file:
            json.dump(self._encode.encode(new_value), file)

            file.flush()
            os.fsync(file.fileno())

        temp_path.rename(self._path)
        self._current_value = new_value
