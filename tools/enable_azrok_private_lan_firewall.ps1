<#
  Permit only the private Azrok browser frontend on the explicit RFC1918 LAN.

  Run this script once from an elevated PowerShell.  It never creates a public
  listener: the process bind remains <lan-ip> and the firewall source
  range remains <lan-ip>/24.
#>
[CmdletBinding(SupportsShouldProcess = $true)]
param()

$ErrorActionPreference = 'Stop'
$bindAddress = '<lan-ip>'
$remoteSubnet = '<lan-ip>/24'
$rules = @(
    @{
        Name = 'Azrok Private LAN HTTPS 8765'
        Program = '<home>\AppData\Local\Programs\Python\Python311\python.exe'
        Port = 8765
    },
    @{
        Name = 'Azrok Private LAN WSS 9201'
        Program = '<home>\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
        Port = 9201
    }
)

$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = [Security.Principal.WindowsPrincipal]::new($identity)
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw 'Administrator elevation is required to create the two private firewall rules.'
}

foreach ($rule in $rules) {
    if (-not (Test-Path -LiteralPath $rule.Program)) {
        throw "Expected Azrok frontend program does not exist: $($rule.Program)"
    }
    if ($PSCmdlet.ShouldProcess($rule.Name, 'Create private inbound allow rule')) {
        Get-NetFirewallRule -DisplayName $rule.Name -ErrorAction SilentlyContinue |
            Remove-NetFirewallRule -ErrorAction Stop
        New-NetFirewallRule `
            -DisplayName $rule.Name `
            -Direction Inbound `
            -Action Allow `
            -Profile Private `
            -Protocol TCP `
            -LocalAddress $bindAddress `
            -LocalPort $rule.Port `
            -RemoteAddress $remoteSubnet `
            -Program $rule.Program `
            -EdgeTraversalPolicy Block | Out-Null
    }
}

Get-NetFirewallRule -DisplayName $rules.Name |
    Get-NetFirewallPortFilter |
    Select-Object InstanceID, Protocol, LocalPort
