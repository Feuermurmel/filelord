import os


def test_limit_non_existing_path(files, fm):
    files['dir1/file1'] = 'a'
    files['dir3'] = ...

    # Limiting to a path not in the file system should not work.
    fm.expect_error('Path does not exist')
    fm('ls dir2')


def test_path_outside_root(fm):
    fm.expect_error('is outside the repository\'s root directory')
    fm('ls ..')


def test_not_regular_file_or_dir(files, fm):
    os.mkfifo(str(files.root / 'pipe'))

    # A path to something that is not a regular file or directory should
    # result in an error.
    fm.expect_error('not a regular file or directory')
    fm('ls pipe')
