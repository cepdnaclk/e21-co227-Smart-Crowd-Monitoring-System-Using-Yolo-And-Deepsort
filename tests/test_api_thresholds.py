from datetime import datetime
import sys
import types


class FakeCursor:
    def execute(self, *args, **kwargs):
        return None

    def fetchall(self):
        return [
            {"building_id": 1, "building_name": "B1", "current_count": 12, "timestamp": datetime.now()},
            {"building_id": 2, "building_name": "B2", "current_count": 3, "timestamp": datetime.now()},
        ]


def test_crowd_includes_threshold_per_building(monkeypatch):
    # Inject minimal dummies so `import api` works without heavy deps
    psycopg2 = types.ModuleType("psycopg2")
    extras = types.ModuleType("psycopg2.extras")
    class RealDictCursor:  # placeholder
        pass
    extras.RealDictCursor = RealDictCursor
    psycopg2.extras = extras
    sys.modules["psycopg2"] = psycopg2
    sys.modules["psycopg2.extras"] = extras
    sys.modules["cv2"] = types.ModuleType("cv2")  # stub OpenCV

    import api  # now safe to import

    # Use fake DB cursor and call handler directly (no startup events)
    monkeypatch.setattr(api, "cur", FakeCursor(), raising=True)
    data = api.get_crowd_counts()

    by_id = {row["buildingId"]: row for row in data}
    assert by_id[1]["threshold"] == api.thresholds.get(1, api.default_threshold)
    assert by_id[2]["threshold"] == api.thresholds.get(2, api.default_threshold)
