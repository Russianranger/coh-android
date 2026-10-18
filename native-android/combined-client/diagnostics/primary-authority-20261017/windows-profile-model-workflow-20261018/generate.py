#!/usr/bin/env python3
"""Generate only a NEW installed-compiler/pure-model job, with no profile API."""
import hashlib
from pathlib import Path
import yaml

ROOT=Path('/workspace/scratch/7ed1da2a7e55/coh-android')
PREFIX='native-android/engine/auth-interop/deployment/windows-profile-process/'
names=[PREFIX+n for n in ('OwnedProfileProcess.cs','InertProfileProbe.cs','TestOwnedProfileProcess.cs','CONTRACT.md','BUILD.md','as-invoker.manifest','build-only.ps1')]
names+=['native-android/engine/auth-interop/deployment/qualification/windows-profile-process-precompile-successor-20261018/'+n for n in ('source-freeze.json','REVIEW.md')]
pins={n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in names}
pin_literal='\n'.join("  '"+n+"' = '"+v+"'" for n,v in pins.items())

gate=r'''$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
function Need([bool]$ok) { if (-not $ok) { throw 'SOURCE_ADMISSION_REFUSED' } }
Need ($env:RUNNER_ENVIRONMENT -ceq 'github-hosted' -and $env:RUNNER_OS -ceq 'Windows' -and $env:RUNNER_ARCH -ceq 'X64')
Need ($env:GITHUB_REPOSITORY -ceq 'Russianranger/coh-android' -and $env:GITHUB_REF -ceq 'refs/heads/native-android')
$head=(& git rev-parse HEAD).Trim();Need ($LASTEXITCODE -eq 0 -and $head -ceq $env:GITHUB_SHA)
$tree=(& git rev-parse 'HEAD^{tree}').Trim();Need ($LASTEXITCODE -eq 0 -and $tree -cmatch '^[0-9a-f]{40}$')
$root=(Get-Location).Path
$pins=[ordered]@{
PIN_LITERAL
}
$workflow='.github/workflows/native-owned-profile-model.yml'
$workflowRaw=[IO.File]::ReadAllBytes((Join-Path $root $workflow))
function Sha([byte[]]$raw) { $h=[Security.Cryptography.SHA256]::Create();try{return ([BitConverter]::ToString($h.ComputeHash($raw))).Replace('-','').ToLowerInvariant()}finally{$h.Dispose()} }
$pins[$workflow]=Sha $workflowRaw
foreach ($name in @($pins.Keys)) {
 $path=Join-Path $root $name;$item=Get-Item -LiteralPath $path -Force
 Need (-not $item.PSIsContainer -and $item.Length -gt 0 -and $item.Length -lt 1048576 -and -not ($item.Attributes -band [IO.FileAttributes]::ReparsePoint))
 $at=$item.Directory;while($null -ne $at){Need (-not ($at.Attributes -band [IO.FileAttributes]::ReparsePoint));$at=$at.Parent}
 $raw=[IO.File]::ReadAllBytes($path);Need ((Sha $raw) -ceq $pins[$name])
 $line=(& git ls-tree HEAD -- $name);Need ($LASTEXITCODE -eq 0 -and $line -cmatch '^(100644|100755) blob ([0-9a-f]{40})\t(.+)$')
 $blob=$Matches[2];Need ($Matches[3] -ceq $name)
 [byte[]]$prefix=[Text.Encoding]::ASCII.GetBytes(('blob '+$raw.Length+[char]0));[byte[]]$all=$prefix+$raw
 $h=[Security.Cryptography.SHA1]::Create();try{$actual=([BitConverter]::ToString($h.ComputeHash($all))).Replace('-','').ToLowerInvariant()}finally{$h.Dispose()}
 Need ($actual -ceq $blob)
}
Need ((& git rev-parse HEAD).Trim() -ceq $head)
$public=Join-Path $root 'out/wpp-model-public';$null=New-Item -ItemType Directory -Path $public
$ps=Join-Path $env:WINDIR 'System32\WindowsPowerShell\v1.0\powershell.exe'
$value=[ordered]@{schema='coh-owned-profile-model-source-admission-v1';passed=$true;source_revision=$head;source_tree=$tree;source_sha256=$pins;installed_windows_powershell_sha256=(Get-FileHash -LiteralPath $ps -Algorithm SHA256).Hash.ToLowerInvariant();source_preflight_only=$true;compiler_or_model_or_profile_api_executed=$false;source_generation_admitted=$false;world_authority=$false}
[IO.File]::WriteAllText((Join-Path $public 'source-admission.json'),($value|ConvertTo-Json -Depth 8)+"`n",(New-Object Text.UTF8Encoding -ArgumentList $false))
Write-Output '{"source_admission_passed":true,"new_model_only":true,"profile_api_executed":false}'
'''.replace('PIN_LITERAL',pin_literal)

