[CmdletBinding()]
param([Parameter(Mandatory)][string]$Psmux)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
if ($env:GITHUB_ACTIONS -ne 'true') { throw 'Run session mutation tests only on disposable CI.' }
$mux = (Resolve-Path -LiteralPath $Psmux).Path
$env:PATH = (Split-Path -Parent $mux) + ';' + $env:PATH
$adapter = Join-Path $PSScriptRoot '..\host\windows\rampi-session.ps1'
$created = @()
try {
    foreach ($name in @('rampi-codex','rampi-codex-neighbor')) {
        & $mux has-session -t "=$name" 2>$null
        if ($LASTEXITCODE -eq 0) { throw 'A session already exists; refusing to modify it.' }
        & $mux new-session -d -s $name 'powershell.exe -NoLogo -NoProfile -Command Start-Sleep -Seconds 120'
        if ($LASTEXITCODE -ne 0) { throw 'Could not create isolated native test session.' }
        $created += $name
    }
    $json = & powershell.exe -NoLogo -NoProfile -File $adapter -Module codex -Action Status
    if ($LASTEXITCODE -ne 0) { throw 'Status action failed.' }
    $status = $json | ConvertFrom-Json
    if ($status.schema -ne 1 -or $status.module -ne 'codex' -or $status.running -ne $true) {
        throw 'Status did not identify the actual native session.'
    }
    $check = (& powershell.exe -NoLogo -NoProfile -File $adapter -Module codex -Action Check) | ConvertFrom-Json
    if ($LASTEXITCODE -ne 0 -or $check.schema -ne 1 -or $check.module -ne 'codex' -or
        $check.program -ne 'codex' -or $check.multiplexer -ne $true -or $check.running -ne $true -or
        $check.installed -isnot [bool]) { throw 'Check did not identify the actual live session.' }
    & powershell.exe -NoLogo -NoProfile -File $adapter -Module codex -Action Stop
    if ($LASTEXITCODE -ne 0) { throw 'Stop action failed.' }
    $status = (& powershell.exe -NoLogo -NoProfile -File $adapter -Module codex -Action Status) | ConvertFrom-Json
    if ($status.running -ne $false) { throw 'Stopped session still reported as running.' }
    foreach ($module in @('codex','claude','antigravity')) {
        $check = (& powershell.exe -NoLogo -NoProfile -File $adapter -Module $module -Action Check) | ConvertFrom-Json
        if ($LASTEXITCODE -ne 0 -or $check.schema -ne 1 -or $check.module -ne $module -or
            $check.multiplexer -ne $true -or $check.running -ne $false -or
            $check.installed -isnot [bool]) { throw 'Check misreported missing session or provider.' }
    }
    & $mux has-session -t '=rampi-codex-neighbor'
    if ($LASTEXITCODE -ne 0) { throw 'Stop affected a different session with the same prefix.' }
    Write-Output 'PASS: real Windows adapter reports and stops its exact session; neighboring session survives.'
    Write-Output 'RAMPI_WINDOWS_PROVIDER_CHECK_OK'
} finally {
    foreach ($name in $created) { & $mux kill-session -t "=$name" 2>$null | Out-Null }
}
