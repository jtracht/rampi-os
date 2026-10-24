# Rampi uses the current Windows token and the existing psmux server, never a shared broker.
[CmdletBinding()]
param(
    [Parameter(Mandatory)][ValidateSet('codex','claude','antigravity')][string]$Module,
    [string]$Project = '',
    [ValidateSet('Attach','List','Stop','Status','Check')][string]$Action = 'Attach'
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$Module = $Module.ToLowerInvariant()
$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
if ($identity.IsSystem) { throw 'KI-Sitzungen dürfen nicht als SYSTEM laufen.' }
$session = 'rampi-' + $Module
$programs = @{codex='codex'; claude='claude'; antigravity='agy'}
if ($Action -eq 'Check') {
    $cli = Get-Command $programs[$Module] -ErrorAction SilentlyContinue
    $mux = Get-Command psmux.exe -ErrorAction SilentlyContinue
    $installed = $null -ne $cli -and $cli.CommandType -in @('Application','ExternalScript')
    $running = $false
    if ($mux) {
        & $mux.Source has-session -t "=$session" 2>$null | Out-Null
        $running = $LASTEXITCODE -eq 0
    }
    # Deliberately do not run the provider or read its authentication files.
    [PSCustomObject]@{schema=1; module=$Module; program=$programs[$Module]; installed=$installed; multiplexer=($null -ne $mux); running=$running} | ConvertTo-Json -Compress
    exit 0
}
$mux = Get-Command psmux.exe -ErrorAction Stop
if ($Action -eq 'List') { & $mux.Source list-sessions; exit $LASTEXITCODE }
if ($Action -eq 'Status') {
    & $mux.Source has-session -t "=$session" 2>$null | Out-Null
    $running = $LASTEXITCODE -eq 0
    [PSCustomObject]@{schema=1; module=$Module; running=$running} | ConvertTo-Json -Compress
    exit 0
}
if ($Action -eq 'Stop') { & $mux.Source kill-session -t "=$session"; exit $LASTEXITCODE }
if ($Project) {
    $resolved = Resolve-Path -LiteralPath $Project -ErrorAction Stop
    if ($resolved.Provider.Name -ne 'FileSystem' -or
        -not (Test-Path -LiteralPath $resolved.ProviderPath -PathType Container)) {
        throw 'Das Projekt muss ein zugängliches lokales Dateisystemverzeichnis sein.'
    }
    $Project = $resolved.ProviderPath
}
$program = Get-Command $programs[$Module] -ErrorAction Stop
if ($program.CommandType -notin @('Application','ExternalScript')) {
    throw 'Der CLI-Befehl muss ein installiertes Programm oder Skript sein.'
}
# All untrusted paths become PowerShell literals within an encoded, fixed command.
$literal = "'" + $program.Source.Replace("'", "''") + "'"
$script = '$ErrorActionPreference=''Stop''; $env:DISABLE_AUTOUPDATER=''1''; $env:AGY_CLI_DISABLE_AUTO_UPDATE=''true''; & ' + $literal + '; exit $LASTEXITCODE'
$encoded = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($script))
$shellCommand = 'powershell.exe -NoLogo -NoProfile -EncodedCommand ' + $encoded
$arguments = @('new-session','-A','-s',$session)
if ($Project) { $arguments += @('-c',$Project) }
$arguments += $shellCommand
& $mux.Source @arguments
exit $LASTEXITCODE