build=r'''$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$source=Join-Path (Get-Location).Path 'native-android/engine/auth-interop/deployment/windows-profile-process'
$build=Join-Path $env:RUNNER_TEMP 'owned-profile-model-build'
$driverLog=Join-Path $env:RUNNER_TEMP 'owned-profile-build-driver.private.txt'
$public=Join-Path (Get-Location).Path 'out/wpp-model-public'
$ok=$false;$diagnostics=@();$truncated=$false;$first='NONE';$stage='DRIVER'
try {
 $ps=Join-Path $env:WINDIR 'System32\WindowsPowerShell\v1.0\powershell.exe'
 & $ps -NoProfile -NonInteractive -File (Join-Path $source 'build-only.ps1') -OutDir $build *> $driverLog
 if ($LASTEXITCODE -ne 0) {throw 'BUILD_REFUSED'}
 $stage='BUILD_RECEIPT'
 $receipt=Get-Content -LiteralPath (Join-Path $build 'build.json') -Raw|ConvertFrom-Json
 if ($receipt.schema -cne 'coh-owned-profile-inert-build-v1' -or $receipt.passed -ne $true -or $receipt.compiler_invocations -ne 3 -or $receipt.output_executable_or_model_tests_executed -ne $false -or $receipt.account_or_profile_or_gui_api_executed -ne $false) {throw 'BUILD_RECEIPT_REFUSED'}
 $stage='OUTPUTS'
 foreach($name in @('OwnedProfileProcess.exe','InertProfileProbe.exe','TestOwnedProfileProcess.exe')) {
  $p=Join-Path $build $name;$entry=$receipt.outputs.$name
  if ((Get-Item -LiteralPath $p).Length -ne $entry.bytes -or (Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant() -cne $entry.sha256) {throw 'BUILD_OUTPUT_REFUSED'}
  Copy-Item -LiteralPath $p -Destination (Join-Path $public $name)
 }
 Copy-Item -LiteralPath (Join-Path $build 'build.json') -Destination (Join-Path $public 'build.json')
 $ok=$true;$stage='COMPLETE'
} catch {if($first -ceq 'NONE'){$first=$stage};$ok=$false}
# Only fixed compiler codes/known source roles/numeric source locations leave
# the private compiler-log boundary. No compiler error text/path/log is exported.
foreach($role in @('OwnedProfileProcess','InertProfileProbe','TestOwnedProfileProcess')) {
 foreach($stream in @('stdout','stderr')) {
  $p=Join-Path $build ($role+'.exe.'+$stream+'.private.txt')
  if(Test-Path -LiteralPath $p) {
   if((Get-Item -LiteralPath $p).Length -gt 65536){$truncated=$true;continue}
   foreach($line in [IO.File]::ReadAllLines($p)) {
    if($diagnostics.Count -ge 32){$truncated=$true;break}
    if($line -match '(error|warning) (CS[0-9]{4})') {
     $kind=$Matches[1];$code=$Matches[2];$sourceRole='NONE';$row=0;$column=0
     if($line -match '(OwnedProfileProcess|InertProfileProbe|TestOwnedProfileProcess)\.cs\(([0-9]{1,5}),([0-9]{1,5})\)'){$sourceRole=$Matches[1];$row=[int]$Matches[2];$column=[int]$Matches[3]}
     if($row -le 10000 -and $column -le 10000){$diagnostics+=[ordered]@{target=$role;kind=$kind;code=$code;source_role=$sourceRole;line=$row;column=$column}}
    }
   }
  }
 }
}
$status=[ordered]@{schema='coh-owned-profile-compile-fixed-status-v1';passed=$ok;first_failure=$first;driver_time_bound='workflow_15min_only';compiler_diagnostics=$diagnostics;diagnostics_truncated=$truncated;raw_compiler_logs_exported=$false;model_executed=$false;profile_api_executed=$false;source_generation_admitted=$false;world_authority=$false}
[IO.File]::WriteAllText((Join-Path $public 'compiler-status.json'),($status|ConvertTo-Json -Depth 8)+"`n",(New-Object Text.UTF8Encoding -ArgumentList $false))
Write-Output ('{"new_compile_passed":'+$ok.ToString().ToLowerInvariant()+',"model_or_profile_executed":false}')
if(-not $ok){exit 2}
'''

