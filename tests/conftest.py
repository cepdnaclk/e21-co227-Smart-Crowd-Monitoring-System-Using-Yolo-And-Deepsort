"""Test configuration to ensure project root is importable when running from tests/.

Pytest auto-loads this file. It prepends the repository root to sys.path so
`import backend_logic` (and other project modules) resolves whether you run
pytest from the repo root or from the tests directory.
"""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
