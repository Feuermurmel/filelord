import os


def test_limit_non_existing_path(files, fl):
    files['dir1/file1'] = 'a'
    files['dir3'] = ...

    # Limiting to a path not in the file system should not work.
    fl.expect_error('Path does not exist')
    fl('ls dir2')


def test_path_outside_root(fl):
    fl.expect_error('is outside the repository\'s root directory')
    fl('ls ..')


def test_not_regular_file_or_dir(files, fl):
    os.mkfifo(str(files.root / 'pipe'))

    # A path to something that is not a regular file or directory should
    # result in an error.
    fl.expect_error('not a regular file or directory')
    fl('ls pipe')
