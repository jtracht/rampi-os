[CmdletBinding()]
param([string]$Psmux = 'psmux.exe')
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$namespace = 'rampi-test-' + [Guid]::NewGuid().ToString('N').Substring(0,12)
$script = '$n=0; while($true){ Write-Output (''RAMPI-HEARTBEAT:''+$n); $n++; Start-Sleep -Milliseconds 300 }'
$encoded = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($script))
try {
    & $Psmux -L $namespace new-session -d -s persistence "powershell.exe -NoLogo -NoProfile -EncodedCommand $encoded"
    if ($LASTEXITCODE -ne 0) { throw 'Detached session could not be created.' }
    Start-Sleep -Seconds 2
    # The launcher above has already exited. Two new clients independently query the same server.
    $first = (& $Psmux -L $namespace capture-pane -p -t persistence) -join "`n"
    if ($LASTEXITCODE -ne 0) { throw 'First capture failed.' }
    Start-Sleep -Seconds 2
    $second = (& $Psmux -L $namespace capture-pane -p -t persistence) -join "`n"
    if ($LASTEXITCODE -ne 0 -or $second -notmatch 'RAMPI-HEARTBEAT:' -or $first -eq $second) {
        throw 'Process did not demonstrably continue after the first client disconnected.'
    }
    Write-Output 'PASS: native ConPTY process continued across independent client exits.'
    Write-Output 'Scope: same Windows user; this is not an SSH-drop or cross-user isolation test.'
} finally {
    & $Psmux -L $namespace kill-server 2>$null
}
