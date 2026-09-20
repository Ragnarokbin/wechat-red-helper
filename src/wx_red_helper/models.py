from dataclasses import dataclass
from enum import StrEnum


class RunMode(StrEnum):
    STOPPED = "stopped"
    DETECT = "detect"
    AUTO = "auto"


class UiState(StrEnum):
    NONE = "none"
    ENVELOPE_CARD = "envelope_card"
    OPEN_BUTTON = "open_button"
    RESULT = "result"
    UNKNOWN = "unknown"


class ActionKind(StrEnum):
    NONE = "none"
    CLICK_ENVELOPE = "click_envelope"
    CLICK_OPEN = "click_open"
    ABORT = "abort"


@dataclass(frozen=True)
class ClientRect:
    left: int
    top: int
    width: int
    height: int

    def __post_init__(self) -> None:
        if self.width <= 0 or self.height <= 0:
            raise ValueError("client rectangle dimensions must be positive")

    def point_at(self, x_ratio: float, y_ratio: float) -> tuple[int, int]:
        if not 0 <= x_ratio <= 1 or not 0 <= y_ratio <= 1:
            raise ValueError("relative coordinate must be between 0 and 1")
        return (
            round(self.left + self.width * x_ratio),
            round(self.top + self.height * y_ratio),
        )

    def contains(self, x: int, y: int) -> bool:
        return self.left <= x < self.left + self.width and self.top <= y < self.top + self.height


@dataclass(frozen=True)
class TemplateMatch:
    label: str
    confidence: float
    x: int
    y: int
    width: int
    height: int

    def __post_init__(self) -> None:
        if not self.label:
            raise ValueError("template label must not be empty")
        if not 0 <= self.confidence <= 1:
            raise ValueError("template confidence must be between 0 and 1")
        if self.width <= 0 or self.height <= 0:
            raise ValueError("template dimensions must be positive")

    @property
    def center(self) -> tuple[int, int]:
        return (self.x + self.width // 2, self.y + self.height // 2)


@dataclass(frozen=True)
class WindowSnapshot:
    handle: int
    title: str
    client_rect: ClientRect
    revision: int


@dataclass(frozen=True)
class Observation:
    chat_title: str
    state: UiState
    match: TemplateMatch | None
    window_revision: int
    window_ready: bool
    chat_header_visible: bool = False


@dataclass(frozen=True)
class Action:
    kind: ActionKind
    match: TemplateMatch | None = None
    reason: str | None = None

    @classmethod
    def none(cls) -> "Action":
        return cls(ActionKind.NONE)

    @classmethod
    def click_envelope(cls, match: TemplateMatch) -> "Action":
        return cls(ActionKind.CLICK_ENVELOPE, match=match)

    @classmethod
    def click_open(cls, match: TemplateMatch) -> "Action":
        return cls(ActionKind.CLICK_OPEN, match=match)

    @classmethod
    def abort(cls, reason: str) -> "Action":
        return cls(ActionKind.ABORT, reason=reason)
