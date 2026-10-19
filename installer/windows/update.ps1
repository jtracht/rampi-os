[CmdletBinding(SupportsShouldProcess)]
param()
# Only an explicit invocation updates Rampi; third-party programs are never silently upgraded.
& (Join-Path $PSScriptRoot 'setup.ps1') -Install -WhatIf:$WhatIfPreference
