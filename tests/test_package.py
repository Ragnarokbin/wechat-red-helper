import subprocess
import sys

from wx_red_helper.cli import wait_before_capture

def test_module_exposes_help() -> None:
    completed = subprocess.run(
        [sys.executable, "-m", "wx_red_helper", "--help"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0
    assert "Windows 微信红包本地助手" in completed.stdout


def test_run_requires_an_explicit_allowed_chat_title() -> None:
    completed = subprocess.run(
        [sys.executable, "-m", "wx_red_helper", "run"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 2
    assert "--allow-title" in completed.stderr


def test_template_collection_waits_before_observing_foreground_window() -> None:
    waits: list[float] = []

    wait_before_capture(3, waits.append)

    assert waits == [3]
