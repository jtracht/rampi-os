# Mutating integration checks are restricted to disposable GitHub-hosted VMs.
[CmdletBinding()]
param()
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
if ($env:GITHUB_ACTIONS -ne 'true' -or $env:RUNNER_ENVIRONMENT -ne 'github-hosted' -or
    $env:GITHUB_REPOSITORY -ne 'jtracht/rampi-os' -or $env:ImageOS -notlike 'win*') {
    throw 'This integration test requires the disposable Rampi GitHub Windows runner.'
}
$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
if (-not ([Security.Principal.WindowsPrincipal]$identity).IsInRole(
    [Security.Principal.WindowsBuiltInRole]::Administrator)) { throw 'Elevated runner required.' }
$installer = Join-Path $PSScriptRoot '../../installer/windows/setup.ps1'
$rdpKey = 'HKLM:\System\CurrentControlSet\Control\Terminal Server'
$before = (Get-ItemProperty $rdpKey).fDenyTSConnections
& $installer -AllowNonTarget -EnableOpenSsh -EnableRdp -WhatIf | Out-Null
if ((Get-ItemProperty $rdpKey).fDenyTSConnections -ne $before) { throw 'WhatIf changed RDP.' }

# Use the actual installed Windows capability and services, without external hosts.
& $installer -AllowNonTarget -EnableOpenSsh -EnableRdp | Out-Null
$ssh = Get-Service sshd
if ($ssh.Status -ne 'Running') { throw 'Official OpenSSH service did not start.' }
$configuration = Join-Path $env:ProgramData 'ssh/sshd_config'
$hashBefore = (Get-FileHash -LiteralPath $configuration -Algorithm SHA256).Hash
& $installer -AllowNonTarget -EnableOpenSsh -EnableRdp | Out-Null
if ((Get-FileHash -LiteralPath $configuration -Algorithm SHA256).Hash -ne $hashBefore) {
    throw 'Repeated installation changed existing SSH configuration.'
}
if ((Get-ItemProperty $rdpKey).fDenyTSConnections -ne 0) { throw 'RDP remains disabled.' }
$nla = (Get-ItemProperty "$rdpKey\WinStations\RDP-Tcp").UserAuthentication
if ($nla -ne 1) { throw 'RDP requires NLA.' }
$firewall = Get-NetFirewallRule -Name 'Rampi-RDP-Private'
if ($firewall.Profile.ToString() -ne 'Private') { throw 'RDP firewall scope changed.' }
$server = Join-Path $env:WINDIR 'System32/OpenSSH/sshd.exe'
& $server -t
if ($LASTEXITCODE -ne 0) { throw 'Official SSH configuration validation failed.' }
$output = Join-Path $env:GITHUB_WORKSPACE 'artifacts/windows-components'
New-Item -ItemType Directory -Force $output | Out-Null
[ordered]@{
    schema_version = 1
    revision = $env:GITHUB_SHA
    installer_sha256 = (Get-FileHash $installer -Algorithm SHA256).Hash.ToLowerInvariant()
    runner = $env:ImageOS
    what_if_preserved = $true
    real_openssh_service_running = $true
    repeat_preserved_configuration = $true
    official_sshd_configuration_valid = $true
    rdp_enabled = $true
    nla_required = $true
    private_firewall_only = $true
    authentication_acceptance = $false
    complete_product_acceptance = $false
} | ConvertTo-Json | Set-Content -Encoding utf8 (Join-Path $output 'components.json')
