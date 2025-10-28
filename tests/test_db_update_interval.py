import time as _time
import types
import sys

import pytest


def test_insert_multiple_counts_respects_update_interval(monkeypatch):
    # Provide a stub psycopg2 before importing db_handler
    sys.modules.setdefault("psycopg2", types.ModuleType("psycopg2"))
    # Now import the module and patch DB connectivity away
    import db_handler

    # Prevent real DB connect on init
    monkeypatch.setattr(db_handler.CrowdDatabase, "connect", lambda self: None, raising=True)

    calls = []

    # Patch insert_count to record calls without touching a DB
    def fake_insert_count(self, building_id, current_count):
        calls.append((building_id, current_count, current_time[0]))

    monkeypatch.setattr(db_handler.CrowdDatabase, "insert_count", fake_insert_count, raising=True)

    # Controlled time source
    current_time = [1000.0]

    def fake_time():
        return current_time[0]

    monkeypatch.setattr(db_handler, "time", types.SimpleNamespace(time=fake_time))

    db = db_handler.CrowdDatabase(host="h", database="d", user="u", password="p", update_interval=2)
    # Initialize last_update to 1000 internally via constructor's default
    db.last_update = 1000.0

    counters = {1: 10, 2: 5}

    # t = 1000.0 -> interval not passed, no calls
    db.insert_multiple_counts(counters)
    assert calls == []

    # t = 1001.9 -> still within interval
    current_time[0] = 1001.9
    db.insert_multiple_counts(counters)
    assert calls == []

    # t = 1002.0 -> interval reached, should call once per building
    current_time[0] = 1002.0
    db.insert_multiple_counts(counters)
    assert sorted(calls) == [(1, 10, 1002.0), (2, 5, 1002.0)]

    # Next call before next interval -> no new calls
    current_time[0] = 1003.0
    db.insert_multiple_counts(counters)
    assert len(calls) == 2

    # After another full interval -> new batch
    current_time[0] = 1004.1
    db.insert_multiple_counts(counters)
    assert len(calls) == 4
