from wx_red_helper.input_controller import InputController, absolute_mouse_coordinate
from wx_red_helper.models import RunMode


def test_detect_mode_never_sends_click() -> None:
    sent: list[tuple[int, int]] = []
    controller = InputController(sent.append, lambda x, y: True)

    result = controller.execute_click(300, 400, RunMode.DETECT)

    assert result.executed is False
    assert result.reason == "mode_detect"
    assert sent == []


def test_auto_mode_refuses_click_when_recheck_fails() -> None:
    sent: list[tuple[int, int]] = []
    controller = InputController(sent.append, lambda x, y: False)

    result = controller.execute_click(300, 400, RunMode.AUTO)

    assert result.executed is False
    assert result.reason == "window_recheck_failed"
    assert sent == []


def test_auto_mode_sends_click_only_after_recheck() -> None:
    sent: list[tuple[int, int]] = []
    controller = InputController(sent.append, lambda x, y: x == 300 and y == 400)

    result = controller.execute_click(300, 400, RunMode.AUTO)

    assert result.executed is True
    assert sent == [(300, 400)]


def test_absolute_mouse_coordinate_uses_virtual_screen_range() -> None:
    assert absolute_mouse_coordinate(960, 540, 1920, 1080) == (32785, 32798)
