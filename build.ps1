$required = @(
  "assets/templates/chat_header.png",
  "assets/templates/envelope_card.png",
  "assets/templates/open_button.png",
  "assets/templates/result.png"
)
$missing = $required | Where-Object { -not (Test-Path $_) }
if ($missing) {
  throw "Missing required local templates: $($missing -join ', ')"
}

& .\.venv\Scripts\python -m PyInstaller --noconfirm --clean --onefile --name WxRedHelper --paths src --add-data "assets/templates;assets/templates" src/wx_red_helper/__main__.py
if ($LASTEXITCODE -ne 0) {
  throw "PyInstaller failed with exit code $LASTEXITCODE"
}
