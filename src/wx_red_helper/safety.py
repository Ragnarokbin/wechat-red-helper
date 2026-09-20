from dataclasses import dataclass
from datetime import datetime

from wx_red_helper.config import AppConfig
from wx_red_helper.models import Observation, RunMode


@dataclass(frozen=True)
class GateDecision:
    allowed: bool
    reason: str


class SafetyGate:
    def __init__(self, config: AppConfig) -> None:
        self._config = config

    def evaluate(
        self,
        observation: Observation,
        now: datetime,
        mode: RunMode,
    ) -> GateDecision:
        del now

        if mode is RunMode.STOPPED:
            return GateDecision(False, "mode_stopped")
        if mode is RunMode.DETECT:
            return GateDecision(False, "mode_detect")
        if not observation.window_ready:
            return GateDecision(False, "window_not_ready")
        if observation.match is None:
            return GateDecision(False, "no_match")
        if observation.state.value == "envelope_card" and not observation.chat_header_visible:
            return GateDecision(False, "chat_not_allowed")
        if observation.match.confidence < self._config.minimum_confidence:
            return GateDecision(False, "low_confidence")
        return GateDecision(True, "allowed")
