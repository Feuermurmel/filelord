from testutil import FL


def test_single_files(files, fl):
    files['file1'] = 'a'
    files['file2'] = 'b'

    # The intended path should be recorded.
    fl('set file1 file3')
    fl.index.check_intended_path('a', 'file3')

    # The intended path for both files should be recorded.
    fl('set file1 file2 file4')
    fl.index.check_intended_path('a', 'file4')
    fl.index.check_intended_path('b', 'file4')

    # The intended path should include the file's names.
    fl('set file1 file2 dir1/')
    fl.index.check_intended_path('a', 'dir1/file1')
    fl.index.check_intended_path('b', 'dir1/file2')


def test_directory(files, fl):
    files['dir1/file1'] = 'a'

    # The intended path should be recorded.
    fl('set dir1 dir2')
    fl.index.check_intended_path('a', 'dir2/file1')

    # The intended path should include the original directory's name.
    fl('set dir1 dir2/')
    fl.index.check_intended_path('a', 'dir2/dir1/file1')


def test_from_subdirectory(files, fl):
    files['file1'] = 'a'
    files['dir1/dir2'] = ...

    # The file is specified using a relative path containing a `..` component.
    fl('set ../file1 ./', cwd='dir1')
    fl.index.check_intended_path('a', 'dir1/file1')

    # The intended path is also specified using relative path containing `..`
    # components.
    fl('set ../../file1 ../../', cwd='dir1/dir2')
    fl.index.check_intended_path('a', 'file1')


def test_intended_path_outside_of_root(files, fake_subprocess):
    files['fl/file1'] = 'a'

    # Initialize the repository in its root directory.
    fl = FL(files.root / 'fl', fake_subprocess)
    fl('init')

    # Setting an intended path outside the root should not work.
    fl.expect_error('is outside the repository\'s root directory')
    fl('set file1 ..')


def test_set_updating_cache(files, fl):
    files['file1'] = 'a'
    fl('')

    # Change the file and set an intended path for it without updating the
    # cache.
    files['file1'] = 'b'
    fl('-U set file1 file2')

    # The intended path should be associated with the old file content
    fl.index.check_intended_path('a', 'file2')
