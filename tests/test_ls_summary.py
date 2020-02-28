
# TODO: Missing files.


def test_indexed_file_count(files, fm):
    files['file1'] = 'a'
    files['file2'] = 'b'
    files['file3'] = 'c'

    # The summary line should show the number of files found.
    fm('ls')
    fm.check_output('3 files')


def test_no_intended_path_count(files, fm):
    files['file1'] = 'a'
    files['file2'] = 'b'
    files['file3'] = 'c'
    fm('set file3 file3')

    # The summary line should show the number of files without an intended
    # path.
    fm('ls')
    fm.check_output('2 without intended path')

    # The part about intended paths should be absent.
    fm('set file1 file2 dir/')
    fm('ls -s')
    fm.check_not_output('intended path')


def test_duplicate_count(files, fm):
    files['file1'] = 'a'
    files['file2'] = 'a'
    files['file3'] = 'a'
    files['file4'] = 'b'

    # The summary line should show the number of duplicates (total number of
    # files minus number of unique files). The number of indexed files should
    # count duplicates.
    fm('ls')
    fm.check_output('4 files', '2 duplicates')

    # Remove the duplicates.
    del files['file2']
    del files['file3']

    # Duplicates should not be mentioned anymore.
    fm('ls')
    fm.check_not_output('duplicates')


def test_limit_paths(files, fm):
    files['dir1/a1'] = 'a'
    files['dir1/a2'] = 'a'

    # Add some files without could affect the counts, but shouldn't.
    files['dir2/a3'] = 'a'
    files['dir2/b1'] = 'b'
    files['dir2/b2'] = 'b'

    # Only files and duplicates in the selected paths should be counted.
    fm('ls dir1')
    fm.check_output('2 files', '2 without intended path', '1 duplicate')
