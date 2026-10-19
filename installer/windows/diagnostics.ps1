[CmdletBinding()]
param()
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$items = @{}
foreach ($name in @('ssh','sshd','codex','claude','agy','psmux','tailscale','wireguard','sunshine')) {
    $found = Get-Command $name -ErrorAction SilentlyContinue
    $items[$name] = if ($found) { $found.Source } else { $null }
}
$services = @(Get-Service sshd,TermService,Tailscale,SunshineService -ErrorAction SilentlyContinue |
    Select-Object Name,Status,StartType)
[PSCustomObject]@{Programs=$items; Services=$services; SessionAdapter=(Test-Path (
    Join-Path $env:LOCALAPPDATA 'Rampi\rampi-session.ps1'))} | ConvertTo-Json -Depth 5
