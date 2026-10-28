import pytest

from collector_engine.models import BlockedError, PermanentFetchError, TemporaryFetchError
from collector_engine.retry import retry_call


def test_succeeds_after_temporary_failures():
    calls = []

    def flaky():
        calls.append(1)
        if len(calls) < 3:
            raise TemporaryFetchError("timeout")
        return "ok"

    sleeps = []
    result, attempts = retry_call(flaky, max_attempts=3, base_delay=2, factor=2, sleep=sleeps.append)
    assert (result, attempts) == ("ok", 3)
    assert sleeps == [2, 4]  # exponential backoff


def test_gives_up_after_max_3_attempts():
    calls = []

    def always_fails():
        calls.append(1)
        raise TemporaryFetchError("down")

    sleeps = []
    with pytest.raises(TemporaryFetchError) as info:
        retry_call(always_fails, max_attempts=3, base_delay=2, sleep=sleeps.append)
    assert len(calls) == 3
    assert info.value.attempts == 3
    assert len(sleeps) == 2  # no sleep after the final attempt


@pytest.mark.parametrize("exc", [BlockedError("403"), PermanentFetchError("404"), ValueError("bug")])
def test_non_temporary_errors_are_not_retried(exc):
    calls = []

    def fail():
        calls.append(1)
        raise exc

    with pytest.raises(type(exc)):
        retry_call(fail, sleep=lambda s: None)
    assert len(calls) == 1
