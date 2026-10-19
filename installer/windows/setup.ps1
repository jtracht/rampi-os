[CmdletBinding(SupportsShouldProcess)]
param(
    [switch]$Install,
    [switch]$InstallMissing,
    [switch]$EnableOpenSsh,
    [switch]$EnableRdp,
    [switch]$AllowNonTarget,
    [string]$SourceRoot = (Split-Path -Parent (Split-Path -Parent $PSScriptRoot))
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$os = Get-CimInstance Win32_OperatingSystem
$edition = (Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion').EditionID
if (-not $AllowNonTarget -and ([int]$os.BuildNumber -lt 22000 -or $edition -ne 'Professional')) {
    throw 'Rampi unterstützt zunächst Windows 11 Pro. Andere Editionen sind nicht validiert.'
}
$names = @('ssh','sshd','codex','claude','agy','psmux','tailscale','wireguard','sunshine')
$programs = @{}
foreach ($name in $names) {
    $found = Get-Command $name -ErrorAction SilentlyContinue
    $programs[$name] = if ($found) { $found.Source } else { $null }
}
[PSCustomObject]@{System=$os.Caption; Build=$os.BuildNumber; Edition=$edition; Programs=$programs} |
    ConvertTo-Json -Depth 4 | Write-Output
if ($InstallMissing -and -not $programs['psmux']) {
    $winget = Get-Command winget.exe -ErrorAction Stop
    if ($PSCmdlet.ShouldProcess('psmux 3.4.0', 'Mit WinGet aus offizieller Quelle installieren')) {
        & $winget.Source install --id marlocarlo.psmux --exact --version 3.4.0 --source winget
        if ($LASTEXITCODE -ne 0) { throw 'psmux-Installation fehlgeschlagen.' }
    }
}
if ($EnableOpenSsh) {
    $admin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
        [Security.Principal.WindowsBuiltInRole]::Administrator)
    if (-not $admin) { throw 'OpenSSH-Einrichtung benötigt eine erhöhte PowerShell.' }
    if ($PSCmdlet.ShouldProcess('Windows OpenSSH Server / TCP 22', 'Installieren und aktivieren')) {
        $capability = Get-WindowsCapability -Online -Name 'OpenSSH.Server~~~~0.0.1.0'
        if ($capability.State -ne 'Installed') {
            Add-WindowsCapability -Online -Name $capability.Name | Out-Null
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
if ($Install) {
    $target = Join-Path $env:LOCALAPPDATA 'Rampi'
    $source = Join-Path $SourceRoot 'host\windows\rampi-session.ps1'
    if (-not (Test-Path -LiteralPath $source)) { throw "Hostpaket unvollständig: $source" }
    if ($PSCmdlet.ShouldProcess($target, 'Persönlichen Rampi-Sitzungsadapter installieren')) {
        New-Item -ItemType Directory -Path $target -Force | Out-Null
        $sid = [Security.Principal.WindowsIdentity]::GetCurrent().User.Value
        $directoryAcl = [Security.AccessControl.DirectorySecurity]::new()
        $directoryAcl.SetAccessRuleProtection($true,$false)
        $directoryAcl.SetOwner([Security.Principal.SecurityIdentifier]::new($sid))
        $fileAcl = [Security.AccessControl.FileSecurity]::new()
        $fileAcl.SetAccessRuleProtection($true,$false)
        $fileAcl.SetOwner([Security.Principal.SecurityIdentifier]::new($sid))
        foreach ($identitySid in @($sid,'S-1-5-18')) {
            $identityReference = [Security.Principal.SecurityIdentifier]::new($identitySid)
            $directoryAcl.AddAccessRule([Security.AccessControl.FileSystemAccessRule]::new(
                $identityReference, [Security.AccessControl.FileSystemRights]::FullControl,
                [Security.AccessControl.InheritanceFlags]'ContainerInherit,ObjectInherit',
                [Security.AccessControl.PropagationFlags]::None,
                [Security.AccessControl.AccessControlType]::Allow))
            $fileAcl.AddAccessRule([Security.AccessControl.FileSystemAccessRule]::new(
                $identityReference, [Security.AccessControl.FileSystemRights]::FullControl,
                [Security.AccessControl.AccessControlType]::Allow))
        }
        Set-Acl -LiteralPath $target -AclObject $directoryAcl
        $adapter = Join-Path $target 'rampi-session.ps1'
        Copy-Item -LiteralPath $source -Destination $adapter -Force
        Set-Acl -LiteralPath $adapter -AclObject $fileAcl
    }
}
Write-Output 'Audit beendet. Anbieter-CLIs, Sunshine und VPN bleiben unter ihren offiziellen Installationswegen.'
