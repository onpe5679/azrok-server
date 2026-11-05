<#
  Entry point for the on-demand `Azrok-Plaza-Stop` scheduled task.
  It is deliberately limited to this workspace's Azrok.exe and launcher.
#>

$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$azrokPath = (Join-Path $repoRoot 'Azrok.exe')
$fridaPythonPath = '<home>\AppData\Local\Programs\Python\Python311\python.exe'
$diagnosticRequest = Join-Path $repoRoot 'artifacts\dynamic-analysis\REQUEST_READ_UI_VTABLES'
$diagnosticOutput = Join-Path $repoRoot 'artifacts\dynamic-analysis\LIVE_UI_VTABLES.json'
$debuggerRequest = Join-Path $repoRoot 'artifacts\dynamic-analysis\REQUEST_LAUNCH_X32DBG'
$automateTraceRequest = Join-Path $repoRoot 'artifacts\dynamic-analysis\REQUEST_X32DBG_000D_TRACE.json'
$hangSnapshotRequest = Join-Path $repoRoot 'artifacts\dynamic-analysis\REQUEST_X32DBG_HANG_SNAPSHOT.json'
$killDebuggerRequest = Join-Path $repoRoot 'artifacts\dynamic-analysis\REQUEST_KILL_X32DBG'
$altLaunchRequest = Join-Path $repoRoot 'artifacts\dynamic-analysis\REQUEST_LAUNCH_ALT_INSTANCE.json'
$uiActionRequest = Join-Path $repoRoot 'artifacts\dynamic-analysis\REQUEST_AZROK_UI_ACTION.json'
$dispatchWatchRequest = Join-Path $repoRoot 'artifacts\dynamic-analysis\REQUEST_READ_DISPATCH_WATCHES'
$dispatchWatchOutput = Join-Path $repoRoot 'artifacts\dynamic-analysis\LIVE_DISPATCH_WATCHES.json'
$closeInstanceRequest = Join-Path $repoRoot 'artifacts\dynamic-analysis\REQUEST_CLOSE_AZROK_INSTANCE.json'
$fridaInputRequest = Join-Path $repoRoot 'artifacts\dynamic-analysis\REQUEST_FRIDA_INPUT.json'
$loaderModuleSnapshotRequest = Join-Path $repoRoot 'artifacts\dynamic-analysis\REQUEST_LOADER_MODULE_SNAPSHOT.json'

# Close one explicitly selected workspace client without taking down the
# shared server or any other Azrok instance.  This is used for real
# disconnect/leave lifecycle tests and remains narrower than the task's
# default stop-all behavior below.
if (Test-Path -LiteralPath $closeInstanceRequest) {
    $request = Get-Content -LiteralPath $closeInstanceRequest -Raw | ConvertFrom-Json
    $targetPid = [int]$request.pid
    if ($targetPid -le 0) { throw 'Invalid Azrok instance pid' }
    $target = Get-Process -Id $targetPid -ErrorAction Stop
    # Some debugger-detached elevated clients expose an empty Path even to a
    # later elevated PowerShell.  The explicit PID request is still safe when
    # both the image name and immutable start time match.
    if ($target.Path -and $target.Path -ine $azrokPath) {
        throw 'Target is not this workspace Azrok.exe'
    }
    if ($target.ProcessName -ine 'Azrok') { throw 'Target image name is not Azrok' }
    if ($request.process_start_utc) {
        $requestedStart = [datetime]::Parse([string]$request.process_start_utc)
        if ([Math]::Abs(($target.StartTime.ToUniversalTime() - $requestedStart.ToUniversalTime()).TotalSeconds) -gt 0.01) {
            throw 'Azrok close target PID has been reused'
        }
    }
    $target | Stop-Process -Force
    $result = [string]$request.result
    if ($result) {
        $full = [IO.Path]::GetFullPath($result)
        $artifactRoot = [IO.Path]::GetFullPath((Join-Path $repoRoot 'artifacts'))
        if (-not $full.StartsWith($artifactRoot, [StringComparison]::OrdinalIgnoreCase)) {
            throw 'Close result path must stay under artifacts'
        }
        "closed_pid=$targetPid" | Set-Content -LiteralPath $full -Encoding UTF8
    }
    Remove-Item -LiteralPath $closeInstanceRequest -Force
    return
}

# A direct, debugger-free loader observation for Gate 1.  It is intentionally
# limited to the already-running, elevated workspace client and records only
# the Toolhelp module table; no target memory is read or written.
if (Test-Path -LiteralPath $loaderModuleSnapshotRequest) {
    $resultPath = $null
    try {
        $request = Get-Content -LiteralPath $loaderModuleSnapshotRequest -Raw | ConvertFrom-Json
        $targetPid = [int]$request.pid
        if ($targetPid -le 0) { throw 'Invalid loader snapshot pid' }
        $target = Get-Process -Id $targetPid -ErrorAction Stop
        if (-not $target.Path -or $target.Path -ine $azrokPath -or $target.ProcessName -ine 'Azrok') {
            throw 'Loader snapshot target is not this workspace Azrok.exe'
        }
        $requestedStart = [datetime]::Parse(
            [string]$request.process_start_utc,
            [Globalization.CultureInfo]::InvariantCulture,
            [Globalization.DateTimeStyles]::RoundtripKind
        )
        if ([Math]::Abs(($target.StartTime.ToUniversalTime() - $requestedStart.ToUniversalTime()).TotalSeconds) -gt 0.01) {
            throw 'Loader snapshot PID has been reused since the request was created'
        }
        $resultPath = [IO.Path]::GetFullPath([string]$request.result)
        $artifactRoot = [IO.Path]::GetFullPath((Join-Path $repoRoot 'artifacts'))
        $artifactPrefix = $artifactRoot.TrimEnd([IO.Path]::DirectorySeparatorChar) + [IO.Path]::DirectorySeparatorChar
        if (-not $resultPath.StartsWith($artifactPrefix, [StringComparison]::OrdinalIgnoreCase)) {
            throw 'Loader snapshot result must stay under artifacts'
        }
        & python.exe (Join-Path $PSScriptRoot 'snapshot_azrok_modules.py') --pid $targetPid --log $resultPath
        if ($LASTEXITCODE -ne 0) { throw "Module snapshot helper exited with code $LASTEXITCODE" }
    }
    catch {
        if ($resultPath) {
            ($_ | Out-String) | Add-Content -LiteralPath $resultPath -Encoding UTF8
        }
        throw
    }
    finally {
        Remove-Item -LiteralPath $loaderModuleSnapshotRequest -Force -ErrorAction SilentlyContinue
    }
    return
}

