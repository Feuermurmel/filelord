import collections
import contextlib
import os
import pathlib
import typing

from filemaster.cache import FileCache
from filemaster.index import AggregatedFile, FileIndex
from filemaster.statusline import StatusLine, with_status_line
from filemaster.tsv import write_tsv
from filemaster.util import UserError, log, format_size, is_descendant_of


filemaster_dir_name = '.filemaster'
_file_cache_store_name = 'filecache'
_file_index_store_name = 'fileindex'


class UpdateStatus:
    def __init__(self, status_line: StatusLine):
        self._status_line = status_line

        self._files_checked = 0
        self._data_read = 0

    def _update_status(self):
        self._status_line.set(
            '{} files checked, {} read (cancel with ^C) ...',
            self._files_checked,
            format_size(self._data_read))

    def file_checked(self):
        self._files_checked += 1
        self._update_status()

    def data_read(self, bytes):
        self._data_read += bytes
        self._update_status()


class FileSet:
    """
    Represents a set of files through a set of root paths. Paths can be
    checked against the roots for whether they are contained in one of the
    roots, regardless of whether a file at that path actually exists.
    """

    def __init__(self, root_paths):
        """
        `root_paths` should be a list of resolved, absolute paths.
        """

        self._root_paths = root_paths

    def __contains__(self, path):
        """
        Return whether the passed path is below any of the paths in this file
        set.
        """

        # Returns true if the iterator is non-empty.
        return any(True for _ in self._iter_matched_roots(path))

    def _iter_matched_roots(self, path):
        # Return an iterator so that we can abort early if we're only
        # interested in the first element.
        return (i for i in self._root_paths if is_descendant_of(path, i))

    def matched_roots(self, path):
        """
        Return a list of all roots which contain the specified path.
        """

        return list(self._iter_matched_roots(path))


MatchedFile = collections.namedtuple(
    'MatchedFile',
    'path matched_root aggregated_file')


class Repository:
    def __init__(self, root_dir: pathlib.Path, aggregated_files: typing.List[AggregatedFile]):
        assert root_dir.is_absolute()

        self.root_dir = root_dir
        self.aggregated_files = aggregated_files

    def get_matched_files(self, file_set) -> typing.List[MatchedFile]:
        """
        Match all aggregated files of this repository with the specified file
        set.

        Returns a `MatchedFile` instance for each combination of a root in
        the file set and an aggregated file where the aggregated file's path
        is below the root. The returned list is sported by the paths of the
        matched files.
        """

        return sorted(
            MatchedFile(c.path, m, a)
            for a in self.aggregated_files
            for c in a.cached_files
            for m in file_set.matched_roots(c.path))

    def create_file_set(self, paths):
        """
        Create a FileSet instance treating the paths in a way that is useful for
        multiple sub-commands. Checks paths for existence and resolves them.
        """

        def iter_resolved_paths():
            for i in paths:
                if not i.exists():
                    raise UserError('Path does not exist: {}', i)

                if not i.is_file() and not i.is_dir():
                    raise UserError(
                        'Path is not a regular file or directory: {}',
                        i)

                # Resolving the paths here basically means that we accept
                # symlinks on the command line but ignore them when they are
                # encountered when selecting files using this list.
                resolved_path = i.resolve()

                if not is_descendant_of(resolved_path, self.root_dir):
                    raise UserError(
                        'Path is outside the repository\'s root directory: {}',
                        i)

                yield resolved_path

        return FileSet(list(iter_resolved_paths()))


@contextlib.contextmanager
def with_repository(update_cache, *, root_dir=None, clear_cache=False):
    """
    Return a context yielding a `Repository` instance for the current
    directory or the specified directory, throwing a user error if no
    repository is found.

    The updated index of the repository is saved when the context is left,
    unless an error is thrown.

    :param update_cache:
        Whether to update the cache before returning the repository.
    """

    # Uses root_dir, if specified, otherwise searches for a repository.
    root_dir = find_filemaster_root(root_dir)
    filemaster_dir = root_dir / filemaster_dir_name

    if not filemaster_dir.exists():
        raise UserError('Repository does not exist: {}', filemaster_dir)
    elif not filemaster_dir.is_dir():
        raise UserError('Repository is not e directory: {}', filemaster_dir)

    cache = FileCache(
        store_path=filemaster_dir / _file_cache_store_name,
        root_path=root_dir,
        filter_fn=file_filter_fn)

    index = FileIndex(
        store_path=filemaster_dir / _file_index_store_name)

    if clear_cache:
        # Produce different messages when the cache is cleared, depending on
        # whether updating the cache is disabled or not.
        if update_cache:
            log('Recreating the file cache ...')
        else:
            log('Clearing the files cache ...')

        cache.clear()

    if update_cache:
        update_cache_with_status(cache)

    aggregated_files = index.aggregate_files(cache.get_cached_files())
    repo = Repository(root_dir, aggregated_files)

    yield repo

    index.set([i.index_entry for i in repo.aggregated_files])


