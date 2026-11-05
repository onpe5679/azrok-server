<#
  On-demand second-client launcher for the local preservation test.
  The caller supplies a distinct game/control port; no browser is opened.
  This is intentionally a separate task entry point so the fixed primary
  launch task remains single-instance and keeps using 9207/9300.
#>
param(
    [Parameter(Mandatory=$true)][int]$Port,
    [Parameter(Mandatory=$true)][int]$ControlPort,
    [ValidateSet('minimal','playable','shipped')][string]$ContentProfile = 'playable',
    [ValidatePattern('^[A-Za-z0-9_-]{1,64}$')][string]$StateNamespace = 'profile_playable_v2',
    [ValidatePattern('^[A-Za-z0-9_]{1,16}$')][string]$Username = 'player',
    [switch]$ReuseServer
)

$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $repoRoot
$env:AZROK_0064_ENTRY_KIND = '0x0A'
$env:AZROK_LEGACY_0019_MEMORY_SHORTCUT = '0'
$env:AZROK_PLAZA_REPLY_MODE = '0064'
$env:AZROK_STARTER_CURRENCY = '1000'
$env:AZROK_CONTENT_PROFILE = $ContentProfile
$env:AZROK_STATE_NAMESPACE = $StateNamespace

$launcherArgs = @('--port', [string]$Port, '--control-port', [string]$ControlPort, '--username', $Username)
if ($ReuseServer) { $launcherArgs += '--reuse-server' }
$stamp = Get-Date -Format 'yyyyMMdd_HHmmss_fff'
$logDir = Join-Path $repoRoot 'artifacts\dynamic-analysis'
$stdout = Join-Path $logDir ("alt_launcher_" + $stamp + ".stdout.log")
$stderr = Join-Path $logDir ("alt_launcher_" + $stamp + ".stderr.log")
Start-Process -FilePath 'python.exe' `
    -ArgumentList (@((Join-Path $repoRoot 'azrok_launcher.py')) + $launcherArgs) `
    -WorkingDirectory $repoRoot -WindowStyle Hidden `
    -RedirectStandardOutput $stdout -RedirectStandardError $stderr | Out-Null
