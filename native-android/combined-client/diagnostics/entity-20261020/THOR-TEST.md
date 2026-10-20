# One observed Atlas entity — Thor test

1. Install the signed 0.1.13 entity diagnostic over 0.1.11/0.1.12. Do not uninstall,
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
   A successful BodyParts file hash supplies 28 directly; no runtime lease is used.
   A missing/different cache does not prevent the earlier entity pose box.
5. Exercise Home/resume/Return and stop the server normally. Keep the final export;
   distinguish sampled process totals/missing PSS from system headroom and named
   native budgets. A new handoff attempt is required after pause.

The app checks the actual imported common `data/bin/BodyParts.bin` locally, once
per handoff, against the offline-compared cache pin (only its dependency timestamp may differ). The pinned cache and
original `.bp` have 28 equal ordered rows. Retained genuine server traces show
2584 bytes/count 28 and the same 128-byte prefix, but contain no complete server
cache. Full device-file equality therefore remains a test result, not a fabricated
host receipt. See engine/body-catalog/OFFLINE_CACHE_TEXT_COMPARISON.md.

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
