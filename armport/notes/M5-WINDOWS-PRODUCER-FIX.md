# Windows producer correction — 2026-10-29 CDT

Build [40805020119](https://github.com/Russianranger/coh-android/actions/runs/40805020119)
at `dd9d755bdfd5914a85bb42144ac3ee4bbaa4852b` passed nine jobs. The source job
prepared both actual donors and passed all eight extracted native cases plus
the specific unpatched missing-metrics runtime control for each variant.
Windows job [123247607771](https://github.com/Russianranger/coh-android/actions/runs/40805020119/job/123247607771)
failed before MSVC at 03:36:56 UTC (October 28, 22:36:56 CDT).

The downloaded job log identifies the precise exception:

```text
verify_bundle -> validate_predecessor -> game_device_diagnostic
  -> game_diagnostic -> dbserver_diagnostic -> diagnostic.py:10
ModuleNotFoundError: No module named 'fcntl'
```

This was a host import error, not evidence of changed source bytes or a failed
native build. Runtime/APK dispatch stopped. The attempted native evidence
upload contained no files because the build stage had not created its directory.

## Correction and preserved checks

`server_package.validate_predecessor` no longer imports Android process
orchestration for retained donor admission. It requires the identical accepted
raw manifest SHA-256 `ef1e5b1aa7cad69f2e25d286cc579531c86417d3f7f1a5de86843a350f4024cd`
before inspecting nested fields, plus the same producer pins. Thus every nested
contract and receipt remains authenticated by the exact complete raw bytes.
No new donor is admitted and no placeholder `fcntl` implementation is installed.
The modern historical contract and subsequent prepared-source/file/PE/import
verification remain in place. A separate test compares the host result with the
actual frozen `c86a5796` historical validator on POSIX.

Follow-up inspection found a second Windows issue: the cache-mode regex retained
the carriage return from `OFF\r\n`, rejecting a valid cache. Line parsing now uses
`splitlines()`, still requires one exact `OFF`, rejects missing/duplicate/ON or
space-suffixed values, and pins the original cache bytes without normalization.

The Windows job runs the fresh-process donor regression before source extraction.
Both native commands preserve their nonzero exit checks. Preflight logs are
always uploaded from a separate directory, preserving the producer's requirement
that its build output directory start absent. Native patches, upstream source,
runtime pins, signer settings and sequential compiler bounds are unchanged.

## Evidence and remaining gate

- 419 ArmPort tests passed using the installed javac module launcher and pristine
  historical baseline; 61 saved-startup/zoning/monorail tests also passed.
- Both real donors pass in fresh Python processes with POSIX modules and guest
  lifecycle imports denied. The old `6245372` retained reader fails on that exact
  lifecycle import; separately denying `fcntl` reproduces the CI exception with
  the real donor from the downloaded bundle.
- Actual source artifact 12870633271 was downloaded: 159,214,983 bytes, ZIP SHA-256
  `3a4da8ad601b1fdc22651e7967ca0060552afc11dd1f80bebb8cd2b9394e4654`.
  The complete tar bundle extracts and verifies using the fixed code on Linux,
  including both source inventories, original donor archives, animation inputs
  and CI fixture reports. This check does not execute the Windows compiler.
- Machine-readable evidence: `../evidence/0.13.46-windows-source-failure.json`.
  Native controls were executed by the original CI; local replay verifies their
  bound reports and source bytes, without claiming to rerun those controls.

The revised candidate includes sampler fixes from `6245372` and remains
0.13.46/code 61 because no APK has been produced for that reservation. Request a
new full serialized chain: build with `build_server_metrics=true`; runtime at
that same head with client/data/server IDs all naming that successful build;
APK with that runtime's `m4_run_id` and `server_metrics=true`. Stop on any failure.
Windows fixtures/compilation, retained runtime qualification, modern Thor testing
and Claude's exact-artifact handoff approval remain pending. No performance or
M5 acceptance claim is made.
