[CmdletBinding(SupportsShouldProcess)]
param(
    [switch]$EnableOpenSsh,
    [switch]$EnableRdp,
    [switch]$AllowNonTarget
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$os = Get-CimInstance Win32_OperatingSystem
$edition = (Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion').EditionID
if (-not $AllowNonTarget -and ([int]$os.BuildNumber -lt 22000 -or $edition -ne 'Professional')) {
    throw 'Rampi unterstützt zunächst Windows 11 Pro. Andere Editionen sind nicht validiert.'
}
$names = @('ssh','sshd','tailscale','wireguard','sunshine')
$programs = @{}
foreach ($name in $names) {
    $found = Get-Command $name -ErrorAction SilentlyContinue
    $programs[$name] = if ($found) { $found.Source } else { $null }
}
[PSCustomObject]@{System=$os.Caption; Build=$os.BuildNumber; Edition=$edition; Programs=$programs} |
    ConvertTo-Json -Depth 4 | Write-Output
if ($EnableOpenSsh) {
    $admin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
        [Security.Principal.WindowsBuiltInRole]::Administrator)
    if (-not $admin) { throw 'OpenSSH-Einrichtung benötigt eine erhöhte PowerShell.' }
    if ($PSCmdlet.ShouldProcess('Windows OpenSSH Server / TCP 22', 'Installieren und aktivieren')) {
        if (-not (Get-Service sshd -ErrorAction SilentlyContinue)) {
            $capability = Get-WindowsCapability -Online -Name 'OpenSSH.Server~~~~0.0.1.0'
            if ($capability.State -ne 'Installed') {
                Add-WindowsCapability -Online -Name $capability.Name | Out-Null
            }
        }
        Set-Service sshd -StartupType Automatic
        Start-Service sshd
        # Windows capability installation normally owns this rule; preserve existing rules.
        if (-not (Get-NetFirewallRule -Name 'OpenSSH-Server-In-TCP' -ErrorAction SilentlyContinue)) {
            New-NetFirewallRule -Name 'OpenSSH-Server-In-TCP' -DisplayName 'OpenSSH Server (sshd)' `
                -Direction Inbound -Protocol TCP -LocalPort 22 -Action Allow -Profile Private | Out-Null
        }
    }
}
if ($EnableRdp -and $PSCmdlet.ShouldProcess('Microsoft RDP', 'RDP mit NLA aktivieren')) {
    Set-ItemProperty 'HKLM:\System\CurrentControlSet\Control\Terminal Server' -Name fDenyTSConnections -Value 0
    Set-ItemProperty 'HKLM:\System\CurrentControlSet\Control\Terminal Server\WinStations\RDP-Tcp' `
        -Name UserAuthentication -Value 1
    # Do not enable the whole localized Remote Desktop firewall group on every interface.
    if (-not (Get-NetFirewallRule -Name 'Rampi-RDP-Private' -ErrorAction SilentlyContinue)) {
        New-NetFirewallRule -Name 'Rampi-RDP-Private' -DisplayName 'Rampi RDP (Private)' `
            -Direction Inbound -Protocol TCP -LocalPort 3389 -Action Allow -Profile Private | Out-Null
    }
}
Write-Output 'Audit beendet. RDP verwendet den vorhandenen Windows-Dienst. Sunshine und VPN bleiben unter ihren offiziellen Installationswegen.'
