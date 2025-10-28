import types
from network_utils import open_capture_with_retry


class DummyCap:
    def __init__(self, opened: bool):
        self._opened = opened

    def isOpened(self) -> bool:
        return self._opened


def test_open_capture_succeeds_after_retries():
    attempts = {"n": 0}
    sleeps = {"count": 0}

    def factory(_url: str):
        attempts["n"] += 1
        # Fail first 3 times, succeed on 4th
        return DummyCap(opened=(attempts["n"] >= 4))

    def fake_sleep(_secs: float):
        sleeps["count"] += 1

    cap = open_capture_with_retry(factory, "dummy", max_attempts=10, wait_seconds=0.01, sleep_fn=fake_sleep)
    assert cap is not None
    # Sleep should have been called exactly for the failed attempts (3 times)
    assert sleeps["count"] == 3


def test_open_capture_gives_up_after_max_attempts():
    sleeps = {"count": 0}

    def factory(_url: str):
        return DummyCap(opened=False)

    def fake_sleep(_secs: float):
        sleeps["count"] += 1

    cap = open_capture_with_retry(factory, "dummy", max_attempts=5, wait_seconds=0.01, sleep_fn=fake_sleep)
    assert cap is None
    # max_attempts=5 -> four waits (between attempts)
    assert sleeps["count"] == 4
