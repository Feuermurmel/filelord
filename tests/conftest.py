import pytest

from tests.testutil import FM, Files


@pytest.fixture
def fm(tmp_path):
    """
    Provide an `FM` instance with an already initialized repository.
    """

    fm = FM(tmp_path)
    fm('init')

    return fm


@pytest.fixture
def files(tmp_path):
    """
    Provide a `Files` instance, which allows very concise access to the files
    in a temporary directory.
    """

    return Files(tmp_path)
