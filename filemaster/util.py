import contextlib
import hashlib
import io
import pathlib
import sys
import typing


def format_size(size: int):
    """
    Format a file size in bytes into a human-readable string, e.g. "15 bytes"
    or 12.3 TB. Uses decimal SI-prefixes.
    """

    if size < 1000:
        return '{} bytes'.format(size)

    for unit in 'KMGTPEZY':
        size = size / 1000

        if size < 10:
            return '{:.2f} {}B'.format(size, unit)
        elif size < 100:
            return '{:.1f} {}B'.format(size, unit)
        elif size < 1000 or unit == 'Y':
            return '{:.0f} {}B'.format(size, unit)


def move_to_end(seq, item):
    """
    Take the specified sequence, which may already contain the specified item
    and append the item to the sequence, replacing an already existing instance.
    """

    def iter_new_list():
        for i in seq:
            if i != item:
                yield i

        yield item

    return list(iter_new_list())


def copy_file(
        fsrc: typing.BinaryIO,
        fdst: typing.BinaryIO,
        *, progress_fn: typing.Callable[[int], None]):
    """
    Variant of shutil.copyfile() which allows a callback to be specified over
    which copy progress is reported.

    :param fsrc: The file-like object to read the data from.
    :param fdst: The file-like object to write the data to.
    :param progress_fn: A function which is called with the number of bytes
    copied for each block copied.
    """

    while True:
        data = fsrc.read(1 << 24)

        if not data:
            break

        read_size = len(data)
        fdst.write(data)

        progress_fn(read_size)


class _HashingFile(io.RawIOBase):
    """
    A simple file-like object which calculates a hash of all data written to
    it.
    """

    def __init__(self, hash=hashlib.sha256):
        self.hash = hash()

    def write(self, b):
        self.hash.update(b)


def file_digest(path: pathlib.Path, *, progress_fn: typing.Callable[[int], None]):
    hashing_file = _HashingFile()

    with path.open('rb') as file:
        copy_file(file, hashing_file, progress_fn=progress_fn)

    return 'sha256:' + hashing_file.hash.digest().hex()


def bytes_digest(data: bytes):
    hashing_file = _HashingFile()
    hashing_file.write(data)

    return 'sha256:' + hashing_file.hash.digest().hex()


def iter_regular_files(root: pathlib.Path, filter_fn: typing.Callable[[pathlib.Path], bool]):
    """
    Return an iterator yielding paths to all regular files under the specified
    paths. `filter_fn` is applied to the path of all files and directories
    should return `false` for files and directories that should be excluded.
    """

    # Using this instead of os.walk because we want a stable, predictable order
    # in which files are visited. This does not gain any technical benefit but
    # allows a user to relate the log output to how much progress has been
    # made.
    def walk_path(path):
        # Follow symlinks specified as the root on the command line but
        # ignore them otherwise.
        if not path.is_symlink() and filter_fn(path):
            if path.is_file():
                yield path
            elif path.is_dir():
                for i in sorted(path.iterdir()):
                    yield from walk_path(i)

    return walk_path(root)


def is_descendant_of(descendant_path: pathlib.Path, path: pathlib.Path):
    """
    Return whether `descendant_path` refers to a descendant of `path`.
    """

    try:
        descendant_path.relative_to(path)
    except ValueError:
        return False
    else:
        return True


@contextlib.contextmanager
def with_log_message_fn(log_message_fn: typing.Callable[[str], None]):
    global _log_message_fn

    orig_log_message_fn = _log_message_fn
    _log_message_fn = log_message_fn

    try:
        yield orig_log_message_fn
    finally:
        _log_message_fn = orig_log_message_fn


def _log_message_fn(message):
    print(message, file=sys.stderr, flush=True)


def log(message, *args):
    _log_message_fn(message.format(*args))


class UserError(Exception):
    def __init__(self, message, *args):
        super().__init__(message.format(*args))
