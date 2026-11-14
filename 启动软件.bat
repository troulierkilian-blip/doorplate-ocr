@echo off
chcp 65001 >nul
cd /d "%~dp0"
if exist "发布版\门牌识别工作台.exe" (
 start "" "发布版\门牌识别工作台.exe"
) else if exist "发布版\DoorplateOCR\DoorplateOCR.exe" (
 start "" "发布版\DoorplateOCR\DoorplateOCR.exe"
) else (
 start "" ".venv\Scripts\pythonw.exe" "app.py"
)
