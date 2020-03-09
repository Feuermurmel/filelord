import contextlib
import io
import pathlib
import unittest.mock

import pytest

from filemaster.cache import with_file_cache
from filemaster.util import bytes_digest


class CacheHarness:
    """
    Class used to implement the `cache_harness` fixture which encapsulates a
    `FileCache` instance.
    """

    def __init__(self, cache):
        self.cache = cache
        self.current_ctime = 100

        # Maps from paths as strings to tuple s of ctime and content as string.
        self.files = {}

        # Used to count the number of files opened for reading. Reset to 0
        # each time update() is called.
        self.files_hashed = None

    def iter_regular_files(self, root, filter_fn):
        return iter(sorted(pathlib.Path(i) for i in self.files))

    def get_current_ctime(self):
        return self.current_ctime

    def file_digest(self, path, progress_fn):
        _, content = self.files[str(path)]

        if content is None:
            raise IOError
        else:
            # Do not count it as a "file hashed" when we purposefully
            # interrupt the cache updating by throwing an exception.
            self.files_hashed += 1

            return bytes_digest(content.encode())

    def stat_path(self, path):
        ctime, content = self.files[str(path)]

        if content is None:
            size = 0
        else:
            size = len(content.encode())

        m = unittest.mock.Mock()
        m.st_ctime = ctime
        m.st_size = size

        return m

    def update(self):
        self.files_hashed = 0

        self.cache.update(
            file_checked_progress_fn=lambda: None,
            data_read_progress_fn=lambda _: None)


@pytest.fixture
def cache_harness_factory(tmp_path, monkeypatch):
    """
    This fixture is used to implement the `cache_harness` fixture. It can be
    used directly to control when the `FileCache` instance wrapped by
    `CacheHarness` is loaded and unloaded.
    """

    cache_store_path = tmp_path / 'filecache'
    cache_store_path.touch()

    @contextlib.contextmanager
    def fn():
        with with_file_cache(cache_store_path, pathlib.Path('/'), lambda x: True) as cache:
            cache_harness = CacheHarness(cache)

            with monkeypatch.context() as m:
                m.setattr(
                    'filemaster.cache.iter_regular_files',
                    cache_harness.iter_regular_files)

                m.setattr(
                    'filemaster.cache.FileCache._get_current_ctime',
                    cache_harness.get_current_ctime)

                m.setattr(
                    'filemaster.cache.file_digest',
                    cache_harness.file_digest)

                m.setattr(
                    'filemaster.cache._stat_path',
                    cache_harness.stat_path)

                yield cache_harness

    return fn


@pytest.fixture
def cache_harness(cache_harness_factory):
    """
    Fixture which creates a `FileCache` instance with its store placed in a
    temporary directory and patches file system access from the cache use
    fake data which can be supplied via the `FileCache` instance.
    """

    with cache_harness_factory() as cache_harness:
        yield cache_harness


def test_simple(cache_harness):
    # Start off by checking that the test harness works.
    cache_harness.update()
    assert cache_harness.files_hashed == 0
    assert len(cache_harness.cache.get_cached_files()) == 0

    # Add a single file and update.
    cache_harness.files['/foo'] = 0, 'hello'
    cache_harness.update()
    assert cache_harness.files_hashed == 1
    assert len(cache_harness.cache.get_cached_files()) == 1

    # Add another file. Only that file shold be read.
    cache_harness.files['/bar'] = 0, 'hello'
    cache_harness.update()
    assert cache_harness.files_hashed == 1
    assert len(cache_harness.cache.get_cached_files()) == 2


def test_write_log(cache_harness):
    cache_harness.files['/a'] = 0, 'a'
    cache_harness.files['/b'] = 0, None
    cache_harness.files['/c'] = 0, 'c'

    # Update the cache. The operation will abort when the path /b is reached.
    with pytest.raises(IOError):
        cache_harness.update()

    # A single file should be read and the cache should still be emtpy.
    assert cache_harness.files_hashed == 1
    assert len(cache_harness.cache.get_cached_files()) == 0

    # Remove the file which aborts the operations and update the cache again.
    # Only a single file shoud still need to be hashed.
    del cache_harness.files['/b']
    cache_harness.update()
    assert cache_harness.files_hashed == 1
    assert len(cache_harness.cache.get_cached_files()) == 2


def test_write_log_new_cache_instance(cache_harness_factory):
    # Same as `test_write_log`, but use a new `FileCache` instance after
    # interrupting the cache updating.
    with cache_harness_factory() as cache_harness:
        cache_harness.files['/a'] = 0, 'a'
        cache_harness.files['/b'] = 0, None

        with pytest.raises(IOError):
            cache_harness.update()

        assert cache_harness.files_hashed == 1
        assert len(cache_harness.cache.get_cached_files()) == 0

    with cache_harness_factory() as cache_harness:
        cache_harness.files['/a'] = 0, 'a'
        cache_harness.files['/c'] = 0, 'c'

        cache_harness.update()
        assert cache_harness.files_hashed == 1
        assert len(cache_harness.cache.get_cached_files()) == 2


def test_moved_file_recorded(cache_harness):
    cache_harness.files['/a'] = 0, 'a'
    cache_harness.update()

    # Move a file.
    del cache_harness.files['/a']
    cache_harness.files['/b'] = 0, 'a'

    # Add a hint for the new path of the file.
    entry = cache_harness.cache.get_cached_files()[0]
    cache_harness.cache.add_hint(entry._replace(path=pathlib.Path('/b')))

    # The file shold not need to be read again because of the hint.
    cache_harness.update()
    assert cache_harness.files_hashed == 0
    assert len(cache_harness.cache.get_cached_files()) == 1

    # Add another hint which is ultimately not used.
    entry = cache_harness.cache.get_cached_files()[0]
    cache_harness.cache.add_hint(entry._replace(path=pathlib.Path('/c')))

    # The hint should not be used when updating the cache again.
    cache_harness.update()
    assert cache_harness.files_hashed == 0
    assert len(cache_harness.cache.get_cached_files()) == 1
