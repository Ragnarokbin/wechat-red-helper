import argparse
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
        print(f"template_directory={_template_directory()}")
        print("window_must_be_visible=true")
        print("default_mode=detect")
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
    print(f"running mode={service.mode}; press Ctrl+C to stop")
    try:
        while True:
            result = service.tick(datetime.now(UTC))
            print(result.last_action)
            time.sleep(args.interval_ms / 1000)
    except KeyboardInterrupt:
        service.stop_now()
        print("stopped")
        return 0


def _collect_template(label: str, delay_seconds: float) -> int:
    if delay_seconds < 0:
        raise SystemExit("--delay-seconds must not be negative")
    if delay_seconds:
        print(f"Switch to the visible WeChat window within {delay_seconds:g} seconds...")
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


def _template_directory() -> Path:
    return Path(__file__).resolve().parents[2] / "assets" / "templates"
