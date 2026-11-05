<#
  UAC-free front end for the narrow Frida branch in Azrok-Plaza-Stop.
  The scheduled task performs all target/path/argument validation again at
  high integrity; this script only creates a one-shot request and waits for it.
#>

[CmdletBinding(DefaultParameterSetName = 'Observe')]
param(
    [Parameter(Mandatory = $true)]
    [ValidateRange(1, 2147483647)]
    [int]$ProcessId,

    [Parameter(Mandatory = $true, ParameterSetName = 'Observe')]
    [switch]$Observe,

    [Parameter(ParameterSetName = 'Observe')]
    [ValidateRange(0.1, 30.0)]
    [double]$Seconds = 1.0,

    [Parameter(Mandatory = $true, ParameterSetName = 'QueueGym')]
    [switch]$QueueGym,

    [Parameter(Mandatory = $true, ParameterSetName = 'QueueGym')]
    [ValidatePattern('^0x[0-9A-Fa-f]+$')]
    [string]$GameManager,

    [Parameter(Mandatory = $true, ParameterSetName = 'QueueRoom')]
    [switch]$QueueRoom,

    [Parameter(Mandatory = $true, ParameterSetName = 'QueueRoom')]
    [ValidateSet('pathouse', 'playroom', 'gym', 'magic', 'cook', 'shop', 'library', 'ground')]
    [string]$Room,

    [Parameter(Mandatory = $true, ParameterSetName = 'QueueRoom')]
    [ValidatePattern('^0x[0-9A-Fa-f]+$')]
    [string]$RoomGameManager,

    [Parameter(Mandatory = $true, ParameterSetName = 'PushButton')]
    [switch]$PushButton,

    [Parameter(Mandatory = $true, ParameterSetName = 'PushButton')]
    [ValidateRange(0, 65535)]
    [int]$ButtonId,

    [Parameter(ParameterSetName = 'PushButton')]
    [ValidateRange(1, 300)]
    [int]$Repeat = 120,

    [Parameter(ParameterSetName = 'PushButton')]
    [ValidateRange(-2147483648, 4294967295)]
    [long]$Param2 = 0xFFFFFFFF,

    [Parameter(ParameterSetName = 'PushButton')]
    [ValidateRange(-2147483648, 4294967295)]
    [long]$Param3 = 0xFFFFFFFF,

    [Parameter(ParameterSetName = 'PushButton')]
    [ValidatePattern('^0x[0-9A-Fa-f]+$')]
    [string]$TargetCaller = '0x0',

    [Parameter(ParameterSetName = 'PushButton')]
    [Parameter(ParameterSetName = 'Click')]
    [Parameter(ParameterSetName = 'ClickSequence')]
    [Parameter(ParameterSetName = 'QueueGym')]
    [Parameter(ParameterSetName = 'QueueRoom')]
    [ValidateRange(0, 30000)]
    [int]$SettleMs = 500,

    [Parameter(ParameterSetName = 'PushButton')]
    [Parameter(ParameterSetName = 'Click')]
    [Parameter(ParameterSetName = 'ClickSequence')]
    [switch]$Trace

    ,

    [Parameter(Mandatory = $true, ParameterSetName = 'Click')]
    [switch]$Click,

    [Parameter(Mandatory = $true, ParameterSetName = 'Click')]
    [ValidateRange(0.0, 1.0)]
    [double]$XRatio,

    [Parameter(Mandatory = $true, ParameterSetName = 'Click')]
    [ValidateRange(0.0, 1.0)]
    [double]$YRatio,

    [Parameter(ParameterSetName = 'Click')]
    [ValidateRange(0, 2000)]
    [int]$HoverMs = 150,

    [Parameter(ParameterSetName = 'Click')]
    [ValidateRange(1, 2000)]
    [int]$HoldMs = 120,

    [Parameter(Mandatory = $true, ParameterSetName = 'ClickSequence')]
    [switch]$ClickSequence,

    [Parameter(Mandatory = $true, ParameterSetName = 'ClickSequence')]
    [ValidateRange(0.0, 1.0)]
    [double]$X1Ratio,

    [Parameter(Mandatory = $true, ParameterSetName = 'ClickSequence')]
    [ValidateRange(0.0, 1.0)]
    [double]$Y1Ratio,

    [Parameter(Mandatory = $true, ParameterSetName = 'ClickSequence')]
    [ValidateRange(0.0, 1.0)]
    [double]$X2Ratio,

    [Parameter(Mandatory = $true, ParameterSetName = 'ClickSequence')]
    [ValidateRange(0.0, 1.0)]
    [double]$Y2Ratio,

    [Parameter(ParameterSetName = 'ClickSequence')]
    [ValidateRange(0, 2000)]
    [int]$SequenceHoverMs = 250,

    [Parameter(ParameterSetName = 'ClickSequence')]
    [ValidateRange(1, 2000)]
    [int]$SequenceHoldMs = 160,

    [Parameter(ParameterSetName = 'ClickSequence')]
    [ValidateRange(0, 2000)]
    [int]$InterClickMs = 1000
)

