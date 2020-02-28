import contextlib
import json
import pathlib
import typing

from filemaster.store import Encode
from filemaster.util import bytes_digest


@contextlib.contextmanager
def with_log_writer(path: pathlib.Path, encode: Encode):
    with path.open('wb') as file:
        yield LogWriter(file, encode)

        # If we leave the context without throwing an exception, it means
        # that the data in the log has already been applied succesfully and
        # is not useful anymore.
        path.unlink()


def iter_records(path: pathlib.Path, encode: Encode):
    # Silently threat a missing log file as being empty.
    if not path.exists():
        return

    with path.open('rb') as file:
        # Try to read valid records until EOF or until a record with a
        # mismatching digest is encountered.
        for line in file:
            # Drop the newline at the end of the line, which technically is
            # part of the record.
            parts = line.split(b' ', 1)[:-1]

            # Until here, there could be anything in this record, so we don't
            # trust there to be a space character.
            if len(parts) < 2:
                return

            digest, data = parts

            if bytes_digest(data) != digest:
                return

            yield encode.decode(json.loads(data.decode()))

        # All records in the log have been replayed and so the log can be
        # removed.
        path.unlink()


class LogWriter:
    def __init__(self, file: typing.BinaryIO, encode: Encode):
        self._encode = encode
        self._file = file

    def append(self, item):
        data = json.dumps(self._encode.encode(item)).encode()
        digest = bytes_digest(data)

        # Write a full record. We just hope that it gets eventually written
        # to disk completely. But we can be sure that it gets ignored unless
        # the digest matches.
        self._file.write(digest + b' ' + data + b'\n')