def file_filter_fn(x):
    return not x.name.startswith('.') and x.suffix != '.tsv'


def update_cache_with_status(cache: FileCache):
    with with_status_line() as status_line:
        update_status = UpdateStatus(status_line)

        cache.update(
            file_checked_progress_fn=update_status.file_checked,
            data_read_progress_fn=update_status.data_read)


def find_filemaster_root(root_dir: pathlib.Path = None):
    """
    Return an absolute, resolved path to the root directory.

    If a root directory is specified, it is tested to be a valid root
    directory. If no root directory is specified, the closest parent
    directory containing a .filemaster directory is used. If no such
    directory can be found, a `UserError` is raised.
    """

    if root_dir is None:
        # Make sure to use an absolute path so that .parents list all the
        # parents.
        current_dir = pathlib.Path().resolve()

        for root_dir in [current_dir, *current_dir.parents]:
            if (root_dir / filemaster_dir_name).is_dir():
                break
        else:
            raise UserError(
                'No {} directory found in the current directory or any of its '
                'parents.',
                filemaster_dir_name)
    else:
        root_dir = root_dir.resolve()

    filemaster_dir = root_dir / filemaster_dir_name

    files_exist = \
        (filemaster_dir / _file_cache_store_name).is_file() \
        and (filemaster_dir / _file_index_store_name).is_file()

    if not files_exist:
        raise UserError(
            'Not a valid repository: {}',
            os.path.relpath(filemaster_dir))

    return root_dir


def export_tsv(repo: Repository, file_set, output_path):
    cached_files_by_hash = {i.hash: i for i in repo.file_cache_store}

    def iter_lines():
        yield ['File Hash', 'Intended Path', 'File Names']

        for i in repo.file_list_store:
            cached_file = cached_files_by_hash.get(i.hash)

            if cached_file is not None and file_set.contains_path(cached_file.path):
                intended_path_str = '' if i.intended_path is None else str(i.intended_path)
                file_names_str = '; '.join(reversed([str(i.name) for i in i.seen_paths]))

                yield [i.hash, intended_path_str, file_names_str]

    write_tsv(output_path, iter_lines())


def initialize_repository(root_dir):
    if not root_dir.exists():
        raise UserError('Path does not exist: {}', root_dir)
    elif not root_dir.is_dir():
        raise UserError('Path is not a directory: {}', root_dir)

    filemaster_dir = root_dir / filemaster_dir_name

    if filemaster_dir.exists():
        raise UserError(
            'Cannot create directory at {} because the path already exists.',
            filemaster_dir)

    # Initialize an empty repository.
    filemaster_dir.mkdir()
    (filemaster_dir / _file_cache_store_name).touch()
    (filemaster_dir / _file_index_store_name).touch()

    log('Initialized empty database at {}.', filemaster_dir)


def list_files(repo: Repository, file_set: FileSet, summary_only):
    # All files to list.
    items = repo.get_matched_files(file_set)

    if not summary_only:
        # Print each file together with additional information.
        for i in items:
            intended_path = i.aggregated_file.index_entry.intended_path

            if intended_path is not None:
                intended_path = repo.root_dir / intended_path

            print(os.path.relpath(i.path))

            # Only display the intended path, if the file is not currently at
            # its intended path.
            if intended_path is None:
                print('  => ?')
            elif intended_path != i.path:
                print('  =>', os.path.relpath(repo.root_dir / intended_path))


        if items:
            # An empty line before the summary, unless we got no files.
            print(flush=False)

    def iter_summary_parts():
        yield '{} files'.format(len(items))

        # Number of files selected, whose hash has no intended path
        # defined.
        num_without_intended_path = sum(
            1 for i in items
            if i.aggregated_file.index_entry.intended_path is None)

        if num_without_intended_path:
            yield '{} without intended path'.format(num_without_intended_path)

        # The number of duplicates is defined as the number of selected files
        # minus the number of distinct hashes of the selected files.
        distinct_hashes = set(i.aggregated_file.index_entry.hash for i in items)
        num_duplicates = len(items) - len(distinct_hashes)

        if num_duplicates:
            yield '{} duplicates'.format(num_duplicates)

    print('{}.'.format(', '.join(iter_summary_parts())))


