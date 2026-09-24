#Requires -Version 5.1
<#
.SYNOPSIS
Generates map server templates using the executable in the repository root.
.EXAMPLE
.\tools\templates.ps1
#>
[CmdletBinding()]
param()

Set-StrictMode -Version 2.0
$ErrorActionPreference = 'Stop'

$repoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).ProviderPath
$exePath = Join-Path $repoRoot 'MapServer.exe'
if (-not (Test-Path -LiteralPath $exePath -PathType Leaf)) {
    throw "MapServer.exe was not found at '$exePath'. Place the developer build in the repository root and complete the README setup steps."
}

Write-Host 'Generating map server templates...'
$process = Start-Process -FilePath $exePath -ArgumentList @('-templates') `
    -WorkingDirectory $repoRoot -NoNewWindow -Wait -PassThru
if ($process.ExitCode -ne 0) {
    throw "Template generation failed: MapServer.exe exited with code $($process.ExitCode)."
}
Write-Host 'Map server template generation completed.'
