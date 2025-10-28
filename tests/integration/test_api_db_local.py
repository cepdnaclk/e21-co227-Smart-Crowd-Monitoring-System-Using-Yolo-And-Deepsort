"""Integration tests for API + local PostgreSQL (no Docker required).

Safety: This test creates a temporary database on your local Postgres server,
uses it for the API, then drops it. It runs ONLY when RUN_LOCAL_DB_TESTS=1.
"""
import importlib
import os
import time
import uuid
from contextlib import closing

import pytest


pytestmark = pytest.mark.integration


def _can_run_local_tests() -> bool:
    return os.getenv("RUN_LOCAL_DB_TESTS") == "1"


@pytest.mark.skipif(not _can_run_local_tests(), reason="Set RUN_LOCAL_DB_TESTS=1 to run local DB integration tests")
def test_api_with_local_temp_database(monkeypatch):
    import psycopg2

    host = os.getenv("DB_HOST", "localhost")
    port = int(os.getenv("DB_PORT", "5432"))
    admin_db = os.getenv("DB_ADMIN_DB", "postgres")  # DB to connect for CREATE DATABASE
    user = os.getenv("DB_USER", "postgres")
    password = os.getenv("DB_PASS", "111@Postgres")

    temp_db = f"it_db_{uuid.uuid4().hex[:8]}"

    # Connect to admin DB and create a temp database for this test
    with closing(psycopg2.connect(host=host, port=port, dbname=admin_db, user=user, password=password)) as conn:
        conn.autocommit = True
        with conn.cursor() as cur:
            try:
                cur.execute(f"CREATE DATABASE {temp_db}")
            except Exception as e:
                pytest.skip(f"Could not create temp DB '{temp_db}': {e}")

    # Create schema and seed inside the temp DB
    SCHEMA_SQL = (
        "CREATE TABLE buildings (building_id INT PRIMARY KEY, building_name TEXT NOT NULL);"
        "CREATE TABLE crowd_counts ("
        " id SERIAL PRIMARY KEY,"
        " building_id INT NOT NULL REFERENCES buildings(building_id),"
        " current_count INT NOT NULL,"
        " timestamp TIMESTAMP NOT NULL DEFAULT NOW() );"
    )

    with closing(psycopg2.connect(host=host, port=port, dbname=temp_db, user=user, password=password)) as conn2:
        with conn2.cursor() as cur2:
            cur2.execute(SCHEMA_SQL)
            cur2.execute("INSERT INTO buildings (building_id, building_name) VALUES (1, 'B1'), (2, 'B2')")
            cur2.execute(
                "INSERT INTO crowd_counts (building_id, current_count, timestamp) VALUES (1, 12, NOW()), (2, 3, NOW())"
            )
            conn2.commit()

    # Point the API at the temp DB via env vars and reload app
    monkeypatch.setenv("DB_HOST", host)
    monkeypatch.setenv("DB_PORT", str(port))
    monkeypatch.setenv("DB_NAME", temp_db)
    monkeypatch.setenv("DB_USER", user)
    monkeypatch.setenv("DB_PASS", password)

    api = importlib.import_module("api")

    from fastapi.testclient import TestClient
    # Use context manager to ensure FastAPI lifespan closes DB connections before we drop DB
    with TestClient(api.app) as client:
        resp = client.get("/crowd")
        assert resp.status_code == 200
        data = resp.json()
        by_id = {row["buildingId"]: row for row in data}
        assert by_id[1]["currentCount"] == 12
        assert by_id[2]["currentCount"] == 3

        r2 = client.get("/crowd/history", params={"buildingId": 1, "minutes": 60})
        assert r2.status_code == 200
        assert len(r2.json()) >= 1

    # Drop the temp database (retry briefly in case of lingering connections)
    with closing(psycopg2.connect(host=host, port=port, dbname=admin_db, user=user, password=password)) as conn3:
        conn3.autocommit = True
        with conn3.cursor() as cur3:
            for _ in range(5):
                try:
                    cur3.execute(f"DROP DATABASE {temp_db}")
                    break
                except Exception:
                    time.sleep(0.2)
