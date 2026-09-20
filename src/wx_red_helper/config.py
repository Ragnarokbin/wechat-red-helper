from dataclasses import dataclass


@dataclass(frozen=True)
class AppConfig:
    allowed_chat_titles: tuple[str, ...]
    minimum_confidence: float
    cooldown_seconds: int = 5
    daily_limit: int = 100

    def __post_init__(self) -> None:
        if not self.allowed_chat_titles or any(not title.strip() for title in self.allowed_chat_titles):
            raise ValueError("allowed_chat_titles must contain at least one non-empty title")
        if not 0 < self.minimum_confidence <= 1:
            raise ValueError("minimum_confidence must be between 0 and 1")
        if self.cooldown_seconds < 0:
            raise ValueError("cooldown_seconds must not be negative")
        if self.daily_limit <= 0:
            raise ValueError("daily_limit must be positive")
