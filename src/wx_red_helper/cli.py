import argparse
import sys
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

from wx_red_helper.capture import ClientCapture
from wx_red_helper.config import AppConfig
from wx_red_helper.input_controller import InputController, send_windows_click
from wx_red_helper.models import RunMode
from wx_red_helper.recognizer import FrameRecognizer, StableRecognizer
from wx_red_helper.safety import SafetyGate
from wx_red_helper.service import HelperService
from wx_red_helper.state_machine import RedEnvelopeStateMachine
from wx_red_helper.templates import TEMPLATE_LABELS, TemplateCollector, TemplateRepository
from wx_red_helper.window_observer import WechatWindowObserver
from wx_red_helper.windows_api import WindowsApi


def main() -> int:
    parser = argparse.ArgumentParser(description="Windows 微信红包本地助手")
    commands = parser.add_subparsers(dest="command", required=True)
    run = commands.add_parser("run", help="运行本地助手")
    run.add_argument("--allow-title", action="append", required=True, help="允许的微信会话标题")
    run.add_argument("--mode", choices=tuple(mode.value for mode in RunMode), default=RunMode.DETECT.value)
    run.add_argument("--threshold", type=float, default=0.93)
    run.add_argument("--interval-ms", type=int, default=150)
    collect = commands.add_parser("collect-template", help="采集当前微信客户区中的模板")
    collect.add_argument("label", choices=TEMPLATE_LABELS)
    collect.add_argument("--delay-seconds", type=float, default=3, help="切回微信窗口前的等待秒数")
    commands.add_parser("show-config", help="显示当前模板目录与运行限制")
    args = parser.parse_args()
    if args.command == "show-config":
        print(f"模板目录：{_template_directory()}")
        print("微信窗口必须保持可见：是")
        print("默认运行模式：仅检测")
        return 0
    if args.command == "collect-template":
        return _collect_template(args.label, args.delay_seconds)
    return _run(args)


def _run(args: argparse.Namespace) -> int:
    if args.interval_ms < 50:
        raise SystemExit("--interval-ms must be at least 50")
    config = AppConfig(tuple(args.allow_title), args.threshold)
    observer = WechatWindowObserver(WindowsApi(), ("微信", "WeChat"))
    templates = TemplateRepository(_template_directory()).load()
    missing = set(TEMPLATE_LABELS).difference(templates)
    if missing:
        raise SystemExit(f"missing local templates: {', '.join(sorted(missing))}")

    def recheck(x: int, y: int) -> bool:
        window = observer.observe()
        return bool(window and window.client_rect.contains(x, y))

    service = HelperService(
        observer=observer,
        capture=ClientCapture(),
        recognizer=FrameRecognizer(templates, config.minimum_confidence),
        stable_recognizer=StableRecognizer(),
        safety_gate=SafetyGate(config),
        state_machine=RedEnvelopeStateMachine(timedelta(seconds=3)),
        input_controller=InputController(send_windows_click, recheck),
    )
    service.set_mode(RunMode(args.mode))
    print(f"正在运行：{localize_status(f'mode_{service.mode.value}')}；按 Ctrl+C 停止")
    try:
        while True:
            result = service.tick(datetime.now(UTC))
            print(localize_status(result.last_action))
            time.sleep(args.interval_ms / 1000)
    except KeyboardInterrupt:
        service.stop_now()
        print("已停止")
        return 0


def _collect_template(label: str, delay_seconds: float) -> int:
    if delay_seconds < 0:
        raise SystemExit("--delay-seconds must not be negative")
    if delay_seconds:
        print(f"请在 {delay_seconds:g} 秒内切换到可见的微信窗口……")
        wait_before_capture(delay_seconds, time.sleep)
    observer = WechatWindowObserver(WindowsApi(), ("微信", "WeChat"))
    window = observer.observe()
    if window is None:
        raise SystemExit("bring a visible WeChat window to the foreground before collecting a template")
    destination = TemplateCollector(_template_directory()).collect(label, ClientCapture().capture(window))
    print(destination)
    return 0


def wait_before_capture(delay_seconds: float, sleep: object) -> None:
    sleep(delay_seconds)


def localize_status(status: str) -> str:
    messages = {
        "mode_stopped": "已停止",
        "mode_detect": "仅检测模式",
        "mode_auto": "自动领取模式",
        "no_action": "未执行操作",
        "no_stable_match": "未检测到稳定目标",
        "window_unavailable": "微信窗口不可用",
        "candidate_detected": "已检测到红包候选",
        "executed": "已完成点击",
        "chat_not_allowed": "当前会话未通过页头验证",
        "low_confidence": "识别置信度不足",
        "unknown_page": "页面状态未知，已中止本轮",
        "window_changed": "微信窗口已变化，已中止本轮",
        "step_timeout": "页面响应超时，已中止本轮",
        "window_recheck_failed": "点击前窗口复核失败",
        "stopped": "已停止",
    }
    return messages.get(status, f"状态：{status}")


def _template_directory() -> Path:
    return runtime_root(
        frozen=bool(getattr(sys, "frozen", False)),
        executable=Path(sys.executable),
        module_file=Path(__file__),
    ) / "assets" / "templates"


def runtime_root(*, frozen: bool, executable: Path, module_file: Path) -> Path:
    if frozen:
        return executable.resolve().parent
    return module_file.resolve().parents[2]
