from testutil import is_subsequence_of


def test_lists_files(files, fm):
    files['dir1/file1'] = 'a'
    files['file2'] = 'b'

    # All files should be listed.
    fm('ls')
    fm.check_lines('dir1/file1', 'file2')

    # Test limiting to a directory.
    fm('ls dir1')
    fm.check_lines('dir1/file1')
    fm.check_not_output('file2')

    # Test limiting to a file.
    fm('ls file2')
    fm.check_lines('file2')
    fm.check_not_output('dir1')


def test_empty_directory(files, fm):
    files['dir1'] = ...

    # The directory itself should not be listed.
    fm('ls')
    fm.check_not_output('dir1')


def test_from_subdirectory(files, fm):
    files['dir1/file1'] = 'a'
    files['file2'] = 'b'

    # Only the files in that directory should be listed.
    fm('ls', cwd='dir1')
    fm.check_lines('file1')
    fm.check_not_output('file2')

    # Limiting to the current directory should not make a difference.
    fm('ls .', cwd='dir1')
    fm.check_lines('file1')
    fm.check_not_output('file2')

    # Explicitly specifying the parent directory or passing '-a' should print
    # both files.
    fm('ls ..', cwd='dir1')
    fm.check_lines('file1', '../file2')
    fm('ls -a', cwd='dir1')
    fm.check_lines('file1', '../file2')


def test_relative_paths(files, fm):
    files['dir1/file1'] = 'a'
    files['dir2/file2'] = 'b'

    # Paths are listed correctly with relative paths.
    fm('ls -a', cwd='dir1')
    fm.check_lines('file1', '../dir2/file2')

    # Paths can be specified using relative paths.
    fm('ls ../dir2/file2', cwd='dir1')
    fm.check_lines('../dir2/file2')


def test_files_are_sorted(files, fm):
    files['1/a'] = 'a'
    files['1/b'] = 'b'
    files['2/a'] = 'c'
    files['2/b'] = 'd'

    fm('ls')
    lines_without_intended_paths = [i for i in fm.lines if '=>' not in i]

    # The files should be printed in some consistent order (i.e. sorted).
    assert is_subsequence_of(
        ['1/a', '1/b', '2/a', '2/b'],
        lines_without_intended_paths)


def test_no_sub_command(files, fm):
    files['file1'] = 'a'

    # Update the cache, because we're disabling that below for better
    # reproducibility (updating the cache might print log messages).
    fm('')

    # Running filemaster without a sub-command should give us the same output
    # as running with ls -s.
    fm('-U')
    output = fm.output
    fm('-U ls -s')
    assert fm.output == output


def test_cache_not_updated(files, fm):
    files['file1'] = 'a'

    # Files not in the index should not be listed, even when they are
    # specified on the command line.
    fm('-U ls file1')
    fm.check_not_output('file1')

    # Index the file, remove it, the try to list it. This should not work,
    # even though the file is still in the index.
    fm('')
    del files['file1']
    fm.expect_error('Path does not exist')
    fm('-U ls file1')

    # Specifying the existing parent directory instead will list the file.
    fm('-U ls')
    fm.check_lines('file1')
