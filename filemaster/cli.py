import argparse
import pathlib
import sys

from filemaster.repository import filemaster_dir_name, with_repository, \
    list_files, MatchedFile, initialize_repository, set_intended_paths, \
    apply_intended_paths, remove_missing_files
from filemaster.util import PathWithSlash, log, UserError


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
             'directory.'.format(filemaster_dir_name))

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

    # Mutually exclusive group for --cache, --missing, --all and paths.
    # Technically these two features are orthogonal and could be combined,
    # but it could lead to confusion e.g. because --missing clears _all_
    # missing files and is not restricted by the specified paths.
    reset_parser_ex_group = \
        reset_parser.add_mutually_exclusive_group(required=True)

    reset_parser_ex_group.add_argument(
         '--cache',
         help='Clear the file cache instead of resetting intended paths.',
         action='store_true')

    reset_parser_ex_group.add_argument(
        '--missing',
        help='Remove the intended path from files which can\'t be found in '
             'the directory tree anymore.',
        action='store_true')

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

    # Paths does not default to the current directory to prevent accidentally
    # resetting the intended path for a large number of files.
    reset_parser_ex_group.add_argument(
        'paths',
        help='Files or directories from which to remove the intended path.',
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
    # TODO: Do we need an option which allows overwriting already-existing files at the intended path of another file? Do we want to rename those files? Do we update the intended path of those files, if they were already at their intended path?
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
        if args.set_current and not (args.all or args.paths):
            parser.error('--set-current requires one of --all or paths.')

    return args


def default_command(update_cache):
    with with_repository(update_cache) as repo:
        file_set = repo.create_file_set([repo.root_dir])

        list_files(repo, file_set, summary_only=True)


def init_command(update_cache, path):
    initialize_repository(path)

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
