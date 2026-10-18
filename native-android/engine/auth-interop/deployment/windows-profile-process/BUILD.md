# Proposed installed-compiler build (not executed)

Root must review and admit these definitions before compiling. No build, test,
account, profile, process, desktop or Windows API qualification has occurred.

Use the hosted x64 Windows PowerShell and installed .NET Framework compiler at
`%WINDIR%\Microsoft.NET\Framework64\v4.0.30319\csc.exe`. Its presence and all four
explicit framework references are capability gates. Refuse missing files; do
not install, download, restore packages, invoke an SDK project, select a PATH
compiler, or fall back to another compiler. No `.csproj` is required.

After root source/Git admission, the complete build command is:

```powershell
& "$env:WINDIR\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -NonInteractive -File .\build-only.ps1 -OutDir $newBuildDirectory
if ($LASTEXITCODE -ne 0) { throw 'INERT_BUILD_REFUSED' }
```

`$newBuildDirectory` is a fresh private output selected by root orchestration.
The script compiles exactly these targets, and executes none:

| Output | Explicit entry point | Sources |
| --- | --- | --- |
| OwnedProfileProcess.exe | CohWpp.Program | OwnedProfileProcess.cs |
| InertProfileProbe.exe | CohWpp.InertProfileProbe | InertProfileProbe.cs |
| TestOwnedProfileProcess.exe | CohWpp.Tests | OwnedProfileProcess.cs + TestOwnedProfileProcess.cs |

Each invocation uses `/noconfig /nostdlib+ /langversion:5 /platform:x64
/target:exe /optimize+ /debug- /warn:4 /codepage:65001 /utf8output`, the explicit
new `as-invoker.manifest`, and absolute references to installed `mscorlib.dll`,
`System.dll`, `System.Core.dll`, and `System.Security.dll`. `/main` and `/out`
select exactly the table's entry point/output. Warnings are retained; this
proposal does not claim a warning-free build or warning-as-error qualification.
There is no hidden `csc.rsp`, MSBuild target, NuGet source, optional source glob,
post-build command or application execution. The explicit manifest requests
`asInvoker` and `uiAccess=false`, including for the fresh ordinary user's probe;
it neither requests elevation nor opts into registry/file virtualization.

The build receipt brackets source/manifest/recipe, selected compiler/reference/
optional compiler-config and output bytes. Compiler logs remain private. This
is a selected-file identity record, not the full compiler's loaded dependency,
reference-assembly, operating-system or CLR mapping closure. Root must pin the
invoking PowerShell, source commit/tree, workflow/run identity and executable
bytes before/after any separately authorized execution. No output is executed
by this script. Failed build outputs/logs are preserved for root review.

The later first qualification may run only the NEW model executable and the
NEW helper's fixed inert probe. Runtime launch/timeout/process-job ownership,
protected private-parent provisioning and cleanup are separate root-owned
workflow work; this build script grants none. Public output must reconstruct
only the fixed receipt allowlist. Never upload the private parent, owner
journal, username/SID, profile paths, arguments, raw output or compiler logs.
The existing Auth/Db/Map/service executables and accepted17 suites are excluded.

Official compiler references read for this proposal:

- https://learn.microsoft.com/en-us/dotnet/csharp/language-reference/compiler-options/
- https://learn.microsoft.com/en-us/dotnet/csharp/language-reference/compiler-options/miscellaneous
- https://learn.microsoft.com/en-us/dotnet/csharp/language-reference/compiler-options/advanced
- https://learn.microsoft.com/en-us/dotnet/csharp/language-reference/compiler-options/win32icon-compiler-option
