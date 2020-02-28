import pytest


# Also rewrite asserts in some additional modules.
pytest.register_assert_rewrite('tests.conftest', 'tests.testutil')
