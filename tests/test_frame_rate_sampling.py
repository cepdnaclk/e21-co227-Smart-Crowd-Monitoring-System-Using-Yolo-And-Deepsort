from backend_logic import should_process_frame


def test_should_process_frame_every_third_frame_default():
    # Matches main.py: frame_id starts at 0, then increment, process if frame_id % 3 == 0
    processed = [i for i in range(1, 11) if should_process_frame(i, stride=3, offset=0)]
    assert processed == [3, 6, 9]


def test_should_process_frame_with_offset():
    # Process frames 2,5,8 when offset=2 and stride=3
    processed = [i for i in range(1, 10) if should_process_frame(i, stride=3, offset=2)]
    assert processed == [2, 5, 8]


def test_should_process_frame_stride_one_process_all():
    processed = [i for i in range(1, 6) if should_process_frame(i, stride=1)]
    assert processed == [1, 2, 3, 4, 5]
