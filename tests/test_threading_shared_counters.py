import threading
import time


def _worker(shared, lock, key, iterations):
    for _ in range(iterations):
        with lock:
            shared[key] = shared.get(key, 0) + 1


def test_shared_counters_thread_safety_and_progress():
    """
    Simple concurrency smoke test: multiple threads increment a shared counter
    under a lock. Ensures no race corruption and that threads make progress
    within a small timeout.
    """
    shared = {}
    lock = threading.Lock()

    num_threads = 8
    iters = 1000

    threads = [threading.Thread(target=_worker, args=(shared, lock, 1, iters)) for _ in range(num_threads)]
    for t in threads:
        t.start()

    # Join with an overall timeout to fail fast on deadlock
    deadline = time.time() + 5
    for t in threads:
        remaining = max(0, deadline - time.time())
        t.join(timeout=remaining)

    # All threads should have finished; if not, test will fail on count mismatch
    expected = num_threads * iters
    assert shared.get(1, 0) == expected
