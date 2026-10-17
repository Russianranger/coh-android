The inventory collector fills the missing toolchain evidence for the proposed full manual PG/Wine compile. Nine local Python suites pass. No Windows inventory, compiler, CMake, dependency download or server execution has occurred in this qualification.

`windows_tool_inventory.py` reads existing installation files and Windows version resources. It never invokes cl, link, ml, rc, MSBuild, patch or CMake, and makes no network connection. Its existing hosted-source guard uses read-only Git queries to check the exact commit and original subtree. All output goes to a new RUNNER_TEMP receipt directory; installed tools, SDKs, repositories and profiles are read-only.

The collector selects a unique VS18 installation (or an explicitly named installed instance), reads its exact default toolset marker and locates Hostx64/x86 cl/link/ml plus the instance's MSBuild. It resolves the current Git and CMake executable paths and the Git installation's patch executable. It enumerates at most16 numeric Windows10 SDK versions from the registered installation root and records each SDK's x64 resource compiler, x86 kernel32/ucrt libraries and Windows header. Partial SDKs retain missing input names and receive no proposed lock.

The seven common executables plus each complete SDK's rc form the intended eight-tool candidate. Every primary executable has path, size and SHA256; cl and CMake versions come from VS_FIXEDFILEINFO, not compiler invocations. SDK representative file hashes are retained; this is not a full hash of every installed SDK file. All observations and the default toolset marker are hashed again and must remain identical. The exact source generation and helper bytes are also checked before/after. Errors retain bounded symbolic status, without raw Windows error messages.

Candidates use `coh-observed-windows-build-tool-lock-v1` and `requires_independent_review=true`; they are rejected by the compile driver's reviewed-lock schema. Collector success means the read-only observation completed. It does not mean a usable candidate exists: missing fixed version resources, partial SDKs or unsupported version shapes may leave the candidate list empty. Inspect the actual artifact before selecting any lock.

The coordinator may create a minimal new Windows inventory workflow after source review. No compiler build, OpenSSL rebuild, source staging/patches, external dependencies, databases or services belong in that workflow. A reasonable timeout is ten minutes and the output directory should be uploaded on failure as well as success.

```powershell
python native-android/engine/auth-interop/deployment/windows_tool_inventory.py --source-root $PWD --expected-commit $env:GITHUB_SHA --output "$env:RUNNER_TEMP/coh-reviewed-tool-inventory"
```

Independent artifact review must verify actual source/image identities, both matching observations, concrete version/tool ownership, the intended SDK and all eight tool hashes. Only then may the coordinator derive a separate reviewed-schema lock, retain the observation-to-lock binding and pin its exact SHA for a subsequent novel-profile compile. No build or runtime permission is emitted by this collector.
