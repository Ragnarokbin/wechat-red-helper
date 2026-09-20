# Windows 微信红包本地助手 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建一个仅在 Windows 微信窗口可见时运行的本地系统托盘工具，以经画面验证的鼠标点击完成红包领取流程。

**Architecture:** 应用是 Python 3.13 的本机进程。Windows 适配层只负责观察前台微信窗口、截取其客户区和通过 `SendInput` 发送普通鼠标点击；视觉识别器和状态机保持为可替换、可离线单测的纯 Python 组件。后台服务将最新观察结果交给状态机，状态机只在配置与连续帧校验均通过时交给输入执行器。

**Tech Stack:** Python 3.13、`mss`、OpenCV、NumPy、Pillow、`pystray`、标准库 `ctypes`、pytest、PyInstaller。

**Spec:** `docs/superpowers/specs/2026-09-18-windows-wechat-red-envelope-helper-design.md`

## Global Constraints

- 仅支持 Windows；微信必须已登录、可见且不能最小化。
- 不读取微信数据库、进程内存或网络通信，不注入微信进程。
- 只截取微信客户区；默认不保存截图、不上传图像或日志。
- 只使用普通鼠标输入；不尝试处理验证码、风控、未知弹窗或后台窗口。
- 每个鼠标动作前重新验证窗口和目标；每个鼠标动作后验证下一画面状态。
- 模式必须为 `AUTO` 且安全门全部放行时才可发出输入；`STOPPED` 与 `DETECT` 永不发出输入。
- 任何低置信度、超时、窗口变化、异常页面或连续失败都必须结束本轮并进入冷却或仅检测模式。
- 初版以用户通过本地模板采集器建立的浅色主题、单一 DPI 缩放样本为识别基准。

---

## File Structure

```text
pyproject.toml                                  # 项目元数据、运行与测试依赖
src/wx_red_helper/__init__.py                   # 包版本
src/wx_red_helper/models.py                     # 不依赖 Windows 的不可变领域类型
src/wx_red_helper/config.py                     # JSON 配置读写与严格校验
src/wx_red_helper/safety.py                     # 白名单、时段、额度、冷却与失败降级
src/wx_red_helper/windows_api.py                # User32/GDI Win32 调用的窄封装
src/wx_red_helper/window_observer.py            # 前台微信客户区有效性判断
src/wx_red_helper/capture.py                    # 指定客户区的 mss 截屏
src/wx_red_helper/templates.py                  # 本地模板读取、采集和原子写入
src/wx_red_helper/recognizer.py                 # OpenCV 模板匹配与连续帧稳定性
src/wx_red_helper/state_machine.py              # 领取流程状态机和超时控制
src/wx_red_helper/input_controller.py           # SendInput 坐标换算及点击前复核
src/wx_red_helper/event_log.py                  # 不含聊天正文的 JSONL 本地日志
src/wx_red_helper/service.py                    # 轮询编排、取消、降级与依赖注入
src/wx_red_helper/tray.py                       # 托盘菜单、状态显示及紧急停止
src/wx_red_helper/cli.py                        # run、collect-template、show-config 命令
src/wx_red_helper/__main__.py                   # python -m wx_red_helper 入口
assets/templates/.gitkeep                       # 用户本地建立的视觉模板目录
tests/conftest.py                               # 可控时钟、假观察器、假输入器
tests/test_models.py                            # 领域类型与坐标边界测试
tests/test_config_safety.py                     # 配置校验及规则门测试
tests/test_window_observer.py                   # 窗口有效性和客户区转换测试
tests/test_recognizer.py                        # 合成图像上的模板匹配与稳定帧测试
tests/test_state_machine.py                     # 状态迁移、超时和中止路径测试
tests/test_input_controller.py                  # 模式门和 SendInput 坐标转换测试
tests/test_service.py                           # 端到端编排与失败降级测试
README.md                                       # 安装、模板采集、测试模式和安全使用说明
build.ps1                                       # 可复现的 Windows 单文件构建命令
```

## Task 1: 建立可测试的 Python 项目骨架

