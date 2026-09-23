import numpy as np

from wx_red_helper.models import TemplateMatch
from wx_red_helper.recognizer import FrameRecognizer, StableRecognizer
from wx_red_helper.templates import selection_console_prompt, selection_window_title


def test_recognizer_locates_embedded_template() -> None:
    frame = np.zeros((120, 160), dtype=np.uint8)
    template = np.arange(240, dtype=np.uint8).reshape(12, 20)
    frame[40:52, 70:90] = template

    matches = FrameRecognizer({"envelope_card": template}, threshold=0.98).recognize(frame)

    assert len(matches) == 1
    assert matches[0].label == "envelope_card"
    assert (matches[0].x, matches[0].y) == (70, 40)


def test_stable_recognizer_requires_two_nearby_matching_frames() -> None:
    stable = StableRecognizer(required_frames=2)
    match = TemplateMatch("open_button", 0.99, 20, 30, 40, 40)

    assert stable.accept(match) is None
    assert stable.accept(match) == match


def test_stable_recognizer_can_accept_the_first_matching_frame() -> None:
    stable = StableRecognizer(required_frames=1)
    match = TemplateMatch("open_button", 0.99, 20, 30, 40, 40)

    assert stable.accept(match) == match


def test_stable_recognizer_resets_for_changed_location() -> None:
    stable = StableRecognizer(required_frames=2)

    assert stable.accept(TemplateMatch("open_button", 0.99, 20, 30, 40, 40)) is None
    assert stable.accept(TemplateMatch("open_button", 0.99, 40, 30, 40, 40)) is None


def test_template_selection_window_uses_chinese_instruction() -> None:
    assert selection_window_title() == "请选择模板区域，按 Enter 确认，按 Esc 取消"


def test_template_selection_console_prompt_uses_chinese_instruction() -> None:
    assert selection_console_prompt() == "请拖动鼠标框选区域；按空格或 Enter 确认，按 Esc 或 C 取消。"
