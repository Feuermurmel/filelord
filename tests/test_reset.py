import re


def test_intended_path_is_reset(files, fl):
    files['file1'] = 'a'
    files['dir1/file2'] = 'b'
    files['dir2/file3'] = 'c'
    files['file4'] = 'd'

    # Set the intended paths for all files.
    fl('set . dir3')

    # The intended path should be removed from a single file.
    fl('reset file1')
    fl.index.check_intended_path('a', None)

    # The intended path should be removed from files in a directory.
    fl('reset dir1')
    fl.index.check_intended_path('b', None)

    # The intended path should be removed from all files in the current
    # directory, but not more.
    fl('reset .', cwd='dir2')
    fl.index.check_intended_path('c', None)
    fl.index.check_intended_path('d', 'dir3/file4')


def test_missing_file_not_reset(files, fl):
    files['file1'] = 'a'

    # Set the intended path of the file, then remove the file.
    fl('reset -s .')
    del files['file1']

    # The intended path is not cleared.
    fl('reset .')
    fl.index.check_intended_path('a', 'file1')


def test_reset_all(files, fl):
    files['file1'] = 'a'
    files['dir1/file2'] = 'b'

    # Use -a form a subdirectory. All files have their intended path set.
    fl('reset -s -a', cwd='dir1')
    fl.index.check_intended_path('a', 'file1')
    fl.index.check_intended_path('b', 'dir1/file2')

    # Same without -s. All files have their intended path reset.
    fl('reset -a', cwd='dir1')
    fl.index.check_intended_path('a', None)
    fl.index.check_intended_path('b', None)


def test_set_intended_path_to_current_path(files, fl):
    files['file1'] = 'a'
    files['dir1/file2'] = 'b'

    # The intended paths for all files should be set to their current paths.
    fl('reset -s .')
    fl.index.check_intended_path('a', 'file1')
    fl.index.check_intended_path('b', 'dir1/file2')

    # Only the intended paths for files in the current directory should be set.
    fl('reset .')
    fl('reset -s .', cwd='dir1')
    fl.index.check_intended_path('a', None)
    fl.index.check_intended_path('b', 'dir1/file2')


def test_reset_missing(files, fl):
    files['file1'] = 'a'
    files['file2'] = 'b'

    # Set the intended path of the files, then remove one file.
    fl('reset -s .')
    del files['file1']

    # Remove the intended path from the missing file and recreate the file.
    # It should not have an intended path anymore.
    fl('reset --missing')
    files['file1'] = 'a'
    fl.index.check_not_in_index('a')
    fl.index.check_intended_path('b', 'file2')


def test_illegal_argument_combinations(fl):
    def check_case(args):
        # Checking for one of many expected error messages. The parsing
        # validity checking is largely done by argparse, so the error
        # messages will be correct. This should just check that the argument
        # parser is correctly set up.
        fl.expect_error(re.compile('one of the arguments .* required|not allowed with argument|requires one of'))
        fl(args)

    check_case('reset --missing foo')
    check_case('reset --missing -a')
    check_case('reset --missing -s')
    check_case('reset --cache foo')
    check_case('reset --cache -a')
    check_case('reset --cache --missing')
    check_case('reset --cache -s')


def test_paths_required(fl):
    # Paths do not default to the current directory.
    fl.expect_error(re.compile('one of the arguments .* required'))
    fl('reset')

    # Same with -s.
    fl.expect_error(re.compile('one of the arguments .* required'))
    fl('reset -s')


def test_clear_cache(files, fl):
    files['file1'] = 'a'

    # After resetting the cache, the files should be indexed again.
    fl('reset --cache')
    fl('ls')
    fl.check_lines('file1')

    # Unless updating the cache is prevented.
    fl('-U reset --cache')
    fl('-U ls')
    fl.check_not_output('file1')