**Files:**
- Create: `pyproject.toml`
- Create: `src/wx_red_helper/__init__.py`
- Create: `src/wx_red_helper/__main__.py`
- Create: `src/wx_red_helper/cli.py`
- Create: `tests/test_package.py`
- Create: `assets/templates/.gitkeep`

**Interfaces:**
- Produces: 可通过 `python -m wx_red_helper --help` 调用的命令行入口，以及 `pytest` 可发现的 `src` 布局。

- [ ] **Step 1: 写出失败的包入口测试。**

```python
# tests/test_package.py
import subprocess
import sys


def test_module_exposes_help() -> None:
    completed = subprocess.run(
        [sys.executable, "-m", "wx_red_helper", "--help"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0
    assert "Windows 微信红包本地助手" in completed.stdout
```

- [ ] **Step 2: 安装开发依赖并运行测试，确认测试因模块缺失而失败。**

Run:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python -m pip install --upgrade pip
.\.venv\Scripts\python -m pip install pytest
.\.venv\Scripts\python -m pytest tests/test_package.py -q
```

Expected: FAIL，错误包含 `No module named 'wx_red_helper'`。

- [ ] **Step 3: 添加最小项目定义和入口。**

```toml
# pyproject.toml
[build-system]
requires = ["setuptools>=75"]
build-backend = "setuptools.build_meta"

[project]
name = "wx-red-helper"
version = "0.1.0"
description = "A local, visible-window-only Windows helper"
requires-python = ">=3.13"
dependencies = [
  "mss>=10.0,<11",
  "numpy>=2.2,<3",
  "opencv-python>=4.11,<5",
  "Pillow>=11,<12",
  "pystray>=0.19,<1",
]

[project.optional-dependencies]
dev = ["pytest>=8.3,<9", "pyinstaller>=6.12,<7"]

[project.scripts]
wx-red-helper = "wx_red_helper.cli:main"

[tool.setuptools.packages.find]
where = ["src"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]
```

```python
# src/wx_red_helper/__main__.py
from wx_red_helper.cli import main

raise SystemExit(main())
```

```python
# src/wx_red_helper/cli.py
import argparse


def main() -> int:
    parser = argparse.ArgumentParser(description="Windows 微信红包本地助手")
    parser.add_argument("command", nargs="?", choices=("run", "collect-template", "show-config"))
    parser.parse_args()
    return 0
```

- [ ] **Step 4: 安装项目并确认入口测试通过。**

Run:

```powershell
.\.venv\Scripts\python -m pip install -e ".[dev]"
.\.venv\Scripts\python -m pytest tests/test_package.py -q
.\.venv\Scripts\python -m wx_red_helper --help
```

Expected: pytest PASS；帮助文本包含项目名称。

- [ ] **Step 5: 提交可运行骨架。**

```powershell
git add pyproject.toml src/wx_red_helper tests/test_package.py assets/templates/.gitkeep
git commit -m "feat: bootstrap Windows helper package"
```

## Task 2: 定义领域模型、配置与安全规则

**Files:**
- Create: `src/wx_red_helper/models.py`
- Create: `src/wx_red_helper/config.py`
- Create: `src/wx_red_helper/safety.py`
- Create: `tests/test_models.py`
- Create: `tests/test_config_safety.py`

**Interfaces:**
- Produces: `RunMode`, `UiState`, `ClientRect`, `WindowSnapshot`, `TemplateMatch`, `Observation`, `Action`, `AppConfig` 和 `SafetyGate.evaluate(observation, now)`。
- Consumes: Task 1 的 Python 包与 pytest 配置。

- [ ] **Step 1: 写出规则门和坐标的失败测试。**

```python
# tests/test_config_safety.py
from datetime import UTC, datetime

from wx_red_helper.config import AppConfig
from wx_red_helper.models import Observation, RunMode, TemplateMatch, UiState
from wx_red_helper.safety import SafetyGate


