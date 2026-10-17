@echo off
set "GTA_ROOT=C:\GTA-Craze\gta-craze-automation-main"
"%GTA_ROOT%\.venv\Scripts\python.exe" "%~dp0update_editor.py" "%GTA_ROOT%"
pause
