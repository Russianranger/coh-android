# Compile exactly one new observation-only helper; reuse accepted inert probe/model.
[CmdletBinding()]
param([Parameter(Mandatory=$true)][string]$AcceptedArtifactDir,
      [Parameter(Mandatory=$true)][string]$OutDir)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
function Need([bool]$ok){if(-not $ok){throw 'FILE_DIAGNOSTIC_BUILD_REFUSED'}}
function Pin([string]$path){
 $item=Get-Item -LiteralPath $path -Force
 Need (-not $item.PSIsContainer -and -not ($item.Attributes -band [IO.FileAttributes]::ReparsePoint))
 return [ordered]@{bytes=[long]$item.Length;sha256=(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()}
}
Need ($env:OS -ceq 'Windows_NT' -and [Environment]::Is64BitProcess)
$original=Get-Content -LiteralPath (Join-Path $AcceptedArtifactDir 'build.json') -Raw|ConvertFrom-Json
Need ($original.schema -ceq 'coh-owned-profile-inert-build-v1' -and $original.passed -eq $true)
$out=[IO.Path]::GetFullPath($OutDir)
$source=Join-Path $out 'OwnedProfileProcessFileDiagnostic.cs'
$preparation=Get-Content -LiteralPath (Join-Path $out 'preparation.json') -Raw|ConvertFrom-Json
Need ($preparation.schema -ceq 'coh-wpp-file-diagnostic-preparation-v1' -and $preparation.passed -eq $true -and $preparation.exact_reverse_verified -eq $true)
$sourcePin=Pin $source
Need ($sourcePin.bytes -eq 47405 -and $sourcePin.sha256 -ceq '3f556f65fa8a6182797c2d42bc0d1ea1c0a57aa54b5de058fe1f7a8c6cec2514')
$manifest=Join-Path $PSScriptRoot 'as-invoker.manifest';$manifestPin=Pin $manifest
Need ($manifestPin.sha256 -ceq '3a462ffbbe724bd1c520e85696599d057e3d2a8f0bb0270d5ec712be20e27331')
$framework=Join-Path $env:WINDIR 'Microsoft.NET\Framework64\v4.0.30319'
$platform=[ordered]@{}
foreach($prop in $original.selected_installed_framework_files.PSObject.Properties){
 $name=$prop.Name;Need ($name -cin @('csc.exe','mscorlib.dll','System.dll','System.Core.dll','System.Security.dll','csc.exe.config'))
 $now=Pin (Join-Path $framework $name)
 Need ($now.bytes -eq $prop.Value.bytes -and $now.sha256 -ceq $prop.Value.sha256)
 $platform[$name]=$now
}
Need ($platform.Count -ge 5 -and $platform.Contains('csc.exe'))
$exe=Join-Path $out 'OwnedProfileProcess.exe';Need (-not (Test-Path -LiteralPath $exe))
$compiler=Join-Path $framework 'csc.exe'
$arguments=@('/nologo','/noconfig','/nostdlib+','/langversion:5','/platform:x64','/target:exe','/optimize+','/debug-','/warn:4','/codepage:65001','/utf8output',('/win32manifest:'+$manifest),'/main:CohWpp.Program',('/out:'+$exe))
foreach($name in @('mscorlib.dll','System.dll','System.Core.dll','System.Security.dll')){$arguments+=('/reference:'+(Join-Path $framework $name))}
$arguments+=$source
& $compiler @arguments 1> (Join-Path $out 'compiler.stdout.private.txt') 2> (Join-Path $out 'compiler.stderr.private.txt')
Need ($LASTEXITCODE -eq 0)
foreach($name in @($platform.Keys)){$now=Pin (Join-Path $framework $name);Need ($now.bytes -eq $platform[$name].bytes -and $now.sha256 -ceq $platform[$name].sha256)}
Need ((Pin $source).sha256 -ceq $sourcePin.sha256 -and (Pin $manifest).sha256 -ceq $manifestPin.sha256)
$image=Pin $exe
$receipt=[ordered]@{
 schema='coh-wpp-file-diagnostic-build-v1';passed=$true;compiler_invocations=1;
 original_source_sha256='6d01645e4df2db0564b6b9db3924c4cebb3ff9a590c1d73b422c5e9cce7ef474';
 generated_source_sha256=$sourcePin.sha256;generated_source_bytes=$sourcePin.bytes;
 exact_reverse_verified=$true;selected_compiler_files_match_accepted_build=$true;
 selected_installed_framework_files=$platform;helper_image=$image;
 accepted_inert_probe_recompiled=$false;accepted_model_recompiled_or_executed=$false;
 helper_executed=$false;source_generation_admitted=$false;world_authority=$false
}
[IO.File]::WriteAllText((Join-Path $out 'diagnostic-build.json'),($receipt|ConvertTo-Json -Depth 8)+"`n",(New-Object Text.UTF8Encoding -ArgumentList $false))
Write-Output '{"file_diagnostic_helper_compiled":true,"compiler_invocations":1,"accepted_probe_or_model_rebuilt":false}'
