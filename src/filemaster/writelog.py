import contextlib
import json
import os
import pathlib

from filemaster.store import Encode
from filemaster.util import bytes_digest


@contextlib.contextmanager
def with_write_log(path: pathlib.Path, encode: Encode):
    """
    Return a context manager which yields a `WriteLog` instance.

    Implements a write log without durability guarantees. After opening the
    write log, records already written to the log can be read and new records
    can be appended.
    """

    # Open file without truncating it and without any buffering.
    # https://stackoverflow.com/questions/28918302/open-file-for-random-write-without-truncating
    file_fd = os.open(str(path), os.O_RDWR | os.O_CREAT)

    with os.fdopen(file_fd, 'r+b', buffering=0) as file:
        records = list(_iter_existing_records(file, encode))

        yield WriteLog(file, encode, records)


class WriteLog:
    def __init__(self, file, encode, records):
        self._file = file
        self._encode = encode
        self.records = records

    def append(self, record):
        """
        Append a new entry to the write log.
        """

        self.records.append(record)

        data = json.dumps(self._encode.encode(record)).encode()
        digest = bytes_digest(data).encode()

        # We have no guarantee that the record will be written completely or
        # durably, but we can be sure that it gets ignored unless the digest
        # matches.
        self._file.write(digest + b' ' + data + b'\n')

    def flush(self):
        """
        Remove all records from the write log.
        """

        self.records = []

        self._file.seek(0)
        self._file.truncate()


def _iter_existing_records(file, encode):
    valid_until = 0

    # Try to read valid records until EOF or until a record with
    # a mismatching digest is encountered.
    for line in file:
        record = _decode_record(line, encode)

        # Ignore everything from the first invalid record.
        if record is None:
            break

        valid_until = file.tell()

        yield record

    # Trim off any garbage after the last valid record. If any garbage was
    # left before writing new records, it would prevent the new records from
    # being found.
    file.truncate(valid_until)


def _decode_record(line, encode):
    # Drop the newline at the end of the line, which technically is part
    # of the record.
    parts = line[:-1].split(b' ', 1)

    # Until here, there could be anything in this record, so we can't
    # trust it to contain a space character.
    if len(parts) < 2:
        return None

    digest, data = parts

    if bytes_digest(data) != digest.decode():
        return None

    return encode.decode(json.loads(data.decode()))
