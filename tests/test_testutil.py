import pytest


def test_fl_expect_error(fl):
    # A successful command after calling fl.expect_error() should raise an
    # assertion.
    with pytest.raises(AssertionError):
        fl.expect_error('')
        fl('ls')

    # Expecting an error message which is not output should raise an assertion.
    with pytest.raises(AssertionError):
        fl.expect_error('floop')
        fl('foo')


def test_fl_failure_caught(fl):
    # Running an invalid command without calling fl.expect_error() should
    # raise an assertion.
    with pytest.raises(AssertionError):
        fl('foo')

    # Expecting a matching error message should not raise an assertion.
    fl.expect_error('invalid choice')
    fl('foo')
