import pytest

from testutil import FL, Files, FakeSubprocess


@pytest.fixture
def fake_subprocess(capsys, monkeypatch):
    """
    Fixture which has a `run()` method which can be used as a replacement for
    `subprocess.run()` and calls an entry point function instead of creating
    a subprocess.
    """

    return FakeSubprocess(capsys, monkeypatch)


@pytest.fixture
def fl(tmp_path, fake_subprocess):
    """
    Provide an `FL` instance with an already initialized repository.
    """

    fl = FL(tmp_path, fake_subprocess)
    fl('init')

    return fl


@pytest.fixture
def files(tmp_path):
    """
    Provide a `Files` instance, which allows very concise access to the files
    in a temporary directory.
    """

    return Files(tmp_path)
