import collections
import contextlib
import pathlib
import typing

from filemaster.store import Store, namedtuple_encode, pathlib_path_encode, \
    list_encode
from filemaster.util import log, format_size, file_digest, iter_regular_files, \
    is_descendant_of, add_suffix, relpath
from filemaster.writelog import with_write_log


"""
Represents an entry in a file cache. The entry stores the file's absolute 
path, its mtime and its hash. The mtime is used to detect when a file has
been modified.
"""
CachedFile = collections.namedtuple('CacheEntry', 'path mtime hash')

_cached_file_encode = namedtuple_encode(CachedFile, path=pathlib_path_encode)

_cache_encode = list_encode(_cached_file_encode)


# Wrapper for pathlib.Path.stat() which can be patched during tests.
def _stat_path(path):
    return path.stat()


class FileCache:
    """
    Used to keep and updated list of the hashes of all files in a tree.
    """

    def __init__(self, store_path, root_path, filter_fn, write_log):
        self._store_path = store_path
        self._root_path = root_path
        self._filter_fn = filter_fn
        self._write_log = write_log

        self._store = Store(path=self._store_path, encode=_cache_encode)

    def _get_current_mtime(self):
        """
        Create a file next to the store file and get its mtime. This is
        necessary so that we also capture the filesystems rounding behavior
        in the returned value.
        """

        mtime_token_path = add_suffix(self._store_path, '_mtime_token')

        mtime_token_path.touch()
        mtime = mtime_token_path.stat().st_mtime
        mtime_token_path.unlink()

        return mtime

    def clear(self):
        self._store.set([])

    def update(self, *, file_checked_progress_fn, data_read_progress_fn):
        """
        Update the hashes of all files in the tree and remove entries for
        files which do not exist anymore.
        """

        # We can't trust hashes computed for files which do not have a mtime
        # that is smaller than the current time. These files could still be
        # written to without visibly changing their mtime. If we hash such a
        # file we store 0 as their mtime, which forces re-computing the hash
        # next time the tree is scanned.
        current_mtime = self._get_current_mtime()

        # List of updated entries.
        new_entries = []

        # Used to look up cache entries by path while scanning. This
        # includes records from an existing write log. Entries of
        # unchanged paths are copied to new_cache_files.
        entries_by_path_mtime = {
            (i.path, i.mtime): i
            for i in self._store.get() + self._write_log.records}

        for path in iter_regular_files(self._root_path, self._filter_fn):
            # TODO: We're stat'ing the file (at least) a second time. iter_regular_files() already had to stat the file.
            stat = _stat_path(path)
            mtime = stat.st_mtime

            # Find a cache entry with correct path and mtime.
            entry = entries_by_path_mtime.get((path, mtime))

            # Hash the file and create a new entry, if non was found.
            if entry is None:
                # Force hashing the file again when the mtime is too recent.
                if mtime >= current_mtime:
                    mtime = 0

                # Do not log small files.
                if stat.st_size >= 1 << 24:
                    log('Hashing {} ({}) ...', relpath(path), format_size(stat.st_size))

                hash = file_digest(path, progress_fn=data_read_progress_fn)
                entry = CachedFile(path, mtime, hash)

                # We're using the write log only to prevent losing the work
                # of hashing files.
                self._write_log.append(entry)

            new_entries.append(entry)
            file_checked_progress_fn()

        # Save the new list of entries.
        self._store.set(new_entries)
        self._write_log.flush()

    def add_hint(self, cached_file):
        """
        Add the specified entries to the write log of the cache. These
        entries will be used on the next update in addition to those already
        in the cache. Thus, it's not problematic if a change recorded here
        ultimately doesn't happened. The file system will have been scanned
        again before these entries will be exported from the cache.
        """

        self._write_log.append(cached_file)

    def get_cached_files(self) -> typing.List[CachedFile]:
        """
        Return the current list of cached files. This only contains files
        inside the current root, even when the root was moved without
        updating the cache.
        """

        return [
            i for i in self._store.get()
            if is_descendant_of(i.path, self._root_path)]


@contextlib.contextmanager
def with_file_cache(store_path, root_path, filter_fn):
    log_path = add_suffix(store_path, '_log')

    with with_write_log(log_path, _cached_file_encode) as write_log:
        yield FileCache(store_path, root_path, filter_fn, write_log)


def initialize_file_cache(path: pathlib.Path):
    Store(path, _cache_encode).set([])
