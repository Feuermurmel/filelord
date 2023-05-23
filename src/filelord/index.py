import collections
import pathlib
import typing

from filelord.cache import CachedFile
from filelord.store import namedtuple_encode, union_with_none_encode, \
    pathlib_path_encode, list_encode, Store


"""
Represents an entry in the index.


:param hash:
    A hash of the file's content.
:param intended_path:
    A path relative to the repository's root where the file should eventually 
    be moved. This is set by the user and is initially set to `None`.
:param seen_paths: 
    A list of absolute paths at which a file with this hash has been seen in 
    the past. New paths are appended to the end of the list.
"""
IndexEntry = \
    collections.namedtuple('IndexEntry', 'hash intended_path seen_paths')

_index_encode = list_encode(
    namedtuple_encode(
        IndexEntry,
        intended_path=union_with_none_encode(pathlib_path_encode),
        seen_paths=list_encode(pathlib_path_encode)))


"""
Used to export data from the index after aggregating it with data from the 
file cache.

`index_entry` contains the `IndexEntry` instance form the file index. This 
entry may have been created, if an entry for a hash present in the cache did 
not already exist. `cached_files` contains a list of `CachedFile` instances. 
This list may be empty. `seen_paths` of `index_entry` will already have been
updated with all the paths from the `CachedFile` instances.
"""
AggregatedFile = \
    collections.namedtuple('AggregatedFile', 'index_entry cached_files')


class FileIndex:
    """
    The index records information about each file in the repository, indexed
    by the hash of each file. This index is edited by the user and used to
    apply those changes to the directory tree.
    """

    def __init__(self, *, store_path):
        self._store = Store(path=store_path, encode=_index_encode)

    def aggregate_files(self, cached_files: typing.List[CachedFile]) -> typing.List[AggregatedFile]:
        """
        Return the content of the index aggregated with the content of the
        cache.
        """

        # Will contain all aggregated files, even for those files that are not
        # yet in the index.
        files_by_hash = {i.hash: AggregatedFile(i, []) for i in self._store.get()}

        for i in cached_files:
            index_entry, cached_files = files_by_hash.get(
                i.hash,
                AggregatedFile(IndexEntry(i.hash, None, []), []))

            cached_files = cached_files + [i]

            if i.path not in index_entry.seen_paths:
                index_entry = index_entry._replace(
                    seen_paths=index_entry.seen_paths + [i.path])

            files_by_hash[i.hash] = AggregatedFile(index_entry, cached_files)

        return list(files_by_hash.values())

    def set(self, index_entries):
        """
        Overwrite and save the list of entries stored in the index.
        """

        self._store.set(index_entries)


def initialize_file_index(path: pathlib.Path):
    Store(path, _index_encode).set([])
