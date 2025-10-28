import pytest

from backend_logic import check_line_crossing


@pytest.mark.parametrize(
    "prev,curr,line_pos,enter_dir,expected",
    [
        # Horizontal line at y=100
        ((50, 90), (50, 110), 100, "down", "entrance"),   # crosses down -> entrance
        ((50, 110), (50, 90), 100, "down", "exit"),       # crosses up -> exit
        ((50, 110), (50, 90), 100, "up", "entrance"),     # with enter up, up-cross is entrance
        ((50, 90), (50, 110), 100, "up", "exit"),         # down-cross becomes exit
        ((50, 90), (50, 95), 100, "down", None),           # no crossing
    ],
)
def test_horizontal_crossing(prev, curr, line_pos, enter_dir, expected):
    result = check_line_crossing(prev, curr, line_type="horizontal", line_pos=line_pos, enter_direction=enter_dir)
    assert result == expected


@pytest.mark.parametrize(
    "prev,curr,line_pos,enter_dir,expected",
    [
        # Vertical line at x=200
        ((190, 50), (210, 50), 200, "right", "entrance"),  # left -> right
        ((210, 50), (190, 50), 200, "right", "exit"),      # right -> left
        ((210, 50), (190, 50), 200, "left", "entrance"),   # entrance is left
        ((190, 50), (210, 50), 200, "left", "exit"),       # crossing opposite to entrance dir
        ((190, 50), (195, 50), 200, "right", None),         # no crossing
    ],
)
def test_vertical_crossing(prev, curr, line_pos, enter_dir, expected):
    result = check_line_crossing(prev, curr, line_type="vertical", line_pos=line_pos, enter_direction=enter_dir)
    assert result == expected
