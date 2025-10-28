import os
import importlib

import pytest


pytestmark = pytest.mark.integration


def test_static_mount_serves_files(tmp_path):
    # Import the app normally
    api = importlib.import_module("api")

    static_dir = getattr(api, "static_dir", None)
    if not static_dir or not os.path.isdir(static_dir):
        pytest.skip("Static directory not available in this environment")

    # Create a unique test file under the mounted static directory
    test_file = os.path.join(static_dir, "__static_test_ok__.html")
    with open(test_file, "w", encoding="utf-8") as f:
        f.write("<html><body>OK</body></html>")

    try:
        from fastapi.testclient import TestClient
        client = TestClient(api.app)
        resp = client.get("/__static_test_ok__.html")
        assert resp.status_code == 200
        assert "OK" in resp.text
    finally:
        try:
            os.remove(test_file)
        except Exception:
            pass
