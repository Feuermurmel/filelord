
# TODO: Missing files.


def test_indexed_file_count(files, fl):
    files['file1'] = 'a'
    files['file2'] = 'b'
    files['file3'] = 'c'

    # The summary line should show the number of files found.
    fl('ls')
    fl.check_output('3 files')


def test_no_intended_path_count(files, fl):
    files['file1'] = 'a'
    files['file2'] = 'b'
    files['file3'] = 'c'
    fl('set file3 file3')

    # The summary line should show the number of files without an intended
    # path.
    fl('ls')
    fl.check_output('2 without intended path')

    # The part about intended paths should be absent.
    fl('set file1 file2 dir/')
    fl('ls -s')
    fl.check_not_output('intended path')


def test_duplicate_count(files, fl):
    files['file1'] = 'a'
    files['file2'] = 'a'
    files['file3'] = 'a'
    files['file4'] = 'b'

    # The summary line should show the number of duplicates (total number of
    # files minus number of unique files). The number of indexed files should
    # count duplicates.
    fl('ls')
    fl.check_output('4 files', '2 duplicates')

    # Remove the duplicates.
    del files['file2']
    del files['file3']

    # Duplicates should not be mentioned anymore.
    fl('ls')
    fl.check_not_output('duplicates')


def test_limit_paths(files, fl):
    files['dir1/a1'] = 'a'
    files['dir1/a2'] = 'a'

    # Add some files without could affect the counts, but shouldn't.
    files['dir2/a3'] = 'a'
    files['dir2/b1'] = 'b'
    files['dir2/b2'] = 'b'

    # Only files and duplicates in the selected paths should be counted.
    fl('ls dir1')
    fl.check_output('2 files', '2 without intended path', '1 duplicate')
