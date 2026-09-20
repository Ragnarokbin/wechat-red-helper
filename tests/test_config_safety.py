from datetime import UTC, datetime

import pytest

from wx_red_helper.config import AppConfig
from wx_red_helper.models import Observation, RunMode, TemplateMatch, UiState
from wx_red_helper.safety import SafetyGate


def make_observation(*, chat_header_visible: bool = True, confidence: float = 0.95) -> Observation:
    return Observation(
        chat_title="微信",
        state=UiState.ENVELOPE_CARD,
        match=TemplateMatch("envelope_card", confidence, 100, 120, 80, 40),
        window_revision=7,
        window_ready=True,
        chat_header_visible=chat_header_visible,
    )


def test_auto_mode_accepts_allowed_chat_above_threshold() -> None:
    config = AppConfig(allowed_chat_titles=("家人群",), minimum_confidence=0.93)

    decision = SafetyGate(config).evaluate(
        make_observation(), datetime.now(UTC), RunMode.AUTO
    )

    assert decision.allowed is True
    assert decision.reason == "allowed"


def test_detect_mode_refuses_action_even_for_valid_candidate() -> None:
    config = AppConfig(allowed_chat_titles=("家人群",), minimum_confidence=0.93)

    decision = SafetyGate(config).evaluate(
        make_observation(), datetime.now(UTC), RunMode.DETECT
    )

    assert decision.allowed is False
    assert decision.reason == "mode_detect"


def test_gate_refuses_envelope_without_matching_chat_header() -> None:
    config = AppConfig(allowed_chat_titles=("家人群",), minimum_confidence=0.93)

    decision = SafetyGate(config).evaluate(
        make_observation(chat_header_visible=False), datetime.now(UTC), RunMode.AUTO
    )

    assert decision.allowed is False
    assert decision.reason == "chat_not_allowed"


def test_gate_refuses_low_confidence() -> None:
    config = AppConfig(allowed_chat_titles=("家人群",), minimum_confidence=0.93)

    decision = SafetyGate(config).evaluate(
        make_observation(confidence=0.92), datetime.now(UTC), RunMode.AUTO
    )

    assert decision.allowed is False
    assert decision.reason == "low_confidence"


def test_config_rejects_empty_allowlist() -> None:
    with pytest.raises(ValueError, match="allowed_chat_titles"):
        AppConfig(allowed_chat_titles=(), minimum_confidence=0.93)
