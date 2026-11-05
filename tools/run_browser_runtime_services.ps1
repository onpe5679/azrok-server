[CmdletBinding()]
param(
    [string]$Bind = '127.0.0.1',
    [string]$InstanceToken = '',
    [string]$AccessSecretFile = '',
    [string]$TlsCert = '',
    [string]$TlsKey = '',
    [switch]$UseExistingCore
)

$ErrorActionPreference = 'Stop'

$normalizedPath = $env:Path
Remove-Item -LiteralPath Env:PATH -ErrorAction SilentlyContinue
if (-not $env:Path) {
    $env:Path = $normalizedPath
}

$workspace = Split-Path -Parent $PSScriptRoot
$python = '<home>\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
$lanAssetPython = '<home>\AppData\Local\Programs\Python\Python311\python.exe'
$logDir = Join-Path $workspace 'logs'
$pythonDeps = Join-Path $workspace 'tools\bridge_pydeps'
if (-not (Test-Path $pythonDeps)) {
    $pythonDeps = Join-Path $workspace '.tmp_pydeps'
}

New-Item -ItemType Directory -Force -Path $logDir | Out-Null
if (($TlsCert -and -not $TlsKey) -or ($TlsKey -and -not $TlsCert)) {
    throw 'TlsCert and TlsKey must be supplied together.'
}
if ($Bind -ne '127.0.0.1' -and -not $TlsCert) {
    throw 'A non-loopback browser bind requires TlsCert/TlsKey so SharedArrayBuffer isolation remains available.'
}
if ($AccessSecretFile -and -not (Test-Path -LiteralPath $AccessSecretFile -PathType Leaf)) {
    throw "AccessSecretFile not found: $AccessSecretFile"
}
$tlsArgs = @()
if ($TlsCert) { $tlsArgs = @('--tls-cert', $TlsCert, '--tls-key', $TlsKey) }

# The private-LAN HTTPS firewall rule is deliberately executable-scoped.  Keep
# the <lan-ip> asset listener on that reviewed Python 3.11 path, while
# the bridge stays on the pinned runtime used by its websocket dependency.
$assetPython = $python
if ($Bind -eq '<lan-ip>' -and (Test-Path -LiteralPath $lanAssetPython -PathType Leaf)) {
    $assetPython = $lanAssetPython
}

$server = $null
if (-not $UseExistingCore) {
    # The preservation core is never exposed on the private NIC.  A browser
    # reaches it only through the authenticated WSS bridge below.
    $server = Start-Process -PassThru -WindowStyle Hidden `
        -FilePath $python `
        -WorkingDirectory $workspace `
        -ArgumentList (@(
            '-u', 'tools\run_server_only.py',
            '--bind', '127.0.0.1',
            '--port', '9200',
            '--control-port', '9300',
            '--content-profile', 'playable',
            '--auto-select-existing'
        ) + $(if ($AccessSecretFile) { @('--access-secret-file', $AccessSecretFile) } else { @() })) `
        -RedirectStandardOutput (Join-Path $logDir 'browser_server_9200.out.log') `
        -RedirectStandardError (Join-Path $logDir 'browser_server_9200.err.log')
}

$oldPythonPath = $env:PYTHONPATH
$env:PYTHONPATH = $pythonDeps
$bridgeArgs = @(
    '-u', 'tools\ws_tcp_bridge.py',
    '--ws-host', $Bind,
    '--ws-port', '9201',
    # The preservation core is loopback-only.  This makes the private WSS
    # gateway a fixed target rather than a second game server or open proxy.
    '--tcp-host', '127.0.0.1',
    '--tcp-port', '9200'
) + $tlsArgs
# Start-Process -ArgumentList rejects empty array elements, and the bridge's
# --instance-token is optional (argparse default ""), so only pass it when set.
if ($InstanceToken) { $bridgeArgs += @('--instance-token', $InstanceToken) }
if ($AccessSecretFile) { $bridgeArgs += @('--access-secret-file', $AccessSecretFile) }
$bridge = Start-Process -PassThru -WindowStyle Hidden `
    -FilePath $python `
    -WorkingDirectory $workspace `
    -ArgumentList $bridgeArgs `
    -RedirectStandardOutput (Join-Path $logDir 'browser_bridge_9201.out.log') `
    -RedirectStandardError (Join-Path $logDir 'browser_bridge_9201.err.log')
$env:PYTHONPATH = $oldPythonPath

$http = Start-Process -PassThru -WindowStyle Hidden `
    -FilePath $assetPython `
    -WorkingDirectory (Join-Path $workspace 'tools\boxedwine_local') `
    -ArgumentList (@('-u', 'server.py', '--bind', $Bind, '--port', '8765') + $tlsArgs + $(if ($AccessSecretFile) { @('--access-secret-file', $AccessSecretFile) } else { @() })) `
    -RedirectStandardOutput (Join-Path $logDir 'browser_http_8765.out.log') `
    -RedirectStandardError (Join-Path $logDir 'browser_http_8765.err.log')

try {
    $managed = @($bridge, $http)
    if ($null -ne $server) { $managed += $server }
    while (@($managed | Where-Object { $_.HasExited }).Count -eq 0) {
        Start-Sleep -Seconds 5
        foreach ($process in $managed) { $process.Refresh() }
    }
}
finally {
    foreach ($process in @($http, $bridge, $server)) {
        if ($null -ne $process -and -not $process.HasExited) {
            Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
        }
    }
}
