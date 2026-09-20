from datetime import UTC, datetime, timedelta

from wx_red_helper.models import ActionKind, Observation, TemplateMatch, UiState
from wx_red_helper.state_machine import RedEnvelopeStateMachine


def observation(state: UiState, *, revision: int = 7) -> Observation:
    label = {
        UiState.ENVELOPE_CARD: "envelope_card",
        UiState.OPEN_BUTTON: "open_button",
        UiState.RESULT: "result",
    }.get(state)
    match = TemplateMatch(label, 0.99, 100, 120, 80, 40) if label else None
    return Observation("家人群", state, match, revision, True)


def test_open_button_is_clicked_only_after_envelope_card_was_seen() -> None:
    machine = RedEnvelopeStateMachine(step_timeout=timedelta(seconds=3))
    now = datetime.now(UTC)

    assert machine.advance(observation(UiState.OPEN_BUTTON), now).kind is ActionKind.NONE
    assert machine.advance(observation(UiState.ENVELOPE_CARD), now).kind is ActionKind.CLICK_ENVELOPE
    assert machine.advance(observation(UiState.OPEN_BUTTON), now).kind is ActionKind.CLICK_OPEN


def test_unknown_page_after_click_aborts_round() -> None:
    machine = RedEnvelopeStateMachine(step_timeout=timedelta(seconds=3))
    now = datetime.now(UTC)
    machine.advance(observation(UiState.ENVELOPE_CARD), now)

    action = machine.advance(observation(UiState.UNKNOWN), now + timedelta(milliseconds=1))

    assert action.kind is ActionKind.ABORT
    assert action.reason == "unknown_page"


def test_step_timeout_aborts_round() -> None:
    machine = RedEnvelopeStateMachine(step_timeout=timedelta(seconds=1))
    now = datetime.now(UTC)
    machine.advance(observation(UiState.ENVELOPE_CARD), now)

    action = machine.advance(observation(UiState.OPEN_BUTTON), now + timedelta(seconds=2))

    assert action.kind is ActionKind.ABORT
    assert action.reason == "step_timeout"


def test_window_revision_change_aborts_round() -> None:
    machine = RedEnvelopeStateMachine(step_timeout=timedelta(seconds=3))
    now = datetime.now(UTC)
    machine.advance(observation(UiState.ENVELOPE_CARD, revision=7), now)

    action = machine.advance(observation(UiState.OPEN_BUTTON, revision=8), now + timedelta(milliseconds=1))

    assert action.kind is ActionKind.ABORT
    assert action.reason == "window_changed"
