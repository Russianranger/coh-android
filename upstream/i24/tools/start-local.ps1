#Requires -Version 5.1
<#
.SYNOPSIS
Generates templates, starts DbServer, waits for it, starts MapServer, waits for it, then starts Game.
.DESCRIPTION
Uses the local launchers and the existing fakeauth configuration in servers.cfg.
Readiness is detected from the servers' startup-complete messages. Output is
saved in a unique directory under the system temporary directory. On failure,
already started servers are left running for inspection or manual shutdown.
.PARAMETER StartupTimeoutSeconds
Maximum time to wait for each server's ready message. Defaults to 300 seconds.
.EXAMPLE
.\tools\start-local.ps1
.EXAMPLE
.\tools\start-local.ps1 -StartupTimeoutSeconds 600
#>
[CmdletBinding()]
param(
    [ValidateRange(1, 86400)]
    [int] $StartupTimeoutSeconds = 300
)

Set-StrictMode -Version 2.0
$ErrorActionPreference = 'Stop'

$repoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).ProviderPath
foreach ($name in @('DbServer.exe', 'MapServer.exe', 'Game.exe')) {
    $exePath = Join-Path $repoRoot $name
    if (-not (Test-Path -LiteralPath $exePath -PathType Leaf)) {
        throw "$name was not found at '$exePath'. Complete the README setup steps before starting."
    }
}

$logDirectory = Join-Path ([IO.Path]::GetTempPath()) ('coh-local-' + [Guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $logDirectory | Out-Null
Write-Host "Server logs: $logDirectory"
$servers = @()

function Assert-ServersRunning {
    foreach ($server in $servers) {
        $server.Refresh()
        if ($server.HasExited) {
            throw "Server process $($server.Id) exited with code $($server.ExitCode). Check logs in '$logDirectory'."
        }
    }
}

function Wait-ServerReady {
    param([string] $Name, [string] $LogPath, [string] $ReadyMessage)

    Write-Host "Waiting for $Name..."
    $timer = [Diagnostics.Stopwatch]::StartNew()
    while ($timer.Elapsed.TotalSeconds -lt $StartupTimeoutSeconds) {
        Assert-ServersRunning
        if ((Test-Path -LiteralPath $LogPath -PathType Leaf) -and
            (Select-String -LiteralPath $LogPath -Pattern $ReadyMessage -SimpleMatch -Quiet)) {
            Write-Host "$Name is ready."
            return
        }
        Start-Sleep -Milliseconds 500
    }
    throw "Timed out waiting for $Name after $StartupTimeoutSeconds seconds. Check logs in '$logDirectory'."
}

try {
    & (Join-Path $PSScriptRoot 'templates.ps1')

    $servers += & (Join-Path $PSScriptRoot 'db.ps1') -LogDirectory $logDirectory -PassThru
    Wait-ServerReady -Name 'DbServer' -LogPath (Join-Path $logDirectory 'db.stderr.log') `
        -ReadyMessage 'DbServer Ready.'

    $servers += & (Join-Path $PSScriptRoot 'map.ps1') -LogDirectory $logDirectory -PassThru
    Wait-ServerReady -Name 'MapServer' -LogPath (Join-Path $logDirectory 'map.stdout.log') `
        -ReadyMessage 'Server ready.'

    Assert-ServersRunning
    & (Join-Path $PSScriptRoot 'client.ps1')
    Write-Host 'Local servers are ready and the client has been launched.'
}
catch {
    Write-Warning "Startup stopped. Any servers already launched are left running for inspection; close them before retrying. Logs: $logDirectory"
    throw
}
