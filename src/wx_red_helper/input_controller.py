import ctypes
from collections.abc import Callable
from dataclasses import dataclass

from wx_red_helper.models import RunMode


@dataclass(frozen=True)
class InputResult:
    executed: bool
    reason: str


class InputController:
    def __init__(
        self,
        send_click: Callable[[tuple[int, int]], None],
        recheck: Callable[[int, int], bool],
    ) -> None:
        self._send_click = send_click
        self._recheck = recheck

    def execute_click(self, x: int, y: int, mode: RunMode) -> InputResult:
        if mode is RunMode.STOPPED:
            return InputResult(False, "mode_stopped")
        if mode is RunMode.DETECT:
            return InputResult(False, "mode_detect")
        if not self._recheck(x, y):
            return InputResult(False, "window_recheck_failed")
        self._send_click((x, y))
        return InputResult(True, "executed")


def absolute_mouse_coordinate(x: int, y: int, width: int, height: int) -> tuple[int, int]:
    if width <= 1 or height <= 1:
        raise ValueError("virtual screen dimensions must exceed one pixel")
    return (round(x * 65535 / (width - 1)), round(y * 65535 / (height - 1)))


class _MouseInput(ctypes.Structure):
    _fields_ = [
        ("dx", ctypes.c_long),
        ("dy", ctypes.c_long),
        ("mouseData", ctypes.c_ulong),
        ("dwFlags", ctypes.c_ulong),
        ("time", ctypes.c_ulong),
        ("dwExtraInfo", ctypes.c_size_t),
    ]


class _InputUnion(ctypes.Union):
    _fields_ = [("mi", _MouseInput)]


class _Input(ctypes.Structure):
    _anonymous_ = ("data",)
    _fields_ = [("type", ctypes.c_ulong), ("data", _InputUnion)]


def send_windows_click(point: tuple[int, int]) -> None:
    """Send one normal left click through User32 after the caller's safety checks."""
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    get_metric = user32.GetSystemMetrics
    get_metric.argtypes = (ctypes.c_int,)
    get_metric.restype = ctypes.c_int
    virtual_left = get_metric(76)
    virtual_top = get_metric(77)
    virtual_width = get_metric(78)
    virtual_height = get_metric(79)
    x, y = point
    absolute_x, absolute_y = absolute_mouse_coordinate(
        x - virtual_left, y - virtual_top, virtual_width, virtual_height
    )
    move_flags = 0x0001 | 0x8000 | 0x4000
    inputs = (_Input * 3)(
        _Input(0, _InputUnion(_MouseInput(absolute_x, absolute_y, 0, move_flags, 0, 0))),
        _Input(0, _InputUnion(_MouseInput(0, 0, 0, 0x0002, 0, 0))),
        _Input(0, _InputUnion(_MouseInput(0, 0, 0, 0x0004, 0, 0))),
    )
    send_input = user32.SendInput
    send_input.argtypes = (ctypes.c_uint, ctypes.POINTER(_Input), ctypes.c_int)
    send_input.restype = ctypes.c_uint
    count = send_input(len(inputs), inputs, ctypes.sizeof(_Input))
    if count != len(inputs):
        raise ctypes.WinError(ctypes.get_last_error())
