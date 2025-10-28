import importlib
from contextlib import asynccontextmanager
from datetime import datetime, timedelta

import pytest


pytestmark = pytest.mark.integration


class FakeCursor:
    def __init__(self):
        self._rows = []

    def execute(self, query, params=None):
        q = " ".join(query.split()).lower()
        if q.startswith("select b.building_id"):
            now = datetime.now()
            self._rows = [
                {
                    "building_id": 1,
                    "building_name": "B1",
                    "current_count": 7,
                    "timestamp": now,
                },
                {
                    "building_id": 2,
                    "building_name": "B2",
                    "current_count": 0,
                    "timestamp": now,
                },
            ]
        elif q.startswith("select timestamp, current_count from crowd_counts"):
            base = datetime.now()
            self._rows = [
                {"timestamp": base - timedelta(minutes=5), "current_count": 3},
                {"timestamp": base - timedelta(minutes=1), "current_count": 5},
            ]
        else:
            self._rows = []

    def fetchall(self):
        return self._rows


@asynccontextmanager
async def no_lifespan(app):
    # Prevent real DB connections during tests
    yield


@pytest.fixture()
def api_with_stubbed_db(monkeypatch):
    api = importlib.import_module("api")
    importlib.reload(api)

    # Disable actual startup DB connection
    api.app.router.lifespan_context = no_lifespan
    # Provide a fake cursor used by endpoints
    api.cur = FakeCursor()
    return api


def test_crowd_contract_shape(api_with_stubbed_db):
    api = api_with_stubbed_db
    from fastapi.testclient import TestClient

    with TestClient(api.app) as client:
        r = client.get("/crowd")
        assert r.status_code == 200
        data = r.json()

    # Expect a list of objects with specific keys/types
    assert isinstance(data, list) and len(data) >= 2
    first = data[0]
    assert set(["buildingId", "buildingName", "currentCount", "timestamp", "threshold"]) <= set(first.keys())
    assert isinstance(first["buildingId"], int)
    assert isinstance(first["buildingName"], str)
    assert isinstance(first["currentCount"], int)
    assert isinstance(first["timestamp"], str)  # HH:MM string from api.py
    assert isinstance(first["threshold"], int)


def test_history_contract_shape(api_with_stubbed_db):
    api = api_with_stubbed_db
    from fastapi.testclient import TestClient

    with TestClient(api.app) as client:
        r = client.get("/crowd/history", params={"buildingId": 1, "minutes": 60})
        assert r.status_code == 200
        rows = r.json()

    assert isinstance(rows, list) and len(rows) >= 1
    row0 = rows[0]
    assert set(["timestamp", "count"]) <= set(row0.keys())
    assert isinstance(row0["timestamp"], str)  # isoformat string
    assert isinstance(row0["count"], int)
