# SOURCE-ONLY recipe. Not run during preparation. Never executes any output.
[CmdletBinding()]
param([Parameter(Mandatory=$true)][string]$OutDir)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
if ($env:OS -ne 'Windows_NT' -or -not [Environment]::Is64BitProcess) { throw 'BUILD_PLATFORM_REFUSED' }
$source = $PSScriptRoot
$framework = Join-Path $env:WINDIR 'Microsoft.NET\Framework64\v4.0.30319'
$csc = Join-Path $framework 'csc.exe'
$refs = @('mscorlib.dll','System.dll','System.Core.dll','System.Security.dll')
$inputs = [ordered]@{}
$expected = [ordered]@{
  'OwnedProfileProcess.cs' = '6d01645e4df2db0564b6b9db3924c4cebb3ff9a590c1d73b422c5e9cce7ef474'
  'InertProfileProbe.cs' = '339aa91a99fc3099e421d8a70d16d350c97d1df94728e83c2f1fab367e85a52c'
  'TestOwnedProfileProcess.cs' = 'b68929efac7fa145a706524dc4d84e3b6afb6bd29258e636b9902297ca38a378'
}
function Pin([string]$path) {
  $item = Get-Item -LiteralPath $path -Force
  if ($item.PSIsContainer -or ($item.Attributes -band [IO.FileAttributes]::ReparsePoint)) { throw 'BUILD_INPUT_REFUSED' }
  return [ordered]@{ bytes = [long]$item.Length; sha256 = (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant() }
}
foreach ($name in @($expected.Keys)) {
  $inputs[$name] = Pin (Join-Path $source $name)
  if ($inputs[$name].sha256 -cne $expected[$name]) { throw 'FROZEN_SOURCE_REFUSED' }
}
foreach ($name in @('as-invoker.manifest','build-only.ps1')) { $inputs[$name] = Pin (Join-Path $source $name) }
$platform = [ordered]@{}
foreach ($name in (@('csc.exe') + $refs)) { $platform[$name] = Pin (Join-Path $framework $name) }
$config = Join-Path $framework 'csc.exe.config'
$configPresent = Test-Path -LiteralPath $config
if ($configPresent) { $platform['csc.exe.config'] = Pin $config }
$out = [IO.Path]::GetFullPath($OutDir)
if (Test-Path -LiteralPath $out) { throw 'BUILD_OUTPUT_EXISTS' }
# Fail on any competing existing output; no overwrite, cleanup or recovery here.
$null = New-Item -ItemType Directory -Path $out
$common = @('/nologo','/noconfig','/nostdlib+','/langversion:5','/platform:x64',
  '/target:exe','/optimize+','/debug-','/warn:4','/codepage:65001','/utf8output',
  ('/win32manifest:' + (Join-Path $source 'as-invoker.manifest')))
foreach ($name in $refs) { $common += ('/reference:' + (Join-Path $framework $name)) }
$targets = @(
  @{ name='OwnedProfileProcess.exe'; main='CohWpp.Program'; files=@('OwnedProfileProcess.cs') },
  @{ name='InertProfileProbe.exe'; main='CohWpp.InertProfileProbe'; files=@('InertProfileProbe.cs') },
  @{ name='TestOwnedProfileProcess.exe'; main='CohWpp.Tests'; files=@('OwnedProfileProcess.cs','TestOwnedProfileProcess.cs') }
)
$outputs = [ordered]@{}
foreach ($target in $targets) {
  $argsForCompiler = $common + @(('/main:' + $target.main), ('/out:' + (Join-Path $out $target.name)))
  foreach ($name in $target.files) { $argsForCompiler += (Join-Path $source $name) }
  # Compiler output is private until root applies an explicit public allowlist.
  & $csc @argsForCompiler 1> (Join-Path $out ($target.name + '.stdout.private.txt')) 2> (Join-Path $out ($target.name + '.stderr.private.txt'))
  if ($LASTEXITCODE -ne 0) { throw 'CSC_REFUSED' }
  $outputs[$target.name] = Pin (Join-Path $out $target.name)
}
foreach ($name in @($inputs.Keys)) {
  $now = Pin (Join-Path $source $name)
  if ($now.bytes -ne $inputs[$name].bytes -or $now.sha256 -cne $inputs[$name].sha256) { throw 'BUILD_SOURCE_CHANGED' }
}
if ((Test-Path -LiteralPath $config) -ne $configPresent) { throw 'BUILD_CONFIG_CHANGED' }
foreach ($name in @($platform.Keys)) {
  $now = Pin (Join-Path $framework $name)
  if ($now.bytes -ne $platform[$name].bytes -or $now.sha256 -cne $platform[$name].sha256) { throw 'BUILD_PLATFORM_CHANGED' }
}
foreach ($name in @($outputs.Keys)) {
  $now = Pin (Join-Path $out $name)
  if ($now.bytes -ne $outputs[$name].bytes -or $now.sha256 -cne $outputs[$name].sha256) { throw 'BUILD_OUTPUT_CHANGED' }
}
$receipt = [ordered]@{
  schema='coh-owned-profile-inert-build-v1'; passed=$true; inputs=$inputs;
  selected_installed_framework_files=$platform; compiler_config_present=$configPresent;
  outputs=$outputs; compiler_invocations=3; target='x64'; language_version='5';
  supplied_manifest='asInvoker/uiAccess=false'; no_config_response_file=$true;
  explicit_standard_library_references=$true; packages_or_restore_used=$false;
  output_executable_or_model_tests_executed=$false; account_or_profile_or_gui_api_executed=$false;
  full_compiler_dependency_closure_verified=$false; loaded_runtime_mapping_verified=$false;
  source_generation_admitted=$false; world_authority=$false
}
$json = $receipt | ConvertTo-Json -Depth 8
[IO.File]::WriteAllText((Join-Path $out 'build.json'), $json + "`n", (New-Object System.Text.UTF8Encoding -ArgumentList $false))
