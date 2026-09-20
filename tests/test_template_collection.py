from pathlib import Path

import cv2
import numpy as np

from wx_red_helper.cli import _collect_template
from wx_red_helper.templates import TemplateCollector


def test_cancelled_roi_keeps_existing_template_and_returns_no_destination(tmp_path, monkeypatch) -> None:
    """A zero-sized ROI is the user cancelling, not a failed template update."""
    destination = tmp_path / "envelope_card.png"
    destination.write_bytes(b"existing-template")
    monkeypatch.setattr(cv2, "selectROI", lambda *args, **kwargs: (0, 0, 0, 0))
    monkeypatch.setattr(cv2, "destroyWindow", lambda *args, **kwargs: None)

    result = TemplateCollector(tmp_path).collect("envelope_card", np.zeros((20, 20, 3), dtype=np.uint8))

    assert result is None
    assert destination.read_bytes() == b"existing-template"


def test_cancelled_template_collection_returns_to_the_launcher_without_saving(monkeypatch, capsys) -> None:
    class VisibleWindowObserver:
        def __init__(self, *args) -> None:
            pass

        def observe(self) -> object:
            return object()

    class Capturer:
        def capture(self, window: object) -> np.ndarray:
            return np.zeros((20, 20, 3), dtype=np.uint8)

    class CancellingCollector:
        def __init__(self, directory: Path) -> None:
            pass

        def collect(self, label: str, frame: np.ndarray) -> None:
            return None

    monkeypatch.setattr("wx_red_helper.cli.WechatWindowObserver", VisibleWindowObserver)
    monkeypatch.setattr("wx_red_helper.cli.ClientCapture", Capturer)
    monkeypatch.setattr("wx_red_helper.cli.TemplateCollector", CancellingCollector)

    result = _collect_template("envelope_card", 0)

    output = capsys.readouterr().out
    assert result == 0
    assert "已取消本次截图，已保留原有模板。" in output
    assert "模板已保存" not in output
