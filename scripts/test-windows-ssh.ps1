[CmdletBinding()]
param([Parameter(Mandatory)][string]$Psmux)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$PSNativeCommandArgumentPassing = 'Standard'
if ($env:GITHUB_ACTIONS -ne 'true') {
    throw 'This test creates temporary accounts and changes sshd only on a disposable GitHub runner.'
}
$suffix = [Guid]::NewGuid().ToString('N').Substring(0,8)
$users = @("rampia$suffix", "rampib$suffix")
$directory = Join-Path $env:ProgramData "RampiCiTest-$suffix"
$testConfig = Join-Path $directory 'sshd_config'
$taskName = "RampiSshTest-$suffix"
$ready = $false
$namespace = "rampi-ci-$suffix"
$sshd = Join-Path $env:WINDIR 'System32\OpenSSH\sshd.exe'
$createdUsers = @()
$adapterAttempted = $false
$adapterTransport = $null
$ssh = (Get-Command ssh.exe -ErrorAction Stop).Source
$keygen = (Get-Command ssh-keygen.exe -ErrorAction Stop).Source
function Invoke-TestSsh([string]$User, [string]$Script) {
    $encoded = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($Script))
    $output = & $ssh -T -i (Join-Path $directory 'client_key') -p 22222 `
        -o BatchMode=yes -o StrictHostKeyChecking=yes -o ConnectTimeout=15 `
        -o "UserKnownHostsFile=$(Join-Path $directory 'known_hosts')" `
        -l $User 127.0.0.1 powershell.exe -NoLogo -NoProfile -EncodedCommand $encoded 2>&1
    return [PSCustomObject]@{Code=$LASTEXITCODE; Text=($output -join "`n")}
}
try {
    New-Item -ItemType Directory -Path $directory -Force | Out-Null
    Copy-Item -LiteralPath $Psmux -Destination (Join-Path $directory 'psmux.exe')
    & icacls.exe $directory /grant '*S-1-5-11:(OI)(CI)RX' | Out-Null
    foreach ($user in $users) {
        $password = ConvertTo-SecureString ([Guid]::NewGuid().ToString('N') + '!Aa9') -AsPlainText -Force
        $account = New-LocalUser -Name $user -Password $password -PasswordNeverExpires
        $createdUsers += $user
        $credential = [PSCredential]::new("$env:COMPUTERNAME\$user", $password)
        Start-Process -FilePath powershell.exe -Credential $credential -LoadUserProfile `
            -ArgumentList '-NoLogo','-NoProfile','-Command','exit 0' -Wait -WindowStyle Hidden
        $profile = Get-CimInstance Win32_UserProfile | Where-Object SID -eq $account.SID.Value
        if (-not $profile) { throw 'Windows did not create a test user profile.' }
        $sshDir = Join-Path $profile.LocalPath '.ssh'
        New-Item -ItemType Directory -Path $sshDir -Force | Out-Null
        & icacls.exe $sshDir /inheritance:r /grant:r "*$($account.SID.Value):(OI)(CI)F" '*S-1-5-18:(OI)(CI)F' '*S-1-5-32-544:(OI)(CI)F' | Out-Null
        & icacls.exe $sshDir /setowner "*$($account.SID.Value)" | Out-Null
    }
    # Generate ephemeral OpenSSH keys; no real credentials or project files are used.
    & $keygen -q -t ed25519 -N '' -f (Join-Path $directory 'client_key')
    if ($LASTEXITCODE -ne 0) { throw 'Could not generate client key.' }
    & $keygen -q -t ed25519 -N '' -f (Join-Path $directory 'host_key')
    if ($LASTEXITCODE -ne 0) { throw 'Could not generate host key.' }
    $keySecurity = [Security.AccessControl.FileSecurity]::new()
    $keySecurity.SetAccessRuleProtection($true,$false)
    $keySecurity.SetOwner([Security.Principal.SecurityIdentifier]::new('S-1-5-32-544'))
    foreach ($sid in @('S-1-5-18','S-1-5-32-544')) {
        $keySecurity.AddAccessRule([Security.AccessControl.FileSystemAccessRule]::new(
            [Security.Principal.SecurityIdentifier]::new($sid),
            [Security.AccessControl.FileSystemRights]::FullControl,
            [Security.AccessControl.AccessControlType]::Allow))
    }
    Set-Acl -LiteralPath (Join-Path $directory 'host_key') -AclObject $keySecurity
    foreach ($user in $users) {
        $account = Get-LocalUser -Name $user
        $profile = Get-CimInstance Win32_UserProfile | Where-Object SID -eq $account.SID.Value
        Copy-Item (Join-Path $directory 'client_key.pub') (Join-Path $profile.LocalPath '.ssh\authorized_keys')
        & icacls.exe (Join-Path $profile.LocalPath '.ssh\authorized_keys') /setowner "*$($account.SID.Value)" | Out-Null
    }
    $publicHost = (Get-Content (Join-Path $directory 'host_key.pub') -Raw).Trim()
    Set-Content (Join-Path $directory 'known_hosts') "[127.0.0.1]:22222 $publicHost" -Encoding ascii
    if (-not (Test-Path -LiteralPath $sshd)) {
        Add-WindowsCapability -Online -Name 'OpenSSH.Server~~~~0.0.1.0' | Out-Null
    }
    $hostKey = (Join-Path $directory 'host_key').Replace('\','/')
    @"
Port 22222
ListenAddress 127.0.0.1
HostKey $hostKey
PubkeyAuthentication yes
PasswordAuthentication no
KbdInteractiveAuthentication no
AuthorizedKeysFile .ssh/authorized_keys
AllowUsers $($users -join ' ')
"@ | Set-Content -LiteralPath $testConfig -Encoding ascii
    & icacls.exe $testConfig /inheritance:r /grant:r '*S-1-5-18:F' '*S-1-5-32-544:F' | Out-Null
    & icacls.exe $testConfig /setowner '*S-1-5-32-544' | Out-Null
    & $sshd -t -f $testConfig
    if ($LASTEXITCODE -ne 0) { throw 'Invalid isolated SSH configuration.' }
    # An isolated SYSTEM task supplies OpenSSH's required privileges without replacing
    # the runner's preconfigured service, its config, its host keys or its listening ports.
    $log = Join-Path $directory 'sshd.log'
    $taskAction = New-ScheduledTaskAction -Execute $sshd -Argument "-D -f `"$testConfig`" -E `"$log`""
    Register-ScheduledTask -TaskName $taskName -Action $taskAction -User SYSTEM -RunLevel Highest -Force | Out-Null
    Start-ScheduledTask -TaskName $taskName
    for ($attempt=0; $attempt -lt 30; $attempt++) {
        if (Get-NetTCPConnection -LocalAddress 127.0.0.1 -LocalPort 22222 -State Listen -ErrorAction SilentlyContinue) {
            $ready=$true; break
        }
        Start-Sleep -Seconds 1
    }
    if (-not $ready) {
        if (Test-Path -LiteralPath $log) { Get-Content -LiteralPath $log | Write-Output }
        throw 'Isolated OpenSSH task did not listen on its loopback test port.'
    }
    $muxLiteral = "'" + (Join-Path $directory 'psmux.exe').Replace("'", "''") + "'"
    $heartbeat = '$n=0;while($true){Write-Output (''RAMPI_SSH_HEARTBEAT:''+$n);$n++;Start-Sleep -Milliseconds 300}'
    $heartbeatEncoded = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($heartbeat))
    $start = "& $muxLiteral -L '$namespace' new-session -d -s alive 'powershell.exe -NoProfile -EncodedCommand $heartbeatEncoded'; exit `$LASTEXITCODE"
    $started = Invoke-TestSsh $users[0] $start
    if ($started.Code -ne 0) { throw "SSH session creation failed: $($started.Text)" }
    Start-Sleep -Seconds 2
    $capture = "& $muxLiteral -L '$namespace' capture-pane -p -t alive; exit `$LASTEXITCODE"
    $first = Invoke-TestSsh $users[0] $capture
    Start-Sleep -Seconds 2
    $second = Invoke-TestSsh $users[0] $capture
    if ($first.Code -ne 0 -or $second.Code -ne 0 -or $first.Text -eq $second.Text -or
        $second.Text -notmatch 'RAMPI_SSH_HEARTBEAT:') {
        throw 'The native Windows process did not continue across closed SSH transports.'
    }
    # Attach through an actual SSH PTY, then abruptly kill the transport process.
    # Keep its stdin open and drain output so this is not an artificial EOF test.
    $attachScript = "& $muxLiteral -L '$namespace' attach-session -t alive"
    $attachEncoded = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($attachScript))
    $startInfo = [Diagnostics.ProcessStartInfo]::new()
    $startInfo.FileName = $ssh
    $startInfo.UseShellExecute = $false
    $startInfo.CreateNoWindow = $true
    $startInfo.RedirectStandardInput = $true
    $startInfo.RedirectStandardOutput = $true
    $startInfo.RedirectStandardError = $true
    foreach ($argument in @('-tt','-i',(Join-Path $directory 'client_key'),'-p','22222',
        '-o','BatchMode=yes','-o','StrictHostKeyChecking=yes',
        '-o',"UserKnownHostsFile=$(Join-Path $directory 'known_hosts')",'-l',$users[0],
        '127.0.0.1','powershell.exe','-NoLogo','-NoProfile','-EncodedCommand',$attachEncoded)) {
        $startInfo.ArgumentList.Add($argument)
    }
    $transport = [Diagnostics.Process]::new()
    $transport.StartInfo = $startInfo
    [void]$transport.Start()
    $outputDrain = $transport.StandardOutput.ReadToEndAsync()
    $errorDrain = $transport.StandardError.ReadToEndAsync()
    Start-Sleep -Seconds 3
    if ($transport.HasExited) { throw "Interactive SSH attach exited early: $($errorDrain.Result)" }
    $transport.Kill()
    $transport.WaitForExit()
    [void]$outputDrain.GetAwaiter().GetResult()
    [void]$errorDrain.GetAwaiter().GetResult()
    Start-Sleep -Seconds 2
    $afterDrop = Invoke-TestSsh $users[0] $capture
    if ($afterDrop.Code -ne 0 -or $afterDrop.Text -eq $second.Text -or
        $afterDrop.Text -notmatch 'RAMPI_SSH_HEARTBEAT:') {
        throw 'Native process did not survive an abruptly killed interactive SSH transport.'
    }
    $identity = Invoke-TestSsh $users[1] 'whoami; exit 0'
    if ($identity.Code -ne 0) { throw 'Second user SSH authentication failed; isolation test would be inconclusive.' }
    $other = Invoke-TestSsh $users[1] "& $muxLiteral -L '$namespace' has-session -t alive; exit `$LASTEXITCODE"
    if ($other.Code -eq 0) { throw 'Second Windows user could see the first user session.' }
    # Exercise the actual Rampi launcher too. This tiny provider fixture makes no
    # model requests; its process/working directory/environment are real Windows.
    $adapter = Join-Path $directory 'rampi-session.ps1'
    Copy-Item (Join-Path $PSScriptRoot '..\host\windows\rampi-session.ps1') $adapter
    $project = Join-Path $directory "Project O'Brien"
    New-Item -ItemType Directory -Path $project | Out-Null
    @'
