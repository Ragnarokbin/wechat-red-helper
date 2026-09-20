import cv2
import numpy as np

from wx_red_helper.models import TemplateMatch


class FrameRecognizer:
    def __init__(self, templates: dict[str, np.ndarray], threshold: float) -> None:
        if not 0 < threshold <= 1:
            raise ValueError("threshold must be between 0 and 1")
        self._templates = templates
        self._threshold = threshold

    def recognize(self, frame: np.ndarray) -> list[TemplateMatch]:
        gray_frame = _as_gray(frame)
        matches: list[TemplateMatch] = []
        for label, template in self._templates.items():
            gray_template = _as_gray(template)
            if gray_template.shape[0] > gray_frame.shape[0] or gray_template.shape[1] > gray_frame.shape[1]:
                continue
            score_map = cv2.matchTemplate(gray_frame, gray_template, cv2.TM_CCOEFF_NORMED)
            _, score, _, location = cv2.minMaxLoc(score_map)
            if score >= self._threshold:
                height, width = gray_template.shape[:2]
                matches.append(TemplateMatch(label, float(score), location[0], location[1], width, height))
        return sorted(matches, key=lambda match: match.confidence, reverse=True)


class StableRecognizer:
    def __init__(self, required_frames: int = 2, position_tolerance: int = 6) -> None:
        if required_frames < 2:
            raise ValueError("required_frames must be at least 2")
        self._required_frames = required_frames
        self._position_tolerance = position_tolerance
        self._previous: TemplateMatch | None = None
        self._count = 0

    def accept(self, match: TemplateMatch | None) -> TemplateMatch | None:
        if match is None:
            self._reset()
            return None
        if self._previous is not None and _matches_nearby(match, self._previous, self._position_tolerance):
            self._count += 1
        else:
            self._previous = match
            self._count = 1
        return match if self._count >= self._required_frames else None

    def _reset(self) -> None:
        self._previous = None
        self._count = 0


def _as_gray(frame: np.ndarray) -> np.ndarray:
    if frame.ndim == 2:
        return frame
    if frame.ndim == 3:
        return cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    raise ValueError("frame must be a two-dimensional or three-dimensional image")


def _matches_nearby(current: TemplateMatch, previous: TemplateMatch, tolerance: int) -> bool:
    return (
        current.label == previous.label
        and abs(current.x - previous.x) <= tolerance
        and abs(current.y - previous.y) <= tolerance
    )
