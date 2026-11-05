<#
  Entry point for the on-demand `Azrok-Plaza-Launch` scheduled task.

  Azrok.exe has a requireAdministrator manifest, so a normal launcher process
  cannot create it (Win32 error 740).  Keep this task's command intentionally
  fixed: per-run protocol variants are selected through the local control API
  before the transition macro is sent.
#>

$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot

Set-Location -LiteralPath $repoRoot
$env:AZROK_0064_ENTRY_KIND = '0x0A'
$env:AZROK_LEGACY_0019_MEMORY_SHORTCUT = '0'
# The client-side quest currency method is a deliberate no-op in this build.
# Give a fresh preservation profile a small server-owned seed so the restored
# shop is playable before quest-credit event detection has accumulated state.
$env:AZROK_STARTER_CURRENCY = '1000'
$requestedEvolution = 0
# Full-content restoration default. This is Acknex's own native -NX option,
# not a binary/runtime memory patch. REQUEST_NEXUS.txt may set 40 for A/B.
$requestedNexus = 200
$requestedContentProfile = 'shipped'
$evolutionRequest = Join-Path $repoRoot 'artifacts\dynamic-analysis\REQUEST_EVOLUTION.txt'
if (Test-Path -LiteralPath $evolutionRequest) {
    $rawEvolution = (Get-Content -LiteralPath $evolutionRequest -Raw).Trim()
    if ($rawEvolution -notmatch '^[0-3]$') {
        throw "Unsupported one-shot evolution request: $rawEvolution"
    }
    $requestedEvolution = [int]$rawEvolution
    Remove-Item -LiteralPath $evolutionRequest -Force
}
$replyModeRequest = Join-Path $repoRoot 'artifacts\dynamic-analysis\REQUEST_PLAZA_REPLY_MODE.txt'
if (Test-Path -LiteralPath $replyModeRequest) {
    $requestedReplyMode = (Get-Content -LiteralPath $replyModeRequest -Raw).Trim().ToLowerInvariant()
    if ($requestedReplyMode -notin @('both', '0064', '006e', 'none')) {
        throw "Unsupported AZROK_PLAZA_REPLY_MODE request: $requestedReplyMode"
    }
    $env:AZROK_PLAZA_REPLY_MODE = $requestedReplyMode
    Remove-Item -LiteralPath $replyModeRequest -Force
}
else {
    $env:AZROK_PLAZA_REPLY_MODE = '0064'
}

# One-shot, auditable native Acknex arena selection. azrok_launcher.py passes
# this through the engine's own -NX option; it performs no memory/binary writes.
$nexusRequest = Join-Path $repoRoot 'artifacts\dynamic-analysis\REQUEST_NEXUS.txt'
if (Test-Path -LiteralPath $nexusRequest) {
    $rawNexus = (Get-Content -LiteralPath $nexusRequest -Raw).Trim()
    if ($rawNexus -notmatch '^\d+$' -or [int]$rawNexus -lt 1 -or [int]$rawNexus -gt 2048) {
        throw "Unsupported one-shot Nexus request: $rawNexus"
    }
    $requestedNexus = [int]$rawNexus
    Remove-Item -LiteralPath $nexusRequest -Force
}

# One-shot restoration-state A/B.  `shipped` preserves the installed
# high-progress demo seed.  `playable` uses the separately documented
# progression-enabled profile and an isolated state namespace, so the A/B
# never deletes or overwrites the established shipped save.
$contentProfileRequest = Join-Path $repoRoot 'artifacts\dynamic-analysis\REQUEST_CONTENT_PROFILE.txt'
if (Test-Path -LiteralPath $contentProfileRequest) {
    $rawContentProfile = (Get-Content -LiteralPath $contentProfileRequest -Raw).Trim().ToLowerInvariant()
    if ($rawContentProfile -notin @('shipped', 'playable', 'minimal')) {
        throw "Unsupported one-shot content profile request: $rawContentProfile"
    }
    $requestedContentProfile = $rawContentProfile
    Remove-Item -LiteralPath $contentProfileRequest -Force
}
$env:AZROK_CONTENT_PROFILE = $requestedContentProfile
$env:AZROK_STATE_NAMESPACE = if ($requestedContentProfile -eq 'shipped') {
    ''
}
elseif ($requestedContentProfile -eq 'playable') {
    # v1 used the diagnostic minimal seed and could not naturally evolve.
    # Keep that evidence intact and start the corrected seed in a new store.
    'profile_playable_v2'
}
else {
    "profile_$requestedContentProfile"
}

& python.exe (Join-Path $repoRoot 'azrok_launcher.py') `
    --port 9207 `
    --control-port 9300 `
    --evolution $requestedEvolution `
    --nexus $requestedNexus
