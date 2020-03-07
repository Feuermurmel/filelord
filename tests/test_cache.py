import io
import pathlib

import pytest
import unittest.mock

from filemaster.cache import FileCache


class CacheHarness:
    def __init__(self, cache):
        self.cache = cache
        self.current_ctime = 100
        self.files = {}

        # Used to count the number of files opened for reading. Reset to 0
        # each time update() is called.
        self.files_read = None

    def iter_regular_files(self, root, filter_fn):
        for path, (ctime, content) in self.files.items():
            data = content.encode()

            def open_fn(_):
                self.files_read += 1
                return io.BytesIO(data)

            m = unittest.mock.Mock()
            m.stat.return_value.st_ctime = ctime
            m.stat.return_value.st_size = len(data)
            m.open = open_fn

            yield m

    def get_current_ctime(self):
        return self.current_ctime

    def update(self):
        self.files_read = 0

        self.cache.update(
            file_checked_progress_fn=lambda: None,
            data_read_progress_fn=lambda _: None)


@pytest.fixture
def cache_harness(tmp_path, monkeypatch):
    cache_store_path = tmp_path / 'filecache'
    cache_store_path.touch()

    cache = FileCache(
        store_path=cache_store_path,
        root_path=pathlib.Path('/'),
        filter_fn=lambda x: True)

    cache_harness = CacheHarness(cache)

    monkeypatch.setattr(
        'filemaster.cache.iter_regular_files',
        cache_harness.iter_regular_files)

    monkeypatch.setattr(
        'filemaster.cache.FileCache._get_current_ctime',
        cache_harness.get_current_ctime)

    yield cache_harness


def test_simple(cache_harness):
    # Start off by checking that the test harness works.
    cache_harness.update()
    assert cache_harness.files_read == 0
    assert len(cache_harness.cache.get_cached_files()) == 0

    cache_harness.files['/foo'] = 0, 'hello'
    cache_harness.update()
    assert cache_harness.files_read == 1
    assert len(cache_harness.cache.get_cached_files()) == 1
