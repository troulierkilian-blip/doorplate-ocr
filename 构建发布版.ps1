$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot
& ".\.venv\Scripts\python.exe" create_icon.py
if ($LASTEXITCODE -ne 0) { throw "Icon generation failed" }
& ".\.venv\Scripts\python.exe" -m PyInstaller --noconfirm --distpath "发布版" --workpath ".build" "DoorplateOCR.spec"
if ($LASTEXITCODE -ne 0) { throw "PyInstaller build failed" }