def test_auto_mode_requires_allowed_chat_and_threshold() -> None:
    config = AppConfig(allowed_chat_titles=("家人群",), minimum_confidence=0.93)
    observation = Observation(
        chat_title="家人群",
        state=UiState.ENVELOPE_CARD,
        match=TemplateMatch("envelope_card", 0.95, 100, 120, 80, 40),
        window_revision=7,
    )
    decision = SafetyGate(config).evaluate(observation, datetime.now(UTC), RunMode.AUTO)
    assert decision.allowed is True
```

```python
# tests/test_models.py
from wx_red_helper.models import ClientRect


def test_relative_center_uses_current_client_rect() -> None:
    rect = ClientRect(left=200, top=100, width=1000, height=800)
    assert rect.point_at(0.5, 0.25) == (700, 300)
```

- [ ] **Step 2: 运行测试，确认类型尚不存在。**

Run: `.\.venv\Scripts\python -m pytest tests/test_models.py tests/test_config_safety.py -q`

Expected: FAIL，导入错误指出 `models`、`config` 和 `safety` 尚未创建。

- [ ] **Step 3: 实现不可变模型、配置的严格验证与安全门。**

```python
# src/wx_red_helper/models.py
from dataclasses import dataclass
from enum import StrEnum


class RunMode(StrEnum):
    STOPPED = "stopped"
    DETECT = "detect"
    AUTO = "auto"


class UiState(StrEnum):
    NONE = "none"
    ENVELOPE_CARD = "envelope_card"
    OPEN_BUTTON = "open_button"
    RESULT = "result"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class ClientRect:
    left: int
    top: int
    width: int
    height: int

    def point_at(self, x_ratio: float, y_ratio: float) -> tuple[int, int]:
        return (round(self.left + self.width * x_ratio), round(self.top + self.height * y_ratio))
```

`AppConfig` 必须拒绝空白名单、阈值不在 `(0, 1]`、负冷却时间和非正每日上限。`SafetyGate` 必须在非 `AUTO` 模式、窗口不可用、会话不在白名单、置信度不足、处于冷却期或已经达到每日上限时返回 `allowed=False` 和精确原因码。

- [ ] **Step 4: 运行规则与模型测试。**

Run: `.\.venv\Scripts\python -m pytest tests/test_models.py tests/test_config_safety.py -q`

Expected: PASS；补充覆盖 `DETECT`、白名单不匹配、低置信度、冷却与日限额五条拒绝路径。

- [ ] **Step 5: 提交安全领域层。**

```powershell
git add src/wx_red_helper/models.py src/wx_red_helper/config.py src/wx_red_helper/safety.py tests/test_models.py tests/test_config_safety.py
git commit -m "feat: add safety-gated domain model"
```

## Task 3: 实现可替换的微信窗口观察器和客户区截屏

**Files:**
- Create: `src/wx_red_helper/windows_api.py`
- Create: `src/wx_red_helper/window_observer.py`
- Create: `src/wx_red_helper/capture.py`
- Create: `tests/test_window_observer.py`

**Interfaces:**
- Consumes: Task 2 的 `ClientRect` 和 `WindowSnapshot`。
- Produces: `WechatWindowObserver.observe() -> WindowSnapshot | None` 与 `ClientCapture.capture(window) -> numpy.ndarray`。

- [ ] **Step 1: 编写前台、可见、未最小化和客户区坐标转换的失败测试。**

```python
# tests/test_window_observer.py
from wx_red_helper.models import ClientRect
from wx_red_helper.window_observer import WechatWindowObserver


class FakeWinApi:
    def foreground_handle(self) -> int: return 12
    def is_visible(self, handle: int) -> bool: return True
    def is_minimized(self, handle: int) -> bool: return False
    def title(self, handle: int) -> str: return "家人群 - 微信"
    def client_rect_on_screen(self, handle: int) -> ClientRect: return ClientRect(20, 30, 900, 700)


def test_observer_accepts_visible_foreground_wechat_window() -> None:
    observed = WechatWindowObserver(FakeWinApi(), ("微信", "WeChat")).observe()
    assert observed is not None
    assert observed.client_rect == ClientRect(20, 30, 900, 700)
