import re


def words(*words):
    """
    Return a `re.Pattern` instance to match a string which contains the
    specified words or phrases in this order.

    The pattern will match a string with those words, where each word must be
    delimited by a "non-word-character" (whitespace, comma or dot).
    """

    return re.compile(
        '.*'.join('[\\s.,]{}[\\s.,]'.format(re.escape(i)) for i in words))


def test_identical_files(files, fl):
    files['file1'] = 'a'
    files['file2'] = 'a'
    fl('set file1 file3')

    # Nothing should happen because both files would be moved to the same
    # location.
    fl.expect_error(words('Cannot move', 'file1', 'file2', 'file3'))
    fl('apply')
    assert 'file3' not in files


def test_same_intended_path(files, fl):
    files['file1'] = 'a'
    files['file2'] = 'b'
    fl('set file1 file2 file3')

    # Nothing should happen because both files would be moved to the same
    # location.
    fl.expect_error(words('Cannot move', 'file1', 'file2', 'file3'))
    fl('apply')
    assert 'file3' not in files


def test_conflicting_intended_paths(files, fl):
    files['file1'] = 'a'
    files['file2'] = 'b'
    fl('set file1 file3')
    fl('set file2 file3/')

    # Nothing should happen because the file's intended paths conflict.
    fl.expect_error(words('Cannot create parent', 'file2', 'file1', 'file3'))
    fl('apply')
    assert 'file3' not in files


def test_file_destination_exists(files, fl):
    files['file1'] = 'a'
    files['file2'] = 'b'
    files['dir1'] = '...'
    fl('set file1 file2')

    # The file should not be moved because the destination already exists.
    fl.expect_error(words('Cannot move file1', 'file2'))
    fl('apply')
    assert files['file1'] == 'a'

    # The same with a directory at the destination.
    fl('set file1 dir1')
    fl.expect_error(words('Cannot move file1', 'dir1'))
    fl('apply')
    assert files['file1'] == 'a'


def test_parent_dir_cannot_be_created(files, fl):
    files['file1'] = 'a'
    files['file2'] = 'b'
    fl('set file1 file2/file2')

    # Nothing should happen because a parent directory can't be created.
    fl.expect_error(words('Cannot create parent', 'file1', 'file2'))
    fl('apply')
    assert files['file1'] == 'a'
    assert files['file2'] == 'b'


def test_conflicts_checked_before_applying(files, fl):
    files['file1'] = 'a'
    files['file2'] = 'b'
    fl('set file1 file3')
    fl('set file2 file1/file1')

    # The operation should abort before anything is done.
    fl.expect_error(words('Cannot create parent', 'file2', 'file1'))
    fl('apply')
    assert files['file1'] == 'a'
    assert files['file2'] == 'b'
