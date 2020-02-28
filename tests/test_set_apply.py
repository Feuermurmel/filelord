def test_does_not_move_file(files, fm):
    files['file1'] = 'a'

    # The file is not moved unless --apply is specified.
    fm('set file1 file2')
    assert files['file1'] == 'a'


def test_does_move_file(files, fm):
    files['file1'] = 'a'

    # The file should be moved.
    fm('set --apply file1 file2')
    assert 'file1' not in files
    assert files['file2'] == 'a'


def test_applies_only_selected_paths(files, fm):
    files['file1'] = 'a'
    files['file2'] = 'b'

    # Set the intended path on one file and then set and apply the intended
    # path on another file. Only the second file should be moved.
    fm('set file1 file3')
    fm('set --apply file2 file4')
    assert files['file1'] == 'a'
    assert files['file4'] == 'b'