# Run the checked-in Frida input harness inside this already-approved
# highest-privilege task.  A normal user process cannot attach to the elevated
# 32-bit game without causing Frida's helper to request elevation, so the
# narrow JSON contract below is the UAC-free automation boundary.  Only
# read-only observation and filtered button-queue injection are accepted; no
# arbitrary script path, Python arguments, or shell text can be supplied.
if (Test-Path -LiteralPath $fridaInputRequest) {
    $resultPath = $null
    try {
        $request = Get-Content -LiteralPath $fridaInputRequest -Raw | ConvertFrom-Json
        $targetPid = [int]$request.pid
        if ($targetPid -le 0) { throw 'Invalid Frida target pid' }
        $target = Get-Process -Id $targetPid -ErrorAction Stop
        if (-not $target.Path -or $target.Path -ine $azrokPath) {
            throw 'Frida target is not this workspace Azrok.exe'
        }
        $requestedStart = [datetime]::Parse(
            [string]$request.process_start_utc,
            [Globalization.CultureInfo]::InvariantCulture,
            [Globalization.DateTimeStyles]::RoundtripKind
        )
        $actualStart = $target.StartTime.ToUniversalTime()
        if ([Math]::Abs(($actualStart - $requestedStart.ToUniversalTime()).TotalSeconds) -gt 0.01) {
            throw 'Frida target PID has been reused since the request was created'
        }

        $result = [string]$request.result
        if (-not $result) { throw 'Frida result path is required' }
        $resultPath = [IO.Path]::GetFullPath($result)
        $artifactRoot = [IO.Path]::GetFullPath((Join-Path $repoRoot 'artifacts'))
        $artifactPrefix = $artifactRoot.TrimEnd([IO.Path]::DirectorySeparatorChar) + [IO.Path]::DirectorySeparatorChar
        if (-not $resultPath.StartsWith($artifactPrefix, [StringComparison]::OrdinalIgnoreCase)) {
            throw 'Frida result path must stay under artifacts'
        }

        $helper = Join-Path $PSScriptRoot 'azrok_frida_input.py'
        $args = @($helper, '--pid', [string]$targetPid)
        $action = [string]$request.action
        switch ($action) {
            'observe' {
                $seconds = [double]$request.seconds
                if ($seconds -le 0 -or $seconds -gt 30) { throw 'Frida observe seconds must be in (0,30] ' }
                $args += @('observe', '--seconds', $seconds.ToString([Globalization.CultureInfo]::InvariantCulture))
            }
            'name_info' {
                # Read-only lookup of the fixed global game-manager pointer;
                # no address or arbitrary argument crosses the boundary.
                $args += @('name-info')
            }
            'hit_test_grid' {
                $x0 = [double]$request.x0_ratio; $y0 = [double]$request.y0_ratio
                $x1 = [double]$request.x1_ratio; $y1 = [double]$request.y1_ratio
                $step = [int]$request.step
                foreach ($ratio in @($x0, $y0, $x1, $y1)) {
                    if ($ratio -lt 0 -or $ratio -gt 1) { throw 'Hit-test grid ratios must be in 0..1' }
                }
                if ($x1 -lt $x0 -or $y1 -lt $y0) { throw 'Hit-test grid bounds are reversed' }
                if ($step -lt 4 -or $step -gt 128) { throw 'Hit-test grid step must be in 4..128' }
                if ($x0 -ne $x1 -or $y0 -ne $y1) {
                    throw 'Multi-point hit-test scans are disabled: the resolver mutates engine trace state and a full scan crashed the client'
                }
                $args += @(
                    'hit-test-grid',
                    '--x0-ratio', $x0.ToString([Globalization.CultureInfo]::InvariantCulture),
                    '--y0-ratio', $y0.ToString([Globalization.CultureInfo]::InvariantCulture),
                    '--x1-ratio', $x1.ToString([Globalization.CultureInfo]::InvariantCulture),
                    '--y1-ratio', $y1.ToString([Globalization.CultureInfo]::InvariantCulture),
                    '--step', [string]$step,
                    '--move-top-left'
                )
            }
            'find_exit_click' {
                throw 'find_exit_click is disabled: repeated off-thread hit resolution destroyed the live client'
            }
            'world_to_screen' {
                $worldX = [double]$request.world_x
                $worldY = [double]$request.world_y
                $worldZ = [double]$request.world_z
                foreach ($coordinate in @($worldX, $worldY, $worldZ)) {
                    if ([double]::IsNaN($coordinate) -or [double]::IsInfinity($coordinate) -or [Math]::Abs($coordinate) -gt 10000) {
                        throw 'World-to-screen coordinates must be finite and within +/-10000'
                    }
                }
                $args += @(
                    'world-to-screen',
                    '--world-x', $worldX.ToString([Globalization.CultureInfo]::InvariantCulture),
                    '--world-y', $worldY.ToString([Globalization.CultureInfo]::InvariantCulture),
                    '--world-z', $worldZ.ToString([Globalization.CultureInfo]::InvariantCulture)
                )
            }
            'map_state' {
                $gmText = [string]$request.gm
                $gm = if ($gmText -match '^0x[0-9A-Fa-f]+$') {
                    [Convert]::ToUInt32($gmText.Substring(2), 16)
                }
                else {
                    [uint32][int64]$request.gm
                }
                if ($gm -lt 0x10000 -or $gm -gt 0x7FFFFFFF) { throw 'Map-state game manager address is out of range' }
                $args += @('map-state', '--gm', ('0x{0:x}' -f $gm))
            }
            'queue_gym' {
                $settleMs = [int]$request.settle_ms
                $gmText = [string]$request.gm
                $gm = if ($gmText -match '^0x[0-9A-Fa-f]+$') {
                    [Convert]::ToUInt32($gmText.Substring(2), 16)
                }
                else {
                    [uint32][int64]$request.gm
                }
                if ($gm -lt 0x10000 -or $gm -gt 0x7FFFFFFF) {
                    throw 'Queue-gym game manager address is out of range'
                }
                if ($settleMs -lt 1000 -or $settleMs -gt 30000) {
                    throw 'Frida queue_gym settle_ms must be in 1000..30000'
                }
                # No address, selector, or arbitrary argument crosses this
                # boundary.  The helper exposes only the statically verified
                # Plaza -> Gym selector and validates phase/pending state.
                $args += @('queue-gym', '--gm', ('0x{0:x}' -f $gm), '--settle-ms', [string]$settleMs)
            }
            'queue_room' {
                $settleMs = [int]$request.settle_ms
                $room = [string]$request.room
                $allowedRooms = @('pathouse', 'playroom', 'gym', 'magic', 'cook', 'shop', 'library', 'ground')
                if ($room -notin $allowedRooms) {
                    throw "Queue-room name is not allowlisted: $room"
                }
                $gmText = [string]$request.gm
                $gm = if ($gmText -match '^0x[0-9A-Fa-f]+$') {
                    [Convert]::ToUInt32($gmText.Substring(2), 16)
                }
                else {
                    [uint32][int64]$request.gm
                }
                if ($gm -lt 0x10000 -or $gm -gt 0x7FFFFFFF) {
                    throw 'Queue-room game manager address is out of range'
                }
                if ($settleMs -lt 1000 -or $settleMs -gt 30000) {
                    throw 'Frida queue_room settle_ms must be in 1000..30000'
                }
                # Only the eight descriptors proven initialized by
                # FUN_00610B90 cross this elevated boundary.  OX selector 12
                # and uninitialized/descriptorless selectors are rejected.
                $args += @('queue-room', '--gm', ('0x{0:x}' -f $gm), '--room', $room, '--settle-ms', [string]$settleMs)
            }
            'rotate_project' {
                $worldX = [double]$request.world_x
                $worldY = [double]$request.world_y
                $worldZ = [double]$request.world_z
                $delta = [double]$request.delta
                $repeats = [int]$request.repeats
                foreach ($coordinate in @($worldX, $worldY, $worldZ)) {
                    if ([double]::IsNaN($coordinate) -or [double]::IsInfinity($coordinate) -or [Math]::Abs($coordinate) -gt 10000) {
                        throw 'Rotate-project coordinates must be finite and within +/-10000'
                    }
                }
                if ([double]::IsNaN($delta) -or [double]::IsInfinity($delta) -or [Math]::Abs($delta) -gt 9000) {
                    throw 'Rotate-project delta must be finite and within +/-9000'
                }
                if ($repeats -lt 1 -or $repeats -gt 4) { throw 'Rotate-project repeats must be in 1..4' }
                $args += @(
                    'rotate-project',
                    '--world-x', $worldX.ToString([Globalization.CultureInfo]::InvariantCulture),
                    '--world-y', $worldY.ToString([Globalization.CultureInfo]::InvariantCulture),
                    '--world-z', $worldZ.ToString([Globalization.CultureInfo]::InvariantCulture),
                    '--delta', $delta.ToString([Globalization.CultureInfo]::InvariantCulture),
                    '--repeats', [string]$repeats
                )
            }
            'prepare_shop' {
                $buttonId = [int]$request.button_id
                $balance = [uint32][int64]$request.balance
                $settleMs = [int]$request.settle_ms
                if ($buttonId -lt 0x14D -or $buttonId -gt 0x179) { throw 'Shop preparation button is outside the verified item range' }
                if ($balance -lt 1 -or $balance -gt 1000000) { throw 'Shop synthetic balance must be in 1..1000000' }
                if ($settleMs -lt 500 -or $settleMs -gt 10000) { throw 'Shop settle_ms must be in 500..10000' }
                $args += @(
                    'prepare-shop', ('0x{0:x}' -f $buttonId),
                    '--balance', [string]$balance,
                    '--target-caller', '0x005c3f81',
                    '--settle-ms', [string]$settleMs
                )
            }
            'push_button' {
                $buttonId = [int64]$request.button_id
                $param2Raw = if ($null -eq $request.param2) { [int64]-1 } else { [int64]$request.param2 }
                $param3Raw = if ($null -eq $request.param3) { [int64]-1 } else { [int64]$request.param3 }
                $param2 = if ($param2Raw -lt 0) { [uint32]($param2Raw + 0x100000000L) } else { [uint32]$param2Raw }
                $param3 = if ($param3Raw -lt 0) { [uint32]($param3Raw + 0x100000000L) } else { [uint32]$param3Raw }
                $repeat = [int]$request.repeat
                $settleMs = [int]$request.settle_ms
                $callerText = [string]$request.target_caller
                $targetCaller = if ($callerText -match '^0x[0-9A-Fa-f]+$') {
                    [Convert]::ToUInt32($callerText.Substring(2), 16)
                }
                else {
                    [uint32][int64]$request.target_caller
                }
                if ($buttonId -lt 0 -or $buttonId -gt 0xFFFF) { throw 'Frida button id must fit u16' }
                if ($repeat -lt 1 -or $repeat -gt 300) { throw 'Frida repeat must be in 1..300' }
                if ($settleMs -lt 0 -or $settleMs -gt 10000) { throw 'Frida settle_ms must be in 0..10000' }
                $allowedPair = (
                    ($targetCaller -eq 0x005EA5E1 -and $buttonId -ge 4 -and $buttonId -le 11) -or
                    ($targetCaller -eq 0x005E7901 -and (($buttonId -ge 0x0E -and $buttonId -le 0x14) -or $buttonId -eq 0x17)) -or
                    # FUN_005E3EE0 consumes the verified PatHouse Sleep
                    # event (0x21), the foodmaker entry (0x2F), the exact
                    # Toast recipe button (0x48), and the verified Gym popup
                    # events 0x41/0x42/0x43 at this exact ButtonQueue_Pop
                    # return.  0x2F/0x48 are constrained to the one
                    # statically proven foodmaker -> Toast path.
                    ($targetCaller -eq 0x005E3F14 -and (
                        $buttonId -eq 0x21 -or $buttonId -eq 0x2F -or
                        $buttonId -eq 0x48 -or
                        ($buttonId -ge 0x41 -and $buttonId -le 0x43)
                    )) -or
                    # Gym selection ring uses 0x5C/0x5D/0x5E.  The separate
                    # OutMap exit registered by FUN_005DB1E0 is 0x1AA.
                    ($targetCaller -eq 0x005DB4D4 -and (
                        ($buttonId -ge 0x5C -and $buttonId -le 0x5E) -or
                        $buttonId -eq 0x1AA
                    )) -or
                    # Playroom fixed overlay: juggling, tumbling, yoyo, exit.
                    ($targetCaller -eq 0x005DD8B4 -and (
                        ($buttonId -ge 0x65 -and $buttonId -le 0x67) -or
                        $buttonId -eq 0x1A9
                    )) -or
                    # Shop item selection.  FUN_005C3F50 consumes the queue
                    # record at this exact return; record+4 click type 2 is
                    # the verified 0x14D item-selection path.
                    ($targetCaller -eq 0x005C3F81 -and (
                        $buttonId -ge 0x14D -and $buttonId -le 0x179
                    )) -or
                    # Item-equip energy slots. FUN_005BAF60 consumes the
                    # verified single-click tuple [0x104..0x107, 2, -1] at
                    # this exact ButtonQueue_Pop return and routes it to
                    # FUN_005BC970 -> C2S 0x000F.
                    ($targetCaller -eq 0x005BAF91 -and (
                        $buttonId -ge 0x104 -and $buttonId -le 0x107
                    )) -or
                    # MyBag has two coincident 15-slot ranges.  FUN_005CFCA0
                    # routes click-type 2 on the real item buttons 0x189..0x197
                    # to FUN_005D27C0 (consume/use), while the paired overlay
                    # events 0x198..0x1A6 route only to FUN_005D2B10.  Keep the
                    # elevated boundary limited to those two verified ranges.
                    ($targetCaller -eq 0x005CFCD1 -and (
                        ($buttonId -ge 0x189 -and $buttonId -le 0x197) -or
                        ($buttonId -ge 0x198 -and $buttonId -le 0x1A6)
                    )) -or
                    # Main-menu accessory entry. FUN_005CC5C0 consumes the
                    # verified [0xBE, -1, -1] tuple at this exact return and
                    # opens CPopupAccessory.  The natural menu exposes it only
                    # in Plaza/Hansol mode 2; this pair is restricted to the
                    # single exact button id for isolated interoperability QA.
                    ($targetCaller -eq 0x005CC5F1 -and $buttonId -eq 0xBE) -or
                    # CPopupAccessory consumes the eight catalogue-selection
                    # ids, four equipped-slot selectors, and the exact
                    # set/clear ids at FUN_005AFF90's ButtonQueue_Pop return.
                    # Clear requires selecting equipped slot 0x1CD..0x1D0;
                    # a catalogue selection deliberately resets that field.
                    # param2/param3 are ignored by the verified consumer.
                    ($targetCaller -eq 0x005AFFC1 -and (
                        ($buttonId -ge 0x1C5 -and $buttonId -le 0x1CC) -or
                        ($buttonId -ge 0x1CD -and $buttonId -le 0x1D0) -or
                        $buttonId -eq 0x1D3 -or $buttonId -eq 0x1D4
                    )) -or
                    # Generic accessory error modal: code 0x1A/0x1B disables
                    # buttons 0/1 and enables only button 2 (confirm). Its
                    # verified handler closes the modal and restores input.
                    ($targetCaller -eq 0x005BE851 -and $buttonId -eq 0x02)
                )
                if (-not $allowedPair) {
                    throw 'Frida caller/button pair is not in the verified allowlist'
                }
                $args += @(
                    'push-button', ('0x{0:x}' -f $buttonId),
                    '--param2', ('0x{0:x}' -f $param2),
                    '--param3', ('0x{0:x}' -f $param3),
                    '--repeat', [string]$repeat,
                    '--target-caller', ('0x{0:x}' -f $targetCaller),
                    '--settle-ms', [string]$settleMs
                )
                if ([bool]$request.observe) { $args += '--observe' }
            }
            'click' {
                $x = [double]$request.x_ratio
                $y = [double]$request.y_ratio
                $hoverMs = [int]$request.hover_ms
                $holdMs = [int]$request.hold_ms
                $settleMs = [int]$request.settle_ms
                if ($x -lt 0 -or $x -gt 1 -or $y -lt 0 -or $y -gt 1) { throw 'Frida click ratios must be in 0..1' }
                if ($hoverMs -lt 0 -or $hoverMs -gt 2000) { throw 'Frida hover_ms must be in 0..2000' }
                if ($holdMs -lt 1 -or $holdMs -gt 2000) { throw 'Frida hold_ms must be in 1..2000' }
                if ($settleMs -lt 0 -or $settleMs -gt 30000) { throw 'Frida click settle_ms must be in 0..30000' }
                $args += @(
                    'click',
                    '--x-ratio', $x.ToString([Globalization.CultureInfo]::InvariantCulture),
                    '--y-ratio', $y.ToString([Globalization.CultureInfo]::InvariantCulture),
                    '--hover-ms', [string]$hoverMs,
                    '--hold-ms', [string]$holdMs,
                    '--settle-ms', [string]$settleMs,
                    '--move-top-left'
                )
                if ([bool]$request.observe) { $args += '--observe' }
            }
            'click_sequence' {
                $x1 = [double]$request.x1_ratio
                $y1 = [double]$request.y1_ratio
                $x2 = [double]$request.x2_ratio
                $y2 = [double]$request.y2_ratio
                $hoverMs = [int]$request.hover_ms
                $holdMs = [int]$request.hold_ms
                $interClickMs = [int]$request.inter_click_ms
                $settleMs = [int]$request.settle_ms
                foreach ($ratio in @($x1, $y1, $x2, $y2)) {
                    if ($ratio -lt 0 -or $ratio -gt 1) { throw 'Frida click-sequence ratios must be in 0..1' }
                }
                if ($hoverMs -lt 0 -or $hoverMs -gt 2000) { throw 'Frida sequence hover_ms must be in 0..2000' }
                if ($holdMs -lt 1 -or $holdMs -gt 2000) { throw 'Frida sequence hold_ms must be in 1..2000' }
                if ($interClickMs -lt 0 -or $interClickMs -gt 2000) { throw 'Frida inter_click_ms must be in 0..2000' }
                if ($settleMs -lt 0 -or $settleMs -gt 30000) { throw 'Frida sequence settle_ms must be in 0..30000' }
                $args += @(
                    'click-sequence',
                    '--x1-ratio', $x1.ToString([Globalization.CultureInfo]::InvariantCulture),
                    '--y1-ratio', $y1.ToString([Globalization.CultureInfo]::InvariantCulture),
                    '--x2-ratio', $x2.ToString([Globalization.CultureInfo]::InvariantCulture),
                    '--y2-ratio', $y2.ToString([Globalization.CultureInfo]::InvariantCulture),
                    '--hover-ms', [string]$hoverMs,
                    '--hold-ms', [string]$holdMs,
                    '--inter-click-ms', [string]$interClickMs,
                    '--settle-ms', [string]$settleMs,
                    '--move-top-left'
                )
                if ([bool]$request.observe) { $args += '--observe' }
            }
            default { throw 'Unsupported Frida action' }
        }

        # A cancelled non-elevated attach can leave the x86 helper waiting on
        # its UAC broker.  It is specific to this 32-bit harness; x64 helpers
        # used by unrelated tools are deliberately left alone.
        Get-Process -Name 'frida-helper-x86' -ErrorAction SilentlyContinue |
            Stop-Process -Force -ErrorAction SilentlyContinue

        if (-not (Test-Path -LiteralPath $fridaPythonPath)) { throw 'Verified Frida Python runtime is missing' }
        $savedErrorActionPreference = $ErrorActionPreference
        try {
            # Preserve the helper's complete stderr traceback in the requested
            # artifact instead of letting PowerShell turn its first stderr
            # line into a terminating NativeCommandError.
            $ErrorActionPreference = 'Continue'
            $output = & $fridaPythonPath @args 2>&1 | Out-String
            $exitCode = $LASTEXITCODE
        }
        finally {
            $ErrorActionPreference = $savedErrorActionPreference
        }
        @(
            "frida_action=$action"
            "target_pid=$targetPid"
            "exit_code=$exitCode"
            $output
        ) | Set-Content -LiteralPath $resultPath -Encoding UTF8
        if ($exitCode -ne 0) { throw "Frida helper exited with code $exitCode" }
    }
    catch {
        $message = ($_ | Out-String)
        if ($resultPath) {
            $message | Add-Content -LiteralPath $resultPath -Encoding UTF8
        }
        else {
            $message | Set-Content -LiteralPath (Join-Path $repoRoot 'artifacts\dynamic-analysis\FRIDA_INPUT_REQUEST.error.txt') -Encoding UTF8
        }
        throw
    }
    finally {
        Remove-Item -LiteralPath $fridaInputRequest -Force -ErrorAction SilentlyContinue
    }
    return
}

