$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
$python = Join-Path $root '.venv\Scripts\python.exe'
if (-not (Test-Path $python)) { throw 'Run setup.cmd first.' }

# Task Scheduler uses the current Windows local time zone.
$runner = Join-Path $root 'run.cmd'
$command = Join-Path $env:SystemRoot 'System32\cmd.exe'
$communityAction = New-ScheduledTaskAction -Execute $command -Argument ('/c ""{0}" --format community"' -f $runner) -WorkingDirectory $root
$explainerAction = New-ScheduledTaskAction -Execute $command -Argument ('/c ""{0}" --format explainer"' -f $runner) -WorkingDirectory $root
$communityTrigger = New-ScheduledTaskTrigger -Daily -At '12:00'
$explainerTrigger = New-ScheduledTaskTrigger -Daily -At '20:00'
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -WakeToRun -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Hours 1)
$principal = New-ScheduledTaskPrincipal -UserId ([System.Security.Principal.WindowsIdentity]::GetCurrent().Name) -LogonType Interactive -RunLevel Limited

# Replace the old combined task to avoid duplicate runs.
foreach ($name in @('GTA Craze Production', 'GTA Craze Community', 'GTA Craze Explainer')) {
    Unregister-ScheduledTask -TaskName $name -Confirm:$false -ErrorAction SilentlyContinue
}

Register-ScheduledTask -Force -TaskName 'GTA Craze Community' -Action $communityAction -Trigger $communityTrigger -Settings $settings -Principal $principal -Description 'Daily community-style GTA Short at noon Windows local time' | Out-Null
Register-ScheduledTask -Force -TaskName 'GTA Craze Explainer' -Action $explainerAction -Trigger $explainerTrigger -Settings $settings -Principal $principal -Description 'Daily GTA explainer Short at 8 PM Windows local time' | Out-Null

Write-Host 'Scheduled 2 Shorts daily: community style at 12:00 PM, explainer style at 8:00 PM Windows local time.'
Write-Host 'Remove with: Unregister-ScheduledTask -TaskName "GTA Craze Community" -Confirm:$false; Unregister-ScheduledTask -TaskName "GTA Craze Explainer" -Confirm:$false'
