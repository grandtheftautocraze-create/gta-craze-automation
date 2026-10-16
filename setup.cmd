@echo off
cd /d "%~dp0"
py -3 --version >nul 2>&1
if errorlevel 1 (
  echo Install Python 3.11 or newer from python.org, then run this again.
  pause
  exit /b 1
)
py -3 -m venv .venv
if errorlevel 1 goto fail
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 goto fail
if not exist .env copy .env.example .env >nul
if not exist media mkdir media
if not exist data mkdir data
.venv\Scripts\python.exe automation.py doctor
pause
exit /b 0
:fail
echo Setup failed. Please share the error, excluding any keys.
pause
exit /b 1
