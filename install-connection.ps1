$ErrorActionPreference = 'Stop'
try {
    $root = 'C:\GTA-Craze\gta-craze-automation-main'
    if (-not (Test-Path (Join-Path $root '.venv\Scripts\python.exe'))) {
        Add-Type -AssemblyName System.Windows.Forms
        $picker = New-Object System.Windows.Forms.FolderBrowserDialog
        $picker.Description = 'Select your existing GTA Craze automation folder (the one containing .venv)'
        if ($picker.ShowDialog() -ne 'OK') { throw 'No project folder selected.' }
        $root = $picker.SelectedPath
    }
    $python = Join-Path $root '.venv\Scripts\python.exe'
    if (-not (Test-Path $python)) { throw 'The selected folder has no installed Python environment.' }
    if (-not (Test-Path (Join-Path $root 'automation.py'))) { throw 'automation.py is missing.' }
    $existing = Get-ScheduledTask -TaskName 'GTA Craze Chat Bridge' -ErrorAction SilentlyContinue
    if ($existing -and $existing.State -eq 'Running') { throw 'The bridge is running. Wait for its job to finish before reinstalling.' }
    $data = Join-Path $root 'data'
    New-Item -ItemType Directory -Path $data -Force | Out-Null
    $source = Join-Path $PSScriptRoot 'bridge_worker.py'
    $target = Join-Path $root 'bridge_worker.py'
    if ([IO.Path]::GetFullPath($source) -ne [IO.Path]::GetFullPath($target)) { Copy-Item -LiteralPath $source -Destination $target -Force }
    $credential = Join-Path $data 'bridge-token.xml'
    if (-not (Test-Path $credential)) {
        Write-Host 'One-time GitHub connection. Create a fine-grained token for ONLY gta-craze-automation.'
        Write-Host 'Repository permissions: Contents = Read and write. Keep the token out of chat.'
        Write-Host 'Choose an expiry you can renew. When it expires, the connection stops until renewed.'
        Start-Process 'https://github.com/settings/personal-access-tokens/new'
        $secret = Read-Host 'Paste the token here and press Enter (input is hidden)' -AsSecureString
        if ($secret.Length -eq 0) { throw 'No token entered.' }
        $secret | Export-Clixml -LiteralPath $credential
    }
    $settings = Join-Path $data 'bridge-config.json'
    if (-not (Test-Path $settings)) {
        @{ activated_at = [DateTime]::UtcNow.ToString('o') } | ConvertTo-Json | Set-Content -LiteralPath $settings -Encoding UTF8
    }
    Push-Location $root
    try {
        & $python 'bridge_worker.py' '--verify'
        if ($LASTEXITCODE -ne 0) {
            Remove-Item -LiteralPath $credential -ErrorAction SilentlyContinue
            throw 'GitHub check failed. Check the token repository selection and Contents read/write permission, then reopen this installer.'
        }
    } finally { Pop-Location }
    $pythonw = Join-Path $root '.venv\Scripts\pythonw.exe'
    if (-not (Test-Path $pythonw)) { $pythonw = $python }
    $action = New-ScheduledTaskAction -Execute $pythonw -Argument 'bridge_worker.py --once' -WorkingDirectory $root
    $poll = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) -RepetitionInterval (New-TimeSpan -Minutes 2)
    $logon = New-ScheduledTaskTrigger -AtLogOn -User ([System.Security.Principal.WindowsIdentity]::GetCurrent().Name)
    $options = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Hours 2) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
    $principal = New-ScheduledTaskPrincipal -UserId ([System.Security.Principal.WindowsIdentity]::GetCurrent().Name) -LogonType Interactive -RunLevel Limited
    Register-ScheduledTask -Force -TaskName 'GTA Craze Chat Bridge' -Action $action -Trigger @($poll, $logon) -Settings $options -Principal $principal -Description 'Check the GTA Craze GitHub request queue every two minutes' | Out-Null
    Start-ScheduledTask -TaskName 'GTA Craze Chat Bridge'
    Write-Host 'CONNECTION INSTALLED. Tell ChatGPT: connection installed.' -ForegroundColor Green
    Write-Host 'Your PC must be awake, online and signed into this Windows account.'
    Write-Host 'The existing noon and 8 PM video schedules remain installed.'
    Write-Host 'To disconnect: disable GTA Craze Chat Bridge in Task Scheduler and revoke its GitHub token.'
} catch {
    Write-Host ('Installation stopped: ' + $_.Exception.Message) -ForegroundColor Red
    exit 1
}
