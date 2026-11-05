[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateRange(1, 2147483647)]
    [int]$ProcessId
)

$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$artifactRoot = Join-Path $repoRoot 'artifacts\dynamic-analysis'
$requestPath = Join-Path $artifactRoot 'REQUEST_X32DBG_HANG_SNAPSHOT.json'
$stamp = Get-Date -Format 'yyyyMMdd_HHmmss_fff'
$resultPath = Join-Path $artifactRoot "x32dbg_hang_snapshot_${ProcessId}_${stamp}.json"
$target = Get-Process -Id $ProcessId -ErrorAction Stop

if (Test-Path -LiteralPath $requestPath) {
    throw 'Another x32dbg hang snapshot request is already pending'
}

[ordered]@{
    pid = $ProcessId
    process_start_utc = $target.StartTime.ToUniversalTime().ToString('o')
    result = $resultPath
} | ConvertTo-Json | Set-Content -LiteralPath $requestPath -Encoding UTF8

try {
    $launchOutput = & schtasks.exe /Run /TN 'Azrok-Plaza-Stop' 2>&1
    if ($LASTEXITCODE -ne 0) { throw "Could not start Azrok-Plaza-Stop: $launchOutput" }
    $deadline = (Get-Date).AddSeconds(40)
    while ((Get-Date) -lt $deadline) {
        if (Test-Path -LiteralPath $resultPath) {
            $raw = Get-Content -LiteralPath $resultPath -Raw
            if ($raw -match '"kind":\s*"(?:detached|detach_error|fatal)"') {
                $raw
                return
            }
        }
        Start-Sleep -Milliseconds 250
    }
    throw "Timed out waiting for $resultPath"
}
finally {
    Remove-Item -LiteralPath $requestPath -Force -ErrorAction SilentlyContinue
}
