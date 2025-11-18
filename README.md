# Crowd Monitoring System

Real-time people counting and crowd monitoring using YOLOv8 + DeepSort for multi-camera feeds, storing results in PostgreSQL, and exposing them via a FastAPI backend with a React (Vite) frontend.

## Features
- Person detection (YOLOv8) and multi-object tracking (DeepSort)
- Entrance/exit line crossing with direction-aware counting
- Threaded processing for multiple buildings/feeds
- PostgreSQL persistence of counts (per-building historical records)
- FastAPI JSON endpoints (`/crowd`, `/crowd/history`) + optional static frontend
- React dashboard (Chart.js) consuming API
- Config-driven feed lines & thresholds (`config.json`)

## Architecture
```
main.py (processing threads) --> PostgreSQL <-- api.py (FastAPI) <-- React frontend (Vite dev proxy or static build)
```
- `main.py` loads `config.json`, starts one thread per building, tracks objects, writes aggregated counts regularly.
- `db_handler.py` manages resilient DB inserts.
- `api.py` serves latest & historical counts; can also serve the built frontend bundle from `frontend/dist`.

## Quick Start (Windows PowerShell)
```powershell
# 1. Python env
py -3.11 -m venv .venv
./.venv/Scripts/Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt

# 2. PostgreSQL schema (connect to crowd_monitor DB)
# Run the SQL in sql/init_schema.sql

# 3. Processing (people counting)
python ./main.py  # opens OpenCV windows; press 'q' to stop

# 4. API
python ./api.py   # serves on http://localhost:5000

# 5a. Frontend (dev)
cd ./frontend
npm install
npm run dev -- --host  # accessible at http://<YOUR_IP>:5173

# 5b. Frontend (build + serve from API)
npm run build
# restart api.py, then browse http://<YOUR_IP>:5000
```

## Configuration (`config.json`)
Key sections:
- `database`: connection settings to Postgres
- `yolo`: `model_path`, `device` ("cpu" or "cuda")
- `buildings`: Each building has `entrance` / `exit` feed entries with `line` definition:
```json
"1": {
  "entrance": {
    "url": "people_video3.mp4",
    "line": {"type": "horizontal", "coords": [0,240,480,240], "enter_direction": "up"}
  },
  "exit": { ... }
}
```
`enter_direction` influences whether crossing increments entrance vs exit count.

## Database Schema
See `sql/init_schema.sql` for:
- `buildings(building_id, building_name)`
- `crowd_counts(id, building_id, current_count, timestamp)`

Ensure building IDs inserted here match those in `config.json`.

## LAN Access
Dev server: `npm run dev -- --host` then visit `http://<YOUR_PC_IP>:5173`
Production: build frontend (`npm run build`), run `api.py` (binds 0.0.0.0) and visit `http://<YOUR_PC_IP>:5000`
Find IP via `ipconfig` or Vite's output.

## Testing
Run all tests:
```powershell
pytest
```
Selective smoke:
```powershell
pytest -k crowd
```
Local DB integration (creates temp DB) requires:
```powershell
$env:RUN_LOCAL_DB_TESTS="1"
pytest tests/integration/test_api_db_local.py
```

## Troubleshooting
| Issue | Fix |
|-------|-----|
| Torch/CUDA errors | Set `"device": "cpu"` in `config.json`; reinstall torch if needed |
| Feed not opening | Use absolute path / valid RTSP URL; test with VLC; check permissions |
| No counts updating | Ensure building IDs exist in DB; verify `main.py` console shows detections |
| API returns DB error | Verify Postgres running and credentials match; tables created |
| Frontend 404 in production | Run `npm run build`; restart `api.py`; check `frontend/dist` exists |
| Port already in use | Change port in `api.py` or stop conflicting process (use `netstat -ano`) |

## Recommended Git Hygiene
Add `.venv/`, `node_modules/`, build artifacts, caches to `.gitignore`. Keep small model weights; large custom weights can be stored via Git LFS.

## Scripts Added
- `scripts/start_api.ps1` – activates venv & runs API
- `scripts/start_processing.ps1` – activates venv & runs processing

## Future Improvements
- Health endpoint for processing service
- Docker compose (Postgres + API + processing + frontend)
- Metrics & logging centralization
- Alerting based on thresholds

## License
(Choose a license and add a LICENSE file – e.g., MIT)
