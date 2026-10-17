# Corrected DbServer binary recovery and isolated compilation

The accessible inventory found no complete corrected DbServer executable with a qualified source/binary receipt. Three committed top-level auth staging receipts explicitly report `patched_dbserver_built=false`; the reachable checksum-candidate source history introduces only host/Win32 fixture controls. Three preserved prior Auth login artifact ZIPs contain no complete DbServer member. Named executable searches in the preserved recovery roots found no complete corrected PE. This bounded inventory does not prove that no unpublished binary ever existed. Exact archive, receipt and existing harness identities are retained in `../evidence/db-checksum-build-preparation-20261017/recovery-inventory.json`.

The existing Win32 `candidate-policy.exe` is 122,368 bytes, SHA256 `56680e359340e29d5515a423c138120c919070f8f78b4244469329bfb324208e`; run `38946462964`, artifact `12066431903`. It is the already qualified 135-check synthetic policy harness, not a complete DbServer. Reuse it for that scope; this helper does not rebuild it, AuthServer, OpenSSL or either encrypted probe.

`hosted_db_checksum_candidate.py` prepares a new external archive of exact original source tree `f634e21e230009fa8edc91d15429cd4da69eee8c`. It changes only `Common/ClientLogin/clientcommLogin.c::clientCommLoginVerifyChecksum`, using the existing declared full-16-byte, missing-reference-refusal candidate. The complete original first login policy block remains unchanged. The helper builds only Win32 OptDebug `DbServer`, with MapServer and BeaconServer disabled. It copies the candidate PE, changed source, patch, manifest, CMake cache, host qualification and bounded build logs into a caller-owned output directory. Original checkout contents are never patched.

This is a standalone original **MSSQL** compile candidate. It has no PostgreSQL/Wine overlays or persistence fixtures, and cannot replace or qualify the accepted server runtime. Selecting and pinning those overlays for a future integration remains separate. Building this target does not qualify actual checksum initialization, nondevelopment version resolution, native/reference interoperability or live authenticated DB/Map login.

## Coordinator invocation

Use a fresh hosted `windows-2025-vs2026` runner with Python 3.12, CMake/Visual Studio 2026 and Git's patch tool. Configure `git config --global core.autocrlf false` **before** checkout. Checkout the exact reviewed commit. Do not add a service/SQL/startup step. Retain logs and receipt with an always-run artifact upload, including failure. Allow the configure/build bounds of 900/1,800 seconds plus cleanup/upload time; this experiment does not need SQL/ODBC installation, public client downloads or server data.

```powershell
python native-android/engine/auth-interop/deployment/hosted_db_checksum_candidate.py build `
  --source-root . --expected-commit $env:GITHUB_SHA `
  --output "$env:RUNNER_TEMP/db-checksum-build" `
  --host-qualification native-android/engine/auth-interop/evidence/db-handoff-profile-contract-20261017/db-policy-matrix.json `
  --expected-host-qualification-sha256 c17afbf163cccb5c924138efffe25e3d788c4f851cbc64b2a7988ccb42fd0503
```

After independently downloading and hashing the completed artifact, call `admit` with its externally pinned receipt and binary SHA256:

```sh
python3 native-android/engine/auth-interop/deployment/hosted_db_checksum_candidate.py admit --stage /private/extracted-stage --expected-receipt-sha256 RECEIPT_SHA256 --expected-binary-sha256 PE_SHA256
```

Admission checks every retained file, exact single source change, source/matrix association, exact four source-oracle result maps, successful build log records with exact bounded argv profiles and PE32 I386 console header identity. Every regular original archive member is hashed before extraction and checked again after the sole patch and after compilation; generated additional files are outside that original-file map. A retained source-file map binds all original paths and hashes, and any original source edit, removal or symlink blocks success. The repository HEAD, host receipt and nine helper/transitive source and pin inputs must remain identical before and after the build; admission rechecks the helper hashes. PE header validation does not execute or disassemble the binary and cannot independently prove its compiled policy. Compilation and matching-source provenance remain distinct from binary negative-case execution and service acceptance. The result leaves live DB login, accepted runtime compatibility and nondevelopment version observation false.

