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

    def collect(self, label: str, frame: np.ndarray) -> Path:
        if label not in TEMPLATE_LABELS:
            raise ValueError(f"unsupported template label: {label}")
        window_title = selection_window_title()
        selection = cv2.selectROI(window_title, frame, showCrosshair=True)
        cv2.destroyWindow(window_title)
        x, y, width, height = (int(value) for value in selection)
        if width <= 0 or height <= 0:
            raise ValueError("template selection must not be empty")
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