```

- [ ] **Step 2: 运行测试，确认观察器尚不存在。**

Run: `.\.venv\Scripts\python -m pytest tests/test_window_observer.py -q`

Expected: FAIL，导入错误指出 `WechatWindowObserver` 尚不存在。

- [ ] **Step 3: 用小型 ctypes 封装实现观察和截屏。**

`windows_api.py` 只能封装 `GetForegroundWindow`、`IsWindowVisible`、`IsIconic`、`GetWindowTextW`、`GetClientRect`、`ClientToScreen`，并将原生失败转换为 `None` 或明确异常。观察器必须只接受标题中包含配置的 `("微信", "WeChat")` 之一且有正客户区尺寸的前台窗口。

```python
# src/wx_red_helper/window_observer.py
class WechatWindowObserver:
    def __init__(self, api: WinApi, title_tokens: tuple[str, ...]) -> None:
        self._api = api
        self._title_tokens = title_tokens

    def observe(self) -> WindowSnapshot | None:
        handle = self._api.foreground_handle()
        if not handle or not self._api.is_visible(handle) or self._api.is_minimized(handle):
            return None
        title = self._api.title(handle)
        if not any(token.casefold() in title.casefold() for token in self._title_tokens):
            return None
        rect = self._api.client_rect_on_screen(handle)
        if rect.width <= 0 or rect.height <= 0:
            return None
        return WindowSnapshot(handle=handle, title=title, client_rect=rect)
```

`capture.py` 使用 `mss.mss().grab()`，且 bbox 必须恰好等于 `WindowSnapshot.client_rect`，不得捕获整个桌面。

- [ ] **Step 4: 运行观察器测试与人工只读截屏检查。**

Run:

```powershell
.\.venv\Scripts\python -m pytest tests/test_window_observer.py -q
.\.venv\Scripts\python -m wx_red_helper show-config
```

Expected: 单元测试 PASS；命令不得产生鼠标或键盘输入。

- [ ] **Step 5: 提交 Windows 只读适配层。**

```powershell
git add src/wx_red_helper/windows_api.py src/wx_red_helper/window_observer.py src/wx_red_helper/capture.py tests/test_window_observer.py
git commit -m "feat: observe visible WeChat client area"
```

## Task 4: 建立本地模板采集与离线视觉识别

**Files:**
- Create: `src/wx_red_helper/templates.py`
- Create: `src/wx_red_helper/recognizer.py`
- Create: `tests/test_recognizer.py`
- Create: `tests/fixtures/.gitkeep`

**Interfaces:**
- Consumes: Task 2 的 `TemplateMatch`、`UiState`，Task 3 的客户区截图。
- Produces: `TemplateRepository.load() -> dict[str, numpy.ndarray]`、`TemplateCollector.collect(label, frame) -> Path`、`FrameRecognizer.recognize(frame) -> list[TemplateMatch]` 和 `StableRecognizer.accept(match) -> TemplateMatch | None`。

- [ ] **Step 1: 用合成图像写出模板匹配和连续帧稳定性的失败测试。**

```python
# tests/test_recognizer.py
import numpy as np

from wx_red_helper.recognizer import FrameRecognizer, StableRecognizer


def test_recognizer_locates_embedded_template() -> None:
    frame = np.zeros((120, 160), dtype=np.uint8)
    template = np.arange(240, dtype=np.uint8).reshape(12, 20)
    frame[40:52, 70:90] = template
    result = FrameRecognizer({"envelope_card": template}, threshold=0.98).recognize(frame)
    assert result[0].label == "envelope_card"
    assert (result[0].x, result[0].y) == (70, 40)


def test_stable_recognizer_requires_two_matching_frames() -> None:
    recognizer = StableRecognizer(required_frames=2)
    assert recognizer.accept("open_button", 0.99, 20, 30) is False
    assert recognizer.accept("open_button", 0.99, 20, 30) is True