# Strictly read-only multi-process dispatch watch.  The approved elevated
# task is used because secondary Azrok clients run at a higher integrity level
# than the ordinary controller.  The Python probe only opens processes with
# QUERY_INFORMATION|VM_READ and never writes client memory.
if (Test-Path -LiteralPath $dispatchWatchRequest) {
    try {
        & python.exe (Join-Path $repoRoot 'tools\read_dispatch_watches.py') |
            Set-Content -LiteralPath $dispatchWatchOutput -Encoding UTF8
        Remove-Item -LiteralPath $dispatchWatchRequest -Force
        return
    }
    catch {
        ($_ | Out-String) | Set-Content -LiteralPath ($dispatchWatchOutput + '.error.txt') -Encoding UTF8
        throw
    }
}

# Start a second, separately-portioned client from this already-approved
# elevated interactive task.  This keeps the primary launcher single-instance
# while allowing a real two-client relay test without a new UAC prompt.
if (Test-Path -LiteralPath $altLaunchRequest) {
    $request = Get-Content -LiteralPath $altLaunchRequest -Raw | ConvertFrom-Json
    $port = [int]$request.port
    $controlPort = [int]$request.control_port
    $reuseServer = [bool]$request.reuse_server
    $contentProfile = if ($request.PSObject.Properties.Name -contains 'content_profile') { [string]$request.content_profile } else { 'playable' }
    $stateNamespace = if ($request.PSObject.Properties.Name -contains 'state_namespace') { [string]$request.state_namespace } else { 'profile_playable_v2' }
    $username = if ($request.PSObject.Properties.Name -contains 'username') { [string]$request.username } else { 'player' }
    if ($port -lt 1024 -or $port -gt 65535 -or ((-not $reuseServer) -and ($controlPort -lt 1024 -or $controlPort -gt 65535)) -or ($reuseServer -and $controlPort -ne 0)) {
        throw 'Invalid alternate instance port'
    }
    if ($contentProfile -notin @('minimal','playable','shipped')) {
        throw 'Invalid alternate content profile'
    }
    if ($stateNamespace -notmatch '^[A-Za-z0-9_-]{1,64}$') {
        throw 'Invalid alternate state namespace'
    }
    if ($username -notmatch '^[A-Za-z0-9_]{1,16}$') {
        throw 'Invalid alternate username'
    }
    $scriptPath = Join-Path $PSScriptRoot 'run_azrok_instance_elevated.ps1'
    $args = @('-NoProfile','-ExecutionPolicy','Bypass','-WindowStyle','Hidden',
              '-File',$scriptPath,'-Port',[string]$port,'-ControlPort',[string]$controlPort,
              '-ContentProfile',$contentProfile,'-StateNamespace',$stateNamespace,'-Username',$username)
    if ([bool]$request.reuse_server) { $args += '-ReuseServer' }
    $proc = Start-Process -FilePath 'PowerShell.exe' -ArgumentList $args `
        -WorkingDirectory $repoRoot -WindowStyle Hidden -PassThru
    $result = [string]$request.result
    if ($result) { "launcher_pid=$($proc.Id) port=$port control_port=$controlPort" | Set-Content -LiteralPath $result -Encoding UTF8 }
    Remove-Item -LiteralPath $altLaunchRequest -Force
    return
}

# Reuse this already-approved elevated interactive task for a narrow set of
# real-client UI actions. The ordinary helper cannot cross the game's higher
# integrity boundary, so this branch runs only the checked-in helper with a
# JSON action contract (click/key/capture/info); it never evaluates arbitrary
# shell text.
if (Test-Path -LiteralPath $uiActionRequest) {
    $request = Get-Content -LiteralPath $uiActionRequest -Raw | ConvertFrom-Json
    $targetPid = [int]$request.pid
    if ($targetPid -le 0) { throw 'Invalid UI action pid' }
    $helper = Join-Path $PSScriptRoot 'auto_azrok_ui.py'
    $action = [string]$request.action
    $args = @('--pid', [string]$targetPid)
    switch ($action) {
        'move_rel' {
            $x = [double]$request.x; $y = [double]$request.y
            if ($x -lt 0 -or $x -gt 1 -or $y -lt 0 -or $y -gt 1) { throw 'UI move ratios must be in 0..1' }
            $args += @('move-rel', $x.ToString([Globalization.CultureInfo]::InvariantCulture), $y.ToString([Globalization.CultureInfo]::InvariantCulture))
        }
        'click_rel' {
            $x = [double]$request.x; $y = [double]$request.y
            if ($x -lt 0 -or $x -gt 1 -or $y -lt 0 -or $y -gt 1) { throw 'UI click ratios must be in 0..1' }
            $args += @('click-rel', $x.ToString([Globalization.CultureInfo]::InvariantCulture), $y.ToString([Globalization.CultureInfo]::InvariantCulture))
        }
        'right_click_rel' {
            $x = [double]$request.x; $y = [double]$request.y
            if ($x -lt 0 -or $x -gt 1 -or $y -lt 0 -or $y -gt 1) { throw 'UI click ratios must be in 0..1' }
            $args += @('right-click-rel', $x.ToString([Globalization.CultureInfo]::InvariantCulture), $y.ToString([Globalization.CultureInfo]::InvariantCulture))
        }
        'click_rel_msg' {
            $x = [double]$request.x; $y = [double]$request.y
            if ($x -lt 0 -or $x -gt 1 -or $y -lt 0 -or $y -gt 1) { throw 'UI click ratios must be in 0..1' }
            $args += @('click-rel-msg', $x.ToString([Globalization.CultureInfo]::InvariantCulture), $y.ToString([Globalization.CultureInfo]::InvariantCulture))
        }
        'click_sequence' {
            $steps = @($request.steps)
            if ($steps.Count -lt 1 -or $steps.Count -gt 16) { throw 'UI click sequence must contain 1..16 steps' }
            $outputs = New-Object System.Collections.Generic.List[string]
            $oldSequenceInput = $env:AZROK_ALLOW_REAL_INPUT
            $env:AZROK_ALLOW_REAL_INPUT = '1'
            try {
                foreach ($step in $steps) {
                    $x = [double]$step.x; $y = [double]$step.y
                    if ($x -lt 0 -or $x -gt 1 -or $y -lt 0 -or $y -gt 1) { throw 'UI click ratios must be in 0..1' }
                    $clickArgs = @('--pid', [string]$targetPid, 'click-rel',
                        $x.ToString([Globalization.CultureInfo]::InvariantCulture),
                        $y.ToString([Globalization.CultureInfo]::InvariantCulture))
                    $outputs.Add((& python.exe $helper @clickArgs 2>&1 | Out-String))
                    $delay = [int]$step.delay_ms
                    if ($delay -gt 0) { Start-Sleep -Milliseconds ([Math]::Min($delay, 10000)) }
                }
            }
            finally {
                $env:AZROK_ALLOW_REAL_INPUT = $oldSequenceInput
            }
            $result = [string]$request.result
            if ($result) { ($outputs -join "`n") | Set-Content -LiteralPath $result -Encoding UTF8 }
            Remove-Item -LiteralPath $uiActionRequest -Force
            return
        }
        'key' {
            $key = ([string]$request.key).ToUpperInvariant()
            if ($key -notin @('ENTER','TAB','ESC','SPACE','LEFT','UP','RIGHT','DOWN')) { throw 'Unsupported UI key' }
            $args += @('key', $key)
        }
        'key_hold' {
            $key = ([string]$request.key).ToUpperInvariant()
            $holdMs = [int]$request.hold_ms
            if ($key -notin @('ENTER','TAB','ESC','SPACE','LEFT','UP','RIGHT','DOWN')) { throw 'Unsupported UI key' }
            if ($holdMs -lt 20 -or $holdMs -gt 2000) { throw 'UI key hold_ms must be in 20..2000' }
            $args += @('key-hold', $key, [string]$holdMs)
        }
        'text' {
            # Keep the elevated request surface bounded: chat probes only need
            # short printable ASCII, while auto_azrok_ui.py already owns the
            # SendInput text implementation used by the non-elevated CLI.
            $text = [string]$request.text
            if ($text.Length -lt 1 -or $text.Length -gt 80) { throw 'UI text must contain 1..80 characters' }
            foreach ($ch in $text.ToCharArray()) {
                $code = [int][char]$ch
                if ($code -lt 0x20 -or $code -gt 0x7E) { throw 'UI text must be printable ASCII' }
            }
            $args += @('text', $text)
        }
        'capture' {
            $path = [string]$request.path
            if (-not $path) { throw 'Capture path is required' }
            $full = [IO.Path]::GetFullPath($path)
            $artifactRoot = [IO.Path]::GetFullPath((Join-Path $repoRoot 'artifacts'))
            if (-not $full.StartsWith($artifactRoot, [StringComparison]::OrdinalIgnoreCase)) { throw 'Capture path must stay under artifacts' }
            $args += @('capture', $full)
        }
        'info' { $args += @('info') }
        default { throw 'Unsupported UI action' }
    }
    $result = [string]$request.result
    $old = $env:AZROK_ALLOW_REAL_INPUT
    $env:AZROK_ALLOW_REAL_INPUT = '1'
    try {
        $output = & python.exe $helper @args 2>&1 | Out-String
        if ($result) { $output | Set-Content -LiteralPath $result -Encoding UTF8 }
    }
    finally { $env:AZROK_ALLOW_REAL_INPUT = $old }
    Remove-Item -LiteralPath $uiActionRequest -Force
    return
}

