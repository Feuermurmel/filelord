import pytest


def test_fm_expect_error(fm):
    # A successful command after calling fm.expect_error() should raise an
    # assertion.
    with pytest.raises(AssertionError):
        fm.expect_error('')
        fm('ls')

    # Expecting an error message which is not output should raise an assertion.
    with pytest.raises(AssertionError):
        fm.expect_error('floop')
        fm('foo')


def test_fm_failure_caught(fm):
    # Running an invalid command without calling fm.expect_error() should
    # raise an assertion.
    with pytest.raises(AssertionError):
        fm('foo')

    # Expecting a matching error message should not raise an assertion.
    fm.expect_error('invalid choice')
    fm('foo')
