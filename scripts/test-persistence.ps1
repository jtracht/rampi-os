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
    # Startup time varies on shared runners; require increasing actual heartbeat counters.
    $firstCounter = -1
    $continued = $false
    $lastOutput = ''
    for ($attempt=0; $attempt -lt 40; $attempt++) {
        Start-Sleep -Seconds 1
        $lastOutput = (& $Psmux -L $namespace capture-pane -p -t persistence) -join "`n"
        $matches = [regex]::Matches($lastOutput, 'RAMPI-HEARTBEAT:(\d+)')
        if ($matches.Count -gt 0) {
            $counter = [int]$matches[$matches.Count-1].Groups[1].Value
            if ($firstCounter -ge 0 -and $counter -gt $firstCounter) { $continued=$true; break }
            $firstCounter = $counter
        }
    }
    if (-not $continued) {
        Write-Output $lastOutput
        throw 'Process did not demonstrably continue after the first client disconnected.'
    }
    Write-Output 'PASS: native ConPTY process continued across independent client exits.'
    Write-Output 'Scope: same Windows user; this is not an SSH-drop or cross-user isolation test.'
} finally {
    & $Psmux -L $namespace kill-server 2>$null
}
