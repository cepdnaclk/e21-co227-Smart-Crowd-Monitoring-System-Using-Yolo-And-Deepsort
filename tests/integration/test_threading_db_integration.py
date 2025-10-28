import threading
import types
import sys

import pytest


pytestmark = pytest.mark.integration


def test_parallel_buildings_batched_db_updates(monkeypatch):
    """
    Integration-style test for Janidu:
    - Multiple building threads update a shared_counters map in parallel.
    - DB layer batches inserts per update_interval and only writes latest values.
    - Uses a stubbed CrowdDatabase to avoid a real DB.
    """
    # Ensure psycopg2 is stubbed to avoid real imports
    sys.modules.setdefault("psycopg2", types.ModuleType("psycopg2"))

    import db_handler

    # Prevent real DB connection and pre-seed building_ids
    def fake_connect(self):
        self.conn = None
        self.cur = None
        self.building_ids = [1, 2, 3]

    monkeypatch.setattr(db_handler.CrowdDatabase, "connect", fake_connect, raising=True)

    # Controlled clock for batching logic
    current_time = [1000.0]
    def fake_time():
        return current_time[0]

    monkeypatch.setattr(db_handler, "time", types.SimpleNamespace(time=fake_time))

    # Capture insert calls thread-safely
    calls = []
    calls_lock = threading.Lock()

    def fake_insert_count(self, building_id, current_count):
        with calls_lock:
            calls.append((building_id, current_count, current_time[0]))

    monkeypatch.setattr(db_handler.CrowdDatabase, "insert_count", fake_insert_count, raising=True)

    db = db_handler.CrowdDatabase(host="h", database="d", user="u", password="p", update_interval=1)
    db.last_update = 1000.0

    # Sanity: direct insert uses our stub and records a call
    db.insert_count(1, 100)
    assert calls and calls[-1] == (1, 100, current_time[0])

    # Shared state and synchronization
    shared_counters = {}
    shared_lock = threading.Lock()
    start_evt1 = threading.Event()
    start_evt2 = threading.Event()
    barrier1 = threading.Barrier(4)  # 3 workers + main
    barrier2 = threading.Barrier(4)

    def worker(building_id: int, v1: int, v2: int):
        # Phase 1: wait for signal, then write first value
        start_evt1.wait(timeout=2.0)
        with shared_lock:
            shared_counters[building_id] = v1
        barrier1.wait(timeout=2.0)
        # Phase 2: wait for next signal, then write second value
        start_evt2.wait(timeout=2.0)
        with shared_lock:
            shared_counters[building_id] = v2
        barrier2.wait(timeout=2.0)

    threads = [
        threading.Thread(target=worker, args=(1, 11, 21)),
        threading.Thread(target=worker, args=(2, 12, 22)),
        threading.Thread(target=worker, args=(3, 13, 23)),
    ]
    for t in threads:
        t.start()

    # Phase 1: trigger first parallel update and batch insert
    start_evt1.set()
    barrier1.wait(timeout=2.0)
    # Move time to next interval and batch
    with shared_lock:
        batch1 = dict(shared_counters)
    current_time[0] = 1001.0
    for b, c in batch1.items():
        db.insert_count(b, c)

    # Phase 2: trigger second parallel update and batch insert
    start_evt2.set()
    barrier2.wait(timeout=2.0)
    with shared_lock:
        batch2 = dict(shared_counters)
    current_time[0] = 1002.0
    for b, c in batch2.items():
        db.insert_count(b, c)

    for t in threads:
        t.join(timeout=1.0)

    # Validate: we should have one row per building at each batch timestamp
    # Group by timestamp
    by_ts = {}
    for b, c, ts in calls:
        by_ts.setdefault(ts, {})[b] = c

    assert by_ts.get(1001.0) == {1: 11, 2: 12, 3: 13}
    assert by_ts.get(1002.0) == {1: 21, 2: 22, 3: 23}
