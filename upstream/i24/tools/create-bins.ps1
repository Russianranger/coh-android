#Requires -Version 5.1
<#
.SYNOPSIS
Creates server and client bins using the executables in the repository root.
.EXAMPLE
.\tools\create-bins.ps1
#>
[CmdletBinding()]
param()

Set-StrictMode -Version 2.0
$ErrorActionPreference = 'Stop'

$repoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).ProviderPath
$builds = @(
    @{ Name = 'server'; Executable = 'MapServer.exe'; Arguments = @('-createbins', '-nogui', '1') }
    @{ Name = 'client'; Executable = 'Game.exe'; Arguments = @('-createbins', '-console', '1') }
)

# Check both executables before starting either build.
foreach ($build in $builds) {
    $exePath = Join-Path $repoRoot $build.Executable
    if (-not (Test-Path -LiteralPath $exePath -PathType Leaf)) {
        throw "$($build.Executable) was not found at '$exePath'. Place the developer build in the repository root and complete the README setup steps."
    }
}

foreach ($build in $builds) {
    $exePath = Join-Path $repoRoot $build.Executable
    Write-Host "Creating $($build.Name) bins..."
    $process = Start-Process -FilePath $exePath -ArgumentList $build.Arguments `
        -WorkingDirectory $repoRoot -NoNewWindow -Wait -PassThru
    if ($process.ExitCode -ne 0) {
        throw "$($build.Name) bin creation failed: $($build.Executable) exited with code $($process.ExitCode)."
    }
}
Write-Host 'Server and client bin creation completed.'
