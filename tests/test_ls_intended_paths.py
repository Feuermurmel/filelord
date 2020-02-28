def test_file_without_intended_path(files, fm):
    files['file1'] = 'a'

    fm('ls')
    fm.check_consecutive_lines('file1', '  => ?')


def test_file_with_intended_path(files, fm):
    files['file1'] = 'a'
    fm('set file1 file1')

    # File is at intended path. No intended path should be displayed.
    fm('ls')
    fm.check_lines('file1')
    fm.check_not_output('  => ?')

    # Move the file.
    files['file1-new'] = files['file1']
    del files['file1']

    # File is not at its intended path anymore. The intended path should be
    # displayed.
    fm('ls')
    fm.check_consecutive_lines('file1-new', '  => file1')

    # Create an additional file with the same content.
    files['file1-new2'] = files['file1-new']

    # Two files should show the same intended path.
    fm('ls')
    fm.check_consecutive_lines('file1-new', '  => file1')
    fm.check_consecutive_lines('file1-new2', '  => file1')


def test_file_with_intended_path_changes(files, fm):
    files['file1'] = 'a'
    fm('reset -s file1')

    # Change the file after setting its intended path.
    files['file1'] = 'b'

    # The intended path should not be displayed anymore.
    fm('ls')
    fm.check_consecutive_lines('file1', '  => ?')
