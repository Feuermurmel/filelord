import argparse
import collections
import contextlib
import os
import pathlib
import sys
import typing

from filemaster.cache import FileCache
from filemaster.index import FileIndex, AggregatedFile
from filemaster.statusline import StatusLine, with_status_line
from filemaster.store import Store, namedtuple_encode, pathlib_path_encode, \
    union_with_none_encode, list_encode
from filemaster.tsv import write_tsv
from filemaster.util import UserError, log, file_digest, format_size, \
    iter_regular_files, move_to_end, is_descendant_of


_filemaster_dir_name = '.filemaster'
_file_cache_store_name = 'filecache'
_file_index_store_name = 'fileindex'


# String containing all the path separator characters used on the current
# platform.
_path_separators = os.path.sep + (os.path.altsep or '')


class PathWithSlash:
    """
    Type used in place of `pathlib.Path` in argument parsers where trailing
    slashes are significant.
    """
    def __init__(self, path_str: str):
        self.path = pathlib.Path(path_str)
        self.trailing_slash = path_str[-1:] in _path_separators


def parse_args():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        '-U',
        '--no-update-cache',
        help='Disable scanning the directory tree for changes before running '
             'the sub-command.',
        action='store_false',
        dest='update_cache')

    subparsers = parser.add_subparsers(dest='command')

    init_parser = subparsers.add_parser(
        'init',
        help='Initialize a {} directory in the current working '
             'directory.'.format(_filemaster_dir_name))

    init_parser.add_argument(
        'path',
        nargs='?',
        type=pathlib.Path,
        default=pathlib.Path())

    ls_parser = subparsers.add_parser(
        'ls',
        help='Print information about the files in the file list.')

    ls_parser.add_argument(
        '-s',
        '--summary',
        help='Instead of listing any files, just print the summary counting '
             'up the files.',
        action='store_true')

    ls_parser_ex_group = ls_parser.add_mutually_exclusive_group()

    ls_parser_ex_group.add_argument(
        '-a',
        '--all',
        help='List all files in the repository.',
        action='store_true')

    # TODO: list past file names or paths.

    # ls_parser.add_argument(
    #     '-u',
    #     '--unset',
    #     help='Only list files for which no intended path has been set.',
    #     action='store_true')

    # ls_parser.add_argument(
    #     '-p',
    #     '--pending',
    #     help='Only list files which have not yet been moved to their intended path.',
    #     action='store_true')

    # ls_parser.add_argument(
    #     '-m',
    #     '--missing',
    #     help='Only list files for which an intended path has been set but which aren\'t in the directory tree anymore.',
    #     action='store_true')

    # ls_parser.add_argument(
    #     '-d',
    #     '--duplicate',
    #     help='Only list files which where more than one exact copy is in the directory tree.',
    #     action='store_true')

    ls_parser_ex_group.add_argument(
        'paths',
        help='List files which are currently located under these paths. '
             'Defaults to the current directory.',
        nargs='*',
        type=pathlib.Path,
        default=[pathlib.Path()])

    set_parser = subparsers.add_parser(
        'set',
        help='Set the intended path of files or directories.\n\nlala')

    set_parser.add_argument(
        '--apply',
        help='Move the files to their new intended paths.',
        action='store_true')

    set_parser.add_argument(
        'paths',
        help='The files or directories whose intended path should be set.',
        nargs='+',
        type=pathlib.Path)

    set_parser.add_argument(
        'intended_path',
        help='The new intended path for the files. If this path ends in a '
             'slash, then the names of files and directories in `path` will '
             'be appended.',
        type=PathWithSlash)

    reset_parser = subparsers.add_parser(
        'reset',
        help='Reset the intended path property of files.')

    reset_parser_ex_group = reset_parser.add_mutually_exclusive_group()

    reset_parser_ex_group.add_argument(
        '-a',
        '--all',
        help='Remove the intended path of  all files in the repository.',
        action='store_true')

    reset_parser.add_argument(
        '-s',
        '--set-current',
        help='Instead of removing the intended paths from files, set it to '
             'their current paths.',
        action='store_true')

    reset_parser.add_argument(
        '--missing',
        help='Remove the intended path from files which can\'t be found in '
             'the directory tree anymore.',
        action='store_true')

    reset_parser.add_argument(
         '--cache',
         help='Clear the file cache instead of resetting intended paths.',
         action='store_true')

    # TODO: Maybe require a path to prevent accidentally removing a lot of paths.
    reset_parser_ex_group.add_argument(
        'paths',
        help='Files or directories from which to remove the intended path. '
             'Defaults to the current directory',
        nargs='*',
        type=pathlib.Path,
        default=[])

    # export_parser = subparsers.add_parser(
    #     'export',
    #     help='Export intended paths of files to a .tsv file so they can be '
    #          'edited and imported again with the `import` sub-command.')
    #
    # export_parser.add_argument(
    #     '--output',
    #     '-o',
    #     help='Path where the .tsv should be created. Defaults to '
    #          'filemaster_index.tsv in the current directory.',
    #     type=pathlib.Path,
    #     default=pathlib.Path('filemaster_index.tsv'))
    #
    # # export_parser.add_argument(
    # #     '--full-paths',
    # #     '-p',
    # #     help='',
    # #     action='store_true')
    #
    # export_parser.add_argument(
    #     'paths',
    #     help='Files or directories to include in the export. Default to the '
    #          'current directory.',
    #     nargs='*',
    #     type=pathlib.Path,
    #     default=[pathlib.Path()])

    # import_parser = subparsers.add_parser(
    #     'import',
    #     help='Import intended paths for files from a .tsv file created with '
    #          'the `export` sub-command.')
    #
    # import_parser.add_argument(
    #     'tsv_file',
    #     help='File to import. Defaults to filemaster_index.tsv in the current '
    #          'directory.',
    #     type=pathlib.Path,
    #     default=pathlib.Path('filemaster_index.tsv'))
    #
    # import_parser.add_argument(
    #     '--apply',
    #     help='Apply the imported intended paths by moving the affected files '
    #          'to their intended paths.',
    #     action='store_true')

    apply_parser = subparsers.add_parser(
        'apply',
        help='Apply the intended path to files by moving them to their '
             'intended paths.')

    apply_parser_ex_group = apply_parser.add_mutually_exclusive_group()

    apply_parser_ex_group.add_argument(
        '-a',
        '--all',
        help='Apply to all files in the repository.',
        action='store_true')

    # TODO: Maybe add these options also to import and set sub-commands.
    # apply_parser.add_argument(
    #     '-d',
    #     '--displace',
    #     help='')

    # apply_parser.add_argument(
    #     '-m',
    #     '--merge',
    #     help='Instead of throwing an error when multiple identical files are selected, delete all except one.')

    # TODO: Add an option which allows multiple identical copies to be merged (deleting all but one copy).
    # TODO: What happens when multiple files have the same intended path?
    # TODO: Do we need an option which allows overwriting already-existing files at the indended path of another file? Do we want to rename those files? Do we update the intended path of those files, if they were already at their intended path?
    # TODO: Add a dry run option.

    apply_parser_ex_group.add_argument(
        'paths',
        help='Apply to files currently located under these paths. Defaults to '
             'the current directory.',
        nargs='*',
        type=pathlib.Path,
        default=[pathlib.Path()])

    args = parser.parse_args()

    if args.command == 'reset':
        if args.cache:
            if args.missing or args.set_current or args.paths:
                # TODO: Look into ArgumentParser.add_mutually_exclusive_group() to replace this ceremony.
                parser.error(
                    '--cache cannot be used with --missing, --set-current or '
                    'any paths.')
        elif args.missing:
            if args.set_current or args.paths:
                # Technically these two features are orthogonal and could be
                # combined, but if could lead to confusion because --missing
                # clears _all_ missing files and is not restricted by the
                # specified paths.
                parser.error(
                    '--missing cannot be used with --set-current or any '
                    'paths.')
        else:
            # Paths does not default to the current directory to prevent
            # accidentally resetting the intended path for a large number of
            # files.
            if not args.paths and not args.missing:
                parser.error('One of --cache, --missing or paths is required.')

    return args


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

    # TODO: Not necessary to be in Repository once we use absolute paths in CachedFile.
    def get_matched_files(self, file_set):
        def iter_matches():
            for i in self.aggregated_files:
                for j in i.cached_files:
                    path = self.root_dir / j.path

                    for k in file_set.matched_roots(path):
                        yield MatchedFile(path, k, i)

        return sorted(iter_matches())

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
    filemaster_dir = root_dir / _filemaster_dir_name

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


