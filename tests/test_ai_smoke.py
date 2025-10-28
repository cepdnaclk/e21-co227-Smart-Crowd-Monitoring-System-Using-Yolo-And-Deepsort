"""Optional smoke tests for AI components (YOLO, DeepSort).

These are intentionally light and skipped by default to avoid heavy installs
and long runtimes. Enable by setting the environment variable RUN_AI_TESTS=1
or by explicitly selecting markers.
"""
import os
import pytest


RUN_AI = os.getenv("RUN_AI_TESTS") == "1"


pytestmark = pytest.mark.skipif(
    not RUN_AI,
    reason="Set RUN_AI_TESTS=1 to run AI smoke tests (YOLO/DeepSort)",
)


@pytest.mark.ai
@pytest.mark.slow
def test_yolo_load_and_infer_on_blank_image():
    ultralytics = pytest.importorskip("ultralytics")
    import numpy as np
    import os

    # Try to use the local lightweight model file
    weights = "yolov8n.pt"
    if not os.path.exists(weights):
        pytest.skip("yolov8n.pt not found in project root")

    model = ultralytics.YOLO(weights)

    # Run on a tiny blank frame just to validate the pipeline doesn't crash
    img = np.zeros((320, 320, 3), dtype=np.uint8)
    results = model(img, conf=0.5, verbose=False, device="cpu")

    # Basic sanity checks on output structure
    assert isinstance(results, list) and len(results) >= 1
    r0 = results[0]
    # results[0].boxes may be empty if blank; just ensure attribute exists
    assert hasattr(r0, "boxes")


@pytest.mark.ai
@pytest.mark.slow
def test_deepsort_tracking_single_object_sequence():
    dsrt = pytest.importorskip("deep_sort_realtime.deepsort_tracker")
    import numpy as np

    DeepSort = dsrt.DeepSort
    tracker = DeepSort(max_age=10)

    # Two frames with a single detection moving slightly right/down
    frame = np.zeros((480, 640, 3), dtype=np.uint8)

    dets_f1 = [([100, 100, 50, 80], 0.9, 0)]  # (x, y, w, h), conf, cls
    tracks1 = tracker.update_tracks(dets_f1, frame=frame)

    dets_f2 = [([110, 110, 50, 80], 0.9, 0)]
    tracks2 = tracker.update_tracks(dets_f2, frame=frame)

    # Not all tracks will be confirmed immediately; at least the call must succeed
    assert isinstance(tracks1, list)
    assert isinstance(tracks2, list)