Local controls:

```sh
python3 -m unittest discover -s native-android/engine/auth-interop/deployment -p test_db_checksum_candidate.py -v
```

Eight host suites cover external staging, changed/missing/linked source refusal, exact corpus fields and policy provenance mutations, compile-only commands, mock build orchestration, every retained artifact mutation, explicit receipt/binary pin mismatch, altered service/source flags and local-host refusal. Additional controls mutate another archived original source, the repository HEAD and a transitive helper; all refuse compilation admission. Command mutations cover target, configuration, architecture, parallelism, source subtree and extra flags, and failure-path command recording is checked. Synthetic PE bytes are never executed. Release and ASan/UBSan qualification of the actual checksum policy is reused from the retained 1,056-check matrix rather than rerun unnecessarily. This change has not executed Windows compilation, a service, Android or Thor.

## Exact nondevelopment version-provider dependency

Original `getCompatibleGameVersion()` calls `getExecutablePatchVersionInternal(regGetAppName())`. Its precedence is:

1. A nonempty process `override_version` wins. The new experiment must leave it empty; a supplied override cannot establish installed version provenance.
2. If the executable is outside the installation directory **and** development data is in use, return `getDevVersion()` before reading `version.ini`.
3. Otherwise, the first version lookup reads `version.ini` from the process current working directory once. `getVersionIniInternal` finds `Version=` with case-sensitive `strstr`, then reads one whitespace-delimited token with `%s` into its 100-byte buffer. Later file edits do not invalidate this cached first result.
4. If no usable file result exists, query the current project registry version; absent data returns the literal `Could not find registry key`.

For a reproducible isolated profile, choose a new process with empty override, prevent the development-data branch through a source-qualified configuration, provide one bounded public `Version=TOKEN` file in its owned current working directory **before first lookup**, and observe the actual function result. Refuse the missing-registry sentinel, empty/development values and a different token. Do not fabricate a normal value from the PE/source hash. `dbinit.c` sets the app name to `CoH` and may later set `server_cfg.client_project`; capture that final source configuration.

A future version observation must carry the following explicit shape. These fields are dependencies, not a presently accepted receipt or authorization:

| Field | Required evidence |
| --- | --- |
| `repository_commit`, `original_source_tree`, `db_binary_sha256` | Exact reviewed candidate build and received running PE |
| `owner_generation`, `process_id`, `process_start_identity` | Fresh owned process lifetime; never a historical session |
| `version_provider_source_sha256`, `get_compatible_function_sha256`, `internal_provider_function_sha256`, `version_ini_function_sha256` | Exact original function/source identities |
| `override_empty`, `using_dev_data`, `executable_in_install_dir` | Source-defined branch facts; `override_empty=true` and no dev-return branch |
| `cwd_owner_generation`, `version_ini_sha256`, `version_ini_bytes`, `version_ini_token` | Owned CWD association, bounded immutable file loaded before first lookup; no private absolute paths in exported reports |
| `compatible_version_observed`, `observation_channel`, `observation_source_sha256` | Actual result from that same process and the source-qualified read-only observation channel |
| `first_lookup_after_inputs_installed`, `client_version` | Fresh cache ordering and exact bounded matching client version |

The original read-only `DBSVRMON_REQUESTVERSION` branch emits `getCompatibleGameVersion()` followed by `getExecutablePatchVersion("CoH Server")` on its connected monitor channel. It is a possible future observation source, not an executed or qualified monitor client. Its listener/packet/ownership protocol must be separately audited and exercised on the owned disposable server. Reading a declared JSON token alone cannot substitute for that runtime observation. Version proof also does not create a checksum reference alias or approve use of a graphical PE hash for native client interoperability.
