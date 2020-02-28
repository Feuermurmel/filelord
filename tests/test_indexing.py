# TODO: Add some tests which check the inner workings. E.g. add a FILEMASTER_DEBUG variable, which makes it print stuff which we can check in the output.



def test_indexing_adds_new_files(files, fm):
    # New files should be listed.
    files['dir1/file1'] = 'a'
    fm('ls')
    fm.check_lines('dir1/file1')

    files['dir2/file2'] = 'b'
    fm('ls')
    fm.check_lines('dir1/file1', 'dir2/file2')


def test_remove_file(files, fm):
    # Index the file.
    files['file1'] = 'a'
    fm('ls')

    # After removing the file, it should not be listed anymore.
    del files['file1']
    fm('ls')
    fm.check_not_output('file1')


def test_update_file(files, fm):
    # Index the file and set an intended path.
    files['file1'] = 'a'
    fm('set file1 floop')
    fm('ls')
    fm.check_output('=> floop')

    # After modifying the file, the intended path should not be shown anymore.
    files['file1'] = 'b'
    fm('ls')
    fm.check_not_output('=> floop')