```

- [ ] **Step 2: 运行测试，确认识别器尚不存在。**

Run: `.\.venv\Scripts\python -m pytest tests/test_recognizer.py -q`

Expected: FAIL，导入错误指出 `recognizer` 尚不存在。

- [ ] **Step 3: 实现模板仓库、手工采集器与识别器。**

`TemplateCollector` 从客户区帧创建预览，使用 `cv2.selectROI` 让用户明确框选模板，仅将选中区域写到 `assets/templates/<label>.png`；写入时先落到同目录临时文件，再使用 `Path.replace()` 原子替换。标签严格限定为 `envelope_card`、`open_button`、`result`。

```python
# src/wx_red_helper/recognizer.py
class FrameRecognizer:
    def __init__(self, templates: dict[str, np.ndarray], threshold: float) -> None:
        self._templates = templates
        self._threshold = threshold

    def recognize(self, gray_frame: np.ndarray) -> list[TemplateMatch]:
        matches: list[TemplateMatch] = []
        for label, template in self._templates.items():
            score_map = cv2.matchTemplate(gray_frame, template, cv2.TM_CCOEFF_NORMED)
            _, score, _, location = cv2.minMaxLoc(score_map)
            if score >= self._threshold:
                height, width = template.shape[:2]
                matches.append(TemplateMatch(label, float(score), location[0], location[1], width, height))
        return matches
```

`StableRecognizer` 必须在标签、位置（±6 px）和分数均达标的连续两帧后才返回可操作的 `TemplateMatch`；不同标签、位置跳变或低分必须重置计数。服务层负责将该结果与当前窗口标题和窗口版本组成 `Observation`。

- [ ] **Step 4: 运行离线识别测试，并人工采集三个本地模板。**

Run:

```powershell
.\.venv\Scripts\python -m pytest tests/test_recognizer.py -q
.\.venv\Scripts\python -m wx_red_helper collect-template envelope_card
.\.venv\Scripts\python -m wx_red_helper collect-template open_button
.\.venv\Scripts\python -m wx_red_helper collect-template result
```

Expected: 单元测试 PASS；每次采集均由用户手动框选，且只在 `assets/templates` 写入对应 PNG。

- [ ] **Step 5: 提交模板与识别逻辑，但不提交用户采集的聊天画面模板。**

```powershell
git add src/wx_red_helper/templates.py src/wx_red_helper/recognizer.py tests/test_recognizer.py tests/fixtures/.gitkeep
git commit -m "feat: add local template recognition"
```

## Task 5: 实现经过验证的红包状态机

**Files:**
- Create: `src/wx_red_helper/state_machine.py`
- Create: `tests/test_state_machine.py`

**Interfaces:**
- Consumes: Task 2 的 `Observation`、`UiState`、`Action` 和 `RunMode`；Task 4 的稳定识别结果。
- Produces: `RedEnvelopeStateMachine.advance(observation, now) -> Action`，其中 `Action.kind` 只能是 `NONE`、`CLICK_ENVELOPE`、`CLICK_OPEN`、`ABORT`。

- [ ] **Step 1: 写出状态推进、点击后验证和超时中止的失败测试。**

```python
# tests/test_state_machine.py
from datetime import UTC, datetime, timedelta

from wx_red_helper.models import ActionKind, Observation, UiState
from wx_red_helper.state_machine import RedEnvelopeStateMachine


def test_open_button_is_clicked_only_after_envelope_click_was_confirmed() -> None:
    machine = RedEnvelopeStateMachine(step_timeout=timedelta(seconds=3))
    now = datetime.now(UTC)
    assert machine.advance(Observation.for_state(UiState.ENVELOPE_CARD), now).kind is ActionKind.CLICK_ENVELOPE
    assert machine.advance(Observation.for_state(UiState.OPEN_BUTTON), now).kind is ActionKind.CLICK_OPEN


def test_unknown_page_after_step_timeout_aborts_round() -> None:
    machine = RedEnvelopeStateMachine(step_timeout=timedelta(seconds=1))
    now = datetime.now(UTC)
    machine.advance(Observation.for_state(UiState.ENVELOPE_CARD), now)
    action = machine.advance(Observation.for_state(UiState.UNKNOWN), now + timedelta(seconds=2))
    assert action.kind is ActionKind.ABORT
