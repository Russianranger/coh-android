#Requires -Version 5.1
<#
.SYNOPSIS
Downloads and extracts the Issue 24 assets, then restores tracked files if Git is available.
.DESCRIPTION
Run on Windows with a separately obtained Pig.exe. In a Git checkout with Git
available, tracked local changes are stashed before extraction. After git reset
--hard HEAD restores the repo's text data, the script pops its stash with --index
to restore changes and staging. Untracked and ignored files are not stashed.
Do not edit tracked files during extraction. Without Git or a Git checkout (such
as a ZIP download), these Git steps are skipped and extracted files may overwrite
existing files. Completed downloads are retained in piggs_bak/, outside the game's
active piggs/ directory so texts.pigg does not prevent developer mode.
.PARAMETER PigPath
Path to Pig.exe. Defaults to Pig.exe in the root of this repository.
.EXAMPLE
.\tools\fetch.ps1
.EXAMPLE
.\tools\fetch.ps1 -PigPath 'C:\CoH Tools\Pig.exe'
#>
[CmdletBinding()]
param(
    [string] $PigPath = (Join-Path (Split-Path -Parent $PSScriptRoot) 'Pig.exe')
)

Set-StrictMode -Version 2.0
$ErrorActionPreference = 'Stop'
# Check native exit codes explicitly, including when the caller enables this in PS7.
$PSNativeCommandUseErrorActionPreference = $false

$repoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).ProviderPath
$dataPath = Join-Path $repoRoot 'data'
$cachePath = Join-Path $repoRoot 'piggs_bak'
$baseUri = 'https://dists.thunderspy.org/piggs/'
[string[]] $archiveNames = @(
    'fonts.pigg'
    'geom.pigg'
    'geomBC.pigg'
    'geomV1.pigg'
    'geomV2.pigg'
    'mapsCities1.pigg'
    'mapsCities2.pigg'
    'mapsHazards.pigg'
    'mapsMisc.pigg'
    'mapsMissions.pigg'
    'mapsTrials.pigg'
    'misc.pigg'
    'player.pigg'
    'sound.pigg'
    'sound1.pigg'
    'sound2.pigg'
    'sound3.pigg'
    'sound4.pigg'
    'sound5.pigg'
    'sound6.pigg'
    'sound7.pigg'
    'soundMusic.pigg'
    'soundMusic1.pigg'
    'soundMusic2.pigg'
    'soundPowers.pigg'
    'soundV1.pigg'
    'soundV2.pigg'
    'soundVMusic.pigg'
    'stage1.pigg'
    'stage1a.pigg'
    'stage1b.pigg'
    'stage1c.pigg'
    'stage1d.pigg'
    'stage1e.pigg'
    'stage1f.pigg'
    'stage2.pigg'
    'stage2a.pigg'
    'stage2b.pigg'
    'stage2c.pigg'
    'stage3.pigg'
    'stage3a.pigg'
    'stage3b.pigg'
    'stage3c.pigg'
    'stage3d.pigg'
    'stage3e.pigg'
    'stage3f.pigg'
    'stage3g.pigg'
    'texEnemies.pigg'
    'texEnemies2.pigg'
    'texEnemies3.pigg'
    'texEnemies4.pigg'
    'texEnemies5.pigg'
    'texFxGuiItems.pigg'
    'texGui1.pigg'
    'texMaps.pigg'
    'texMisc.pigg'
    'texPlayersUI.pigg'
    'texVEnemies.pigg'
    'texVWorld.pigg'
    'texVWorld1.pigg'
    'texVWorld2.pigg'
    'texVWorld3.pigg'
    'texVWorldBases1.pigg'
    'texVWorldBases2.pigg'
    'texWorld.pigg'
    'texWorldBC.pigg'
    'texWorldBuildings.pigg'
    'texWorldCZ.pigg'
    'texWorldSW.pigg'
    'texWorldV1.pigg'
    'texWorldV2.pigg'
    'texts.pigg'
)
# Archive order determines which version of a duplicate asset wins.
[Array]::Sort($archiveNames, [StringComparer]::OrdinalIgnoreCase)

$useGit = $false
$gitCommand = Get-Command git -CommandType Application -ErrorAction SilentlyContinue |
    Select-Object -First 1
if ($null -eq $gitCommand) {
    Write-Host 'Git was not found on PATH. Skipping Git stash and restore steps.'
}
elseif (-not (Test-Path -LiteralPath (Join-Path $repoRoot '.git'))) {
    Write-Host 'This directory is not a Git checkout. Skipping Git stash and restore steps.'
}
else {
    $gitPath = $gitCommand.Source
    $gitRoot = & $gitPath -C $repoRoot rev-parse --show-toplevel
    if ($LASTEXITCODE -ne 0 -or
        [IO.Path]::GetFullPath($gitRoot) -ne [IO.Path]::GetFullPath($repoRoot)) {
        throw 'The script must be in the tools directory of this Git checkout.'
    }
    & $gitPath -C $repoRoot rev-parse --verify HEAD | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw 'The repository must have a HEAD commit to restore after extraction.'
    }
    $useGit = $true
}
if (-not (Test-Path -LiteralPath $PigPath -PathType Leaf)) {
    throw "Pig.exe was not found at '$PigPath'. Obtain it separately, place it in the repository root, or pass -PigPath."
}
$PigPath = (Resolve-Path -LiteralPath $PigPath).ProviderPath

function Get-TrackedChanges {
    $changes = & $gitPath -C $repoRoot status --porcelain --untracked-files=no
    if ($LASTEXITCODE -ne 0) {
        throw 'Could not check the tracked working tree.'
    }
    return $changes
}

