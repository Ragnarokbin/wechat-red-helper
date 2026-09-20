import numpy as np

from wx_red_helper.models import TemplateMatch
from wx_red_helper.recognizer import FrameRecognizer, StableRecognizer


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


def test_stable_recognizer_resets_for_changed_location() -> None:
    stable = StableRecognizer(required_frames=2)

    assert stable.accept(TemplateMatch("open_button", 0.99, 20, 30, 40, 40)) is None
    assert stable.accept(TemplateMatch("open_button", 0.99, 40, 30, 40, 40)) is None
