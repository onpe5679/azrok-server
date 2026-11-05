param(
    [string]$SpaceName = "Lobby",
    [string]$CharacterName = "",
    [int]$UiTimeoutSeconds = 45,
    [int]$AttachTimeoutSeconds = 300,
    [switch]$SkipFallback,
    [switch]$PostLoadConfirm,
    [double]$PostLoadConfirmWaitSeconds = 6.0,
    [switch]$KeepAlive
)

$ErrorActionPreference = "Stop"

$workspace = Split-Path -Parent $PSScriptRoot
$artifactDir = Join-Path $workspace "artifacts\ui-probes"
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"

New-Item -ItemType Directory -Path $artifactDir -Force | Out-Null

$serverOut = Join-Path $artifactDir ("cycle_{0}.server.stdout.log" -f $timestamp)
$serverErr = Join-Path $artifactDir ("cycle_{0}.server.stderr.log" -f $timestamp)
$uiOut = Join-Path $artifactDir ("cycle_{0}.ui.stdout.log" -f $timestamp)
$uiErr = Join-Path $artifactDir ("cycle_{0}.ui.stderr.log" -f $timestamp)
$attachOut = Join-Path $artifactDir ("cycle_{0}.attach.stdout.log" -f $timestamp)
$attachErr = Join-Path $artifactDir ("cycle_{0}.attach.stderr.log" -f $timestamp)
$attachLog = Join-Path $artifactDir ("cycle_{0}.attach.log" -f $timestamp)
$eventLog = Join-Path $artifactDir ("cycle_{0}.event.log" -f $timestamp)
$finalCapture = Join-Path $artifactDir ("cycle_{0}.final.bmp" -f $timestamp)
$postConfirmCapture = Join-Path $artifactDir ("cycle_{0}.post_confirm.bmp" -f $timestamp)

$server = $null
$attach = $null
$ui = $null
$leaveRunning = $false

function Stop-TaskProcesses {
    Get-CimInstance Win32_Process |
        Where-Object {
            ($_.Name -match '^(python|powershell)(?:\.exe)?$') -and
            $_.CommandLine -and
            (
                $_.CommandLine -match 'azrok_server\.py' -or
                $_.CommandLine -match 'auto_azrok_ui\.py' -or
                $_.CommandLine -match 'attach_azrok_debugger\.py'
            )
        } |
        ForEach-Object {
            try { Stop-Process -Id $_.ProcessId -Force -ErrorAction Stop } catch {}
        }

    Get-Process Azrok -ErrorAction SilentlyContinue | ForEach-Object {
        try { Stop-Process -Id $_.Id -Force -ErrorAction Stop } catch {}
    }
}

function Wait-ForAzrokProcess {
    param(
        [int]$TimeoutSeconds = 60,
        [datetime]$StartedAfter = [datetime]::MinValue
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        $proc = Get-Process Azrok -ErrorAction SilentlyContinue |
            Where-Object { $_.StartTime -ge $StartedAfter } |
            Sort-Object StartTime -Descending |
            Select-Object -First 1
        if ($proc) { return $proc }
        Start-Sleep -Milliseconds 500
    }
    throw "Azrok.exe did not start"
}

function Wait-ForCharacterCreatePacket {
    param([int]$TimeoutSeconds = 25)

    $packetLog = Join-Path $workspace "packets_log.txt"
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        if (Test-Path $packetLog) {
            $text = Get-Content $packetLog -Raw -ErrorAction SilentlyContinue
            if ($text -match 'opcode=0x0004') { return $true }
        }
        Start-Sleep -Seconds 1
    }
    return $false
}

function Run-FallbackCreateFlow {
    param([int]$GamePid, [string]$NameToUse)

    python .\tools\auto_azrok_ui.py --pid $GamePid click-create 2 | Out-Null
    Start-Sleep -Milliseconds 900
    python .\tools\auto_azrok_ui.py --pid $GamePid click-rel 0.43 0.46 | Out-Null
    Start-Sleep -Milliseconds 200
    if ($NameToUse) {
        python .\tools\auto_azrok_ui.py --pid $GamePid text $NameToUse | Out-Null
        Start-Sleep -Milliseconds 200
    }
    python .\tools\auto_azrok_ui.py --pid $GamePid click-rel 0.42 0.56 | Out-Null
}

function Save-LatestAppError {
    $event = $null
    try {
        $event = Get-WinEvent -FilterHashtable @{
            LogName = "Application"
            ProviderName = "Application Error"
            StartTime = (Get-Date).AddMinutes(-20)
        } -MaxEvents 12 -ErrorAction Stop |
        Where-Object { $_.Message -like '*Azrok.exe*' } |
        Select-Object -First 1
    } catch {
        return
    }

    if ($event) {
        "TimeCreated: $($event.TimeCreated)" | Out-File -FilePath $eventLog -Encoding utf8
        "" | Out-File -FilePath $eventLog -Append -Encoding utf8
        $event.Message | Out-File -FilePath $eventLog -Append -Encoding utf8
    }
}