def find_filemaster_root(root_dir: pathlib.Path=None):
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
            if (root_dir / _filemaster_dir_name).is_dir():
                break
        else:
            raise UserError(
                'No {} directory found in the current directory or any of its '
                'parents.',
                _filemaster_dir_name)
    else:
        root_dir = root_dir.resolve()

    filemaster_dir = root_dir / _filemaster_dir_name

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


def list_files(repo: Repository, file_set: FileSet, summary_only):
    # All files to list.
    items = repo.get_matched_files(file_set)

    if not summary_only:
        # Print each file together with additional information.
        for i in items:
            intended_path = i.aggregated_file.index_entry.intended_path

            if intended_path is None:
                intended_path_str = '?'
            else:
                intended_path_str = \
                    os.path.relpath(repo.root_dir / intended_path)

            print(os.path.relpath(i.path), flush=False)
            print('  =>', intended_path_str)

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


def apply_intended_paths(repo, file_set):
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
        log('Creating directory: {}', os.path.relpath(path))
        path.mkdir()

    # No problems detected. Create the directories and move the files.
    for destination, moved_file in moved_files_by_destination.items():
        log('Moving: {} -> {}', os.path.relpath(moved_file.path),  os.path.relpath(destination))

        # Can't prevent race conditions. But this should catch bugs in the
        # logic above.
        assert not destination.exists()

        moved_file.path.rename(destination)


