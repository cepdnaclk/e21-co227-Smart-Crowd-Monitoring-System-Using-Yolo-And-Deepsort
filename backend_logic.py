"""
Small, testable helpers extracted from the backend logic.

These functions mirror the behavior in `main.py` around:
- determining entrance vs exit when a tracked point crosses a counting line
- computing crowd inside from entrance/exit counters
- filtering detections by confidence and class name (lightweight stand-in for YOLO filtering)
"""
from __future__ import annotations

from typing import Literal, Optional, Tuple


DirectionH = Literal["up", "down"]
DirectionV = Literal["left", "right"]
LineType = Literal["horizontal", "vertical"]


def check_line_crossing(
    prev: Tuple[int, int] | None,
    curr: Tuple[int, int],
    *,
    line_type: LineType,
    line_pos: Optional[int],
    enter_direction: Optional[str] = None,
) -> Optional[Literal["entrance", "exit"]]:
    """
    Decide whether a tracked point crossing constitutes an entrance or exit.

    Inputs
    - prev: previous (cx, cy) or None if not available yet
    - curr: current (cx, cy)
    - line_type: 'horizontal' or 'vertical'
    - line_pos: pixel coordinate of the line (y if horizontal, x if vertical)
    - enter_direction: preferred direction that counts as 'entrance'.
      For horizontal lines: 'down' or 'up'. For vertical: 'right' or 'left'.
      If None, defaults to 'down' (horizontal) or 'right' (vertical), matching main.py behavior.

    Output
    - 'entrance' | 'exit' | None (no crossing)
    """
    if prev is None or line_pos is None:
        return None

    prev_cx, prev_cy = prev
    cx, cy = curr

    if line_type == "horizontal":
        # Crossings across y = line_pos
        crossed_down = prev_cy < line_pos <= cy
        crossed_up = prev_cy > line_pos >= cy
        if not (crossed_down or crossed_up):
            return None

        desired: DirectionH = (enter_direction or "down").lower()  # default old behavior
        if (crossed_down and desired == "down") or (crossed_up and desired == "up"):
            return "entrance"
        return "exit"

    if line_type == "vertical":
        # Crossings across x = line_pos
        crossed_right = prev_cx < line_pos <= cx
        crossed_left = prev_cx > line_pos >= cx
        if not (crossed_right or crossed_left):
            return None

        desired: DirectionV = (enter_direction or "right").lower()
        if (crossed_right and desired == "right") or (crossed_left and desired == "left"):
            return "entrance"
        return "exit"

    # unknown type
    return None


def compute_crowd_inside(entrance_count: int, exit_count: int) -> int:
    """Mirror `max(0, entrance - exit)` logic from main.py."""
    return max(0, int(entrance_count) - int(exit_count))


def filter_person_detections(
    detections: list[tuple[Tuple[int, int, int, int], float, int]],
    *,
    class_names: dict[int, str],
    min_conf: float = 0.4,
    person_label: str = "person",
) -> list[tuple[Tuple[int, int, int, int], float, int]]:
    """
    Lightweight filter to emulate the YOLO + class gating used in main.py.

    Inputs
    - detections: list of (xywh, confidence, class_id)
    - class_names: mapping from class_id -> label (like `model.names`)
    - min_conf: minimum confidence threshold
    - person_label: label name to keep

    Output
    - filtered list matching both confidence and class label
    """
    out = []
    for xywh, conf, cls_id in detections:
        if conf >= min_conf and class_names.get(int(cls_id)) == person_label:
            out.append((xywh, float(conf), int(cls_id)))
    return out


def should_process_frame(frame_index: int, *, stride: int = 3, offset: int = 0) -> bool:
    """
    Decide whether to process a frame based on sampling stride.

    Mirrors logic like: `frame_id += 1; if frame_id % 3 == 0: ...` when offset=0, stride=3.

    - frame_index: the 1-based (or monotonically increasing) frame counter
    - stride: process every Nth frame
    - offset: shift the phase; e.g., process when (frame_index - offset) % stride == 0
    """
    if stride <= 0:
        return True
    return ((int(frame_index) - int(offset)) % int(stride)) == 0
