from datetime import UTC, datetime, timedelta

import numpy as np

from wx_red_helper.config import AppConfig
from wx_red_helper.models import ClientRect, RunMode, TemplateMatch, WindowSnapshot
from wx_red_helper.safety import SafetyGate
from wx_red_helper.service import HelperService
from wx_red_helper.state_machine import RedEnvelopeStateMachine


class FakeObserver:
    def observe(self) -> WindowSnapshot:
        return WindowSnapshot(12, "家人群", ClientRect(20, 30, 900, 700), 7)


class FakeCapture:
    def capture(self, window: WindowSnapshot) -> np.ndarray:
        return np.zeros((20, 20, 3), dtype=np.uint8)


class FakeRecognizer:
    def recognize(self, frame: np.ndarray) -> list[TemplateMatch]:
        return [TemplateMatch("envelope_card", 0.99, 100, 120, 80, 40)]


class FakeStable:
    def accept(self, match: TemplateMatch) -> TemplateMatch:
        return match


class FakeInput:
    def __init__(self) -> None:
        self.calls: list[tuple[int, int, RunMode]] = []

    def execute_click(self, x: int, y: int, mode: RunMode):
        self.calls.append((x, y, mode))
        return type("Result", (), {"executed": True, "reason": "executed"})()


def build_service(input_controller: FakeInput) -> HelperService:
    return HelperService(
        observer=FakeObserver(),
        capture=FakeCapture(),
        recognizer=FakeRecognizer(),
        stable_recognizer=FakeStable(),
        safety_gate=SafetyGate(AppConfig(("家人群",), 0.93)),
        state_machine=RedEnvelopeStateMachine(timedelta(seconds=3)),
        input_controller=input_controller,
    )


def test_detect_mode_reports_candidate_without_input() -> None:
    fake_input = FakeInput()
    service = build_service(fake_input)
    service.set_mode(RunMode.DETECT)

    status = service.tick(datetime.now(UTC))

    assert status.last_action == "candidate_detected"
    assert fake_input.calls == []


def test_auto_mode_clicks_verified_envelope_center() -> None:
    fake_input = FakeInput()
    service = build_service(fake_input)
    service.set_mode(RunMode.AUTO)

    status = service.tick(datetime.now(UTC))

    assert status.last_action == "executed"
    assert fake_input.calls == [(160, 170, RunMode.AUTO)]
