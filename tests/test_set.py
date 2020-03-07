from tests.testutil import FM


def test_single_files(files, fm):
    files['file1'] = 'a'
    files['file2'] = 'b'

    # The intended path should be recorded.
    fm('set file1 file3')
    fm.index.check_intended_path('a', 'file3')

    # The intended path for both files should be recorded.
    fm('set file1 file2 file4')
    fm.index.check_intended_path('a', 'file4')
    fm.index.check_intended_path('b', 'file4')

    # The intended path should include the file's names.
    fm('set file1 file2 dir1/')
    fm.index.check_intended_path('a', 'dir1/file1')
    fm.index.check_intended_path('b', 'dir1/file2')


def test_directory(files, fm):
    files['dir1/file1'] = 'a'

    # The intended path should be recorded.
    fm('set dir1 dir2')
    fm.index.check_intended_path('a', 'dir2/file1')

    # The intended path should include the original directory's name.
    fm('set dir1 dir2/')
    fm.index.check_intended_path('a', 'dir2/dir1/file1')


def test_from_subdirectory(files, fm):
    files['file1'] = 'a'
    files['dir1/dir2'] = ...

    # The file is specified using a relative path containing a `..` component.
    fm('set ../file1 ./', cwd='dir1')
    fm.index.check_intended_path('a', 'dir1/file1')

    # The intended path is also specified using relative path containing `..`
    # components.
    fm('set ../../file1 ../../', cwd='dir1/dir2')
    fm.index.check_intended_path('a', 'file1')


def test_intended_path_outside_of_root(files, fake_subprocess):
    files['fm/file1'] = 'a'

    # Initialize the repository in its root directory.
    fm = FM(files.root / 'fm', fake_subprocess)
    fm('init')

    # Setting an intended path outside the root should not work.
    fm.expect_error('is outside the repository\'s root directory')
    fm('set file1 ..')


def test_set_updating_cache(files, fm):
    files['file1'] = 'a'
    fm('')

    # Change the file and set an intended path for it without updating the
    # cache.
    files['file1'] = 'b'
    fm('-U set file1 file2')

    # The intended path should be associated with the old file content
    fm.index.check_intended_path('a', 'file2')
