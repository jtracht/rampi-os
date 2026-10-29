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
$edition = (Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion').EditionID
if ($edition -eq 'Professional') { throw 'This non-target acceptance fixture expects Windows Server.' }
$rejectedEdition = $false
try { & $installer | Out-Null } catch {
    if ($_.Exception.Message -notlike 'Rampi unterstützt zunächst Windows 11 Pro.*') { throw }
    $rejectedEdition = $true
}
if (-not $rejectedEdition) { throw 'Default Windows edition restriction was bypassed.' }
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

# Real standard-user authentication, including a rejected other user's key.
# Userenv creates genuine profiles; no simulated authentication or home directories.
Add-Type @'
using System;
using System.Text;
using System.Runtime.InteropServices;
public static class RampiCiProfile {
    [DllImport("userenv.dll", CharSet=CharSet.Unicode)]
    public static extern int CreateProfile(string sid, string name, [Out] StringBuilder path, uint length);
}
'@
$fixtureRoot = Join-Path $env:RUNNER_TEMP ('rampi-ssh-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory $fixtureRoot | Out-Null
$sshRoot = Join-Path $env:WINDIR 'System32/OpenSSH'
$accounts = @()
$originalConfiguration = [IO.File]::ReadAllBytes($configuration)
function Set-PrivateFixtureAcl([string]$Path, [Security.Principal.SecurityIdentifier]$Owner) {
    $acl = Get-Acl -LiteralPath $Path
    $acl.SetAccessRuleProtection($true, $false)
    foreach ($rule in @($acl.Access)) { $acl.RemoveAccessRuleSpecific($rule) }
    $acl.SetOwner($Owner)
    foreach ($sid in @($Owner.Value, 'S-1-5-18', 'S-1-5-32-544') | Select-Object -Unique) {
        $accountSid = [Security.Principal.SecurityIdentifier]::new($sid)
        $acl.AddAccessRule([Security.AccessControl.FileSystemAccessRule]::new(
            $accountSid, 'FullControl', 'Allow'))
    }
    Set-Acl -LiteralPath $Path -AclObject $acl
}
function Invoke-FixtureSsh([string]$Name, [string]$Key, [string]$Command) {
    $start = [Diagnostics.ProcessStartInfo]::new((Join-Path $sshRoot 'ssh.exe'))
    $start.UseShellExecute = $false
    $start.RedirectStandardOutput = $true
    $start.RedirectStandardError = $true
    foreach ($argument in @('-F', (Join-Path $fixtureRoot 'client.conf'), '-p', '22422',
        '-o', 'BatchMode=yes', '-o', 'IdentitiesOnly=yes', '-o', 'IdentityAgent=none',
        '-o', 'StrictHostKeyChecking=yes', '-o', 'ConnectTimeout=10',
        '-o', ('UserKnownHostsFile=' + (Join-Path $fixtureRoot 'known_hosts')),
        '-i', $Key, "$Name@127.0.0.1", $Command)) { $start.ArgumentList.Add($argument) }
    $process = [Diagnostics.Process]::Start($start)
    $stdout = $process.StandardOutput.ReadToEndAsync()
    $stderr = $process.StandardError.ReadToEndAsync()
    if (-not $process.WaitForExit(45000)) {
        $process.Kill($true)
        throw 'Native SSH authentication timed out.'
    }
    [pscustomobject]@{Code=$process.ExitCode; Output=$stdout.GetAwaiter().GetResult(); Error=$stderr.GetAwaiter().GetResult()}
}
function Find-FixtureBadPassword([string]$UserName, [datetime]$Since) {
    foreach ($event in @(Get-WinEvent -FilterHashtable @{LogName='Security'; Id=4625; StartTime=$Since} -ErrorAction SilentlyContinue)) {
        $xml = [xml]$event.ToXml()
        $fields = @{}
        foreach ($node in $xml.Event.EventData.Data) { $fields[$node.GetAttribute('Name')] = $node.InnerText }
        if ($fields['TargetUserName'] -eq $UserName -and $fields['Status'] -eq '0xc000006d' -and
            $fields['SubStatus'] -eq '0xc000006a' -and $fields['LogonType'] -in @('3','10')) {
            return [pscustomobject]@{EventId=4625; RecordId=$event.RecordId; Status=$fields['Status']; SubStatus=$fields['SubStatus']; LogonType=[int]$fields['LogonType']}
        }
    }
    return $null
}
function Invoke-FixtureRdp([string]$ExpectedRejectedUser = '') {
    $start = [Diagnostics.ProcessStartInfo]::new("$env:WINDIR/System32/WindowsPowerShell/v1.0/powershell.exe")
    $start.UseShellExecute = $false
    $start.RedirectStandardOutput = $true
    $start.RedirectStandardError = $true
    foreach ($argument in @('-NoProfile', '-NonInteractive', '-STA', '-File',
        (Join-Path $PSScriptRoot 'rdp-client-ci.ps1'))) { $start.ArgumentList.Add($argument) }
    $since = Get-Date
    $process = [Diagnostics.Process]::Start($start)
    $stdout = $process.StandardOutput.ReadToEndAsync()
    $stderr = $process.StandardError.ReadToEndAsync()
    $timer = [Diagnostics.Stopwatch]::StartNew()
    $denial = $null
    $cancelledAfterDenial = $false
    while (-not $process.WaitForExit(250)) {
        if ($ExpectedRejectedUser) { $denial = Find-FixtureBadPassword $ExpectedRejectedUser $since }
        if ($denial) {
            # A real, credential-specific server denial is the result. Cancel only
            # this client after observing it; a deadline is never such evidence.
            $process.Kill($true)
            if (-not $process.WaitForExit(5000)) { throw 'Controlled RDP client cancellation did not finish.' }
            $cancelledAfterDenial = $true
            break
        }
        if ($timer.Elapsed.TotalSeconds -ge 90) {
            $process.Kill($true)
            throw 'Native RDP client timed out; no authentication acceptance.'
        }
    }
    if ($ExpectedRejectedUser -and -not $denial) {
        for ($attempt=0; $attempt -lt 10 -and -not $denial; $attempt++) {
            $denial = Find-FixtureBadPassword $ExpectedRejectedUser $since
            if (-not $denial) { Start-Sleep -Milliseconds 200 }
        }
    }
    [pscustomobject]@{Code=$process.ExitCode; Output=$stdout.GetAwaiter().GetResult(); Error=$stderr.GetAwaiter().GetResult(); Denial=$denial; CancelledAfterDenial=$cancelledAfterDenial}
}
try {
    foreach ($index in 1..2) {
        $name = 'rampi' + [guid]::NewGuid().ToString('N').Substring(0,10)
        $password = 'R!a9' + [Convert]::ToBase64String([Security.Cryptography.RandomNumberGenerator]::GetBytes(24))
        Write-Output "::add-mask::$password"
        $user = New-LocalUser -Name $name -Password (ConvertTo-SecureString $password -AsPlainText -Force)
        $path = [Text.StringBuilder]::new(260)
        $accounts += [pscustomobject]@{Name=$name; Sid=$user.SID.Value; Profile=$null; Key=$null; Password=(ConvertTo-SecureString $password -AsPlainText -Force)}
        $result = [RampiCiProfile]::CreateProfile($user.SID.Value, $name, $path, 260)
        if ($result -ne 0) { throw "Native profile creation failed: $result" }
        $accounts[-1].Profile = $path.ToString()
        $key = Join-Path $fixtureRoot "identity-$index"
        & (Join-Path $sshRoot 'ssh-keygen.exe') -q -t ed25519 -N '' -f $key
        if ($LASTEXITCODE -ne 0) { throw 'Native key generation failed.' }
        Set-PrivateFixtureAcl $key $identity.User
        $accounts[-1].Key = $key
        $directory = Join-Path $path.ToString() '.ssh'
        New-Item -ItemType Directory $directory | Out-Null
        $authorized = Join-Path $directory 'authorized_keys'
        [IO.File]::WriteAllText($authorized, [IO.File]::ReadAllText("$key.pub"))
        Set-PrivateFixtureAcl $directory $user.SID
        Set-PrivateFixtureAcl $authorized $user.SID
        $privateFile = Join-Path $path.ToString() 'rampi-private-fixture.txt'
        [IO.File]::WriteAllText($privateFile, "synthetic-user-$index")
        Set-PrivateFixtureAcl $privateFile $user.SID
    }
    $hostKey = Join-Path $env:ProgramData 'ssh/ssh_host_ed25519_key'
    $public = ([IO.File]::ReadAllText("$hostKey.pub").Trim() -split '\s+')[0..1] -join ' '
    [IO.File]::WriteAllText((Join-Path $fixtureRoot 'known_hosts'), "[127.0.0.1]:22422 $public`n")
    [IO.File]::WriteAllText((Join-Path $fixtureRoot 'client.conf'), '')
    $hostPath = $hostKey.Replace('\','/')
    $settings = "Port 22422`nListenAddress 127.0.0.1`nHostKey $hostPath`nPasswordAuthentication no`nPubkeyAuthentication yes`nAuthorizedKeysFile .ssh/authorized_keys`nAllowUsers $($accounts.Name -join ' ')`n"
    Stop-Service sshd
    [IO.File]::WriteAllText($configuration, $settings)
    & $server -t
    if ($LASTEXITCODE -ne 0) { throw 'Loopback fixture configuration invalid.' }
    Start-Service sshd
    foreach ($account in $accounts) {
        $login = Invoke-FixtureSsh $account.Name $account.Key 'whoami /user /fo csv /nh'
        $remoteIdentity = @($login.Output.Trim() | ConvertFrom-Csv -Header Name,Sid)
        if ($login.Code -ne 0 -or $remoteIdentity.Count -ne 1 -or $remoteIdentity[0].Sid -ne $account.Sid) {
            throw "Real standard-user SSH identity check failed: $($login.Error)"
        }
        $other = @($accounts | Where-Object Sid -ne $account.Sid)[0]
        $ownFile = (Join-Path $account.Profile 'rampi-private-fixture.txt').Replace("'", "''")
        $otherFile = (Join-Path $other.Profile 'rampi-private-fixture.txt').Replace("'", "''")
        $command = "`$ErrorActionPreference='Stop'; if (-not [IO.File]::ReadAllText('$ownFile').StartsWith('synthetic-user-')) {exit 3}; try { [IO.File]::ReadAllText('$otherFile') | Out-Null; exit 4 } catch [UnauthorizedAccessException] { Write-Output 'RAMPI_WINDOWS_PRIVATE_PROFILE_OK'; exit 0 }"
        $encoded = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($command))
        $privacy = Invoke-FixtureSsh $account.Name $account.Key "powershell.exe -NoProfile -NonInteractive -EncodedCommand $encoded"
        if ($privacy.Code -ne 0 -or $privacy.Output -notmatch 'RAMPI_WINDOWS_PRIVATE_PROFILE_OK') {
            throw "Actual Windows profile isolation failed: $($privacy.Error)"
        }
    }
    $rejected = Invoke-FixtureSsh $accounts[0].Name $accounts[1].Key 'whoami'
    if ($rejected.Code -ne 255 -or $rejected.Error -notmatch 'Permission denied') {
        throw 'The other user key was not explicitly rejected by OpenSSH.'
    }
    Write-Output 'RAMPI_WINDOWS_SSH_IDENTITIES_AND_PRIVATE_FILES_OK'
    # The client and server are both existing Microsoft components in this VM.
    if ((Get-Service TermService).Status -ne 'Running') {
        throw 'Actual Windows RDP service is not running after installation.'
    }
    $rdp = Get-CimInstance -Namespace root/cimv2/terminalservices -ClassName Win32_TSGeneralSetting -Filter "TerminalName='RDP-tcp'"
    $thumbprint = $rdp.SSLCertificateSHA1Hash
    if (-not $thumbprint) { throw 'Actual RDP listener has no bound server certificate.' }
    $certificate = Get-ChildItem 'Cert:\LocalMachine\Remote Desktop', 'Cert:\LocalMachine\My' |
        Where-Object Thumbprint -eq $thumbprint | Select-Object -First 1
    if (-not $certificate) { throw 'Bound RDP server certificate not found.' }
    Write-Output 'RAMPI_WINDOWS_BOUND_RDP_CERTIFICATE_FOUND'
    # CurrentUser\Root invokes Windows' interactive protected-root confirmation.
    # This elevated, disposable VM can temporarily trust its own existing listener
    # certificate in LocalMachine\Root without a dialog. Restore only our addition.
    $rootStore = [Security.Cryptography.X509Certificates.X509Store]::new('Root', 'LocalMachine')
    $rootStore.Open('ReadWrite')
    $alreadyTrusted = @($rootStore.Certificates | Where-Object Thumbprint -eq $thumbprint).Count -ne 0
    $publicCertificate = [Security.Cryptography.X509Certificates.X509Certificate2]::new($certificate.RawData)
    $auditBackup = Join-Path $fixtureRoot 'audit-policy.csv'
    $auditBackedUp = $false
    try {
        & "$env:WINDIR/System32/auditpol.exe" /backup "/file:$auditBackup" | Out-Null
        if ($LASTEXITCODE -ne 0) { throw 'Cannot preserve disposable VM audit policy.' }
        $auditBackedUp = $true
        & "$env:WINDIR/System32/auditpol.exe" /set /subcategory:Logon /success:enable /failure:enable | Out-Null
        if ($LASTEXITCODE -ne 0) { throw 'Cannot enable actual logon evidence in disposable VM.' }
        if (-not $alreadyTrusted) { $rootStore.Add($publicCertificate) }
        Write-Output 'RAMPI_WINDOWS_OWN_LISTENER_CERTIFICATE_TRUST_READY'
        Add-LocalGroupMember -SID ([Security.Principal.SecurityIdentifier]'S-1-5-32-555') -Member $accounts[0].Name
        Write-Output 'RAMPI_WINDOWS_OWN_RDP_FIXTURE_ACCOUNT_AUTHORIZED'
        $env:RAMPI_CI_RDP_USER = $accounts[0].Name
        $env:RAMPI_CI_RDP_PASSWORD = ([pscredential]::new($accounts[0].Name, $accounts[0].Password)).GetNetworkCredential().Password
        $login = Invoke-FixtureRdp
        if ($login.Code -ne 0 -or $login.Output.Trim() -ne 'login-complete') {
            throw "Actual Microsoft RDP login failed: $($login.Output) $($login.Error)"
        }
        Write-Output 'RAMPI_WINDOWS_MICROSOFT_RDP_LOGIN_COMPLETE'
        $remoteIdentityFound = $false
        foreach ($session in @(Get-CimInstance Win32_LogonSession -Filter 'LogonType=10' -OperationTimeoutSec 15)) {
            $remoteAccounts = @(Get-CimAssociatedInstance -InputObject $session -Association Win32_LoggedOnUser -ResultClassName Win32_Account -OperationTimeoutSec 15)
            if (@($remoteAccounts | Where-Object SID -eq $accounts[0].Sid).Count) {
                $remoteIdentityFound = $true
            }
        }
        if (-not $remoteIdentityFound) { throw 'Actual Windows remote-interactive logon SID not found.' }
        Write-Output 'RAMPI_WINDOWS_RDP_REMOTE_INTERACTIVE_SID_OK'
        $env:RAMPI_CI_RDP_PASSWORD = 'Wrong!' + [guid]::NewGuid().ToString('N')
        Write-Output "::add-mask::$env:RAMPI_CI_RDP_PASSWORD"
        $rejection = Invoke-FixtureRdp $accounts[0].Name
        if (-not $rejection.Denial -or $rejection.Denial.RecordId -le 0 -or $rejection.Output.Trim() -eq 'login-complete') {
            throw "Actual RDP negative authentication did not complete: $($rejection.Output) $($rejection.Error)"
        }
        Write-Output 'RAMPI_WINDOWS_RDP_ACTUAL_BAD_PASSWORD_4625_OK'
    } finally {
        try {
            if ($auditBackedUp) {
                & "$env:WINDIR/System32/auditpol.exe" /restore "/file:$auditBackup" | Out-Null
                if ($LASTEXITCODE -ne 0) { throw 'Cannot restore disposable VM audit policy.' }
            }
        } finally {
            Remove-Item Env:RAMPI_CI_RDP_PASSWORD -ErrorAction SilentlyContinue
            Remove-Item Env:RAMPI_CI_RDP_USER -ErrorAction SilentlyContinue
            if (-not $alreadyTrusted) { $rootStore.Remove($publicCertificate) }
            $rootStore.Close()
        }
    }
} finally {
    Stop-Service sshd -ErrorAction SilentlyContinue
    [IO.File]::WriteAllBytes($configuration, $originalConfiguration)
    Start-Service sshd
    foreach ($account in $accounts) {
        # Only users created by this invocation can enter this collection.
        $current = Get-LocalUser -Name $account.Name -ErrorAction SilentlyContinue
        if ($current -and $current.SID.Value -eq $account.Sid) { Remove-LocalUser -SID $current.SID }
    }
    # The hosted VM is destroyed after the job; private profiles/keys are never uploaded.
}
$output = Join-Path $env:GITHUB_WORKSPACE 'artifacts/windows-components'
New-Item -ItemType Directory -Force $output | Out-Null
[ordered]@{
    schema_version = 1
    revision = $env:GITHUB_SHA
    installer_sha256 = (Get-FileHash $installer -Algorithm SHA256).Hash.ToLowerInvariant()
    test_sha256 = (Get-FileHash $PSCommandPath -Algorithm SHA256).Hash.ToLowerInvariant()
    rdp_test_sha256 = (Get-FileHash (Join-Path $PSScriptRoot 'rdp-client-ci.ps1') -Algorithm SHA256).Hash.ToLowerInvariant()
    runner = $env:ImageOS
    unsupported_edition_rejected_by_default = $true
    what_if_preserved = $true
    real_openssh_service_running = $true
    repeat_preserved_configuration = $true
    official_sshd_configuration_valid = $true
    rdp_enabled = $true
    nla_required = $true
    private_firewall_only = $true
    two_real_standard_user_ssh_logins = $true
    wrong_user_key_rejected = $true
    two_real_private_profile_checks = $true
    microsoft_rdp_login_complete = $true
    microsoft_rdp_remote_interactive_sid = $true
    microsoft_rdp_wrong_password_rejected = $true
    rdp_negative_server_event = $rejection.Denial
    rdp_client_cancelled_after_server_denial = $rejection.CancelledAfterDenial
    authentication_acceptance = $false
    complete_product_acceptance = $false
} | ConvertTo-Json | Set-Content -Encoding utf8 (Join-Path $output 'components.json')
