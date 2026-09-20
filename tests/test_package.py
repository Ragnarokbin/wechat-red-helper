import subprocess
import sys
from pathlib import Path

from wx_red_helper.cli import localize_status, main, runtime_root, wait_before_capture

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


def test_localize_status_translates_runtime_codes_for_terminal_output() -> None:
    assert localize_status("no_action") == "未执行操作"
    assert localize_status("no_stable_match") == "未检测到稳定目标"
    assert localize_status("window_unavailable") == "微信窗口不可用"
    assert localize_status("stopped") == "已停止"


def test_frozen_app_stores_templates_beside_the_executable() -> None:
    root = runtime_root(
        frozen=True,
        executable=Path("C:/Portable/WxRedHelper/WxRedHelper.exe"),
        module_file=Path("C:/source/src/wx_red_helper/cli.py"),
    )

    assert root == Path("C:/Portable/WxRedHelper")


def test_launch_without_command_shows_chinese_guide_and_waits(capsys) -> None:
    prompts: list[str] = []

    result = main([], prompts.append)

    assert result == 0
    assert "使用说明" in capsys.readouterr().out
    assert prompts == ["按 Enter 键关闭窗口……"]
