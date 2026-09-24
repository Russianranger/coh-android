#Requires -Version 5.1
<#
.SYNOPSIS
Starts map 29 on the local map server, connecting to the local database server.
.EXAMPLE
.\tools\map.ps1
#>
[CmdletBinding()]
param(
    [string] $LogDirectory,
    [switch] $PassThru
)

Set-StrictMode -Version 2.0
$ErrorActionPreference = 'Stop'

$repoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).ProviderPath
$exePath = Join-Path $repoRoot 'MapServer.exe'
if (-not (Test-Path -LiteralPath $exePath -PathType Leaf)) {
    throw "MapServer.exe was not found at '$exePath'. Place the developer build in the repository root and complete the README setup steps."
}

$startOptions = @{ PassThru = $PassThru.IsPresent }
if ($LogDirectory) {
    # Keep the existing console so startup code does not replace redirected output.
    $startOptions.NoNewWindow = $true
    $startOptions.RedirectStandardOutput = Join-Path $LogDirectory 'map.stdout.log'
    $startOptions.RedirectStandardError = Join-Path $LogDirectory 'map.stderr.log'
}
Start-Process -FilePath $exePath -WorkingDirectory $repoRoot @startOptions -ArgumentList @(
    '-db', '127.0.0.1', '-notimeout', '-nosharedmemory', '-hidetrans', '-map_id', '29'
)