if ($env:DISABLE_AUTOUPDATER -ne '1' -or $env:AGY_CLI_DISABLE_AUTO_UPDATE -ne 'true') { throw 'Automatic updates were not disabled in the actual provider process.' }
Write-Output ('RAMPI_ADAPTER_PID:' + $PID)
Write-Output 'RAMPI_ADAPTER_MANUAL_UPDATES_OK'
Write-Output ('RAMPI_ADAPTER_PROJECT:' + (Split-Path -Leaf (Get-Location).Path))
$counter = 0
while ($true) { Write-Output ('RAMPI_ADAPTER_HEARTBEAT:' + $counter); $counter++; Start-Sleep -Milliseconds 300 }
'@ | Set-Content -LiteralPath (Join-Path $directory 'codex.ps1') -Encoding utf8
    $adapterLiteral = "'" + $adapter.Replace("'", "''") + "'"
    $projectLiteral = "'" + $project.Replace("'", "''") + "'"
    $pathLiteral = "'" + $directory.Replace("'", "''") + ";'"
    $prefix = "`$env:PATH=$pathLiteral+`$env:PATH; "
    $guard = Invoke-TestSsh $users[0] ($prefix + "& $muxLiteral has-session -t '=rampi-codex'; exit `$LASTEXITCODE")
    if ($guard.Code -eq 0) { throw 'Unexpected preexisting default Rampi session.' }
    $adapterAttempted = $true
    $attach = $prefix + "& $adapterLiteral -Module codex -Project $projectLiteral; exit `$LASTEXITCODE"
    $startInfo.ArgumentList[$startInfo.ArgumentList.Count-1] = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($attach))
    $adapterTransport = [Diagnostics.Process]::new()
    $adapterTransport.StartInfo = $startInfo
    [void]$adapterTransport.Start()
    $adapterOutput = $adapterTransport.StandardOutput.ReadToEndAsync()
    $adapterError = $adapterTransport.StandardError.ReadToEndAsync()
    $captureAdapter = $prefix + "& $muxLiteral capture-pane -p -t '=rampi-codex'; exit `$LASTEXITCODE"
    $firstAdapter = $null
    for ($attempt=0; $attempt -lt 20; $attempt++) {
        Start-Sleep -Seconds 1
        if ($adapterTransport.HasExited) { throw "Rampi adapter attach exited: $($adapterError.Result)" }
        $firstAdapter = Invoke-TestSsh $users[0] $captureAdapter
        if ($firstAdapter.Code -eq 0 -and $firstAdapter.Text -match 'RAMPI_ADAPTER_HEARTBEAT:') { break }
    }
    if ($firstAdapter.Code -ne 0 -or $firstAdapter.Text -notmatch 'RAMPI_ADAPTER_MANUAL_UPDATES_OK' -or
        $firstAdapter.Text -notmatch "RAMPI_ADAPTER_PROJECT:Project O'Brien" -or
        $firstAdapter.Text -notmatch 'RAMPI_ADAPTER_PID:(\d+)') { throw 'Actual provider process did not receive the safe project and manual-update environment.' }
    $providerPid = $Matches[1]
    $adapterTransport.Kill()
    $adapterTransport.WaitForExit()
    [void]$adapterOutput.GetAwaiter().GetResult()
    [void]$adapterError.GetAwaiter().GetResult()
    Start-Sleep -Seconds 2
    $afterAdapter = Invoke-TestSsh $users[0] $captureAdapter
    if ($afterAdapter.Code -ne 0 -or $afterAdapter.Text -eq $firstAdapter.Text -or
        $afterAdapter.Text -notmatch "RAMPI_ADAPTER_PID:$providerPid") { throw 'Actual Rampi-launched process did not survive SSH loss.' }
    $adapterTransport.Dispose()
    $adapterTransport = [Diagnostics.Process]::new()
    $adapterTransport.StartInfo = $startInfo
    [void]$adapterTransport.Start()
    $reattachOutput = $adapterTransport.StandardOutput.ReadToEndAsync()
    $reattachError = $adapterTransport.StandardError.ReadToEndAsync()
    Start-Sleep -Seconds 2
    if ($adapterTransport.HasExited) { throw "Actual adapter reconnect failed: $($reattachError.Result)" }
    $reattached = Invoke-TestSsh $users[0] $captureAdapter
    if ($reattached.Code -ne 0 -or $reattached.Text -eq $afterAdapter.Text -or
        $reattached.Text -notmatch "RAMPI_ADAPTER_PID:$providerPid") { throw 'Adapter reconnect replaced the original provider process.' }
    $adapterTransport.Kill()
    $adapterTransport.WaitForExit()
    [void]$reattachOutput.GetAwaiter().GetResult()
    [void]$reattachError.GetAwaiter().GetResult()
    $check = Invoke-TestSsh $users[0] ($prefix + "& $adapterLiteral -Module codex -Action Check; exit `$LASTEXITCODE")
    if ($check.Code -ne 0 -or ($check.Text | ConvertFrom-Json).running -ne $true) { throw 'Actual adapter did not report its surviving session.' }
    $otherCheck = Invoke-TestSsh $users[1] ($prefix + "& $adapterLiteral -Module codex -Action Check; exit `$LASTEXITCODE")
    if ($otherCheck.Code -ne 0 -or ($otherCheck.Text | ConvertFrom-Json).running -ne $false) { throw 'Rampi Check crossed Windows account boundaries.' }
    $stopAdapter = Invoke-TestSsh $users[0] ($prefix + "& $adapterLiteral -Module codex -Action Stop; exit `$LASTEXITCODE")
    if ($stopAdapter.Code -ne 0) { throw 'Actual adapter could not stop its session.' }
    Write-Output 'RAMPI_WINDOWS_ACTUAL_ADAPTER_SSH_DROP_OK'
    Write-Output 'PASS: native ConPTY survived SSH reconnects and an abruptly killed PTY transport; second user denied same namespace.'
} finally {
    if ($null -ne $adapterTransport -and -not $adapterTransport.HasExited) { $adapterTransport.Kill(); $adapterTransport.WaitForExit() }
    if ($adapterAttempted -and $ready) {
        $cleanupMux = "'" + (Join-Path $directory 'psmux.exe').Replace("'", "''") + "'"
        Invoke-TestSsh $users[0] "& $cleanupMux kill-session -t '=rampi-codex'; exit `$LASTEXITCODE" | Out-Null
    }
    if ($createdUsers.Count -gt 0 -and $ready) {
        $mux = "'" + (Join-Path $directory 'psmux.exe').Replace("'", "''") + "'"
        Invoke-TestSsh $users[0] "& $mux -L '$namespace' kill-server; exit `$LASTEXITCODE" | Out-Null
    }
    Stop-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue
    foreach ($user in $createdUsers) { Remove-LocalUser -Name $user -ErrorAction SilentlyContinue }
    # Remove only this test's verified directory, never account profiles or shared services.
    $resolved = [IO.Path]::GetFullPath($directory)
    $expected = [IO.Path]::GetFullPath((Join-Path $env:ProgramData "RampiCiTest-$suffix"))
    if ($resolved -eq $expected -and (Split-Path -Leaf $resolved) -match '^RampiCiTest-[a-f0-9]{8}$') {
        Remove-Item -LiteralPath $resolved -Recurse -Force -ErrorAction SilentlyContinue
    }
}
