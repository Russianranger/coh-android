# Thor diagnostic acceptance (0.1.5)

On 2026-09-28 at 01:24:05 UTC (September 27, 20:24 CDT), **0.1.5 passed the
physical Thor database and headless client diagnostic gate**. The user reported
both modes passed. The supplied archive contains the later combined client run,
which independently includes the complete database suite. The first database-only
run is user-attested; its separate report was not supplied.

The [selected acceptance receipt](android-evidence/accepted-thor-20260928.json)
preserves report/archive hashes and measured results. The original support archive
remains private. Its Android wrapper identifies AYN Thor, Android API 33 and the
accepted app version. The wrapper's runtime manifest hash matches the
[accepted hosted build](android-evidence/accepted-wine-threads-36364550345.json)
at `9dc58f62c58dc4fc5c01288071429bf2aa06d2f4`. All exported manifest content and
six guest-reported asset hashes match. The support export reformats manifest JSON,
so its raw byte hash differs from the embedded manifest. The installed APK was
not separately pulled and hashed. Guest metadata deliberately does not self-attest
Android execution; the Android wrapper supplies that provenance.

## Verified on the device

All **12 stages passed**, with no failures, in **55.344 seconds**:

- Native ARM64 PostgreSQL 18.6, the existing owned cluster, all 65 simultaneous
  stock DbServer ODBC connections, SQL/value/metadata checks and persisted data
  after a graceful restart of the same cluster.
- PE32 DLL and ODBC driver loading through Wine/FEX. The ready Wine prefix was
  reused with zero registration passes; initialization took 9.666 seconds.
- Headless OpenGL 4.3 through Mesa llvmpipe software rendering. Four RGB samples
  exactly matched red, green, blue and white; buffer swap succeeded.
- Synthetic keyboard/mouse messages and DirectInput device creation. DirectSound
  enumeration completed with zero audio devices; playback was not tested.
- Complete cleanup: all **30 process input/output captures closed**, PostgreSQL
  stopped gracefully, and the Wine prefix lock and socket were inactive.

The thread cleanup path observed **three dead leaders with live tasks** and
three owned worker witnesses. It sent three TERM signals and one KILL through
pidfds, with zero inspection failures and zero remaining owned groups. Wineboot's
capture was open when its leader returned and closed by final cleanup. This
confirms the repaired ownership path is needed and works on Thor. The report does
not inventory the exact device pipe writer; that descriptor-level causal proof
belongs to the separate native regression.

## Next work

Keep the installed **0.1.5** and its runtime. No replacement APK, reinstall,
runtime download or repeat of the successful diagnostic is needed for this gate.
The reused state proves a subsequent combined run, but does not establish app
reopening, Stop cancellation or suspend/resume behavior. These lifecycle checks
and peak memory measurements remain device work and can accompany the next
candidate: stop an active run, export its stopped report before it is overwritten,
then verify a new run succeeds; also switch away and return during active work.
A stopped run must report cancellation rather than a successful diagnostic.

The [first hosted M3 DbServer gate](ANDROID_DBSERVER.md) has now passed in
run 36369485666. A separate Wine build overlay applies the ODBC compatibility
changes to the real DbServer. Its persistence fixture and normal fixture-OFF
schema initialization/export/reload passed against ARM64 PostgreSQL; this does
not establish physical Android DbServer execution. The subsequent
[full hosted Atlas gate](ANDROID_GAME_RUNTIME.md#accepted-full-hosted-workflow)
also passed in run 36460005201, including both protocol saves, same-cluster
restart and exact-name resume. Do not repeat that completed gate as an unfinished
milestone. First hosted service readiness took 18 minutes 38 seconds; restart
readiness took 3 minutes 14 seconds, so device startup performance remains open.

The separate loopback DbServer package is
[hosted-qualified](android-evidence/accepted-dbserver-hosted-36460867428.json).
Continue with app integration and physical Android listener/runtime execution,
then the Stop/rerun, app reopening, suspend/resume and memory checks above.
The loopback package has not replaced the accepted Atlas donor 36451873322;
integrating it needs its own game/runtime validation before device acceptance.
Preserve the accepted stock Windows reference and immutable upstream source.

This acceptance does not establish CoH gameplay, Android surface presentation,
hardware acceleration, Cg shaders, physical controls or audible playback.
