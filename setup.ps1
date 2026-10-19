[CmdletBinding(SupportsShouldProcess)]
param([switch]$Install,[switch]$InstallMissing,[switch]$EnableOpenSsh,[switch]$EnableRdp)
& (Join-Path $PSScriptRoot 'installer\windows\setup.ps1') @PSBoundParameters
