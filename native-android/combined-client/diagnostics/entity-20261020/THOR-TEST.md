# One observed Atlas entity — Thor test

1. Export the current diagnostics and stop the server normally. Install the
   signed 0.1.14 entity diagnostic over the existing app. Do not uninstall,
   clear data, change imports or replace the running server.
2. Start the existing server normally, launch the native client, choose **Test
   world handoff**, and select the same Atlas Park character once.
3. Look for an orange box. Its index/position come from the actual selected-self
   ALLENTS prefix; movement controls do not move it. Camera/scene selection center
   on that received coordinate. It is a crude diagnostic entity, with no costume
   or complete-world/ACK claim. Empty retained environment coverage is allowed.
4. Export JSON and the launcher diagnostic ZIP after at least 15 seconds with
   Wine, PostgreSQL and the native client running together. Retain `bodyparts_default`,
   `costume_continuation`, renderer `observed_server_entity` and memory diagnostics.
   The verified CLIENT count supplies 28 directly; no server-cache match or
   runtime lease is required. Check `bodyparts_default:[0,28]` and element 8
   (`count_validated`) of `costume_continuation`. The optional
   `bodyparts_server_cache_status` is advisory; a missing cache cannot block
   the count or pose box. Historical compact progress may still say stage 41.
5. Exercise Home/resume/Return and stop the server normally. Keep the final export;
   distinguish sampled process totals/missing PSS from system headroom and named
   native budgets. A new handoff attempt is required after pause.

Physical 0.1.13 submitted the real selected-self box (index125,1384draws,
zero GL errors), then cleared it on pause and completed both renderer contexts.
It remained at stage41 because the old server-file admission reported
`bodyparts_default:[3,0]` (missing file), with no costume continuation.
0.1.14 contains the client-authority correction absent from that APK. The next
live costume field remains to be observed; source fixtures stop at indexed
costume geometry strings. Retained server trace count28 is a consistency check.

The 0.1.13 process sampler observes Wine/Postgres/client together, but reaches
its32-process cap with two Wine metrics unavailable. Complete totals are null;
partial observed sums and older complete-snapshot peaks must stay distinct.
No sampler, decoded-message, scene, report or ServerMemoryPolicy cap is raised.

Earlier memory evidence: the retained Oct 19 ZIP records two Android LOW_MEMORY
(reason 3) exits on Oct 15 at 16:26:19 and 20:31:31 America/Chicago, status 0.
App PSS/RSS were 79,716/172,248 KiB and 59,936/165,236 KiB. Available server attempts
start Oct 16, so cannot explain those deaths. Latest 0.1.11 shows requested stop,
guest exit 0 and completed cleanup, with no recorded -9/137 process result.
444 later policy samples show no pressure stops and minimum headroom 7,512,121,344
bytes; 14 app samples peak RSS/PSS 208,277,504/99,427,328 bytes. Those later samples
exclude combined guest totals and do not disprove the earlier low-memory exits.
The new simultaneous-window process sampler fills that missing observation where
/proc permits it; partial coverage remains explicit.

Newer evidence in the version12/13 exports also records Android LOW_MEMORY
(reason3) deaths on Oct19 at23:08:17.925 and23:08:21.504 America/Chicago.
The earlier startup attempt lacks concurrent guest totals, so their cause is
not established. Later spare headroom and clean shutdowns do not disprove them.
