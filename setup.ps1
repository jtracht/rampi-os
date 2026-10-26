[CmdletBinding(SupportsShouldProcess)]
param([switch]$EnableOpenSsh,[switch]$EnableRdp)
$localInstaller = Join-Path $PSScriptRoot 'installer\windows\setup.ps1'
if (Test-Path -LiteralPath $localInstaller) {
    & $localInstaller @PSBoundParameters
    return
}
# Release packaging updates this marker. Never auto-updates a configured machine.
$RampiBootstrapVersion = '0.1.0.dev0'
$temporary = Join-Path ([IO.Path]::GetTempPath()) ('rampi-bootstrap-' + [Guid]::NewGuid().ToString('N'))
try {
    New-Item -ItemType Directory -Path $temporary | Out-Null
    $archive = "rampi-windows-host-$RampiBootstrapVersion.zip"
    $url = "https://github.com/jtracht/rampi-os/releases/download/v$RampiBootstrapVersion"
    Invoke-WebRequest "$url/$archive" -OutFile (Join-Path $temporary $archive)
    Invoke-WebRequest "$url/SHA256SUMS" -OutFile (Join-Path $temporary 'SHA256SUMS')
    $sums = [IO.File]::ReadAllText((Join-Path $temporary 'SHA256SUMS'))
    $expected = $null
    foreach ($line in ($sums -split "`n")) {
        if ($line.Trim() -match ('^([a-f0-9]{64})  ' + [regex]::Escape($archive) + '$')) {
            $expected = $Matches[1]
        }
    }
    $actual = (Get-FileHash (Join-Path $temporary $archive) -Algorithm SHA256).Hash.ToLowerInvariant()
    if (-not $expected -or $expected -ne $actual) { throw 'Release-Prüfsumme stimmt nicht überein.' }
    $unpacked = Join-Path $temporary 'package'
    Expand-Archive -LiteralPath (Join-Path $temporary $archive) -DestinationPath $unpacked
    & (Join-Path $unpacked 'installer\windows\setup.ps1') @PSBoundParameters
} finally {
    $absolute = [IO.Path]::GetFullPath($temporary)
    $parent = [IO.Path]::GetFullPath([IO.Path]::GetTempPath()).TrimEnd('\')
    if ((Split-Path -Parent $absolute).TrimEnd('\') -eq $parent -and
        (Split-Path -Leaf $absolute) -match '^rampi-bootstrap-[a-f0-9]{32}$') {
        Remove-Item -LiteralPath $absolute -Recurse -Force -ErrorAction SilentlyContinue
    }
}
