# Rampi uses the current Windows token and the existing psmux server, never a shared broker.
[CmdletBinding()]
param(
    [Parameter(Mandatory)][ValidateSet('codex','claude','antigravity')][string]$Module,
    [string]$Project = '',
    [ValidateSet('Attach','List','Stop')][string]$Action = 'Attach'
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$mux = Get-Command psmux.exe -ErrorAction Stop
$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
if ($identity.IsSystem) { throw 'KI-Sitzungen dürfen nicht als SYSTEM laufen.' }
$session = 'rampi-' + $Module
if ($Action -eq 'List') { & $mux.Source list-sessions; exit $LASTEXITCODE }
if ($Action -eq 'Stop') { & $mux.Source kill-session -t $session; exit $LASTEXITCODE }
if ($Project) {
    $resolved = Resolve-Path -LiteralPath $Project -ErrorAction Stop
    if ($resolved.Provider.Name -ne 'FileSystem' -or
        -not (Test-Path -LiteralPath $resolved.ProviderPath -PathType Container)) {
        throw 'Das Projekt muss ein zugängliches lokales Dateisystemverzeichnis sein.'
    }
    $Project = $resolved.ProviderPath
}
$programs = @{codex='codex'; claude='claude'; antigravity='agy'}
$program = Get-Command $programs[$Module] -ErrorAction Stop
if ($program.CommandType -notin @('Application','ExternalScript')) {
    throw 'Der CLI-Befehl muss ein installiertes Programm oder Skript sein.'
}
# All untrusted paths become PowerShell literals within an encoded, fixed command.
$literal = "'" + $program.Source.Replace("'", "''") + "'"
$script = '$ErrorActionPreference=''Stop''; & ' + $literal + '; exit $LASTEXITCODE'
$encoded = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($script))
$shellCommand = 'powershell.exe -NoLogo -NoProfile -EncodedCommand ' + $encoded
$arguments = @('new-session','-A','-s',$session)
if ($Project) { $arguments += @('-c',$Project) }
$arguments += $shellCommand
& $mux.Source @arguments
exit $LASTEXITCODE
