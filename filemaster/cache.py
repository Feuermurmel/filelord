import collections
import typing

from filemaster.store import Store, namedtuple_encode, pathlib_path_encode
from filemaster.util import log, format_size, file_digest, iter_regular_files


"""
Represents an entry in a file cache. The entry stores the file's absolute 
path, its ctime and its hash. The ctime is used to detect when a file has 
been modified.
"""
CacheEntry = collections.namedtuple('CacheEntry', 'path ctime hash')

_cache_entry_encode = namedtuple_encode(CacheEntry, path=pathlib_path_encode)


# TODO: Remove this type and export absolute paths from get_cached_files()
"""
Used to export data from the file cache. Only contains the path and hash of an
entry. The path is relative to the root directory of the cache.
"""
CachedFile = collections.namedtuple('CachedFile', 'path hash')


# TODO: Great idea here! While indexing, to not lose any work when the user cancels or we crash during indexing, write a line some temporary file, which contains the information for already-scanned paths and which can be replayed before the next scan begins.
class FileCache:
    """
    Used to keep and updated list of the hashes of all files in a tree.
    """

    def __init__(self, *, store_path, root_path, filter_fn):
        self._store_path = store_path
        self._root_path = root_path
        self._filter_fn = filter_fn

        self._store = Store(path=self._store_path, encode=_cache_entry_encode)

    def _get_current_ctime(self):
        """
        Create a file next to the store file and get its ctime. This is
        necessary so that we also capture the filesystems rounding behavior
        in the returned value.
        """

        ctime_token_path = \
            self._store_path.with_name(self._store_path.name + 'ctime_token')

        ctime_token_path.touch()
        ctime = ctime_token_path.stat().st_ctime
        ctime_token_path.unlink()

        return ctime

    def clear(self):
        self._store[:] = []
        self._store.save()

    def update(self, *, file_checked_progress_fn, data_read_progress_fn):
        """
        Update the hashes of all files in the tree and remove entries for
        files which do not exist anymore.
        """

        # We can't trust hashes computed for files which do not have a ctime
        # that is smaller than the current time. These files could still be
        # written to without visibly changing their ctime. If we hash such a
        # file we store 0 as their ctime, which forces re-computing the hash
        # next time the tree is scanned.
        current_ctime = self._get_current_ctime()

        # List of updated entries.
        new_entries = []

        # Used to look up cache entries by path while scanning. Entries of
        # unchanged paths are copied to new_cache_files.
        entries_by_path = {i.path: i for i in self._store}

        for path in iter_regular_files(self._root_path, self._filter_fn):
            entry = entries_by_path.get(path)
            stat = path.stat()
            ctime = stat.st_ctime

            # Force hashing the file again when the ctime is too recent.
            if ctime >= current_ctime:
                ctime = 0

            # Ignore cached entry when the ctime doesn't match.
            if entry is None or entry.ctime != ctime:
                size = stat.st_size

                # Do not log small files.
                if size >= 1 << 24:
                    log('Hashing {} ({}) ...', path, format_size(size))

                hash = file_digest(path, progress_fn=data_read_progress_fn)
                entry = CacheEntry(path, ctime, hash)

            new_entries.append(entry)
            file_checked_progress_fn()

        # Save the new list of entries.
        self._store[:] = new_entries
        self._store.save()

    def get_cached_files(self) -> typing.List[CachedFile]:
        """
        Return the current list of cached files. This only contains files
        inside the current root, even when root was changed and the index not
        updated.
        """

        def iter_entries():
            for i in self._store:
                try:
                    path = i.path.relative_to(self._root_path)
                except ValueError:
                    pass
                else:
                    yield CachedFile(path, i.hash)

        return list(iter_entries())
