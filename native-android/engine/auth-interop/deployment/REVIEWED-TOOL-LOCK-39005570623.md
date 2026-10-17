The actual read-only tool inventory is admitted from run39005570623/source d6ef33b3306c496e6d6a9ee2f8c9ab12ffdfbc05. The exact 4,986-byte artifact12090613318 has SHA256 a9435c960839c4a4b93174d527b5d1c294ed9f964ed507ccd943cd9676e40c23. Its raw CRLF receipt is retained unchanged with SHA256 9f34ad291572a4424d17f400f05b2b9aceaabefc2d2cce23fcecbe5235a9666b.

All61 reported helper identities are exactly the pinned Git LF blobs converted to Windows checkout CRLF bytes. The original workflow did not override Git checkout line endings. `admit_tool_inventory.py` verifies the complete61-file domain and records both original and actual hashes and lengths. It refuses a raw LF hash substituted into this actual receipt. No receipt or helper byte is silently normalized.

Actual pre/post tool observations match. The single complete candidate identifies image win25-vs2026/20261007.264.1, VS18 Enterprise/toolset14.51.36231, cl19.51.36260.0, CMake4.4.4 and SDK10.0.26100.0. Eight executable rows are preserved exactly; canonical Windows path strings are unchanged. The three SDK representative rows and toolset marker are bound too. The inventory invoked no compiler, CMake, patch, dependency fetch or service.

The derived reviewed-schema lock retains the same observed bytes/path/hash records and adds the exact inventory provenance and SDK representatives. Its LF JSON SHA256 is a70e878ad1f8872cc876987f6ec644f27bbf7c5ec98db528742f28ed5b098125. Six local admission suites pass, including the exact lock through `tool_lock()` with an explicit recorded-file observer and mutation controls. This validates consumer compatibility, not access to installed Windows binaries from Linux. The future unmocked Windows guard must rehash all8 executable and3 SDK representative files and refuse changed image/tool identities.

Independent F review of the actual inventory is retained separately in c5fa65001; source/derived-lock follow-up review is required before coordinator publication. The reviewed lock supplies a compile guard input. It does not qualify a new DbServer, persistence, Wine runtime replacement, real authentication handoff or Android/Thor execution.

The new compile workflow must set only these Git configuration environment values at job scope before actions/checkout, and keep persisted credentials disabled:

```yaml
env:
  GIT_CONFIG_COUNT: '1'
  GIT_CONFIG_KEY_0: core.autocrlf
  GIT_CONFIG_VALUE_0: 'false'
```

The driver now accepts and records exactly that singleton override or an empty profile, and rejects arbitrary/extra settings. It verifies actual helper bytes against raw LF host qualification pins before any source composition or compiler invocation. This preserves original manifest CRLF blobs too: disabling autocrlf prevents transformations of every tracked blob. Dependency checkout and patch operations additionally retain explicit `-c core.autocrlf=false`. No global Git configuration is modified.

After independent review, the coordinator can author one genuinely new compile-only workflow (not a retry of the MSSQL binary). Suggested timeout45minutes, fresh Windows-hosted output and always-upload receipt directory. Use the actual new publication SHA, not the inventory's historical source SHA:

```powershell
python native-android/engine/auth-interop/deployment/hosted_manual_atlas_compile.py build --source-root $PWD --expected-commit $env:GITHUB_SHA --output "$env:RUNNER_TEMP/coh-full-manual-pg-wine-compile" --host-qualification native-android/engine/auth-interop/evidence/manual-atlas-full-recipe-20261017/qualification.json --expected-host-qualification-sha256 c15813238fff23cff22984dd283981965a4fd1208932cb7e18fba6e2319568d6 --toolchain-lock native-android/engine/auth-interop/evidence/windows-tool-inventory-39005570623/reviewed-toolchain-lock.json --expected-toolchain-sha256 a70e878ad1f8872cc876987f6ec644f27bbf7c5ec98db528742f28ed5b098125
```

No AuthServer, DbServer, SQL, Wine, emulator or application startup belongs in this compile-only workflow. Successful compilation must later undergo exact receipt/binary admission and independent runtime qualification. The accepted fake-auth-only manual wait guard and all shipping profiles remain unchanged.