function Get-FetchStash {
    # Resolve our own entry each time; other stashes may have changed its position.
    $entries = & $gitPath -C $repoRoot stash list '--format=%gd%x09%gs'
    if ($LASTEXITCODE -ne 0) {
        throw "Could not find the recovery stash named '$stashMessage'. Check git stash list before proceeding."
    }
    foreach ($entry in $entries) {
        $fields = $entry -split "`t", 2
        if ($fields.Count -eq 2 -and $fields[1].EndsWith($stashMessage, [StringComparison]::Ordinal)) {
            return $fields[0]
        }
    }
}

$originalSecurityProtocol = [Net.ServicePointManager]::SecurityProtocol
$originalProgressPreference = $ProgressPreference
$locationPushed = $false
$extractionStarted = $false
$stashMessage = 'fetch.ps1 before extraction ' + [Guid]::NewGuid().ToString('N')
$stashCreated = $false
$failure = $null

try {
    [Net.ServicePointManager]::SecurityProtocol = $originalSecurityProtocol -bor
        [Net.SecurityProtocolType]::Tls12
    # Windows PowerShell's per-byte web progress is costly for large downloads.
    $ProgressPreference = 'SilentlyContinue'
    New-Item -ItemType Directory -Path $cachePath -Force | Out-Null

    for ($i = 0; $i -lt $archiveNames.Length; $i++) {
        $name = $archiveNames[$i]
        $archivePath = Join-Path $cachePath $name
        if (Test-Path -LiteralPath $archivePath -PathType Leaf) {
            Write-Host "[$($i + 1)/$($archiveNames.Length)] Using cached $name"
            continue
        }

        Write-Host "[$($i + 1)/$($archiveNames.Length)] Downloading $name"
        $partialPath = "$archivePath.part"
        try {
            # An interrupted .part file is replaced, never treated as a full archive.
            Invoke-WebRequest -Uri ($baseUri + $name) -OutFile $partialPath -UseBasicParsing
            Move-Item -LiteralPath $partialPath -Destination $archivePath -Force
        }
        catch {
            throw "Download failed for '$name': $($_.Exception.Message). Rerun to retry; completed archives remain in '$cachePath'."
        }
    }

    # Include edits made during downloads, and leave the user's files alone if
    # downloading fails. Default stash behavior saves tracked changes only.
    if ($useGit) {
        if (Get-TrackedChanges) {
            Write-Host "Stashing tracked local changes as '$stashMessage'"
            & $gitPath -C $repoRoot stash push --message $stashMessage
            $stashExitCode = $LASTEXITCODE
            # A failed push can still have saved an entry before its cleanup failed.
            $stashCreated = $null -ne (Get-FetchStash)
            if ($stashExitCode -ne 0) {
                throw "Could not stash local changes (exit code $stashExitCode). Extraction has not started."
            }
        }
        if (Get-TrackedChanges) {
            throw 'Tracked changes remain after stashing. Extraction has not started.'
        }
    }
    New-Item -ItemType Directory -Path $dataPath -Force | Out-Null
    Push-Location -LiteralPath $dataPath
    $locationPushed = $true
    $extractionStarted = $true

    for ($i = 0; $i -lt $archiveNames.Length; $i++) {
        $name = $archiveNames[$i]
        $archivePath = Join-Path $cachePath $name
        Write-Host "[$($i + 1)/$($archiveNames.Length)] Extracting $name"
        try {
            & $PigPath xy $archivePath --nocrash
            if ($LASTEXITCODE -ne 0) {
                throw "Pig.exe exited with code $LASTEXITCODE."
            }
        }
        catch {
            throw "Extraction failed for '$name': $($_.Exception.Message). If the cached archive is damaged, delete '$archivePath' and rerun."
        }
    }
}
catch {
    $failure = $_
}
finally {
    try {
        if ($useGit -and $extractionStarted) {
            Write-Host 'Restoring tracked repository files with git reset --hard HEAD'
            & $gitPath -C $repoRoot reset --hard HEAD
            if ($LASTEXITCODE -ne 0) {
                throw "git reset --hard HEAD failed with exit code $LASTEXITCODE. Tracked files may still contain extracted data."
            }
        }
        if ($stashCreated) {
            $stashRef = Get-FetchStash
            if ($null -eq $stashRef) {
                throw "The recovery stash '$stashMessage' could not be found. Check git stash list to recover your changes."
            }
            Write-Host "Restoring local changes from $stashRef ($stashMessage)"
            & $gitPath -C $repoRoot stash pop --index $stashRef
            if ($LASTEXITCODE -ne 0) {
                throw "Could not restore local changes from $stashRef. The stash '$stashMessage' has been kept; resolve any conflicts before retrying git stash pop --index '$stashRef'."
            }
            $stashCreated = $false
        }
    }
    catch {
        if ($null -ne $failure) {
            Write-Warning $failure.Exception.Message
        }
        $failure = $_
        if ($stashCreated) {
            Write-Warning "Local changes remain in the stash named '$stashMessage'. Use git stash list to locate it for recovery."
        }
    }
    finally {
        if ($locationPushed) {
            Pop-Location
        }
        [Net.ServicePointManager]::SecurityProtocol = $originalSecurityProtocol
        $ProgressPreference = $originalProgressPreference
    }
}

if ($null -ne $failure) {
    throw $failure
}
Write-Host "Assets are available in '$dataPath'. Downloads are cached in '$cachePath'."
