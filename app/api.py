import os
from fastapi import FastAPI, Response, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import psycopg2
from psycopg2.extras import RealDictCursor
import json
import sys
import uvicorn
import os
import time
import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timedelta

"""FastAPI app providing crowd counts and history from PostgreSQL.

Note: Startup/shutdown use FastAPI lifespan to avoid deprecated on_event.
"""

def _project_root(path: str) -> str:
    return os.path.abspath(os.path.join(path, os.pardir))


# --- Load config first ---
if getattr(sys, 'frozen', False):
    base_path = sys._MEIPASS  # type: ignore[attr-defined]
else:
    base_path = os.path.dirname(__file__)

def _load_config(base_path: str) -> dict:
    candidates = [
        os.path.join(base_path, "config.json"),
        os.path.join(_project_root(base_path), "config", "config.json"),
        os.path.join(_project_root(base_path), "config.json"),
    ]
    for p in candidates:
        try:
            if os.path.exists(p):
                with open(p, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception:
            pass
    raise FileNotFoundError("config.json not found in expected locations (app dir, ../config/, ../)")


config = _load_config(base_path)

# --- DB credentials ---
db_config = config.get("database", {})

DB_HOST = os.getenv("DB_HOST", db_config.get("host", "localhost"))
DB_PORT = int(os.getenv("DB_PORT", str(db_config.get("port", 5432))))
DB_NAME = os.getenv("DB_NAME", db_config.get("database", "crowd_monitor"))
DB_USER = os.getenv("DB_USER", db_config.get("user", "postgres"))
DB_PASS = os.getenv("DB_PASS", db_config.get("password", "111@Postgres"))

# --- Camera URLs & Thresholds ---
camera_urls = {}
thresholds = {}
default_threshold = int(config.get("default_threshold", 50))
for b_id, cams in config.get("buildings", {}).items():
    if "entrance" in cams:
        camera_urls[f"{b_id}_entrance"] = cams["entrance"]
    if "exit" in cams:  # only add if it exists
        camera_urls[f"{b_id}_exit"] = cams["exit"]
    # collect per-building threshold if present
    try:
        thresholds[int(b_id)] = int(cams.get("threshold", default_threshold))
    except Exception:
        # ignore malformed ids/thresholds
        pass




"""Globals for DB connection; set during lifespan startup."""
conn = None
cur = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage DB connection with retries using FastAPI lifespan API."""
    global conn, cur
    retries = 0
    while retries < 5:
        try:
            conn = psycopg2.connect(
                host=DB_HOST,
                database=DB_NAME,
                user=DB_USER,
                password=DB_PASS,
                port=DB_PORT,
            )
            cur = conn.cursor(cursor_factory=RealDictCursor)
            print("✅ DB connected (API)")
            break
        except Exception as e:
            retries += 1
            print(f"❌ API DB connect failed (attempt {retries}): {e}")
            await asyncio.sleep(5 * retries)

    try:
        yield
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()
        print("DB disconnected")


# Create app with lifespan
app = FastAPI(lifespan=lifespan)

# --- CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------- API ENDPOINTS ----------------
@app.get("/crowd")
def get_crowd_counts():
    """Returns latest crowd counts for all buildings."""
    if cur is None:
        return {"error": "Database not available"}
    try:
        query = """
            SELECT b.building_id, b.building_name, c.current_count, c.timestamp
            FROM buildings b
            JOIN LATERAL (
                SELECT current_count, timestamp
                FROM crowd_counts c2
                WHERE c2.building_id = b.building_id
                ORDER BY timestamp DESC
                LIMIT 1
            ) c ON true
            ORDER BY b.building_id;
        """
        cur.execute(query)
        rows = cur.fetchall()
    except Exception as e:
        return {"error": f"DB query failed: {e}"}

    return [
        {
            "buildingId": row["building_id"],
            "buildingName": row["building_name"],
            "currentCount": row["current_count"],
            "timestamp": row["timestamp"].strftime("%H:%M") if hasattr(row["timestamp"], "strftime") else str(row["timestamp"]),
            "threshold": thresholds.get(row["building_id"], default_threshold)
        }
        for row in rows
    ]

# Optional: list routes for debugging
@app.get("/_routes")
def list_routes():
    return [{"path": r.path, "methods": list(r.methods)} for r in app.routes]

@app.get("/")
def root():
    return {"message": "API is running"}

# Historical counts for a building
@app.get("/crowd/history")
def get_crowd_history(
    buildingId: int = Query(..., description="Building ID"),
    minutes: int | None = Query(60, ge=1, le=60*24*7, description="Lookback in minutes (ignored if start/end provided)"),
    start: str | None = Query(None, description="ISO datetime start, e.g., 2025-10-26T12:00:00"),
    end: str | None = Query(None, description="ISO datetime end, e.g., 2025-10-26T13:00:00"),
):
    if cur is None:
        return {"error": "Database not available"}
    try:
        if start and end:
            try:
                start_dt = datetime.fromisoformat(start)
                end_dt = datetime.fromisoformat(end)
            except Exception:
                return {"error": "Invalid start/end format. Use ISO-8601, e.g., 2025-10-26T12:00:00"}
        else:
            end_dt = datetime.now()
            lookback = minutes or 60
            start_dt = end_dt - timedelta(minutes=int(lookback))

        query = (
            "SELECT timestamp, current_count FROM crowd_counts "
            "WHERE building_id = %s AND timestamp BETWEEN %s AND %s "
            "ORDER BY timestamp ASC"
        )
        cur.execute(query, (buildingId, start_dt, end_dt))
        rows = cur.fetchall()
        return [
            {
                "timestamp": (row["timestamp"].isoformat() if hasattr(row["timestamp"], "isoformat") else str(row["timestamp"])),
                "count": row["current_count"],
            }
            for row in rows
        ]
    except Exception as e:
        return {"error": f"DB query failed: {e}"}

# Serve React build if present, otherwise fall back to current directory
# Allow disabling in tests with DISABLE_STATIC=1 to avoid any route shadowing
if os.getenv("DISABLE_STATIC") != "1":
    try:
        frontend_dist = os.path.join(_project_root(base_path), "frontend", "dist")
        static_dir = frontend_dist if os.path.isdir(frontend_dist) else _project_root(base_path)
        app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
        print(f"Static served from: {static_dir}")
    except Exception as e:
        print(f"Static mount failed: {e}")
else:
    print("Static mounting disabled via DISABLE_STATIC=1")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)