```

- [ ] **Step 2: 运行测试，确认状态机尚不存在。**

Run: `.\.venv\Scripts\python -m pytest tests/test_state_machine.py -q`

Expected: FAIL，导入错误指出 `RedEnvelopeStateMachine` 尚不存在。

- [ ] **Step 3: 以显式状态和单调时钟实现状态机。**

```python
# src/wx_red_helper/state_machine.py
class RedEnvelopeStateMachine:
    def advance(self, observation: Observation, now: datetime) -> Action:
        if self._state is FlowState.IDLE and observation.state is UiState.ENVELOPE_CARD:
            self._state = FlowState.AWAIT_OPEN
            self._deadline = now + self._step_timeout
            return Action.click_envelope(observation.match)
        if self._state is FlowState.AWAIT_OPEN and observation.state is UiState.OPEN_BUTTON:
            self._state = FlowState.AWAIT_RESULT
            self._deadline = now + self._step_timeout
            return Action.click_open(observation.match)
        if self._deadline is not None and now >= self._deadline:
            self.reset()
            return Action.abort("step_timeout")
        return Action.none()
```

实现必须要求 `RESULT` 状态才把当前轮标记完成；`UNKNOWN`、窗口版本变化、模板缺失和所有超时均调用 `reset()` 并返回安全中止。状态机不能直接调用 Windows 或鼠标 API。

- [ ] **Step 4: 运行覆盖所有状态边的单元测试。**

Run: `.\.venv\Scripts\python -m pytest tests/test_state_machine.py -q`

Expected: PASS；覆盖 `IDLE → AWAIT_OPEN → AWAIT_RESULT → IDLE`、未知页面、窗口变化、重复卡片和三个超时分支。

- [ ] **Step 5: 提交状态机。**

```powershell
git add src/wx_red_helper/state_machine.py tests/test_state_machine.py
git commit -m "feat: add verified red envelope state machine"
```

## Task 6: 实现输入模式门、点击前复核和本地事件日志

**Files:**
- Create: `src/wx_red_helper/input_controller.py`
- Create: `src/wx_red_helper/event_log.py`
- Create: `tests/test_input_controller.py`

**Interfaces:**
- Consumes: Task 2 的 `RunMode` 与当前客户区边界，Task 5 产生并由服务层换算为屏幕点击点的状态机动作。
- Produces: `InputController.execute_click(x, y, mode) -> InputResult` 和 `EventLogger.record(event) -> None`。

- [ ] **Step 1: 写出自动模式门和屏幕绝对坐标转换的失败测试。**

```python
# tests/test_input_controller.py
from wx_red_helper.input_controller import InputController, absolute_mouse_coordinate
from wx_red_helper.models import RunMode


def test_detect_mode_never_sends_click() -> None:
    sent: list[object] = []
    controller = InputController(send_input=lambda event: sent.append(event), recheck=lambda: True)
    result = controller.execute_click(300, 400, RunMode.DETECT)
    assert result.executed is False
    assert result.reason == "mode_detect"
    assert sent == []


def test_absolute_mouse_coordinate_uses_virtual_screen_range() -> None:
    assert absolute_mouse_coordinate(960, 540, 1920, 1080) == (32785, 32798)
```

- [ ] **Step 2: 运行测试，确认输入控制器尚不存在。**

Run: `.\.venv\Scripts\python -m pytest tests/test_input_controller.py -q`

Expected: FAIL，导入错误指出 `input_controller` 尚不存在。

- [ ] **Step 3: 添加唯一的 SendInput 调用点和 JSONL 诊断日志。**

`input_controller.py` 使用 ctypes 定义 `INPUT`、`MOUSEINPUT` 和 `SendInput`，一次点击必须发送绝对移动、左键按下、左键抬起三项。任何输入前都必须依次检查：`mode is RunMode.AUTO`、全局取消令牌未设置、`recheck()` 返回真、目标点仍在当前客户区内。若任一检查失败，返回未执行结果且不得调用 `SendInput`。

```python
# src/wx_red_helper/input_controller.py
def absolute_mouse_coordinate(x: int, y: int, width: int, height: int) -> tuple[int, int]:
    return (round(x * 65535 / (width - 1)), round(y * 65535 / (height - 1)))
