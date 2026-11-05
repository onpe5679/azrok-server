# Example of the private deployment flow.  It assumes the full private working
# tree: the browser-runtime trees (tools\boxedwine_local\*, tools\bridge_pydeps)
# come from the bridge repository, and the front-end files kept under web\ in
# this repository live in tools\boxedwine_local\ there.  The 2012 homepage
# restoration and its image assets are not part of the published repositories.
[CmdletBinding()]
param(
    [string]$TargetRoot = 'X:\home\u32ws\32dev\azroksrv',
    [switch]$InitializeState
)

$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$targetParent = (Resolve-Path (Split-Path -Parent $TargetRoot)).Path
$targetFull = [System.IO.Path]::GetFullPath($TargetRoot)
if (-not $targetFull.StartsWith($targetParent + [System.IO.Path]::DirectorySeparatorChar,
        [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Target must stay below $targetParent"
}

function Ensure-Directory([string]$Path) {
    New-Item -ItemType Directory -Force -Path $Path | Out-Null
}

function Copy-RelativeFile([string]$RelativePath) {
    $source = Join-Path $repo $RelativePath
    if (-not (Test-Path -LiteralPath $source -PathType Leaf)) {
        throw "Missing deployment file: $RelativePath"
    }
    $destination = Join-Path $targetFull $RelativePath
    Ensure-Directory (Split-Path -Parent $destination)
    if (Test-Path -LiteralPath $destination -PathType Leaf) {
        $sourceInfo = Get-Item -LiteralPath $source
        $destinationInfo = Get-Item -LiteralPath $destination
        if ($sourceInfo.Length -eq $destinationInfo.Length) {
            $sourceHash = (Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash
            $destinationHash = (Get-FileHash -LiteralPath $destination -Algorithm SHA256).Hash
            if ($sourceHash -eq $destinationHash) { return }
        }
    }
    Copy-Item -LiteralPath $source -Destination $destination -Force
}

function Copy-RelativeTree([string]$RelativePath) {
    $source = Join-Path $repo $RelativePath
    if (-not (Test-Path -LiteralPath $source -PathType Container)) {
        throw "Missing deployment tree: $RelativePath"
    }
    $destination = Join-Path $targetFull $RelativePath
    Ensure-Directory $destination
    Copy-Item -Path (Join-Path $source '*') -Destination $destination -Recurse -Force
}

Ensure-Directory $targetFull
foreach ($directory in @('logs', 'server_state', 'captures', 'bin')) {
    Ensure-Directory (Join-Path $targetFull $directory)
}

$rootFiles = @(
    'azrok_capture.py',
    'azrok_control.py',
    'azrok_admin.py',
    'azrok_admin_service.py',
    'azrok_admin_history.py',
    'azrok_control_page.py',
    'azrok_operator_page.py',
    'azrok_network.py',
    'azrok_private_access.py',
    'azrok_protocol_registry.py',
    'azrok_ox_progression.py',
    'azrok_server.py',
    'Azrok.dat',
    'init.csv'
)
foreach ($file in $rootFiles) { Copy-RelativeFile $file }

foreach ($file in @(
    'tools\run_server_only.py',
    'tools\ws_tcp_bridge.py',
    'tools\boxedwine_local\server.py'
)) { Copy-RelativeFile $file }

$webRoot = 'tools\boxedwine_local'
foreach ($pattern in @('*.html', '*.css', '*.js', '*.ico', '*.mp4', '*.wmv')) {
    Get-ChildItem -LiteralPath (Join-Path $repo $webRoot) -File -Filter $pattern | ForEach-Object {
        Copy-RelativeFile (Join-Path $webRoot $_.Name)
    }
}
foreach ($tree in @(
    'tools\boxedwine_local\assets',
    'tools\boxedwine_local\web_backend',
    'tools\boxedwine_local\assets_d3d9web\audio',
    'tools\bridge_pydeps'
)) { Copy-RelativeTree $tree }

foreach ($file in @(
    'tools\boxedwine_local\assets_d3d9web\boxedwine-shell.js',
    'tools\boxedwine_local\assets_d3d9web\boxedwine.upstreamjit64fn6inlineabi2korean6chat1touch2.js',
    'tools\boxedwine_local\assets_d3d9web\boxedwine.upstreamjit64fn6inlineabi2korean6chat1touch2.wasm',
    'tools\boxedwine_local\assets_d3d9web\boxedwine.upstreamjit64fn6inlineabi2korean6chat1touch2multidirectloops1.js',
    'tools\boxedwine_local\assets_d3d9web\boxedwine.upstreamjit64fn6inlineabi2korean6chat1touch2multidirectloops1.wasm',
    'tools\boxedwine_local\assets_d3d9web\boxedwine.upstreamjit64fn6inlineabi2korean6chat1touch2multidirectloops1facewishle1.js',
    'tools\boxedwine_local\assets_d3d9web\boxedwine.upstreamjit64fn6inlineabi2korean6chat1touch2multidirectloops1facewishle1.wasm',
    'tools\boxedwine_local\assets_d3d9web\boxedwine.upstreamjit64fn6inlineabi2korean6chat1touch2multidirectloops1facewishle1r10cwdrepublish1.js',
    'tools\boxedwine_local\assets_d3d9web\boxedwine.upstreamjit64fn6inlineabi2korean6chat1touch2multidirectloops1facewishle1r10cwdrepublish1.wasm',
    'tools\boxedwine_local\apps\Azrok_D3D9Web_pathouse_guestprofiles6_rsdefaults1_utf8ime2_dynamicaccounts2_startersplash1_fastboot4.zip',
    'tools\boxedwine_local\apps\Azrok_D3D9Web_pathouse_guestprofiles6_rsdefaults1_utf8ime2_dynamicaccounts2_startersplash1_fastboot4_questfont1.zip',
    'tools\boxedwine_local\fs\TinyCore15Wine11.0-wsaeventfix5-korean4-bgmloop3-dsound80ms1-pcrestd1-noprefixupd1-acp949-xim25koreanlocale2.zip',
    'tools\boxedwine_local\profiles\azrok-jit-grouped-commonfast64-depthlocal-inlinefetch2-currentabi1.zip',
    'tools\boxedwine_local\profiles\azrok-jit-grouped-multidirectloops1-currentabi1-20260830.zip',
    'tools\boxedwine_local\profiles\azrok-jit-grouped-multidirectloops1-currentabi1-facewishle1-map12984728-r5-20260901.zip',
    'tools\boxedwine_local\profiles\azrok-jit-grouped-multidirectloops1-currentabi1-facewishle1r10cwdrepublish1-map13009736-r1-20260901.zip'
)) { Copy-RelativeFile $file }

Copy-RelativeTree 'deploy\u32ws'

if ($InitializeState) {
    foreach ($file in @('logs\private_runtime_192.token', 'logs\private_browser_accounts.json')) {
        $destination = Join-Path $targetFull $file
        if (-not (Test-Path -LiteralPath $destination)) { Copy-RelativeFile $file }
    }
    $stateDestination = Join-Path $targetFull 'server_state'
    if (-not (Get-ChildItem -LiteralPath $stateDestination -File -ErrorAction SilentlyContinue)) {
        Copy-Item -Path (Join-Path $repo 'server_state\*') -Destination $stateDestination -Force
    }
}

$manifestFiles = Get-ChildItem -LiteralPath $targetFull -Recurse -File |
    Where-Object { $_.FullName -notmatch '[\\/]logs[\\/]' -and $_.FullName -notmatch '[\\/]server_state[\\/]' }
$manifest = foreach ($file in $manifestFiles) {
    try {
        $hash = (Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256 -ErrorAction Stop).Hash
    } catch [System.IO.FileNotFoundException], [System.Management.Automation.ItemNotFoundException] {
        # SSHFS can briefly retain a directory entry after an immutable
        # rejected asset is moved to quarantine.  It is not part of the
        # deployed tree and must not abort an otherwise complete sync.
        continue
    }
    [pscustomobject]@{
        path = $file.FullName.Substring($targetFull.Length + 1).Replace('\', '/')
        bytes = $file.Length
        sha256 = $hash.ToLowerInvariant()
    }
}
$manifest | ConvertTo-Json -Depth 3 | Set-Content -LiteralPath (Join-Path $targetFull 'deploy-manifest.json') -Encoding utf8
Write-Host "Azrok server deployment synchronized to $targetFull"
