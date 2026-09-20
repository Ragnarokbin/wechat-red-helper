import pytest

from wx_red_helper.models import ClientRect


def test_relative_center_uses_current_client_rect() -> None:
    rect = ClientRect(left=200, top=100, width=1000, height=800)

    assert rect.point_at(0.5, 0.25) == (700, 300)


def test_relative_point_rejects_coordinate_outside_client_area() -> None:
    rect = ClientRect(left=200, top=100, width=1000, height=800)

    with pytest.raises(ValueError, match="relative coordinate"):
        rect.point_at(1.01, 0.25)
