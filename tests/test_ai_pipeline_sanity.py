import os
import pytest

from backend_logic import filter_person_detections


pytestmark = pytest.mark.ai


@pytest.mark.skipif(os.getenv("RUN_AI_TESTS") != "1", reason="Set RUN_AI_TESTS=1 to enable AI tests")
def test_yolo_runs_and_filters_person(tmp_path):
    # Lazy import heavy deps
    try:
        from ultralytics import YOLO
        import numpy as np
    except Exception as e:  # pragma: no cover
        pytest.skip(f"AI deps not available: {e}")

    # Use the local small model to keep it fast
    model_path = "yolov8n.pt"
    model = YOLO(model_path)

    # Create a simple blank image; no detections expected
    img = (np.zeros((320, 320, 3), dtype=np.uint8))
    results = model.predict(img, verbose=False)

    # The pipeline should produce a results list with .names mapping
    assert isinstance(results, (list, tuple)) and len(results) >= 1
    class_names = getattr(results[0], "names", {}) or getattr(model, "names", {}) or {}
    assert isinstance(class_names, dict)

    # Build detections tuple list similar to (cls_id, conf, x1,y1,x2,y2)
    # For a blank image, detections may be empty
    dets = []
    filtered = filter_person_detections(dets, class_names=class_names, min_conf=0.25, person_label="person")
    assert isinstance(filtered, list)


#$env:RUN_AI_TESTS='1'
#python -m pytest -q -k test_ai_pipeline_sanity -m ai