from datetime import datetime, timedelta
from enum import StrEnum

from wx_red_helper.models import Action, Observation, UiState


class FlowState(StrEnum):
    IDLE = "idle"
    AWAIT_OPEN = "await_open"
    AWAIT_RESULT = "await_result"


class RedEnvelopeStateMachine:
    def __init__(self, step_timeout: timedelta) -> None:
        self._step_timeout = step_timeout
        self._state = FlowState.IDLE
        self._deadline: datetime | None = None
        self._window_revision: int | None = None

    def advance(self, observation: Observation, now: datetime) -> Action:
        if self._state is not FlowState.IDLE and observation.window_revision != self._window_revision:
            self.reset()
            return Action.abort("window_changed")
        if self._deadline is not None and now >= self._deadline:
            self.reset()
            return Action.abort("step_timeout")
        if self._state is FlowState.IDLE:
            return self._begin_round(observation, now)
        if observation.state is UiState.UNKNOWN:
            self.reset()
            return Action.abort("unknown_page")
        if self._state is FlowState.AWAIT_OPEN and observation.state is UiState.OPEN_BUTTON and observation.match:
            self._state = FlowState.AWAIT_RESULT
            self._deadline = now + self._step_timeout
            return Action.click_open(observation.match)
        if self._state is FlowState.AWAIT_RESULT and observation.state is UiState.RESULT:
            self.reset()
        return Action.none()

    def reset(self) -> None:
        self._state = FlowState.IDLE
        self._deadline = None
        self._window_revision = None

    def _begin_round(self, observation: Observation, now: datetime) -> Action:
        if observation.state is not UiState.ENVELOPE_CARD or observation.match is None:
            return Action.none()
        self._state = FlowState.AWAIT_OPEN
        self._deadline = now + self._step_timeout
        self._window_revision = observation.window_revision
        return Action.click_envelope(observation.match)
