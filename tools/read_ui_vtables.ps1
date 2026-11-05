param(
    [Parameter(Mandatory = $true)]
    [int]$ProcessId,

    [uint32]$GameManager = 0
)

$source = @'
using System;
using System.Runtime.InteropServices;

public static class ReadOnlyProcessMemory
{
    [DllImport("kernel32.dll", SetLastError = true)]
    public static extern IntPtr OpenProcess(uint access, bool inherit, int processId);

    [DllImport("kernel32.dll", SetLastError = true)]
    public static extern bool ReadProcessMemory(
        IntPtr process,
        IntPtr address,
        byte[] buffer,
        int size,
        out IntPtr bytesRead);

    [DllImport("kernel32.dll")]
    public static extern bool CloseHandle(IntPtr handle);

    public static uint ReadUInt32(IntPtr process, uint address)
    {
        byte[] buffer = new byte[4];
        IntPtr bytesRead;
        bool ok = ReadProcessMemory(process, (IntPtr)(long)address, buffer, 4, out bytesRead);
        if (!ok || bytesRead.ToInt64() != 4)
        {
            throw new InvalidOperationException(
                "ReadProcessMemory failed at 0x" + address.ToString("X8") +
                "; Win32Error=" + Marshal.GetLastWin32Error());
        }
        return BitConverter.ToUInt32(buffer, 0);
    }
}
'@

Add-Type -TypeDefinition $source

# PROCESS_QUERY_INFORMATION | PROCESS_VM_READ. No write/operation/debug rights.
$process = [ReadOnlyProcessMemory]::OpenProcess(0x0410, $false, $ProcessId)
if ($process -eq [IntPtr]::Zero) {
    throw "OpenProcess failed; Win32Error=$([Runtime.InteropServices.Marshal]::GetLastWin32Error())"
}