if (Test-Path -LiteralPath $killDebuggerRequest) {
    Get-Process -Name 'x32dbg' -ErrorAction SilentlyContinue | Stop-Process -Force
    Remove-Item -LiteralPath $killDebuggerRequest -Force
    return
}

# One-shot elevated x64dbg-automate trace.  The request is deliberately a
# narrow JSON contract so repeated experiments do not need GUI automation or
# another UAC confirmation.  This branch never performs the task's stop action.
if (Test-Path -LiteralPath $automateTraceRequest) {
    $request = Get-Content -LiteralPath $automateTraceRequest -Raw | ConvertFrom-Json
    $profile = if ($request.PSObject.Properties.Name -contains 'profile') {
        [string]$request.profile
    }
    else {
        ''
    }
    if ($profile) {
        $allowedProfiles = @('room', 'door', 'roster', 'gate', 'gym', 'shop', 'ox', 'cook')
        if ($profile -notin $allowedProfiles) {
            throw "Unsupported x32dbg observer profile: $profile"
        }
        $traceScript = Join-Path $PSScriptRoot 'x32dbg_plaza_interaction_trace.py'
        $traceArgs = @(
            $traceScript,
            '--pid', [string][int]$request.pid,
            '--log', [string]$request.log,
            '--ready-file', [string]$request.ready_file,
            '--timeout', [string][double]$request.timeout,
            '--profile', $profile
        )
    }
    else {
        $traceScript = Join-Path $PSScriptRoot 'x32dbg_000d_trace.py'
        $traceArgs = @(
            $traceScript,
            '--pid', [string][int]$request.pid,
            '--log', [string]$request.log,
            '--ready-file', [string]$request.ready_file,
            '--timeout', [string][double]$request.timeout
        )
    }
    # Keep the dedicated Automate client beside the B: debugger.  The global
    # Python MCP process may retain an older package in use, so forcing this
    # child-only import path prevents its locked console entry point from
    # changing the observer's plugin compatibility.  The spawned trace inherits
    # it; the scheduled task itself is restored immediately afterwards.
    $priorPythonPath = $env:PYTHONPATH
    $env:PYTHONPATH = 'B:\Azrok_Automate_Runtime'
    try {
        Start-Process -FilePath 'python.exe' -ArgumentList $traceArgs -WorkingDirectory $repoRoot -WindowStyle Hidden
    }
    finally {
        $env:PYTHONPATH = $priorPythonPath
    }
    Remove-Item -LiteralPath $automateTraceRequest -Force
    return
}

