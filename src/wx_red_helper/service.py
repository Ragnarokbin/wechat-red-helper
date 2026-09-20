from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from wx_red_helper.models import ActionKind, Observation, RunMode, TemplateMatch, UiState


class ServiceStatus(StrEnum):
    STOPPED = "stopped"
    WINDOW_UNAVAILABLE = "window_unavailable"
    NO_CANDIDATE = "no_candidate"
    CANDIDATE_DETECTED = "candidate_detected"
    EXECUTED = "executed"
    REFUSED = "refused"
    ABORTED = "aborted"


@dataclass(frozen=True)
class TickResult:
    status: ServiceStatus
    last_action: str


class HelperService:
    def __init__(
        self,
        *,
        observer: object,
        capture: object,
        recognizer: object,
        stable_recognizer: object,
        safety_gate: object,
        state_machine: object,
        input_controller: object,
    ) -> None:
        self._observer = observer
        self._capture = capture
        self._recognizer = recognizer
        self._stable_recognizer = stable_recognizer
        self._safety_gate = safety_gate
        self._state_machine = state_machine
        self._input_controller = input_controller
        self._mode = RunMode.STOPPED

    @property
    def mode(self) -> RunMode:
        return self._mode

    def set_mode(self, mode: RunMode) -> None:
        if mode is not RunMode.AUTO:
            self._state_machine.reset()
        self._mode = mode

    def stop_now(self) -> None:
        self._state_machine.reset()
        self._mode = RunMode.STOPPED

    def tick(self, now: datetime) -> TickResult:
        if self._mode is RunMode.STOPPED:
            return TickResult(ServiceStatus.STOPPED, "mode_stopped")
        window = self._observer.observe()
        if window is None:
            self._state_machine.reset()
            return TickResult(ServiceStatus.WINDOW_UNAVAILABLE, "window_unavailable")
        frame = self._capture.capture(window)
        matches = self._recognizer.recognize(frame)
        stable_match = self._stable_recognizer.accept(matches[0] if matches else None)
        if stable_match is None:
            return TickResult(ServiceStatus.NO_CANDIDATE, "no_stable_match")
        observation = Observation(
            chat_title=window.title,
            state=_state_for_label(stable_match.label),
            match=stable_match,
            window_revision=window.revision,
            window_ready=True,
        )
        if self._mode is RunMode.DETECT:
            return TickResult(ServiceStatus.CANDIDATE_DETECTED, "candidate_detected")
        action = self._state_machine.advance(observation, now)
        if action.kind is ActionKind.ABORT:
            return TickResult(ServiceStatus.ABORTED, action.reason or "aborted")
        if action.kind is ActionKind.NONE or action.match is None:
            return TickResult(ServiceStatus.NO_CANDIDATE, "no_action")
        decision = self._safety_gate.evaluate(observation, now, self._mode)
        if not decision.allowed:
            self._state_machine.reset()
            return TickResult(ServiceStatus.REFUSED, decision.reason)
        x, y = action.match.center
        x += window.client_rect.left
        y += window.client_rect.top
        result = self._input_controller.execute_click(x, y, self._mode)
        return TickResult(
            ServiceStatus.EXECUTED if result.executed else ServiceStatus.REFUSED,
            result.reason,
        )


def _state_for_label(label: str) -> UiState:
    return {
        "envelope_card": UiState.ENVELOPE_CARD,
        "open_button": UiState.OPEN_BUTTON,
        "result": UiState.RESULT,
    }.get(label, UiState.UNKNOWN)
