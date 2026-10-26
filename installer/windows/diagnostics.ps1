[CmdletBinding()]
param()
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$items = @{}
foreach ($name in @('ssh','sshd','tailscale','wireguard','sunshine')) {
    $found = Get-Command $name -ErrorAction SilentlyContinue
    $items[$name] = if ($found) { $found.Source } else { $null }
}
$services = @(Get-Service sshd,TermService,Tailscale,SunshineService -ErrorAction SilentlyContinue |
    Select-Object Name,Status,StartType)
[PSCustomObject]@{Programs=$items; Services=$services} | ConvertTo-Json -Depth 5
