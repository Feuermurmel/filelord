import pytest

from tests.testutil import FM, Files, FakeSubprocess


@pytest.fixture
def fake_subprocess(capsys, monkeypatch):
    """
    Fixture which has a `run()` method which can be used as a replacement for
    `subprocess.run()` and calls an entry point function instead of creating
    a subprocess.
    """

    return FakeSubprocess(capsys, monkeypatch)


@pytest.fixture
def fm(tmp_path, fake_subprocess):
    """
    Provide an `FM` instance with an already initialized repository.
    """

    fm = FM(tmp_path, fake_subprocess)
    fm('init')

    return fm


@pytest.fixture
def files(tmp_path):
    """
    Provide a `Files` instance, which allows very concise access to the files
    in a temporary directory.
    """

    return Files(tmp_path)