try {
    $gmGlobal = [uint32]0x006E8430
    $gm = if ($GameManager) {
        $GameManager
    }
    else {
        [ReadOnlyProcessMemory]::ReadUInt32($process, $gmGlobal)
    }
    $uiRoot = $gm + 0x4A78F
    $definitions = @(
        [pscustomobject]@{ Name = 'CPopupStatus';    Offset = 0x716; Expected = 0x006ADA34 },
        [pscustomobject]@{ Name = 'CPopupAzronInfo'; Offset = 0x004; Expected = 0x006AE3C4 },
        [pscustomobject]@{ Name = 'CPopupCalendar';  Offset = 0x641; Expected = 0x006A7D6C },
        [pscustomobject]@{ Name = 'CPopupStateList'; Offset = 0x45E; Expected = 0x006AD970 }
    )

    $objects = foreach ($definition in $definitions) {
        $objectAddress = $uiRoot + $definition.Offset
        $vptr = [ReadOnlyProcessMemory]::ReadUInt32($process, $objectAddress)
        $slot0C = $null
        $slotReadError = $null
        if ($vptr -ne 0) {
            try {
                $slot0C = [ReadOnlyProcessMemory]::ReadUInt32($process, $vptr + 0x0C)
            }
            catch {
                $slotReadError = $_.Exception.Message
            }
        }
        $firstDwords = foreach ($index in 0..3) {
            '0x{0:X8}' -f [ReadOnlyProcessMemory]::ReadUInt32(
                $process,
                $objectAddress + ($index * 4))
        }

        [pscustomobject]@{
            Name = $definition.Name
            Offset = '0x{0:X3}' -f $definition.Offset
            ObjectAddress = '0x{0:X8}' -f $objectAddress
            Vptr = '0x{0:X8}' -f $vptr
            ExpectedVptr = '0x{0:X8}' -f $definition.Expected
            Match = ($vptr -eq $definition.Expected)
            VtableSlot0C = if ($null -eq $slot0C) { $null } else { '0x{0:X8}' -f $slot0C }
            SlotReadError = $slotReadError
            FirstFourDwords = $firstDwords
        }
    }

    $childDefinitions = @()
    $childDefinitions += [pscustomobject]@{ Name = 'status_74'; Offset = 0x716 + 0x74 }
    foreach ($index in 0..5) {
        $childDefinitions += [pscustomobject]@{ Name = "status_78_$index"; Offset = 0x716 + 0x78 + ($index * 4) }
        $childDefinitions += [pscustomobject]@{ Name = "status_90_$index"; Offset = 0x716 + 0x90 + ($index * 4) }
    }
    foreach ($offset in @(0x73, 0x77, 0x7B, 0x7F, 0x83, 0x87, 0x8B)) {
        $childDefinitions += [pscustomobject]@{ Name = 'azron_{0:x2}' -f $offset; Offset = 0x004 + $offset }
    }
    foreach ($index in 0..9) {
        $childDefinitions += [pscustomobject]@{ Name = "azron_8f_$index"; Offset = 0x004 + 0x8F + ($index * 4) }
    }
    foreach ($offset in @(0xDF, 0xE3)) {
        $childDefinitions += [pscustomobject]@{ Name = 'azron_{0:x2}' -f $offset; Offset = 0x004 + $offset }
    }
    foreach ($offset in @(0xB2, 0xB6, 0xBA, 0xBE, 0xC2)) {
        $childDefinitions += [pscustomobject]@{ Name = 'calendar_{0:x2}' -f $offset; Offset = 0x641 + $offset }
    }
    $childDefinitions += [pscustomobject]@{ Name = 'state_list_73'; Offset = 0x45E + 0x73 }
    foreach ($row in 0..7) {
        foreach ($column in 0..4) {
            $childDefinitions += [pscustomobject]@{
                Name = "state_list_${row}_${column}"
                Offset = 0x45E + 0x77 + ($row * 0x14) + ($column * 4)
            }
        }
    }

    $children = foreach ($definition in $childDefinitions) {
        $fieldAddress = $uiRoot + $definition.Offset
        $handle = [ReadOnlyProcessMemory]::ReadUInt32($process, $fieldAddress)
        $panelReadable = $false
        $bmap = [uint32]0
        $bmapReadable = $null
        if ($handle) {
            try {
                [void][ReadOnlyProcessMemory]::ReadUInt32($process, $handle)
                $bmap = [ReadOnlyProcessMemory]::ReadUInt32($process, $handle + 0x24)
                $panelReadable = $true
                if ($bmap) {
                    try {
                        [void][ReadOnlyProcessMemory]::ReadUInt32($process, $bmap)
                        $bmapReadable = $true
                    }
                    catch {
                        $bmapReadable = $false
                    }
                }
            }
            catch {
                $panelReadable = $false
            }
        }
        [pscustomobject]@{
            Name = $definition.Name
            RootOffset = '0x{0:X3}' -f $definition.Offset
            FieldAddress = '0x{0:X8}' -f $fieldAddress
            Handle = '0x{0:X8}' -f $handle
            PanelReadable = $panelReadable
            Bmap = '0x{0:X8}' -f $bmap
            BmapReadable = $bmapReadable
        }
    }

    $nonzeroChildren = @($children | Where-Object { $_.Handle -ne '0x00000000' })
    $nonzeroBmaps = @($nonzeroChildren | Where-Object { $_.Bmap -ne '0x00000000' })
    $childSummary = [pscustomobject]@{
        Total = $children.Count
        Zero = @($children | Where-Object { $_.Handle -eq '0x00000000' }).Count
        Nonzero = $nonzeroChildren.Count
        DistinctNonzeroHandles = @($nonzeroChildren.Handle | Sort-Object -Unique).Count
        ReadablePanels = @($nonzeroChildren | Where-Object { $_.PanelReadable }).Count
        NonzeroBmaps = $nonzeroBmaps.Count
        DistinctNonzeroBmaps = @($nonzeroBmaps.Bmap | Sort-Object -Unique).Count
        ReadableNonzeroBmaps = @($nonzeroBmaps | Where-Object { $_.BmapReadable }).Count
    }

    [pscustomobject]@{
        ProcessId = $ProcessId
        GameManagerGlobal = '0x{0:X8}' -f $gmGlobal
        GameManagerSource = if ($GameManager) { 'explicit verified CGameManager' } else { 'legacy global value' }
        GameManager = '0x{0:X8}' -f $gm
        SceneState31796 = '0x{0:X8}' -f [ReadOnlyProcessMemory]::ReadUInt32($process, $gm + 0x31796)
        UiRoot = '0x{0:X8}' -f $uiRoot
        Objects = $objects
        CleanupChildSummary = $childSummary
        CleanupChildren = $children
    } | ConvertTo-Json -Depth 6
}
finally {
    [ReadOnlyProcessMemory]::CloseHandle($process) | Out-Null
}
