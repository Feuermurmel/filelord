# TODO: Add some tests which check the inner workings. E.g. add a FILELORD_DEBUG variable, which makes it print stuff which we can check in the output.



def test_indexing_adds_new_files(files, fl):
    # New files should be listed.
    files['dir1/file1'] = 'a'
    fl('ls')
    fl.check_lines('dir1/file1')

    files['dir2/file2'] = 'b'
    fl('ls')
    fl.check_lines('dir1/file1', 'dir2/file2')


def test_remove_file(files, fl):
    # Index the file.
    files['file1'] = 'a'
    fl('ls')

    # After removing the file, it should not be listed anymore.
    del files['file1']
    fl('ls')
    fl.check_not_output('file1')


def test_update_file(files, fl):
    # Index the file and set an intended path.
    files['file1'] = 'a'
    fl('set file1 floop')
    fl('ls')
    fl.check_output('=> floop')

    # After modifying the file, the intended path should not be shown anymore.
    files['file1'] = 'b'
    fl('ls')
    fl.check_not_output('=> floop')
