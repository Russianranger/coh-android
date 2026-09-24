#Requires -Version 5.1
<#
.SYNOPSIS
Starts the game client in local map server mode, connecting to the local database server.
.EXAMPLE
.\tools\client.ps1
#>
[CmdletBinding()]
param()

Set-StrictMode -Version 2.0
$ErrorActionPreference = 'Stop'

$repoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).ProviderPath
$exePath = Join-Path $repoRoot 'Game.exe'
if (-not (Test-Path -LiteralPath $exePath -PathType Leaf)) {
    throw "Game.exe was not found at '$exePath'. Place the developer build in the repository root and complete the README setup steps."
}

Start-Process -FilePath $exePath -WorkingDirectory $repoRoot -ArgumentList @(
    '-db', '127.0.0.1', '-console', '1', '-fullscreen', '0',
    '-localmapserver', '1', '-notimeout', '1', '-noaudio', '1'
)
