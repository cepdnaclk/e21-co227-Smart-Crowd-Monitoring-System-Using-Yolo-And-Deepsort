from backend_logic import compute_crowd_inside


def test_compute_crowd_inside_basic():
    assert compute_crowd_inside(entrance_count=10, exit_count=3) == 7


def test_compute_crowd_inside_never_negative():
    assert compute_crowd_inside(entrance_count=2, exit_count=5) == 0
