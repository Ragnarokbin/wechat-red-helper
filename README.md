# Windows 微信红包本地助手

仅供个人在 Windows 上本机使用。工具只在微信窗口可见、位于前台且未最小化时工作；不会读取微信数据库、进程内存或网络通信。

## 准备

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python -m pip install -e ".[dev]"
```

打开并置顶微信窗口后，分别在红包卡片、领取页“开”按钮和领取结果页运行模板采集命令。出现选框时，仅框选目标控件本身并按 Enter 保存。

```powershell
.\.venv\Scripts\python -m wx_red_helper collect-template envelope_card
.\.venv\Scripts\python -m wx_red_helper collect-template open_button
.\.venv\Scripts\python -m wx_red_helper collect-template result
```

模板只保存在本机 `assets/templates`，不会提交到 Git。

## 使用

先运行检测模式。`--allow-title` 必须与微信窗口显示的会话标题完全相同；检测模式绝不发送鼠标输入。

```powershell
.\.venv\Scripts\python -m wx_red_helper run --mode detect --allow-title "家人群"
```

确认终端持续显示正确的候选状态，并且微信窗口位置、缩放比例和主题不变后，才可显式改用自动模式：

```powershell
.\.venv\Scripts\python -m wx_red_helper run --mode auto --allow-title "家人群"
```

按 `Ctrl+C` 随时停止。窗口最小化、前台切换、模板不匹配、加载超时或出现未知页面时，本轮不会继续点击。

## 验证与打包

```powershell
.\.venv\Scripts\python -m pytest -q
.\build.ps1
```

构建脚本仅在三个本地模板都存在时产生 `dist\WxRedHelper.exe`。
