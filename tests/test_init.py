import pytest

from testutil import FM


# Overwrite the global `fm` fixture with one which is not automatically
# initialized.
@pytest.fixture
def fm(tmp_path, fake_subprocess):
    return FM(tmp_path, fake_subprocess)


def test_init_empty(fm):
    fm('init')
    assert fm.index.size == 0


def test_init_with_files(files, fm):
    files['a'] = 'a'
    files['dir/b'] = 'b'

    fm('init')
    assert fm.index.size == 2


def test_init_already_exists(fm):
    fm('init')

    fm.expect_error('because the path already exists')
    fm('init')


def test_init_different_directory(files, fm):
    files['foo/file'] = 'a'
    files['bar/file'] = 'b'

    # Go into one directory and initialize a repository in another directory.
    fm('init ../bar', cwd='foo')

    # Check that the repository exists and only a single file has been indexed.
    fm.root_dir /= 'bar'
    assert fm.index.size == 1


def test_init_root_does_not_exist(fm):
    # Try to initialize a repository in a non-existing directory. I have not
    # yet decided whether we want to support that.
    fm.expect_error('Path does not exist')
    fm('init foo')


def test_run_sub_command_no_repository(files, fm):
    files['file1'] = 'a'

    # Running any sub-command without a repository should fail.
    fm.expect_error('No .filemaster directory found')
    fm('ls')

    # The command should fail before it does anything.
    fm.expect_error('No .filemaster directory found')
    fm('set --apply file1 file2')
    assert files['file1'] == 'a'
