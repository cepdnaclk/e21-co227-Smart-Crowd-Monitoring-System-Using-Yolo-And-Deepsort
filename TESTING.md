# Backend unit tests

This repo includes focused unit tests for core backend evaluation scopes:
- Counts per building (inside = max(0, entrances - exits))
- Enter/exit decision based on line-crossing direction
- Detection threshold filtering (confidence + class name)

## What’s tested
- `backend_logic.py` contains small, pure helpers that mirror the logic from `main.py` so they’re easy to test.
- `tests/test_logic_crossing.py`: verifies enter/exit for horizontal and vertical lines with different directions.
- `tests/test_logic_crowd.py`: verifies inside-count calculation and clamping to zero.
- `tests/test_detection_threshold.py`: verifies confidence threshold + person class filtering.
- `tests/test_api_thresholds.py`: verifies that `/crowd` returns a `threshold` value per building. It stubs `cv2` and `psycopg2` modules so no heavy deps or DB are needed during the test.

## How to run (Windows PowerShell)

If you don’t want to install the full runtime dependencies, you can install only what’s needed for tests:

```powershell
# from the repository root
# ensure venv is active; if not created, create it:
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# install minimal test deps
python -m pip install -U pip
python -m pip install pytest fastapi==0.110.0 "uvicorn[standard]==0.23.2"

# run tests
python -m pytest -q
```

If you prefer to install all dependencies:

```powershell
# from repo root with venv active
python -m pip install -r requirements.txt
python -m pytest -q
```

## Notes
- The tests avoid importing heavyweight CV/ML packages (Ultralytics/Torch/OpenCV) by isolating logic into `backend_logic.py` and stubbing modules where needed.
- You can extend tests to cover more edge cases (e.g., debounce windows, multiple simultaneous crossings, malformed config values).