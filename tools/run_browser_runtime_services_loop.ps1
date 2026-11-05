param(
    [ValidateRange(1, 60)]
    [int]$RestartDelaySeconds = 2
)

$ErrorActionPreference = 'Continue'
$runner = Join-Path $PSScriptRoot 'run_browser_runtime_services.ps1'

while ($true) {
    try {
        & $runner
    }
    catch {
        Write-Error $_
    }
    Start-Sleep -Seconds $RestartDelaySeconds
}