# Read-only post-mortem snapshot for a still-running but stalled client.  The
# request is one-shot and pins both the PID and its start time to reject reuse.
if (Test-Path -LiteralPath $hangSnapshotRequest) {
    $request = Get-Content -LiteralPath $hangSnapshotRequest -Raw | ConvertFrom-Json
    $targetPid = [int]$request.pid
    $target = Get-Process -Id $targetPid -ErrorAction Stop
    if (-not $target.Path -or $target.Path -ine $azrokPath) {
        throw 'x32dbg snapshot target is not this workspace Azrok.exe'
    }
    $requestedStart = [datetime]::Parse([string]$request.process_start_utc)
    if ([Math]::Abs(($target.StartTime.ToUniversalTime() - $requestedStart.ToUniversalTime()).TotalSeconds) -gt 0.01) {
        throw 'x32dbg snapshot target PID has been reused'
    }
    $resultPath = [IO.Path]::GetFullPath([string]$request.result)
    $artifactRoot = [IO.Path]::GetFullPath((Join-Path $repoRoot 'artifacts'))
    $artifactPrefix = $artifactRoot.TrimEnd([IO.Path]::DirectorySeparatorChar) + [IO.Path]::DirectorySeparatorChar
    if (-not $resultPath.StartsWith($artifactPrefix, [StringComparison]::OrdinalIgnoreCase)) {
        throw 'x32dbg snapshot result must stay under artifacts'
    }
    $snapshotScript = Join-Path $PSScriptRoot 'x32dbg_hang_snapshot.py'
    & python.exe $snapshotScript --pid $targetPid --log $resultPath
    Remove-Item -LiteralPath $hangSnapshotRequest -Force
    return
}

