$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$pidFile = Join-Path $projectRoot 'reports\assistant-sync.pid'
$watchScript = Join-Path $PSScriptRoot 'sync_assistant.py'
if (Test-Path -LiteralPath $pidFile) {
    $syncProcessId = [int](Get-Content -LiteralPath $pidFile -Raw)
    $existing = Get-CimInstance Win32_Process -Filter "ProcessId = $syncProcessId"
    if ($existing -and $existing.CommandLine.Contains($watchScript) -and $existing.CommandLine.Contains('--watch')) {
        Write-Output "Sync is already running. PID=$syncProcessId"
        exit 0
    }
}
$pythonCommand = Get-Command python -ErrorAction Stop
$started = Start-Process -FilePath $pythonCommand.Source -ArgumentList @('-X', 'utf8', ('"' + $watchScript + '"'), '--watch') -WorkingDirectory $projectRoot -WindowStyle Hidden -RedirectStandardOutput (Join-Path $projectRoot 'reports\assistant-sync.log') -RedirectStandardError (Join-Path $projectRoot 'reports\assistant-sync-error.log') -PassThru
$started.Id | Set-Content -LiteralPath $pidFile -Encoding ascii
Write-Output "Sync started. PID=$($started.Id)"