model=r"""$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$public=Join-Path (Get-Location).Path 'out/wpp-model-public'
$build=Join-Path $env:RUNNER_TEMP 'owned-profile-model-build'
$exe=Join-Path $build 'TestOwnedProfileProcess.exe'
$p=$null;$ok=$false;$resultValid=$false;$exitObserved=$false;$timedOut=$false
$first='NONE';$cleanupFirst='NONE';$stage='IMAGE';$disposeAttempted=$false;$disposeSucceeded=$false
$stdoutBytes=0;$stderrBytes=0;$value=$null
try {
 $before=(Get-FileHash -LiteralPath $exe -Algorithm SHA256).Hash.ToLowerInvariant()
 $buildReceipt=Get-Content -LiteralPath (Join-Path $build 'build.json') -Raw|ConvertFrom-Json
 if($before -cne $buildReceipt.outputs.'TestOwnedProfileProcess.exe'.sha256){throw 'MODEL_IMAGE_REFUSED'}
 $stage='START'
 $p=New-Object Diagnostics.Process;$p.StartInfo.FileName=$exe;$p.StartInfo.WorkingDirectory=$build
 $p.StartInfo.UseShellExecute=$false;$p.StartInfo.CreateNoWindow=$true;$p.StartInfo.RedirectStandardOutput=$true;$p.StartInfo.RedirectStandardError=$true
 $p.StartInfo.EnvironmentVariables.Clear()
 foreach($key in @('SystemRoot','WINDIR','TEMP','TMP')){$p.StartInfo.EnvironmentVariables[$key]=[Environment]::GetEnvironmentVariable($key)}
 if(-not $p.Start()){throw 'MODEL_START_REFUSED'}
 $stage='READ'
 # Raw byte reads have one fixed1024-byte buffer per stream and one fixed
 # 16384-byte stdout capture. There is no ReadToEnd/line accumulation. The
 # same30s deadline covers process exit AND both pipe EOF observations.
 $outBuffer=[byte[]]::new(1024);$errBuffer=[byte[]]::new(1024);$capture=[byte[]]::new(16384)
 $outStream=$p.StandardOutput.BaseStream;$errStream=$p.StandardError.BaseStream
 $outRead=$outStream.ReadAsync($outBuffer,0,$outBuffer.Length)
 $errRead=$errStream.ReadAsync($errBuffer,0,$errBuffer.Length)
 $outEof=$false;$errEof=$false;$watch=[Diagnostics.Stopwatch]::StartNew()
 while(-not ($outEof -and $errEof -and $p.HasExited)) {
  if($watch.ElapsedMilliseconds -ge 30000){$timedOut=$true;$stage='TIMEOUT';throw 'MODEL_TIMEOUT'}
  if(-not $outEof -and $outRead.IsCompleted){
   $n=$outRead.GetAwaiter().GetResult()
   if($n -eq 0){$outEof=$true}
   else{
    if($n -gt $capture.Length-$stdoutBytes){$stage='STDOUT_LIMIT';throw 'MODEL_STDOUT_LIMIT'}
    [Buffer]::BlockCopy($outBuffer,0,$capture,$stdoutBytes,$n);$stdoutBytes+=$n
    $outRead=$outStream.ReadAsync($outBuffer,0,$outBuffer.Length)
   }
  }
  if(-not $errEof -and $errRead.IsCompleted){
   $n=$errRead.GetAwaiter().GetResult()
   if($n -eq 0){$errEof=$true}
   else{$stderrBytes+=$n;$stage='STDERR';throw 'MODEL_STDERR_REFUSED'}
  }
  [Threading.Thread]::Sleep(10)
 }
 $watch.Stop();$exitObserved=$true;$stage='EXIT'
 if($p.ExitCode -ne 0){throw 'MODEL_EXIT_REFUSED'}
 $stage='SCHEMA'
 # The admitted producer emits this exact ASCII line in this fixed order.
 # Anchoring excludes duplicate keys, extra output, type coercion and floats.
 $stdout=[Text.Encoding]::ASCII.GetString($capture,0,$stdoutBytes)
 $pattern='\A\{"schema":"coh-owned-profile-process-model-controls-v1","passed":true,"scenarios":36,"checks":([1-9][0-9]{0,6}),"actual_windows_api_executed":false,"native_probe_executed":false,"services_or_network_executed":false\}\r?\n\z'
 $match=[regex]::Match($stdout,$pattern,[Text.RegularExpressions.RegexOptions]::CultureInvariant)
 if(-not $match.Success){throw 'MODEL_SCHEMA_REFUSED'}
 $checks=[int]::Parse($match.Groups[1].Value,[Globalization.CultureInfo]::InvariantCulture)
 if($checks -gt 1000000){throw 'MODEL_CHECKS_REFUSED'}
 $stage='BRACKET'
 $after=(Get-FileHash -LiteralPath $exe -Algorithm SHA256).Hash.ToLowerInvariant();if($after -cne $before){throw 'MODEL_IMAGE_CHANGED'}
 $source=Get-Content -LiteralPath (Join-Path $public 'source-admission.json') -Raw|ConvertFrom-Json
 foreach($prop in $source.source_sha256.PSObject.Properties){if((Get-FileHash -LiteralPath (Join-Path (Get-Location).Path $prop.Name) -Algorithm SHA256).Hash.ToLowerInvariant() -cne $prop.Value){throw 'MODEL_SOURCE_CHANGED'}}
 $value=[ordered]@{schema='coh-owned-profile-process-model-controls-v1';passed=$true;scenarios=36;checks=$checks;actual_windows_api_executed=$false;native_probe_executed=$false;services_or_network_executed=$false}
 $resultValid=$true;$ok=$true;$stage='COMPLETE'
} catch {if($first -ceq 'NONE'){$first=$stage};$ok=$false}
finally {
 if($null -ne $p){
  try {
   if(-not $p.HasExited){$p.Kill();$exitObserved=$p.WaitForExit(5000);if(-not $exitObserved){throw 'MODEL_CLEANUP_WAIT_REFUSED'}}
  } catch {if($cleanupFirst -ceq 'NONE'){$cleanupFirst='PROCESS_STOP'};$ok=$false}
  try {$disposeAttempted=$true;$p.Dispose();$disposeSucceeded=$true}
  catch {if($cleanupFirst -ceq 'NONE'){$cleanupFirst='DISPOSE'};$ok=$false}
 }
}
# Result validity and outer cleanup are separately reported. A cleanup refusal
# cannot turn an invalid model into a pass or overwrite the first model cause.
$status=[ordered]@{schema='coh-owned-profile-process-model-controls-v1';passed=$ok;model_result_valid=$resultValid;first_failure=$first;cleanup_first_failure=$cleanupFirst;actual_windows_api_executed=$false;native_probe_executed=$false;services_or_network_executed=$false}
if($resultValid){$status['scenarios']=36;$status['checks']=$value.checks}
[IO.File]::WriteAllText((Join-Path $public 'model-status.json'),($status|ConvertTo-Json -Depth 5)+"`n",(New-Object Text.UTF8Encoding -ArgumentList $false))
$observation=[ordered]@{schema='coh-owned-profile-model-execution-observation-v1';passed=$ok;model_result_valid=$resultValid;first_failure=$first;cleanup_first_failure=$cleanupFirst;model_process_exit_observed=$exitObserved;model_timeout=$timedOut;bounded_raw_stdout_bytes=$stdoutBytes;bounded_raw_stderr_bytes=$stderrBytes;process_dispose_attempted=$disposeAttempted;process_dispose_succeeded=$disposeSucceeded;fixed_executable_hash_bracketed=$resultValid;loaded_runtime_mapping_verified=$false;process_job_or_profile_api_qualified=$false;actual_profile_helper_executed=$false;old_model_or_service_tests_reexecuted=$false;source_generation_admitted=$false;world_authority=$false}
[IO.File]::WriteAllText((Join-Path $public 'model-execution.json'),($observation|ConvertTo-Json -Depth 5)+"`n",(New-Object Text.UTF8Encoding -ArgumentList $false))
Write-Output ('{"new_model_passed":'+$ok.ToString().ToLowerInvariant()+',"profile_helper_executed":false}')
if(-not $ok){exit 2}
"""

