import ctypes
from ctypes import wintypes

from wx_red_helper.models import ClientRect


class _Point(ctypes.Structure):
    _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]


class _Rect(ctypes.Structure):
    _fields_ = [
        ("left", wintypes.LONG),
        ("top", wintypes.LONG),
        ("right", wintypes.LONG),
        ("bottom", wintypes.LONG),
    ]


class WindowsApi:
    """Small, read-only User32 wrapper used by the foreground-window observer."""

    def __init__(self) -> None:
        self._user32 = ctypes.WinDLL("user32", use_last_error=True)
        self._user32.GetForegroundWindow.restype = wintypes.HWND
        self._user32.IsWindowVisible.argtypes = (wintypes.HWND,)
        self._user32.IsWindowVisible.restype = wintypes.BOOL
        self._user32.IsIconic.argtypes = (wintypes.HWND,)
        self._user32.IsIconic.restype = wintypes.BOOL
        self._user32.GetWindowTextW.argtypes = (wintypes.HWND, wintypes.LPWSTR, ctypes.c_int)
        self._user32.GetWindowTextW.restype = ctypes.c_int
        self._user32.GetClientRect.argtypes = (wintypes.HWND, ctypes.POINTER(_Rect))
        self._user32.GetClientRect.restype = wintypes.BOOL
        self._user32.ClientToScreen.argtypes = (wintypes.HWND, ctypes.POINTER(_Point))
        self._user32.ClientToScreen.restype = wintypes.BOOL

    def foreground_handle(self) -> int:
        return int(self._user32.GetForegroundWindow() or 0)

    def is_visible(self, handle: int) -> bool:
        return bool(self._user32.IsWindowVisible(wintypes.HWND(handle)))

    def is_minimized(self, handle: int) -> bool:
        return bool(self._user32.IsIconic(wintypes.HWND(handle)))

    def title(self, handle: int) -> str:
        buffer = ctypes.create_unicode_buffer(512)
        self._user32.GetWindowTextW(wintypes.HWND(handle), buffer, len(buffer))
        return buffer.value

    def client_rect_on_screen(self, handle: int) -> ClientRect:
        hwnd = wintypes.HWND(handle)
        rect = _Rect()
        if not self._user32.GetClientRect(hwnd, ctypes.byref(rect)):
            raise ctypes.WinError(ctypes.get_last_error())

        origin = _Point(0, 0)
        if not self._user32.ClientToScreen(hwnd, ctypes.byref(origin)):
            raise ctypes.WinError(ctypes.get_last_error())

        return ClientRect(
            left=origin.x,
            top=origin.y,
            width=rect.right - rect.left,
            height=rect.bottom - rect.top,
        )
