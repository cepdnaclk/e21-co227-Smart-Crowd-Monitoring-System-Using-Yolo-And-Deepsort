import importlib
from contextlib import asynccontextmanager

import pytest

from network_utils import open_capture_with_retry
from backend_logic import should_process_frame


pytestmark = pytest.mark.integration


class FailingThenOKFactory:
    def __init__(self, fail_times=2, frames=10):
        self.fail_times = fail_times
        self.calls = 0
        self.frames = frames

    def __call__(self, url):
        self.calls += 1
        if self.calls <= self.fail_times:
            return FakeClosedCap()
        return FakeCapture(self.frames)


class FakeCapture:
    def __init__(self, frames=10):
        self.n = int(frames)
        self.i = 0
        self.open = True

    def isOpened(self):
        return self.open

    def read(self):
        if self.i >= self.n:
            return False, None
        self.i += 1
        return True, self.i  # frame index as payload


class FakeClosedCap:
    def isOpened(self):
        return False


@asynccontextmanager
async def no_lifespan(app):
    yield


def test_open_retry_sampling_and_threshold_alerts(monkeypatch):
    # 1) Open/retry: first 2 attempts fail, then capture is returned
    factory = FailingThenOKFactory(fail_times=2, frames=12)
    sleeps = []
    def fake_sleep(sec):
        sleeps.append(sec)

    cap = open_capture_with_retry(factory, url="dummy", max_attempts=5, wait_seconds=0.01, sleep_fn=fake_sleep)
    assert cap is not None
    assert factory.calls == 3  # 2 fails + 1 success
    assert len(sleeps) == 2

    # 2) Frame sampling: process only every 3rd frame
    processed = 0
    idx = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        idx += 1
        if should_process_frame(idx, stride=3, offset=0):
            processed += 1

    # With 12 frames and stride=3, we expect 4 processed frames
    assert processed == 4

    # 3) API threshold: stub DB and assert returned threshold + counts allow frontend alert logic
    api = importlib.import_module("api")
    importlib.reload(api)
    api.app.router.lifespan_context = no_lifespan

    # Lower threshold to trigger alert easily
    api.thresholds[1] = 3

    class FakeCursor:
        def __init__(self):
            self._rows = []
        def execute(self, query, params=None):
            q = " ".join(query.split()).lower()
            if q.startswith("select b.building_id"):
                self._rows = [
                    {
                        "building_id": 1,
                        "building_name": "B1",
                        "current_count": processed,
                        "timestamp": None,
                    }
                ]
            else:
                self._rows = []
        def fetchall(self):
            return self._rows

    api.cur = FakeCursor()

    from fastapi.testclient import TestClient
    with TestClient(api.app) as client:
        r = client.get("/crowd")
        assert r.status_code == 200
        data = r.json()

    assert isinstance(data, list) and len(data) == 1
    row = data[0]
    assert row["buildingId"] == 1
    assert row["currentCount"] == processed
    assert row["threshold"] == 3

    # Frontend alert logic (derived): currentCount >= threshold -> alert
    assert (row["currentCount"] >= row["threshold"]) is True
