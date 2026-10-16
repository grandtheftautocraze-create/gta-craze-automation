@echo off
cd /d "%~dp0"
if not exist data mkdir data
.venv\Scripts\python.exe automation.py run %* >> data\runner.log 2>&1
exit /b %errorlevel%
