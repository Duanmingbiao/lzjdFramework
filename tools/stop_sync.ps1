$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$pidFile = Join-Path $projectRoot 'reports\assistant-sync.pid'
$watchScript = Join-Path $PSScriptRoot 'sync_assistant.py'
if (!(Test-Path -LiteralPath $pidFile)) { Write-Output 'No tracked sync process.'; exit 0 }
$syncProcessId = [int](Get-Content -LiteralPath $pidFile -Raw)
$existing = Get-CimInstance Win32_Process -Filter "ProcessId = $syncProcessId"
if ($existing -and $existing.CommandLine.Contains($watchScript) -and $existing.CommandLine.Contains('--watch')) {
    Stop-Process -Id $syncProcessId
    Write-Output "Sync stopped. PID=$syncProcessId"
} else { Write-Output 'Tracked sync process is no longer running.' }
