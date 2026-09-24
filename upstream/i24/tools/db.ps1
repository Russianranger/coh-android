#Requires -Version 5.1
<#
.SYNOPSIS
Starts the local database server using the existing servers.cfg configuration.
.EXAMPLE
.\tools\db.ps1
#>
[CmdletBinding()]
param(
    [string] $LogDirectory,
    [switch] $PassThru
)

Set-StrictMode -Version 2.0
$ErrorActionPreference = 'Stop'

$repoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).ProviderPath
$exePath = Join-Path $repoRoot 'DbServer.exe'
if (-not (Test-Path -LiteralPath $exePath -PathType Leaf)) {
    throw "DbServer.exe was not found at '$exePath'. Place the developer build in the repository root and complete the README setup steps."
}

$startOptions = @{ PassThru = $PassThru.IsPresent }
if ($LogDirectory) {
    # Keep the existing console so startup code does not replace redirected output.
    $startOptions.NoNewWindow = $true
    $startOptions.RedirectStandardOutput = Join-Path $LogDirectory 'db.stdout.log'
    $startOptions.RedirectStandardError = Join-Path $LogDirectory 'db.stderr.log'
}
Start-Process -FilePath $exePath -WorkingDirectory $repoRoot @startOptions
