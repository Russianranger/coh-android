#Requires -Version 5.1
<#
.SYNOPSIS
Downloads a City of Heroes release and installs its executables, DLLs, and server configs.
.DESCRIPTION
Downloads CoX-OptDebug-Win32.zip for the selected GitHub release tag.
Only .exe and .dll files from the archive are extracted, and they are placed
in the root of this repository. servers.cfg and loadBalanceDefault.cfg are
downloaded from the latest master commit in Thunderspies/CityOfHeroes and
placed in data/server/db. Existing executables, DLLs, and configs are always replaced.
.PARAMETER ReleaseTag
GitHub release tag to download. Defaults to v2i3.
.PARAMETER Force
Accepted for compatibility. Existing files are always replaced.
.EXAMPLE
.\tools\fetch_release.ps1
.EXAMPLE
.\tools\fetch_release.ps1 -ReleaseTag v2i3
#>
[CmdletBinding()]
param(
    [ValidatePattern('^[A-Za-z0-9][A-Za-z0-9._-]*$')]
    [string] $ReleaseTag = 'v2i3',
    [switch] $Force
)

Set-StrictMode -Version 2.0
$ErrorActionPreference = 'Stop'

$repoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).ProviderPath
$archiveName = 'CoX-OptDebug-Win32.zip'
$releaseUri = "https://github.com/Thunderspies/CityOfHeroes/releases/download/$ReleaseTag/$archiveName"
$configBaseUri = 'https://raw.githubusercontent.com/Thunderspies/CityOfHeroes/refs/heads/master/data/server/db'
$archivePath = Join-Path ([IO.Path]::GetTempPath()) ("$archiveName.$([Guid]::NewGuid().ToString('N')).zip")
$configDirectory = Join-Path $repoRoot 'data/server/db'
$configs = @('servers.cfg', 'loadBalanceDefault.cfg') | ForEach-Object {
    [PSCustomObject]@{
        Name = $_
        DownloadPath = Join-Path ([IO.Path]::GetTempPath()) ("$_.$([Guid]::NewGuid().ToString('N'))")
    }
}
$zip = $null

try {
    Write-Host "Downloading release '$ReleaseTag'..."
    Invoke-WebRequest -Uri $releaseUri -OutFile $archivePath -UseBasicParsing
    foreach ($config in $configs) {
        Write-Host "Downloading $($config.Name) from master..."
        Invoke-WebRequest -Uri "$configBaseUri/$($config.Name)" -OutFile $config.DownloadPath -UseBasicParsing
    }

    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $zip = [IO.Compression.ZipFile]::OpenRead($archivePath)
    $files = @($zip.Entries | Where-Object {
        $_.Name -and (
            $_.Name.EndsWith('.exe', [StringComparison]::OrdinalIgnoreCase) -or
            $_.Name.EndsWith('.dll', [StringComparison]::OrdinalIgnoreCase)
        )
    })

    if ($files.Count -eq 0) {
        throw "The archive did not contain any executables or DLLs."
    }

    $duplicateNames = @($files | Group-Object Name | Where-Object Count -gt 1)
    if ($duplicateNames.Count -gt 0) {
        $names = $duplicateNames.Name -join ', '
        throw "The archive contains duplicate target filenames: $names"
    }

    foreach ($entry in $files) {
        $destinationPath = Join-Path $repoRoot $entry.Name
        Write-Host "Extracting $($entry.Name)"
        [IO.Compression.ZipFileExtensions]::ExtractToFile($entry, $destinationPath, $true)
    }
    New-Item -ItemType Directory -Path $configDirectory -Force | Out-Null
    foreach ($config in $configs) {
        Move-Item -LiteralPath $config.DownloadPath -Destination (Join-Path $configDirectory $config.Name) -Force
        Write-Host "Installed $($config.Name) from master."
    }
}
finally {
    if ($null -ne $zip) {
        $zip.Dispose()
    }
    if (Test-Path -LiteralPath $archivePath -PathType Leaf) {
        Remove-Item -LiteralPath $archivePath -Force
    }
    foreach ($config in $configs) {
        if (Test-Path -LiteralPath $config.DownloadPath -PathType Leaf) {
            Remove-Item -LiteralPath $config.DownloadPath -Force
        }
    }
}

Write-Host "Installed $($files.Count) executable(s) and DLL(s) from release '$ReleaseTag'."