def set_intended_paths(repo, file_set, intended_path_fn):
    """
    :param intended_path_fn:
        A function which is applied to the `MatchedFile` for each selected
        file and which should return the new intended path for that file as
        an absolute path or None, to return the intended path.
    """

    def fail_identical_files(path1, path2):
        # Produce a different error message when same file is selected twice.
        if path1 == path2:
            raise UserError(
                'The same file is selected through multiple command line '
                'arguments: {}',
                os.path.relpath(path1))
        else:
            raise UserError(
                'Cannot apply an intended path for identical files '
                'simultaneously: {} and {}',
                os.path.relpath(path1),
                os.path.relpath(path2))

    # MatchedFiles instances by hash for files whose intended paths is being
    # set.
    matched_files_by_hash = {}

    for i in repo.get_matched_files(file_set):
        hash = i.aggregated_file.index_entry.hash
        matched_file = matched_files_by_hash.get(hash)

        if matched_file:
            fail_identical_files(matched_file.path, i.path)

        matched_files_by_hash[hash] = i

    def process_aggregated_file(aggregated_file):
        matched_file = \
            matched_files_by_hash.get(aggregated_file.index_entry.hash)

        if matched_file is None:
            # Return the instance unmodified.
            return aggregated_file

        new_intended_path = intended_path_fn(matched_file)

        # intended_path_fn returns None to remove the intended path.
        if new_intended_path is not None:
            try:
                new_intended_path = new_intended_path.relative_to(repo.root_dir)
            except ValueError:
                raise UserError(
                    'Intended path is outside the repository\'s root '
                    'directory: {}',
                    os.path.relpath(new_intended_path))

        return aggregated_file._replace(
            index_entry=aggregated_file.index_entry._replace(
                intended_path=new_intended_path))

    repo.aggregated_files[:] = map(process_aggregated_file, repo.aggregated_files)


def remove_missing_files(repo):
    """
    Remove all index entries for files which aren't currently in the cache.
    """

    repo.aggregated_files[:] = \
        [i for i in repo.aggregated_files if i.cached_files]


def apply_intended_paths(repo, file_set, *, dry_run=False):
    if dry_run:
        def create_directory(path):
            log('Would create directory: {}', os.path.relpath(path))

        def move_file(source, dest):
            log('Would move: {} -> {}', os.path.relpath(source), os.path.relpath(dest))
    else:
        def create_directory(path):
            log('Creating directory: {}', os.path.relpath(path))
            path.mkdir()

        def move_file(source, dest):
            log('Moving: {} -> {}', os.path.relpath(source), os.path.relpath(dest))

            # Can't prevent race conditions. But this should catch logic bugs.
            assert not dest.exists()

            source.rename(dest)

    # Records changes to the file system before performing them so that we
    # can detect conflicts before doing anything.
    moved_files_by_created_directories = {}
    moved_files_by_destination = {}

    def check_create_directory(path, matched_file):
        # TODO: Here and in many places, exists() returns false for symlinks.
        if path.exists():
            # Raise an error if the parent exists but is not directory. If it
            # does not exist. It is recorded as a directory to be created
            if not path.is_dir():
                raise UserError(
                    'Cannot create parent directory for {}, path already '
                    'exists: {}',
                    os.path.relpath(matched_file.path),
                    os.path.relpath(path))
        elif path not in moved_files_by_created_directories:
            check_create_directory(path.parent, matched_file)

            # Record one of the files for which the directory needs to be
            # created so we can have a nice error message on conflict.
            moved_files_by_created_directories[path] = matched_file

    def check_move_file(destination, matched_file):
        # Check for an already existing file.
        if destination.exists():
            raise UserError(
                'Cannot move {}, path already exists: {}',
                os.path.relpath(matched_file.path),
                os.path.relpath(destination))

        # Check that all necessary parents can be created.
        check_create_directory(destination.parent, matched_file)

        other_matched_file = moved_files_by_destination.get(destination)

        # Check for another file to be moved to this destination.
        if other_matched_file is not None:
            raise UserError(
                'Cannot move both {} and {} to same path: {}',
                os.path.relpath(other_matched_file.path),
                os.path.relpath(matched_file.path),
                os.path.relpath(destination))

        moved_files_by_destination[destination] = matched_file

    # We first process all files to be moved and make sure that no operations
    # conflict with already existing files and directories or with each other.
    # There are 4 distinct cases that can arise that need to be checked
    # individually:
    #
    # 1. A file is to be moved to a path that already exists (as a file, a
    #    directory, or something else).
    # 2. Two files are to be moved to the exact same path.
    # 3. A directory needs to be created but ...
    #   3a. ... one of the parents already exists but is not a directory.
    #   3b. ... one of the parents is the destination for a file to be moved.
    for i in repo.get_matched_files(file_set):
        intended_path = i.aggregated_file.index_entry.intended_path

        if intended_path is not None:
            absolute_intended_path = repo.root_dir / intended_path

            if i.path != absolute_intended_path:
                check_move_file(absolute_intended_path, i)

    # After generating all operations, check for conflicts between moved
    # files and created directories.
    for path, matched_file in moved_files_by_destination.items():
        other_moved_file = moved_files_by_created_directories.get(path)

        if other_moved_file is not None:
            raise UserError(
                'Cannot create parent directory for {}, {} will be moved to '
                'that path: {}',
                os.path.relpath(other_moved_file.path),
                os.path.relpath(matched_file.path),
                os.path.relpath(path))

    # Iterating over these sorted will give us the parents before the children.
    for path in sorted(moved_files_by_created_directories):
        create_directory(path)

    # No problems detected. Create the directories and move the files.
    for destination, moved_file in moved_files_by_destination.items():
        move_file(moved_file.path, destination)
