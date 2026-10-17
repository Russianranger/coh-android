The disposable full PG/Wine compile driver is implemented and qualified by twelve local Python control suites. It has not run on Windows and has not produced a new executable. The source recipe and donor recovery were separately reviewed; they do not grant runtime compatibility or authenticated-login permission.

`hosted_manual_atlas_compile.py` accepts only fresh GitHub-hosted Windows, a clean exact repository commit, an absent output under RUNNER_TEMP, the externally SHA-pinned five-suite full-source qualification and an externally SHA-pinned reviewed toolchain lock. It never starts AuthServer, DbServer, SQL or Wine. It does not install a binary, edit accounts, replace an accepted package or relax the fake-auth-only manual wait guard.

The tool lock must contain these fields:

| Field | Required content |
| --- | --- |
| schema | `coh-reviewed-windows-build-tool-lock-v1` |
| image_os, image_version | Exact hosted image observations |
| generator, architecture | `Visual Studio 18 2026`, `Win32` |
| vs_installation | Absolute installed VS18 directory |
| vc_toolset_version | Exact installed numeric `14.*.*` toolset |
| windows_sdk_version | Exact installed numeric `10.0.*.*` SDK |
| compiler_version, cmake_version | Exact generated compiler and CMake version observations |
| tools | Exactly cmake, git, patch, cl, link, ml, rc, msbuild; each with absolute path, bytes and SHA256 |

This lock must come from independent host inspection and review. The driver hashes every named tool before and after the experiment, verifies installation ownership and exact image identity, forces the linker/assembler/resource compiler/MSBuild paths, pins VS toolset/SDK selection and validates emitted CMake compiler and cache files. It also refuses ambient compiler/toolchain overrides and verifies the Git found by the original source preparer is the locked Git. The primary executable hashes and image/SDK version pins do not constitute a hash of every SDK header, library or compiler DLL.

Existing MSSQL compile evidence records CMake4.4.4, MSVC19.51.36260.0 and toolset14.51.36231 on image win25-vs2026/20261007.264.1. It does not record all eight tool hashes or the SDK version. Those missing values must be observed, not inferred. No tool lock with invented values is supplied here.

The driver composes the complete accepted manual source in an owned temporary copy. It fetches each of the three exact Git revisions from the static recipe into fresh owned dependency checkouts. The two pinned patches add only their verified CMakeLists.txt files; the driver stages those exact bytes, then supplies explicit CPM source overrides and disconnected FetchContent. No accepted source/CMake file is edited to bypass patching or fetch checks. Common and DbServer are the only enabled registered projects; fixture/MapServer/BeaconServer/test/tool options remain off. The build targets DbServer/OptDebug with two workers and disables MSBuild node reuse.

The artifact contains the ordered command argv/results/logs, source recipe, exact reviewed lock and host receipt, CMake cache/compiler files, all source/dependency maps before configuration and after compilation, final cleanup-time maps, new StructParser source bytes, and Win32 DbServer.exe/CrashRpt.dll identities with bounded ordinary-import inventories. All6,007 existing source bytes must remain unchanged. New source files are restricted to C/C++/header sidecars in the three consumer AutoGen directories; they are retained, not discarded. Dependency maps may differ only by the pinned added CMakeLists.txt. Initial/incremental maps survive failed commands; complete success additionally requires final input/tool stability. Each command has a bounded deadline/log and owned-child termination; an overall35minute budget reserves2minutes for final capture/cleanup. A hosting workflow must allow a longer timeout and always upload the receipt directory.

The pure PE parser bounds section/RVA ownership, import-table termination and DLL names. Its inventory excludes delay imports and dynamic loads, and does not establish runtime DLL availability, API behavior or PostgreSQL/Wine compatibility. The old accepted VC runtime DLL hashes are evidence, not automatic admission for this newly built profile.

Once exact new inputs have been reviewed, the coordinator can invoke (these are templates, not a dispatch):

```powershell
python native-android/engine/auth-interop/deployment/hosted_manual_atlas_compile.py build --source-root $PWD --expected-commit EXACT_SOURCE_SHA --output NEW_RUNNER_TEMP_OUTPUT --host-qualification native-android/engine/auth-interop/evidence/manual-atlas-full-recipe-20261017/qualification.json --expected-host-qualification-sha256 EXACT_HOST_RECEIPT_SHA --toolchain-lock REVIEWED_TOOL_LOCK.json --expected-toolchain-sha256 EXACT_TOOL_LOCK_SHA
python native-android/engine/auth-interop/deployment/hosted_manual_atlas_compile.py admit --source-root $PWD --stage RETAINED_OUTPUT --expected-receipt-sha256 EXACT_RECEIPT_SHA --expected-binary-sha256 EXACT_DB_PE_SHA --expected-toolchain-sha256 EXACT_TOOL_LOCK_SHA
```

Admission rechecks historical Git helper/recipe inputs, the complete candidate map, all retained files, exact fetch/patch/configure/build argv, corpus/source profile, final source/dependency stability, cache/compiler versions, generated bytes and PE identities. Cross-host comparison normalizes path separators. Successful admission remains caller-pinned compilation only. Actual persistence, original nondevelopment version/checksum observations, real authenticated shard/cookie handoff and Android/Thor execution are all subsequent qualifications.
