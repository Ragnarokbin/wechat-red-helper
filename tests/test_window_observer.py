import numpy as np

from wx_red_helper.capture import ClientCapture
from wx_red_helper.models import ClientRect, WindowSnapshot
from wx_red_helper.window_observer import WechatWindowObserver


class FakeWinApi:
    def __init__(self, *, title: str = "家人群 - 微信", visible: bool = True, minimized: bool = False) -> None:
        self._title = title
        self._visible = visible
        self._minimized = minimized

    def foreground_handle(self) -> int:
        return 12

    def is_visible(self, handle: int) -> bool:
        return self._visible

    def is_minimized(self, handle: int) -> bool:
        return self._minimized

    def title(self, handle: int) -> str:
        return self._title

    def client_rect_on_screen(self, handle: int) -> ClientRect:
        return ClientRect(20, 30, 900, 700)


def test_observer_accepts_visible_foreground_wechat_window() -> None:
    observed = WechatWindowObserver(FakeWinApi(), ("微信", "WeChat")).observe()

    assert observed is not None
    assert observed.handle == 12
    assert observed.client_rect == ClientRect(20, 30, 900, 700)


def test_observer_rejects_minimized_window() -> None:
    observed = WechatWindowObserver(FakeWinApi(minimized=True), ("微信", "WeChat")).observe()

    assert observed is None


def test_observer_rejects_non_wechat_foreground_window() -> None:
    observed = WechatWindowObserver(FakeWinApi(title="记事本"), ("微信", "WeChat")).observe()

    assert observed is None


class FakeScreenshotSession:
    def __init__(self) -> None:
        self.bbox: dict[str, int] | None = None

    def __enter__(self) -> "FakeScreenshotSession":
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        return None

    def grab(self, bbox: dict[str, int]) -> np.ndarray:
        self.bbox = bbox
        return np.zeros((bbox["height"], bbox["width"], 4), dtype=np.uint8)


def test_capture_uses_only_client_rectangle() -> None:
    session = FakeScreenshotSession()
    window = WindowSnapshot(12, "家人群 - 微信", ClientRect(20, 30, 900, 700), 1)

    frame = ClientCapture(lambda: session).capture(window)

    assert session.bbox == {"left": 20, "top": 30, "width": 900, "height": 700}
    assert frame.shape == (700, 900, 3)
