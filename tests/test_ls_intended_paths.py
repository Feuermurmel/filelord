def test_file_without_intended_path(files, fl):
    files['file1'] = 'a'

    fl('ls')
    fl.check_consecutive_lines('file1', '  => ?')


def test_file_with_intended_path(files, fl):
    files['file1'] = 'a'
    fl('set file1 file1')

    # File is at intended path. No intended path should be displayed.
    fl('ls')
    fl.check_lines('file1')
    fl.check_not_output('=>')

    # Move the file.
    files['file1-new'] = files['file1']
    del files['file1']

    # File is not at its intended path anymore. The intended path should be
    # displayed.
    fl('ls')
    fl.check_consecutive_lines('file1-new', '  => file1')

    # Create an additional file with the same content.
    files['file1-new2'] = files['file1-new']

    # Two files should show the same intended path.
    fl('ls')
    fl.check_consecutive_lines('file1-new', '  => file1')
    fl.check_consecutive_lines('file1-new2', '  => file1')


def test_file_with_intended_path_changes(files, fl):
    files['file1'] = 'a'
    fl('reset -s file1')

    # Change the file after setting its intended path.
    files['file1'] = 'b'

    # The intended path should not be displayed anymore.
    fl('ls')
    fl.check_consecutive_lines('file1', '  => ?')