summary=r'''$ErrorActionPreference='Stop'
$public=Join-Path (Get-Location).Path 'out/wpp-model-public';$null=New-Item -ItemType Directory -Path $public -Force
$v=[ordered]@{schema='coh-owned-profile-build-model-public-summary-v1';source_admission_passed=($env:SOURCE_OUTCOME -ceq 'success');compile_passed=($env:BUILD_OUTCOME -ceq 'success');new_model_passed=($env:MODEL_OUTCOME -ceq 'success');actual_profile_helper_executed=$false;account_profile_desktop_or_service_qualified=$false;raw_compiler_or_process_logs_exported=$false;source_generation_admitted=$false;world_authority=$false}
[IO.File]::WriteAllText((Join-Path $public 'summary.json'),($v|ConvertTo-Json -Depth 5)+"`n",(New-Object Text.UTF8Encoding -ArgumentList $false))
'''

steps=[{'name':'Preserve exact source bytes before checkout','shell':'pwsh','run':'git config --global core.autocrlf false'},
 {'uses':'actions/checkout@11d5960a326750d5838078e36cf38b85af677262','with':{'persist-credentials':False,'fetch-depth':1}},
 {'id':'source','name':'Admit exact new C# and build source before any project script','shell':'pwsh','run':gate},
 {'id':'build','name':'Compile only three new x64 managed executables with installed csc','shell':'pwsh','run':build},
 {'id':'model','name':'Run only the new pure-platform model controls; no profile helper','shell':'pwsh','run':model},
 {'name':'Retain only fixed public build and model outcomes','if':'always()','shell':'pwsh','env':{'SOURCE_OUTCOME':'${{ steps.source.outcome }}','BUILD_OUTCOME':'${{ steps.build.outcome }}','MODEL_OUTCOME':'${{ steps.model.outcome }}'},'run':summary},
 {'uses':'actions/upload-artifact@v4','if':'always()','with':{'name':'owned-profile-build-model-${{ github.sha }}','path':'\n'.join('out/wpp-model-public/'+n for n in ('source-admission.json','build.json','compiler-status.json','model-status.json','model-execution.json','summary.json','OwnedProfileProcess.exe','InertProfileProbe.exe','TestOwnedProfileProcess.exe')),'if-no-files-found':'warn','retention-days':90}}]
