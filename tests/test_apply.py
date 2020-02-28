def test_apply_intended_path(files, fm):
    # A file with an intended path.
    files['file1'] = 'a'
    fm('set file1 file2')

    # Applying the intended paths should move the file.
    fm('apply')
    assert files['file2'] == 'a'


def test_limit_path(files, fm):
    files['dir1/file1'] = 'a'
    files['dir2/file2'] = 'b'
    fm('set dir1/file1 dir2/file2 ./')

    # Applying the intended paths for a single directory should only move
    # files in that directory.
    fm('apply dir1')
    assert files['file1'] == 'a'
    assert files['dir2/file2'] == 'b'


def test_parent_dirs_are_created(files, fm):
    files['file1'] = 'a'
    fm('set file1 dir1/dir2/')

    # The file should end up at its intended path even though the parent
    # directories did not exists.
    fm('apply')
    assert files['dir1/dir2/file1'] == 'a'


def test_identical_files(files, fm):
    files['file1'] = 'a'
    files['file2'] = 'a'
    fm('set file1 file3')

    # The file mentioned on the command line should be moved.
    fm('apply file1')
    assert files['file2'] == 'a'
    assert files['file3'] == 'a'


def test_apply_without_updating_cache(files, fm):
    files['file1'] = 'a'
    fm('set file1 file2')

    # Applying without updating the cache after changing a file should still
    # move the file.
    files['file1'] = 'b'
    fm('-U apply')
    assert files['file2'] == 'b'
