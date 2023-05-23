import pytest

from testutil import FL


# Overwrite the global `fl` fixture with one which is not automatically
# initialized.
@pytest.fixture
def fl(tmp_path, fake_subprocess):
    return FL(tmp_path, fake_subprocess)


def test_init_empty(fl):
    fl('init')
    assert fl.index.size == 0


def test_init_with_files(files, fl):
    files['a'] = 'a'
    files['dir/b'] = 'b'

    fl('init')
    assert fl.index.size == 2


def test_init_already_exists(fl):
    fl('init')

    fl.expect_error('because the path already exists')
    fl('init')


def test_init_different_directory(files, fl):
    files['foo/file'] = 'a'
    files['bar/file'] = 'b'

    # Go into one directory and initialize a repository in another directory.
    fl('init ../bar', cwd='foo')

    # Check that the repository exists and only a single file has been indexed.
    fl.root_dir /= 'bar'
    assert fl.index.size == 1


def test_init_root_does_not_exist(fl):
    # Try to initialize a repository in a non-existing directory. I have not
    # yet decided whether we want to support that.
    fl.expect_error('Path does not exist')
    fl('init foo')


def test_run_sub_command_no_repository(files, fl):
    files['file1'] = 'a'

    # Running any sub-command without a repository should fail.
    fl.expect_error('No .filelord directory found')
    fl('ls')

    # The command should fail before it does anything.
    fl.expect_error('No .filelord directory found')
    fl('set --apply file1 file2')
    assert files['file1'] == 'a'
