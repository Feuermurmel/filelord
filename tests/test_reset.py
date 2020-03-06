import re


def test_intended_path_is_reset(files, fm):
    files['file1'] = 'a'
    files['dir1/file2'] = 'b'
    files['dir2/file3'] = 'c'
    files['file4'] = 'd'

    # Set the intended paths for all files.
    fm('set . dir3')

    # The intended path should be removed from a single file.
    fm('reset file1')
    fm.index.check_intended_path('a', None)

    # The intended path should be removed from files in a directory.
    fm('reset dir1')
    fm.index.check_intended_path('b', None)

    # The intended path should be removed from all files in the current
    # directory, but not more.
    fm('reset .', cwd='dir2')
    fm.index.check_intended_path('c', None)
    fm.index.check_intended_path('d', 'dir3/file4')


def test_missing_file_not_reset(files, fm):
    files['file1'] = 'a'

    # Set the intended path of the file, then remove the file.
    fm('reset -s .')
    del files['file1']

    # The intended path is not cleared.
    fm('reset .')
    fm.index.check_intended_path('a', 'file1')


def test_reset_all(files, fm):
    files['file1'] = 'a'
    files['dir1/file2'] = 'b'

    # Use -a form a subdirectory. All files have their intended path set.
    fm('reset -s -a', cwd='dir1')
    fm.index.check_intended_path('a', 'file1')
    fm.index.check_intended_path('b', 'dir1/file2')

    # Same without -s. All files have their intended path reset.
    fm('reset -a', cwd='dir1')
    fm.index.check_intended_path('a', None)
    fm.index.check_intended_path('b', None)


def test_set_intended_path_to_current_path(files, fm):
    files['file1'] = 'a'
    files['dir1/file2'] = 'b'

    # The intended paths for all files should be set to their current paths.
    fm('reset -s .')
    fm.index.check_intended_path('a', 'file1')
    fm.index.check_intended_path('b', 'dir1/file2')

    # Only the intended paths for files in the current directory should be set.
    fm('reset .')
    fm('reset -s .', cwd='dir1')
    fm.index.check_intended_path('a', None)
    fm.index.check_intended_path('b', 'dir1/file2')


def test_reset_missing(files, fm):
    files['file1'] = 'a'
    files['file2'] = 'b'

    # Set the intended path of the files, then remove one file.
    fm('reset -s .')
    del files['file1']

    # Remove the intended path from the missing file and recreate the file.
    # It should not have an intended path anymore.
    fm('reset --missing')
    files['file1'] = 'a'
    fm.index.check_not_in_index('a')
    fm.index.check_intended_path('b', 'file2')


def test_illegal_argument_combinations(fm):
    def check_case(args):
        # Checking for one of many expected error messages. The parsing
        # validity checking is largely done by argparse, so the error
        # messages will be correct. This should just check that the argument
        # parser is correctly set up.
        fm.expect_error(re.compile('one of the arguments .* required|not allowed with argument|requires one of'))
        fm(args)

    check_case('reset --missing foo')
    check_case('reset --missing -a')
    check_case('reset --missing -s')
    check_case('reset --cache foo')
    check_case('reset --cache -a')
    check_case('reset --cache --missing')
    check_case('reset --cache -s')


def test_paths_required(fm):
    # Paths do not default to the current directory.
    fm.expect_error(re.compile('one of the arguments .* required'))
    fm('reset')

    # Same with -s.
    fm.expect_error(re.compile('one of the arguments .* required'))
    fm('reset -s')


def test_clear_cache(files, fm):
    files['file1'] = 'a'

    # After resetting the cache, the files should be indexed again.
    fm('reset --cache')
    fm('ls')
    fm.check_lines('file1')

    # Unless updating the cache is prevented.
    fm('-U reset --cache')
    fm('-U ls')
    fm.check_not_output('file1')
