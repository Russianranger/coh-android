# M4 app integration report

Status: ARM64-runner guest qualification passed; milestone approval pending.
No physical Android surface or Thor gameplay result is claimed.

## Exit test and evidence

PORT-PLAN.md requires the app to run the ARM64 client in its existing runtime,
verified on an ARM64 runner with the same runtime files. Run
[40176336731](https://github.com/Russianranger/coh-android/actions/runs/40176336731)
at `63f091defc0a9c5fda78bb1420bfce73df59c4f8` passes app-source compilation,
assets, guest boot and interactive job 121118808157. The latter executes
creation, ordinary logout/committed SQL save, restart and reopen using the
same persistent profile and character. Both host-session validators pass,
with no forced quit/kill and no guest failure. Total elapsed time is 2805.644 s.

The downloaded interactive artifact 12593347536 matches the GitHub API SHA256
`24a4230600127b4d5f5bde58bfc270b875e9b625b4598dd01422fee6d16e7cb7`.
Selected fields and raw-report hashes are in
`evidence/m4-continuity-40176336731.json`. Source: artifact host-report.json,
creation/reopen host-session-report.json and latest-report.json.

The selected ARM64 executable is from run 40170942752, data from 40100355259.
Its SHA256 is `500cea5f1bae84d7c38cacda50c0b4c21410c9a24b82a5b5b322b3d6a1a50752`.
The test extracts the pinned app runtime from retained run 36920583713; it
builds no APK. x86 remains the default architecture; ARM64 is an explicit option.

## Corrections and review

Earlier guest creation succeeded but the host rejected newer receipt fields.
The adapter validates the host-owned manifest/content identity before the
legacy validators. Native patch 0076 on M3 fixes the signed text-selection
boundary that crashed reopen. Sol review 5642182878 then identified the
explicit-Finish/timeout-0 contract mismatch. Tested commit 63f091de validates
the host Finish identity/hash and guest receipt without rewriting the timeout,
while preserving time bounds, save, observer, network, cleanup and continuity.
Its committed evidence records 36 passing local app tests. The new live run
now reaches and passes final continuity rather than only guest completion.

## Remaining criteria and review request

The report deliberately retains m4_complete=false, android_surface_validated=false
and apk_built=false. Sol must assess the new Finish contract and live evidence
before milestone/merge approval. Review PR #7, tested code 63f091de, with runs
40176336731 (passing) and 40171292922 (prior contract rejection). Check that
Finish authentication, host deadline and downstream acceptance remain intact.

M3 still needs rendered Atlas and accepted replay/full-state/audio evidence;
its current Atlas run is 40176407354. This result cannot complete M3 or M5.
APK building/signing requires the explicit approval in HANDOFF.md section 6.
The later single-install Thor session is prepared in M5-THOR-PLAN.md; do not
request installation until its prerequisites and reviewer decisions are met.