doc={'name':'New Windows profile helper compilation and pure model only','on':{'push':{'branches':['native-android'],'paths':['.github/workflows/native-owned-profile-model.yml',PREFIX+'**']},'workflow_dispatch':{}},'permissions':{'contents':'read'},'concurrency':{'group':'native-owned-profile-model-${{ github.ref }}','cancel-in-progress':False},'jobs':{'installed-compiler-and-new-model-only':{'if':"github.repository == 'Russianranger/coh-android' && github.ref == 'refs/heads/native-android' && (github.event_name == 'workflow_dispatch' || contains(github.event.head_commit.message, '[windows-profile-model-build]'))",'runs-on':'windows-2025','timeout-minutes':15,'steps':steps}}}
output=Path('/workspace/scratch/7ed1da2a7e55/proposals/native-owned-profile-model.yml')
def literal(dumper,value):
    return dumper.represent_scalar('tag:yaml.org,2002:str',value,style='|' if '\n' in value else None)
yaml.SafeDumper.add_representer(str,literal)
with output.open('w') as stream:yaml.safe_dump(doc,stream,sort_keys=False,width=120)
print({'bytes':output.stat().st_size,'sha256':hashlib.sha256(output.read_bytes()).hexdigest(),'source_pins':len(pins),'actual_profile_helper_invocations':0})
