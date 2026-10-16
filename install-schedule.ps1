$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
$python = Join-Path $root '.venv\Scripts\python.exe'
if (-not (Test-Path $python)) { throw 'Run setup.cmd first.' }
# Uses Windows local time. Change Windows timezone to Asia/Karachi for 8 PM Pakistan time.
$action = New-ScheduledTaskAction -Execute "$env:SystemRoot\System32\cmd.exe" -Argument ('/c ""{0}""' -f (Join-Path $root 'run.cmd')) -WorkingDirectory $root
$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday,Wednesday,Friday -At '20:00'
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -WakeToRun -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Hours 1)
$principal = New-ScheduledTaskPrincipal -UserId ([System.Security.Principal.WindowsIdentity]::GetCurrent().Name) -LogonType Interactive -RunLevel Limited
Register-ScheduledTask -TaskName 'GTA Craze Production' -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Description 'Local GTA Shorts generation; publishing depends on config.json' | Out-Null
Write-Host 'Scheduled Monday/Wednesday/Friday at 20:00 Windows local time. Stay signed in; screen may be locked.'
Write-Host 'Remove with: Unregister-ScheduledTask -TaskName "GTA Craze Production" -Confirm:$false'
