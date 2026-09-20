from collections.abc import Callable
from contextlib import AbstractContextManager

import mss
import numpy as np

from wx_red_helper.models import WindowSnapshot


class ScreenshotSession(AbstractContextManager["ScreenshotSession"]):
    def grab(self, bbox: dict[str, int]) -> object: ...


class ClientCapture:
    def __init__(self, session_factory: Callable[[], ScreenshotSession] = mss.mss) -> None:
        self._session_factory = session_factory

    def capture(self, window: WindowSnapshot) -> np.ndarray:
        rect = window.client_rect
        bbox = {"left": rect.left, "top": rect.top, "width": rect.width, "height": rect.height}
        with self._session_factory() as session:
            raw_frame = np.asarray(session.grab(bbox))
        return raw_frame[:, :, :3].copy()
