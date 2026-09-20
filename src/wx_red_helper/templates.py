import os
import sys
from contextlib import contextmanager
from pathlib import Path

import cv2
import numpy as np


TEMPLATE_LABELS = ("chat_header", "envelope_card", "open_button", "result")


class TemplateRepository:
    def __init__(self, directory: Path) -> None:
        self._directory = directory

    def load(self) -> dict[str, np.ndarray]:
        templates: dict[str, np.ndarray] = {}
        for label in TEMPLATE_LABELS:
            path = self._directory / f"{label}.png"
            if not path.exists():
                continue
            image = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
            if image is None or image.size == 0:
                raise ValueError(f"template is unreadable: {path}")
            templates[label] = image
        return templates


class TemplateCollector:
    def __init__(self, directory: Path) -> None:
        self._directory = directory

    def collect(self, label: str, frame: np.ndarray) -> Path | None:
        if label not in TEMPLATE_LABELS:
            raise ValueError(f"unsupported template label: {label}")
        window_title = selection_window_title()
        print(selection_console_prompt())
        with suppress_native_console_output():
            selection = cv2.selectROI(window_title, frame, showCrosshair=True)
        cv2.destroyWindow(window_title)
        x, y, width, height = (int(value) for value in selection)
        if width <= 0 or height <= 0:
            return None
        template = frame[y : y + height, x : x + width]
        self._directory.mkdir(parents=True, exist_ok=True)
        temporary = self._directory / f".{label}.tmp.png"
        destination = self._directory / f"{label}.png"
        if not cv2.imwrite(str(temporary), template):
            raise OSError(f"unable to write template: {temporary}")
        temporary.replace(destination)
        return destination


def selection_window_title() -> str:
    return "请选择模板区域，按 Enter 确认，按 Esc 取消"


def selection_console_prompt() -> str:
    return "请拖动鼠标框选区域；按空格或 Enter 确认，按 Esc 或 C 取消。"


@contextmanager
def suppress_native_console_output():
    """Temporarily hide OpenCV's hard-coded ROI instructions for this CLI action."""
    stdout_fd = sys.stdout.fileno()
    stderr_fd = sys.stderr.fileno()
    saved_stdout = os.dup(stdout_fd)
    saved_stderr = os.dup(stderr_fd)
    try:
        with open(os.devnull, "w", encoding="utf-8") as null:
            sys.stdout.flush()
            sys.stderr.flush()
            os.dup2(null.fileno(), stdout_fd)
            os.dup2(null.fileno(), stderr_fd)
            yield
    finally:
        os.dup2(saved_stdout, stdout_fd)
        os.dup2(saved_stderr, stderr_fd)
        os.close(saved_stdout)
        os.close(saved_stderr)