$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$artifactRoot = Join-Path $repoRoot 'artifacts\dynamic-analysis'
$requestPath = Join-Path $artifactRoot 'REQUEST_FRIDA_INPUT.json'
$stamp = Get-Date -Format 'yyyyMMdd_HHmmss_fff'
$resultPath = Join-Path $artifactRoot "FRIDA_ELEVATED_${stamp}.txt"
$target = Get-Process -Id $ProcessId -ErrorAction Stop

if (Test-Path -LiteralPath $requestPath) {
    throw 'Another Frida scheduled-task request is already pending'
}

if ($PSCmdlet.ParameterSetName -eq 'Observe') {
    $request = [ordered]@{
        pid = $ProcessId
        process_start_utc = $target.StartTime.ToUniversalTime().ToString('o')
        action = 'observe'
        seconds = $Seconds
        result = $resultPath
    }
}
elseif ($PSCmdlet.ParameterSetName -eq 'QueueGym') {
    $request = [ordered]@{
        pid = $ProcessId
        process_start_utc = $target.StartTime.ToUniversalTime().ToString('o')
        action = 'queue_gym'
        gm = $GameManager
        settle_ms = [Math]::Max(1000, $SettleMs)
        result = $resultPath
    }
}
elseif ($PSCmdlet.ParameterSetName -eq 'QueueRoom') {
    $request = [ordered]@{
        pid = $ProcessId
        process_start_utc = $target.StartTime.ToUniversalTime().ToString('o')
        action = 'queue_room'
        room = $Room
        gm = $RoomGameManager
        settle_ms = [Math]::Max(1000, $SettleMs)
        result = $resultPath
    }
}
elseif ($PSCmdlet.ParameterSetName -eq 'PushButton') {
    $request = [ordered]@{
        pid = $ProcessId
        process_start_utc = $target.StartTime.ToUniversalTime().ToString('o')
        action = 'push_button'
        button_id = $ButtonId
        param2 = $Param2
        param3 = $Param3
        repeat = $Repeat
        target_caller = $TargetCaller
        settle_ms = $SettleMs
        observe = [bool]$Trace
        result = $resultPath
    }
}
elseif ($PSCmdlet.ParameterSetName -eq 'Click') {
    $request = [ordered]@{
        pid = $ProcessId
        process_start_utc = $target.StartTime.ToUniversalTime().ToString('o')
        action = 'click'
        x_ratio = $XRatio
        y_ratio = $YRatio
        hover_ms = $HoverMs
        hold_ms = $HoldMs
        settle_ms = $SettleMs
        observe = [bool]$Trace
        result = $resultPath
    }
}
else {
    $request = [ordered]@{
        pid = $ProcessId
        process_start_utc = $target.StartTime.ToUniversalTime().ToString('o')
        action = 'click_sequence'
        x1_ratio = $X1Ratio
        y1_ratio = $Y1Ratio
        x2_ratio = $X2Ratio
        y2_ratio = $Y2Ratio
        hover_ms = $SequenceHoverMs
        hold_ms = $SequenceHoldMs
        inter_click_ms = $InterClickMs
        settle_ms = $SettleMs
        observe = [bool]$Trace
        result = $resultPath
    }
}

$request | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $requestPath -Encoding UTF8

try {
    $launchOutput = & schtasks.exe /Run /TN 'Azrok-Plaza-Stop' 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "Could not start Azrok-Plaza-Stop: $launchOutput"
    }

    $deadline = (Get-Date).AddSeconds(45)
    while ((Test-Path -LiteralPath $requestPath) -and (Get-Date) -lt $deadline) {
        Start-Sleep -Milliseconds 200
    }
    if (Test-Path -LiteralPath $requestPath) {
        throw 'Timed out waiting for the elevated Frida request to finish'
    }
    if (-not (Test-Path -LiteralPath $resultPath)) {
        throw 'Elevated Frida request finished without a result file'
    }
    Get-Content -LiteralPath $resultPath
}
catch {
    Remove-Item -LiteralPath $requestPath -Force -ErrorAction SilentlyContinue
    throw
}
