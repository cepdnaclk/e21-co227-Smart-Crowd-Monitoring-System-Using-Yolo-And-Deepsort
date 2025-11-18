# Setup Guide (Extended)

## 1. Python Environment
```powershell
py -3.11 -m venv .venv
./.venv/Scripts/Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```
If activation is blocked by execution policy:
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

## 2. Database
Run the schema file:
```powershell
psql -U postgres -d crowd_monitor -f sql/init_schema.sql
```
(Or copy-paste contents into PgAdmin query tool.)

## 3. Configuration
Edit `config.json`:
- Set absolute file paths for local video feeds if needed (escape backslashes).
- Set `"device": "cpu"` unless CUDA is verified.

## 4. Processing Service
```powershell
./.venv/Scripts/Activate.ps1
python ./main.py
```
Opens OpenCV windows; each shows entrance/exit tracking. Press `q` to quit.

## 5. API Service
```powershell
./.venv/Scripts/Activate.ps1
python ./api.py
```
Endpoints:
- `GET /` health message
- `GET /crowd` latest counts
- `GET /crowd/history?buildingId=1&minutes=60` historical window

## 6. Frontend
Dev mode (network accessible):
```powershell
cd ./frontend
npm install
npm run dev -- --host
```
Production build served by API:
```powershell
npm run build
# restart api.py and visit http://localhost:5000
```

## 7. Testing
```powershell
pytest               # full test suite
pytest -k api        # subset by keyword
```
Local temp DB integration test (creates and drops a DB automatically):
```powershell
$env:RUN_LOCAL_DB_TESTS="1"
pytest tests/integration/test_api_db_local.py
```

## 8. Troubleshooting Quick Table
| Symptom | Cause | Resolution |
|---------|-------|------------|
| Torch import error | Incomplete wheel install | `pip install --force-reinstall torch torchvision` |
| OpenCV can't open video | Wrong path or codec | Use full path; test in VLC; ensure file readable |
| API returns empty list | No rows yet | Keep processing running until inserts occur |
| History endpoint empty | Time range misses rows | Increase `minutes` or ensure timestamps are current |
| Vite not reachable via LAN | Host flag missing | Run `npm run dev -- --host` or add `host: true` in `vite.config.js` |
| Port already in use | Previous process running | Find with `netstat -ano | findstr :5000` then `taskkill /PID <pid> /F` |

## 9. Security / Prod Notes
- Replace default DB password before deploying beyond local.
- Consider Docker Compose for isolated dev reproduction.
- Enable authentication for API if exposed externally.

## 10. Next Steps
- Containerize services
- Add alerting when `current_count` exceeds threshold
- Include Grafana/Prometheus metrics