# One-shot elevated debugger launcher. This keeps the scheduled task's normal
# stop behavior unchanged and avoids a new UAC prompt for each experiment.
if (Test-Path -LiteralPath $debuggerRequest) {
    $debuggerArguments = (Get-Content -LiteralPath $debuggerRequest -Raw).Trim()
    $x32dbgCandidates = @(
        [string]$env:AZROK_X32DBG_PATH,
        'B:\x64dbg\x32\x32dbg.exe',
        'B:\x64dbg\release\x32\x32dbg.exe',
        (Join-Path $repoRoot 'tools\x64dbg\x32\x32dbg.exe'),
        'C:\x64dbg\x32\x32dbg.exe'
    )
    $x32dbgPath = $null
    foreach ($candidate in $x32dbgCandidates) {
        if (-not $candidate) { continue }
        $candidateFull = [IO.Path]::GetFullPath($candidate)
        if ([IO.Path]::GetPathRoot($candidateFull) -ieq 'D:\') { continue }
        if (Test-Path -LiteralPath $candidateFull -PathType Leaf) {
            $x32dbgPath = $candidateFull
            break
        }
    }
    if (-not $x32dbgPath) {
        throw 'x32dbg not found on allowed B:/workspace/C: paths; set AZROK_X32DBG_PATH to a non-D: executable'
    }
    Get-Process -Name 'x32dbg' -ErrorAction SilentlyContinue |
        Stop-Process -Force -ErrorAction SilentlyContinue
    if ($debuggerArguments) {
        Start-Process -FilePath $x32dbgPath -ArgumentList $debuggerArguments
    }
    else {
        Start-Process -FilePath $x32dbgPath
    }
    Remove-Item -LiteralPath $debuggerRequest -Force
    return
}

# Reuse the already-approved highest-privilege task for a strictly read-only
# diagnostic. The marker makes this branch explicit and one-shot; without it,
# the task retains its original stop behavior below.
if (Test-Path -LiteralPath $diagnosticRequest) {
    try {
        $target = Get-Process -Name 'Azrok' -ErrorAction Stop |
            Where-Object { $_.Path -and $_.Path -ieq $azrokPath } |
            Select-Object -First 1
        if (-not $target) {
            throw "Workspace Azrok process not found"
        }

        $requestedGmText = (Get-Content -LiteralPath $diagnosticRequest -Raw).Trim()
        $requestedGm = if ($requestedGmText -match '^0x[0-9A-Fa-f]+$') {
            [Convert]::ToUInt32($requestedGmText.Substring(2), 16)
        }
        else {
            [uint32]0
        }

        & (Join-Path $PSScriptRoot 'read_ui_vtables.ps1') -ProcessId $target.Id -GameManager $requestedGm |
            Set-Content -LiteralPath $diagnosticOutput -Encoding UTF8
        Remove-Item -LiteralPath $diagnosticRequest -Force
        return
    }
    catch {
        ($_ | Out-String) | Set-Content -LiteralPath ($diagnosticOutput + '.error.txt') -Encoding UTF8
        throw
    }
}

# Refuse the destructive fallback when a caller clearly intended a one-shot
# request but misspelled its filename.  Without this guard an unknown
# REQUEST_* marker would fall through to the historical stop-all behavior,
# which can close a healthy shared-server session.  A deliberate plain task
# invocation with no request marker still retains the original stop action.
$knownRequestPaths = @(
    $diagnosticRequest, $debuggerRequest, $automateTraceRequest,
    $hangSnapshotRequest, $killDebuggerRequest, $altLaunchRequest,
    $uiActionRequest, $dispatchWatchRequest, $closeInstanceRequest,
    $fridaInputRequest
) | ForEach-Object { [IO.Path]::GetFullPath($_) }
$unknownRequests = @(
    Get-ChildItem -LiteralPath (Join-Path $repoRoot 'artifacts\dynamic-analysis') `
        -Filter 'REQUEST_*' -File -ErrorAction SilentlyContinue |
        Where-Object { $knownRequestPaths -notcontains [IO.Path]::GetFullPath($_.FullName) }
)
if ($unknownRequests.Count -gt 0) {
    $names = ($unknownRequests | Select-Object -ExpandProperty Name) -join ', '
    throw "Unknown request marker(s): $names. Refusing default stop-all fallback."
}

$azrok = Get-Process -Name 'Azrok' -ErrorAction SilentlyContinue |
    Where-Object { $_.Path -and $_.Path -ieq $azrokPath }

if ($azrok) {
    $azrok | Stop-Process -Force
}

$launchers = Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
    Where-Object { $_.CommandLine -match '(?i)azrok_launcher\.py' }

foreach ($launcher in $launchers) {
    Stop-Process -Id $launcher.ProcessId -Force -ErrorAction SilentlyContinue
}