```

`EventLogger` 每行写一个 JSON 对象，仅允许字段 `timestamp`、`event`、`state`、`confidence_band`、`result`、`reason`；在传入未知字段时抛出 `ValueError`，从而避免意外写入聊天标题或图像数据。

- [ ] **Step 4: 运行输入与日志测试。**

Run: `.\.venv\Scripts\python -m pytest tests/test_input_controller.py -q`

Expected: PASS；补充覆盖 `STOPPED`、取消令牌、窗口复核失败、目标在客户区外和成功自动模式五条路径。

- [ ] **Step 5: 提交受控输入和日志。**

```powershell
git add src/wx_red_helper/input_controller.py src/wx_red_helper/event_log.py tests/test_input_controller.py
git commit -m "feat: add guarded input and private event logging"
```

## Task 7: 组合后台服务、托盘控制和紧急停止

**Files:**
- Create: `src/wx_red_helper/service.py`
- Create: `src/wx_red_helper/tray.py`
- Modify: `src/wx_red_helper/cli.py`
- Modify: `src/wx_red_helper/__main__.py`
- Create: `tests/conftest.py`
- Create: `tests/test_service.py`

**Interfaces:**
- Consumes: Tasks 2–6 的观察器、捕获器、识别器、安全门、状态机、输入控制器和日志。
- Produces: `HelperService.tick(now) -> ServiceStatus`、`HelperService.set_mode(mode)`、`HelperService.stop_now()` 和托盘的 `Stop`、`Detect only`、`Auto` 菜单回调。

- [ ] **Step 1: 写出从观察到决策的服务失败测试。**

```python
# tests/test_service.py
from wx_red_helper.models import RunMode, UiState
from wx_red_helper.service import HelperService


def test_service_in_detect_mode_reports_candidate_without_input(fake_dependencies) -> None:
    service = HelperService(**fake_dependencies)
    service.set_mode(RunMode.DETECT)
    status = service.tick(fake_dependencies["clock"]())
    assert status.state is UiState.ENVELOPE_CARD
    assert status.last_action == "candidate_detected"
    assert fake_dependencies["input_controller"].calls == []


def test_service_stops_after_consecutive_failures(fake_dependencies) -> None:
    service = HelperService(**fake_dependencies, max_consecutive_failures=3)
    for _ in range(3):
        fake_dependencies["recognizer"].return_unknown = True
        service.tick(fake_dependencies["clock"]())
    assert service.mode is RunMode.DETECT
```

- [ ] **Step 2: 运行服务测试，确认编排层尚不存在。**

Run: `.\.venv\Scripts\python -m pytest tests/test_service.py -q`

Expected: FAIL，导入错误指出 `HelperService` 尚不存在。

- [ ] **Step 3: 实现单线程轮询服务和托盘 UI。**

`HelperService.tick()` 的顺序必须固定为：观察窗口、捕获客户区、识别、稳定帧检查、安全门、状态机、输入控制器、事件日志。窗口无效或截图异常必须记录并返回，不能继续使用上一帧。默认轮询间隔为 150 ms；只有服务线程调用 `tick()`，以避免同时发出输入。

```python
# src/wx_red_helper/service.py
def stop_now(self) -> None:
    self._cancel_event.set()
    self._state_machine.reset()
    self._mode = RunMode.STOPPED
