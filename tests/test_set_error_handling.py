import pytest


def test_file_with_same_content(files, fm):
    files['file1'] = 'a'
    files['file2'] = 'a'

    # Setting the intended path of two identical files should not work.
    fm.expect_error('for identical files')
    fm('set file1 file2 dir/')


def test_same_file_twice(files, fm):
    files['dir1/file1'] = 'a'

    # Mentioning the same file twice should not work.
    fm.expect_error('selected through multiple command line arguments')
    fm('set dir1/file1 dir1/file1 dir2/')

    # Selecting the same file twice even through different paths should not
    # work.
    fm.expect_error('selected through multiple command line arguments')
    fm('set dir1 dir1/file1 dir2/')


def test_path_does_not_exist(files, fm):
    files['dir1'] = ...

    # Passing a non-existing path should not work.
    fm.expect_error('Path does not exist')
    fm('set file1 file2')

    # But passing an empty directory should work.
    fm('set dir1 dir2')


def test_intended_path_outside_root(files, fm):
    files['file1'] = 'a'

    # Passing a path outside the root directory should not work because the
    # resulting intended paths would also lie outside the root directory.
    fm.expect_error('is outside the repository\'s root directory')
    fm('set . ..')

    # This should just so work. `.` selects `file1` in the root directory but
    # because of the trailing slash on the intended path, the relative path
    # which is appended ti the intended path for the file is computed against
    # the parent of `.`, i.e. the directory containing the root directory.
    # Thus that relative path starts with the name of root directory which
    # results in a path which is again inside the root.
    fm('set . ../')


# Not sure if we want to disallow this.
@pytest.mark.skip
def test_intended_path_is_root(files, fm):
    files['file1'] = 'a'

    # This would result in the intended path being set to the root directory.
    fm.expect_error('is not below the repository\'s root directory')
    fm('set file1 .')
