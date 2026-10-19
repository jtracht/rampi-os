[CmdletBinding(SupportsShouldProcess)]
param()
Set-StrictMode -Version Latest
$target = Join-Path $env:LOCALAPPDATA 'Rampi\rampi-session.ps1'
if ((Test-Path -LiteralPath $target) -and $PSCmdlet.ShouldProcess($target, 'Rampi-Adapter entfernen')) {
    Remove-Item -LiteralPath $target
}
# Shared Windows services, provider authentication and persistent sessions are preserved.
