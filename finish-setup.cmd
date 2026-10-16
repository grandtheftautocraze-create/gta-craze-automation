@echo off
setlocal
cd /d "%~dp0"
set "PATH=C:\ffmpeg\bin;%PATH%"
if not exist ".venv\Scripts\python.exe" (
  echo Python setup is missing. Run setup.cmd first.
  pause
  exit /b 1
)
echo Installing the downloader packages...
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 (
  echo Package installation failed. Please send the error above.
  pause
  exit /b 1
)
echo Finding and checking a Creative Commons GTA source...
.venv\Scripts\python.exe automation.py fetch-footage
if errorlevel 1 (
  echo Footage discovery failed. Please send the error above.
  pause
  exit /b 1
)
echo Checking required setup...
.venv\Scripts\python.exe automation.py doctor
if errorlevel 1 (
  echo Some setup items are missing. Do not schedule publishing yet.
  pause
  exit /b 1
)
echo Installing the automatic Monday, Wednesday, Friday 8 PM schedule...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install-schedule.ps1"
if errorlevel 1 (
  echo Schedule installation failed. Please send the error above.
  pause
  exit /b 1
)
echo Setup complete. The PC must be on, connected, and signed into Windows at scheduled times.
pause
