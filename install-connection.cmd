@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0install-connection.ps1"
if errorlevel 1 echo Installation did not complete. Send the visible error text in chat.
pause
