import subprocess
import sys
from pathlib import Path

import pytest

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


def test_launch_without_command_shows_chinese_menu(capsys) -> None:
    answers = iter(["0"])

    result = main([], lambda prompt: next(answers))

    assert result == 0
    assert "启动自动领取模式" in capsys.readouterr().out


def test_menu_returns_after_template_collection(monkeypatch, capsys) -> None:
    answers = iter(["1", "0"])
    collected: list[tuple[str, float]] = []
    monkeypatch.setattr("wx_red_helper.cli._collect_template", lambda label, delay: collected.append((label, delay)) or 0)

    result = main([], lambda prompt: next(answers))

    assert result == 0
    assert collected == [("chat_header", 5)]
    assert capsys.readouterr().out.count("采集群聊页头模板") == 2


def test_menu_starts_auto_mode_with_requested_minimum_interval(monkeypatch, capsys) -> None:
    answers = iter(["6", "30", "测试群", "0"])
    runs = []
    prompts: list[str] = []
    monkeypatch.setattr("wx_red_helper.cli._run", lambda args: runs.append(args) or 0)

    result = main([], lambda prompt: prompts.append(prompt) or next(answers))

    assert result == 0
    assert len(runs) == 1
    assert runs[0].allow_title == ["测试群"]
    assert runs[0].mode == "auto"
    assert runs[0].interval_ms == 30
    assert "请输入扫描间隔（30-80ms）：" in prompts


def test_menu_reprompts_until_scan_interval_is_in_range(monkeypatch, capsys) -> None:
    answers = iter(["6", "29", "不是数字", "81", "80", "测试群", "0"])
    runs = []
    monkeypatch.setattr("wx_red_helper.cli._run", lambda args: runs.append(args) or 0)

    result = main([], lambda prompt: next(answers))

    assert result == 0
    assert len(runs) == 1
    assert runs[0].allow_title == ["测试群"]
    assert runs[0].interval_ms == 80
    assert capsys.readouterr().out.count("扫描间隔必须是 30 到 80 之间的整数毫秒。") == 3


@pytest.mark.parametrize("interval_ms", [29, 81])
def test_command_rejects_scan_interval_outside_selectable_range(interval_ms: int) -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "wx_red_helper",
            "run",
            "--allow-title",
            "测试群",
            "--mode",
            "auto",
            "--interval-ms",
            str(interval_ms),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 1
    assert "--interval-ms must be between 30 and 80" in completed.stderr


def test_launch_without_command_exits_cleanly_when_stdin_is_unavailable() -> None:
    def no_stdin(prompt: str) -> str:
        raise EOFError

    assert main([], no_stdin) == 0
