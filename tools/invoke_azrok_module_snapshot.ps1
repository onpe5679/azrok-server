<#
  Request one read-only loader/module snapshot through Azrok-Plaza-Stop.
  This does not attach a debugger and never suspends the selected client.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateRange(1, 2147483647)]
    [int]$ProcessId
)

$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$artifactRoot = Join-Path $repoRoot 'artifacts\dynamic-analysis'
$requestPath = Join-Path $artifactRoot 'REQUEST_LOADER_MODULE_SNAPSHOT.json'
$stamp = Get-Date -Format 'yyyyMMdd_HHmmss_fff'
$resultPath = Join-Path $artifactRoot "loader_module_snapshot_${ProcessId}_${stamp}.json"
$target = Get-Process -Id $ProcessId -ErrorAction Stop

if (Test-Path -LiteralPath $requestPath) {
    throw 'Another loader module snapshot request is already pending'
}

[ordered]@{
    pid = $ProcessId
    process_start_utc = $target.StartTime.ToUniversalTime().ToString('o')
    result = $resultPath
} | ConvertTo-Json | Set-Content -LiteralPath $requestPath -Encoding UTF8

try {
    $launchOutput = & schtasks.exe /Run /TN 'Azrok-Plaza-Stop' 2>&1
    if ($LASTEXITCODE -ne 0) { throw "Could not start Azrok-Plaza-Stop: $launchOutput" }
    $deadline = (Get-Date).AddSeconds(20)
    while ((Get-Date) -lt $deadline) {
        if (Test-Path -LiteralPath $resultPath) {
            Get-Content -LiteralPath $resultPath -Raw
            return
        }
        Start-Sleep -Milliseconds 200
    }
    throw "Timed out waiting for $resultPath"
}
finally {
    Remove-Item -LiteralPath $requestPath -Force -ErrorAction SilentlyContinue
}
