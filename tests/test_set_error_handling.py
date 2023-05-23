import pytest


def test_file_with_same_content(files, fl):
    files['file1'] = 'a'
    files['file2'] = 'a'

    # Setting the intended path of two identical files should not work.
    fl.expect_error('for identical files')
    fl('set file1 file2 dir/')


def test_same_file_twice(files, fl):
    files['dir1/file1'] = 'a'

    # Mentioning the same file twice should not work.
    fl.expect_error('selected through multiple command line arguments')
    fl('set dir1/file1 dir1/file1 dir2/')

    # Selecting the same file twice even through different paths should not
    # work.
    fl.expect_error('selected through multiple command line arguments')
    fl('set dir1 dir1/file1 dir2/')


def test_path_does_not_exist(files, fl):
    files['dir1'] = ...

    # Passing a non-existing path should not work.
    fl.expect_error('Path does not exist')
    fl('set file1 file2')

    # But passing an empty directory should work.
    fl('set dir1 dir2')


def test_intended_path_outside_root(files, fl):
    files['file1'] = 'a'

    # Passing a path outside the root directory should not work because the
    # resulting intended paths would also lie outside the root directory.
    fl.expect_error('is outside the repository\'s root directory')
    fl('set . ..')

    # This should just so work. `.` selects `file1` in the root directory but
    # because of the trailing slash on the intended path, the relative path
    # which is appended ti the intended path for the file is computed against
    # the parent of `.`, i.e. the directory containing the root directory.
    # Thus that relative path starts with the name of root directory which
    # results in a path which is again inside the root.
    fl('set . ../')


# Not sure if we want to disallow this.
def test_intended_path_is_root(files, fl):
    files['file1'] = 'a'

    # This would result in the intended path being set to the root directory.
    fl.expect_error('is outside the repository\'s root directory')
    fl('set file1 .')
