"""Utilities for network/stream management with testable hooks.

These mirror the retry logic used when opening camera streams, but abstract
sleep and capture construction for easy unit testing.
"""
from __future__ import annotations

from typing import Callable, Optional, Protocol, Any


class _Cap(Protocol):
    def isOpened(self) -> bool: ...


def open_capture_with_retry(
    factory: Callable[[str], _Cap],
    url: str,
    *,
    max_attempts: int = 13,
    wait_seconds: float = 5.0,
    sleep_fn: Optional[Callable[[float], Any]] = None,
) -> Optional[_Cap]:
    """
    Try to open a video capture, retrying if it isn't opened.

    - factory: callable that returns a capture object (like cv2.VideoCapture)
    - url: stream/file URL
    - max_attempts: total attempts before giving up (default 13 to match main.py >12 check)
    - wait_seconds: delay between attempts
    - sleep_fn: injected sleep function; if None, uses a no-op to keep tests fast

    Returns a capture handle or None if it couldn't be opened after attempts.
    """
    if sleep_fn is None:
        def sleep_fn(_: float) -> None:  # type: ignore[no-redef]
            return None

    attempts = 0
    cap = factory(url)
    while not cap.isOpened():
        attempts += 1
        if attempts >= max_attempts:
            return None
        sleep_fn(wait_seconds)
        cap = factory(url)
    return cap

#python -m pytest tests/integration/test_network_sampling_alerts_integration.py -q