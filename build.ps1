& .\.venv\Scripts\python -m PyInstaller --noconfirm --clean --onedir --name WxRedHelper --paths src src/wx_red_helper/__main__.py
if ($LASTEXITCODE -ne 0) {
  throw "PyInstaller failed with exit code $LASTEXITCODE"
}

$packageRoot = "dist\WxRedHelper"
New-Item -ItemType Directory -Force "$packageRoot\assets\templates" | Out-Null
Copy-Item "使用说明.txt" "$packageRoot\使用说明.txt" -Force