```

`tray.py` 使用 `pystray.Icon` 创建三个模式菜单项，并使用 `Ctrl+Shift+F12` 注册全局停止热键。停止回调必须先调用 `stop_now()`，再刷新托盘状态。`cli.py run` 启动服务线程和托盘；`collect-template <label>` 只能在服务未运行时执行。

- [ ] **Step 4: 运行服务测试和手工测试模式检查。**

Run:

```powershell
.\.venv\Scripts\python -m pytest tests/test_service.py -q
.\.venv\Scripts\python -m wx_red_helper run --mode detect
```

Expected: 单元测试 PASS；手工检查确认托盘可切换模式，测试模式永不调用 `SendInput`，紧急停止后状态显示为停止。

- [ ] **Step 5: 提交服务与控制界面。**

```powershell
git add src/wx_red_helper/service.py src/wx_red_helper/tray.py src/wx_red_helper/cli.py src/wx_red_helper/__main__.py tests/conftest.py tests/test_service.py
git commit -m "feat: add tray-controlled helper service"
```

## Task 8: 编写用户文档、创建可复现构建并完成测试模式验收

**Files:**
- Create: `README.md`
- Create: `build.ps1`
- Modify: `pyproject.toml`
- Modify: `.gitignore`

**Interfaces:**
- Consumes: Tasks 1–7 的 CLI、模板目录和测试命令。
- Produces: 用户可按文档安装、采集模板、先运行测试模式、手工切换自动模式并构建本地 `.exe`。

- [ ] **Step 1: 写出构建脚本存在且拒绝无模板打包的失败测试。**

```python
# tests/test_package.py
from pathlib import Path


def test_build_script_requires_all_three_templates() -> None:
    script = Path("build.ps1").read_text(encoding="utf-8")
    assert "envelope_card.png" in script
    assert "open_button.png" in script
    assert "result.png" in script
```

- [ ] **Step 2: 运行测试，确认构建脚本尚不存在。**

Run: `.\.venv\Scripts\python -m pytest tests/test_package.py -q`

Expected: FAIL，错误包含找不到 `build.ps1`。

- [ ] **Step 3: 添加操作文档、忽略规则和安全构建脚本。**

`README.md` 必须写明：仅支持可见、非最小化窗口；首次运行顺序为创建虚拟环境、安装、采集三个模板、运行 `--mode detect`、检查识别框与日志、手动改为自动模式；在未知页面或微信窗口切换时工具会中止；用户应保留紧急停止热键。

```powershell
# build.ps1
$required = @(
  "assets/templates/envelope_card.png",
  "assets/templates/open_button.png",
  "assets/templates/result.png"
)
$missing = $required | Where-Object { -not (Test-Path $_) }
if ($missing) { throw "Missing required local templates: $($missing -join ', ')" }
& .\.venv\Scripts\python -m PyInstaller --noconfirm --clean --onefile --noconsole --name WxRedHelper --paths src --add-data "assets/templates;assets/templates" src/wx_red_helper/__main__.py
if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed with exit code $LASTEXITCODE" }
```

`.gitignore` 必须忽略 `.venv/`、`__pycache__/`、`.pytest_cache/`、`build/`、`dist/`、`*.spec`、`logs/` 与 `assets/templates/*.png`，保留 `assets/templates/.gitkeep`。

- [ ] **Step 4: 完整回归、测试模式验收与构建。**

Run:

```powershell
.\.venv\Scripts\python -m pytest -q
.\.venv\Scripts\python -m wx_red_helper run --mode detect
.\build.ps1
```

Expected: 所有测试 PASS；测试模式未发送点击；只有三个用户本地模板均存在时才产生 `dist\WxRedHelper.exe`。

- [ ] **Step 5: 提交文档、构建与验收记录。**

```powershell
git add README.md build.ps1 .gitignore pyproject.toml tests/test_package.py
git commit -m "docs: add safe setup and build workflow"
```

## Plan Self-Review

### Spec coverage

- 可见且前台的微信窗口：Task 3。
- 仅客户区截屏和视觉识别：Tasks 3–4。
- 每一步界面验证、超时和状态中止：Task 5。
- 普通鼠标输入、点击前复核和不在检测模式点击：Task 6。
- 白名单、时段、冷却、日上限、失败降级和紧急停止：Tasks 2 and 7。
- 本地私密日志、默认无截图和不上传：Task 6 与 Task 8。
- 本地模板采集、测试模式和 Windows 可执行文件：Tasks 4, 7 and 8。

### Consistency checks

- 所有状态流转使用 `UiState`，所有可执行输入使用 `Action`，并由 `RunMode.AUTO` 与 `SafetyGate` 双重约束。
- Windows 调用集中在 `windows_api.py` 和 `input_controller.py`；测试可通过假依赖运行，不接触真实微信或鼠标。
- 模板为用户本地数据且被忽略，不会随源代码、日志或构建缓存提交。
