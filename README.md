# Windows 微信红包本地助手

仅供个人在 Windows 上本机使用。工具只在微信窗口可见、位于前台且未最小化时工作；不会读取微信数据库、进程内存或网络通信。

## 准备

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python -m pip install -e ".[dev]"
```

打开指定群聊并置顶微信窗口后，先采集群聊页头中包含群名称的稳定区域；随后分别在红包卡片、领取页“开”按钮和领取结果页采集模板。出现选框时，它会显示在微信窗口最前方；仅框选目标区域并按 Enter 保存。

```powershell
.\.venv\Scripts\python -m wx_red_helper collect-template chat_header
.\.venv\Scripts\python -m wx_red_helper collect-template envelope_card
.\.venv\Scripts\python -m wx_red_helper collect-template open_button
.\.venv\Scripts\python -m wx_red_helper collect-template result
```

模板只保存在本机 `assets/templates`，不会提交到 Git。

## 使用

先运行检测模式。`--allow-title` 是你为本次运行明确指定的会话标签；实际会话验证由 `chat_header` 模板完成，检测模式绝不发送鼠标输入。

```powershell
.\.venv\Scripts\python -m wx_red_helper run --mode detect --allow-title "家人群"
```

确认终端持续显示正确的候选状态，并且微信窗口位置、缩放比例和主题不变后，才可显式改用自动模式：

```powershell
.\.venv\Scripts\python -m wx_red_helper run --mode auto --allow-title "家人群"
```

交互菜单中的“自动领取模式”会先要求输入 `10ms` 到 `50ms` 之间的整数扫描间隔，再输入目标群聊名称。数值越小，扫描越频繁；调整间隔不会取消群聊页头验证、两帧稳定识别、点击前窗口复核和异常页面中止。

```powershell
.\.venv\Scripts\python -m wx_red_helper run --mode auto --allow-title "家人群" --interval-ms 50
```

按 `Ctrl+C` 随时停止。窗口最小化、前台切换、模板不匹配、加载超时或出现未知页面时，本轮不会继续点击。

## 验证与打包

```powershell
.\.venv\Scripts\python -m pytest -q
.\build.ps1
```

构建脚本会生成 `dist\WxRedHelper\` 文件夹；可将整个文件夹压缩后分享。中文使用说明会以 `使用说明.txt` 一并放入该文件夹，接收者需自行采集四张本地模板。
