[CmdletBinding()]
param()
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
if ($env:GITHUB_ACTIONS -ne 'true') { throw 'Run this mutation test only on a disposable CI runner.' }
$target = Join-Path $env:LOCALAPPDATA 'Rampi'
New-Item -ItemType Directory -Path $target -Force | Out-Null
$personal = Join-Path $target 'personal-setting.txt'
Set-Content -LiteralPath $personal -Value 'keep-this-value' -Encoding ascii
$adapter = Join-Path $target 'rampi-session.ps1'
Set-Content -LiteralPath $adapter -Value '# old adapter' -Encoding ascii
& icacls.exe $adapter /grant '*S-1-1-0:F' | Out-Null
& (Join-Path $PSScriptRoot '..\installer\windows\setup.ps1') -Install -AllowNonTarget
$sid = [Security.Principal.WindowsIdentity]::GetCurrent().User.Value
foreach ($path in @($target,$adapter)) {
    $rules = (Get-Acl -LiteralPath $path).GetAccessRules($true,$true,[Security.Principal.SecurityIdentifier])
    foreach ($rule in $rules) {
        if ($rule.IdentityReference.Value -notin @($sid,'S-1-5-18')) {
            throw 'Installer retained an unauthorized explicit or inherited access rule.'
        }
    }
}
if ((Get-Content -LiteralPath $personal -Raw).Trim() -ne 'keep-this-value') {
    throw 'Installer changed an unrelated personal setting.'
}
Write-Output 'PASS: Windows installer replaces unsafe adapter ACLs and preserves personal data.'