Push-Location $workspace
try {
    Stop-TaskProcesses
    $azrokLaunchCutoff = Get-Date

    $env:AZROK_SPACE_NAME = $SpaceName
    $server = Start-Process python -ArgumentList "-u", ".\azrok_server.py" `
        -RedirectStandardOutput $serverOut `
        -RedirectStandardError $serverErr `
        -PassThru `
        -WindowStyle Hidden

    $game = Wait-ForAzrokProcess -TimeoutSeconds 90 -StartedAfter $azrokLaunchCutoff

    $attach = Start-Process python -ArgumentList "tools\attach_azrok_debugger.py", "--pid", "$($game.Id)", "--timeout", "$AttachTimeoutSeconds", "--log", $attachLog `
        -RedirectStandardOutput $attachOut `
        -RedirectStandardError $attachErr `
        -PassThru `
        -WindowStyle Hidden

    Start-Sleep -Seconds 1

    $uiArgs = @(
        ".\tools\auto_azrok_ui.py",
        "--pid", "$($game.Id)",
        "--timeout", "$UiTimeoutSeconds",
        "create-flow",
        "--move-top-left",
        "--slot", "1",
        "--candidate", "2",
        "--wait-char-screen-seconds", "25",
        "--settle-seconds", "1.0",
        "--slot-repeat", "2",
        "--post-slot-seconds", "0.7",
        "--post-create-seconds", "0.9",
        "--create-retry-count", "4"
    )
    if ($CharacterName) {
        $uiArgs += @("--name", $CharacterName)
    }

    $ui = Start-Process python -ArgumentList $uiArgs `
        -RedirectStandardOutput $uiOut `
        -RedirectStandardError $uiErr `
        -PassThru `
        -WindowStyle Hidden

    try { Wait-Process -Id $ui.Id -Timeout 120 } catch {}

    $sentCreate = Wait-ForCharacterCreatePacket -TimeoutSeconds 25
    if ((-not $sentCreate) -and (-not $SkipFallback)) {
        Run-FallbackCreateFlow -Pid $game.Id -NameToUse $CharacterName
    }

    try { Wait-Process -Id $attach.Id -Timeout ($AttachTimeoutSeconds + 30) } catch {}

    if (Get-Process Azrok -ErrorAction SilentlyContinue) {
        if ($PostLoadConfirm) {
            try {
                python .\tools\auto_azrok_ui.py --pid $game.Id --timeout 10 click-popup-confirm --wait-seconds $PostLoadConfirmWaitSeconds |
                    Out-File -FilePath $uiOut -Append -Encoding utf8
            } catch {
                $_ | Out-File -FilePath $uiErr -Append -Encoding utf8
            }
            Start-Sleep -Seconds 1
            try { python .\tools\auto_azrok_ui.py --pid $game.Id capture --client $postConfirmCapture | Out-Null } catch {}
        }
        try { python .\tools\auto_azrok_ui.py --pid $game.Id capture --client $finalCapture | Out-Null } catch {}
    }

    Start-Sleep -Seconds 2
    Save-LatestAppError
    $leaveRunning = $KeepAlive -and [bool](Get-Process Azrok -ErrorAction SilentlyContinue)

    Write-Output ("RUN_TS={0}" -f $timestamp)
    Write-Output ("SERVER_STDOUT={0}" -f $serverOut)
    Write-Output ("SERVER_STDERR={0}" -f $serverErr)
    Write-Output ("UI_STDOUT={0}" -f $uiOut)
    Write-Output ("UI_STDERR={0}" -f $uiErr)
    Write-Output ("ATTACH_LOG={0}" -f $attachLog)
    Write-Output ("ATTACH_STDOUT={0}" -f $attachOut)
    Write-Output ("ATTACH_STDERR={0}" -f $attachErr)
    Write-Output ("EVENT_LOG={0}" -f $eventLog)
    Write-Output ("FINAL_CAPTURE={0}" -f $finalCapture)
    if (Test-Path $postConfirmCapture) {
        Write-Output ("POST_CONFIRM_CAPTURE={0}" -f $postConfirmCapture)
    }
    Write-Output ("KEEP_ALIVE={0}" -f ([int]$leaveRunning))
    Write-Output "--- SERVER TAIL ---"
    if (Test-Path $serverOut) { Get-Content $serverOut -Tail 160 }
    Write-Output "--- UI TAIL ---"
    if (Test-Path $uiOut) { Get-Content $uiOut -Tail 120 }
    Write-Output "--- ATTACH TAIL ---"
    if (Test-Path $attachLog) { Get-Content $attachLog -Tail 160 }
    Write-Output "--- EVENT TAIL ---"
    if (Test-Path $eventLog) { Get-Content $eventLog -Tail 80 }
}
finally {
    Pop-Location
    if (-not $leaveRunning) {
        Stop-TaskProcesses
    }
}