def default_command(update_cache):
    with with_repository(update_cache) as repo:
        file_set = repo.create_file_set([repo.root_dir])

        list_files(repo, file_set, summary_only=True)


def init_command(update_cache, path):
    if not path.exists():
        raise UserError('Path does not exist: {}', path)
    elif not path.is_dir():
        raise UserError('Path is not a directory: {}', path)

    filemaster_dir = path / _filemaster_dir_name

    if filemaster_dir.exists():
        raise UserError(
            'Cannot create directory at {} because the path already exists.',
            filemaster_dir)

    # Initialize an empty repository.
    filemaster_dir.mkdir()
    (filemaster_dir / _file_cache_store_name).touch()
    (filemaster_dir / _file_index_store_name).touch()

    util.log('Initialized empty database at {}.', filemaster_dir)

    # This has the side effect of updating the cache and index.
    with with_repository(update_cache, root_dir=path):
        pass


def ls_command(update_cache, summary, all, paths):
    with with_repository(update_cache) as repo:
        if all:
            paths = [repo.root_dir]

        list_files(repo, repo.create_file_set(paths), summary)


def set_command(update_cache, apply, paths, intended_path):
    with with_repository(update_cache) as repo:
        file_set = repo.create_file_set(paths)

        def intended_path_fn(matched_file: MatchedFile):
            matched_root = matched_file.matched_root

            # If the intended path has a trailing slash on the command line,
            # then all generated intended paths include the last component of
            # the corresponding root path specified on the command line for
            # selecting files
            if intended_path.trailing_slash:
                matched_root = matched_root.parent

            absolute_intended_path_base = intended_path.path.resolve()

            return absolute_intended_path_base \
                   / matched_file.path.relative_to(matched_root)

        set_intended_paths(repo, file_set, intended_path_fn)

        if apply:
            apply_intended_paths(repo, file_set)


def reset_command(update_cache, all, set_current, missing, cache, paths):
    with with_repository(update_cache, clear_cache=cache) as repo:
        if missing:
            remove_missing_files(repo)
        else:
            if all:
                paths = [repo.root_dir]

            def intended_path_fn(matched_file: MatchedFile):
                return matched_file.path if set_current else None

            set_intended_paths(repo, repo.create_file_set(paths), intended_path_fn)


# def export_command():
#     # with
#
#     with with_repository(update_cache) as repo:
#         file_set = repo.create_file_set(repo, paths)
#
#         export_tsv(repo, file_set, output)


# def import_command():
#     pass


def apply_command(update_cache, all, paths):
    with with_repository(update_cache) as repo:
        if all:
            paths = [repo.root_dir]

        apply_intended_paths(repo, repo.create_file_set(paths))


def main(command, **kwargs):
    commands = {
        None: default_command,
        'init': init_command,
        'ls': ls_command,
        'set': set_command,
        'reset': reset_command,
        # 'export': export_command,
        # 'import': import_command,
        'apply': apply_command}

    commands[command](**kwargs)


def entry_point():
    try:
        main(**vars(parse_args()))
    except KeyboardInterrupt:
        log('Operation interrupted.')
        sys.exit(1)
    except UserError as e:
        log('error: {}', e)
        sys.exit(2)
