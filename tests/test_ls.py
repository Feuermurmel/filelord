from testutil import is_subsequence_of


def test_lists_files(files, fl):
    files['dir1/file1'] = 'a'
    files['file2'] = 'b'

    # All files should be listed.
    fl('ls')
    fl.check_lines('dir1/file1', 'file2')

    # Test limiting to a directory.
    fl('ls dir1')
    fl.check_lines('dir1/file1')
    fl.check_not_output('file2')

    # Test limiting to a file.
    fl('ls file2')
    fl.check_lines('file2')
    fl.check_not_output('dir1')


def test_empty_directory(files, fl):
    files['dir1'] = ...

    # The directory itself should not be listed.
    fl('ls')
    fl.check_not_output('dir1')


def test_from_subdirectory(files, fl):
    files['dir1/file1'] = 'a'
    files['file2'] = 'b'

    # Only the files in that directory should be listed.
    fl('ls', cwd='dir1')
    fl.check_lines('file1')
    fl.check_not_output('file2')

    # Limiting to the current directory should not make a difference.
    fl('ls .', cwd='dir1')
    fl.check_lines('file1')
    fl.check_not_output('file2')

    # Explicitly specifying the parent directory or passing '-a' should print
    # both files.
    fl('ls ..', cwd='dir1')
    fl.check_lines('file1', '../file2')
    fl('ls -a', cwd='dir1')
    fl.check_lines('file1', '../file2')


def test_relative_paths(files, fl):
    files['dir1/file1'] = 'a'
    files['dir2/file2'] = 'b'

    # Paths are listed correctly with relative paths.
    fl('ls -a', cwd='dir1')
    fl.check_lines('file1', '../dir2/file2')

    # Paths can be specified using relative paths.
    fl('ls ../dir2/file2', cwd='dir1')
    fl.check_lines('../dir2/file2')


def test_files_are_sorted(files, fl):
    files['1/a'] = 'a'
    files['1/b'] = 'b'
    files['2/a'] = 'c'
    files['2/b'] = 'd'

    fl('ls')
    lines_without_intended_paths = [i for i in fl.lines if '=>' not in i]

    # The files should be printed in some consistent order (i.e. sorted).
    assert is_subsequence_of(
        ['1/a', '1/b', '2/a', '2/b'],
        lines_without_intended_paths)


def test_no_sub_command(files, fl):
    files['file1'] = 'a'

    # Update the cache, because we're disabling that below for better
    # reproducibility (updating the cache might print log messages).
    fl('')

    # Running filelord without a sub-command should give us the same output
    # as running with ls -s.
    fl('-U')
    output = fl.output
    fl('-U ls -s')
    assert fl.output == output


def test_cache_not_updated(files, fl):
    files['file1'] = 'a'

    # Files not in the index should not be listed, even when they are
    # specified on the command line.
    fl('-U ls file1')
    fl.check_not_output('file1')

    # Index the file, remove it, the try to list it. This should not work,
    # even though the file is still in the index.
    fl('')
    del files['file1']
    fl.expect_error('Path does not exist')
    fl('-U ls file1')

    # Specifying the existing parent directory instead will list the file.
    fl('-U ls')
    fl.check_lines('file1')
