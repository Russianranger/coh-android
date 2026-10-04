# City of Heroes Android handoff

**Current continuation: runtime setup memory protection (October 4, 2026 UTC).**
The user reports that running 0.13.4 Set up runtime interrupted all apps. No new
log bundle accompanied this report: neither Android LMK nor a precise failing
phase is confirmed. [Recorded report](android-evidence/setup-memory-0.13.4-user-report.json).
Accepted storage recovery and manual task completion remain accepted; do not
reset the profile or repeat those gates to diagnose this setup failure.

The next wrapper, 0.13.5, adds setup memory headroom checks, bounded pauses and
safe refusal under persistent pressure, bounded I/O/synchronization, effective
Stop during extraction, and interruption checkpoints with own Android exit
history. It retains the exact 0.13.4 runtime manifest and all 67 runtime payloads;
no additional runtime generation is required solely by this wrapper update.
A completed 0.13.4 generation is reused, while an interrupted staging operation
must complete verification before activation. Do not uninstall, clear data,
reimport assets or recreate THORHERO. Request only setup and its report before
another long Reopen; no device safety/speedup or system-wide LMK immunity is
claimed. [Setup-only instructions](COH-Atlas-Gameplay-0.13.5-testing.txt).

Local qualification passed **467 checks / 29 suites / zero skips / 160 source
pins**, including production guard, real archive cancellation, installer reuse
and publication refusal, Service heap/ownership/recovery and all retained prior
guards. All 19 authored Java sources are receipted (six changes plus one setup
guard). CI wrapper/signature/publication verification is pending; no native
rebuild or physical setup qualification is claimed.

The setup controller checks at admission, bounded I/O (1 MiB aggregate reads and
writes) or 250 ms between cooperative checkpoints. It keeps 512 MiB–1 GiB above
Android's low-memory threshold, adds 64 MiB resume hysteresis, and checks Java
heap headroom. A single pressure wait is limited to 15 seconds, with a 60-second
operation total. Memory-service/clock failure refuses further setup I/O. Stream
buffers are 64 KiB; every regular output file is synced at close, active large
files at 8 MiB, and cumulative 8 MiB write windows are paced by 25 ms. These are
cooperative limits: blocked OS I/O is not forcibly preempted and polling cannot
guarantee prevention of a system process kill.

Stop, persistent pressure, unavailable memory telemetry and heap exhaustion
leave only owned unactivated staging for a later admitted retry; its ready
marker is removed. Cleanup streams no-follow entries with depth/entry limits.
No protected profile, SQL data, import or prior runtime generation is retired.
Setup phases and original app version are durably checkpointed with bounded
records; interruption recovery exports the last phase and at most four own
Android process-exit records. The setup reservation spans terminal evidence and
wake cleanup, including same-process Service replacement, before another
operation can start. Surface frame arrays/bitmap are released before setup.

**0.13.4 published and independently payload-verified (October 4, 2026 UTC).**
[Download APK](https://github.com/Russianranger/coh-android/releases/download/coh-atlas-gameplay-v0.13.4/COH-Atlas-Gameplay-0.13.4.apk)
from source `6d16acf8330774e5fee4c0410c9cc56746d60b58`.
[CI 37171443387](https://github.com/Russianranger/coh-android/actions/runs/37171443387)
passed qualification and wrapper packaging, with no native build:
**374 checks / 25 suites / zero skips / 148 source pins**. APK is
**676,108,222 bytes**, the same size as 0.13.3; SHA-256
`5cfd2cd929467f1797d72a142cd39999c3d5dbceee65a02d4baf7bba287f2052`.
[Publication receipt](android-evidence/task-receipt-cleanup-0.13.4-publication.json)
records the actual public download, all 67 payload digests, 64 retained payloads,
corrected DEX/resources, exact server archive extraction, source pins and public
checksum/instructions. CI official SDK signature/version checks are bound to
identical public bytes; no separate local SDK rerun is claimed. The signer is
retained. One Java source/DEX, the reopen helper and its two manifests change;
all native payloads and the four prior startup improvements remain exact.

Install over the app, **Set up runtime once**, then **Reopen saved THORHERO** as
an explicit startup-only connection/timing check. Existing journal rows are
preserved and no task qualification is requested. Stop and export after
connection; a cancelled verdict without ordinary Save is timing evidence, not
an ordinary-save or gameplay pass. No reinstall, import or completed physical
gate repetition is required. [Testing instructions](COH-Atlas-Gameplay-0.13.4-testing.txt).
The prior generation remains available for rollback and reviewed storage cleanup.
Actual device startup improvement and the <=300-second target remain open.

The retained activity's static explanatory paragraphs still describe the old
task test. Follow the new startup-only status and 0.13.4 instructions; adapt that
static copy to the active mode on the next UI pass. Task controls are gated off
for the explicit startup-only mode. Do not replace/rebuild this qualified APK
solely for that legacy explanatory copy.

**Prior device result: 0.13.3 Reopen stopped on a stale task-helper receipt;
PostgreSQL login passed (October 4, 2026 UTC).**
[Failure receipt](android-evidence/startup-schedule-0.13.3-reopen-blocked.json)
pins `coh-atlas-gameplay-20261004-021301.zip`. The installed runtime and native
supplement match published 0.13.3. Persistent profile and client worktree were
reused, PostgreSQL durability/admin/fixture checks passed, and owned cleanup
plus graceful database shutdown passed. Wine, DbServer, Atlas and graphical
client never started; this result cannot qualify the startup speedup.

`ClientRuntime.removePreviousGuestOutput()` omitted the two fixed transient
outputs `character-task-contact.json` and `character-task-completion.json`.
The retained guest correctly refused a leftover receipt. The export does not
include that receipt's exact filename or previous session, so do not infer
either. Retire these session outputs under the existing prelaunch operation
lock and retain all current-session delivery/save/readiness guards.

The accepted manual-task run also recorded a task row, while the old one-task
diagnostic requires an empty journal. The approved next activity is startup
timing, so explicitly select ordinary saved-character Reopen, preserve existing
task rows and do not reopen the accepted task gate. The 0.13.4 correction is implemented with an explicit startup-only flag;
**374 checks / 25 suites / zero skips / 148 source pins** passed locally.
CI publication passed. Native startup optimizations and all earlier
physical acceptances remain retained. Changed reopen helper
requires one runtime setup; no reinstall, data clear, import or character
recreation is justified. [Continuation instructions](COH-Atlas-Gameplay-0.13.4-testing.txt).

**0.13.3 published and independently payload-verified (October 4, 2026 UTC).**
[Download APK](https://github.com/Russianranger/coh-android/releases/download/coh-atlas-gameplay-v0.13.3/COH-Atlas-Gameplay-0.13.3.apk)
from startup source `dee916f80e9e336f374f31228535afdbe2c928ca`.
[CI run 37167835800](https://github.com/Russianranger/coh-android/actions/runs/37167835800)
passed Windows native build, qualification and retained-signer publication:
**331 tests / 23 suites / zero skips / 141 source pins**. Public APK is
**676,108,222 bytes**, only **807,084 bytes** larger than 0.13.2; SHA-256
`2626dcabcc9d69bfd1b9ad723e9748746df77e93d565a0fb1740eeff4b516709`.
[Publication receipt](android-evidence/startup-schedule-0.13.3-publication.json)
records the actual downloaded 67-payload audit, ZIP CRCs, retained DEX/resources,
server archive extraction and native/source pins. CI official SDK signature and
version checks are bound to these identical public bytes; no separate local SDK
rerun is claimed. The normal Win32 DbServer supplement is the only native rebuild.

Install over the existing app, **Set up runtime once**, then do one saved-hero
startup/connection timing session and export. Keep assets/profile; preserve all
accepted gameplay/storage/recovery gates. No new physical speedup is claimed.

Publication tooling follow-up: the frozen 0.13.3 manifest producer/checker uses
frozenset insertion order for its two new native keys. A new
`tools/android/interactive/audit_startup_schedule_public.py` companion preserves
the actual client manifest's order without changing values, allowed updates or
original derivative guards; four mutation/order checks and independent review
passed. The actual client hash matches its runtime pin. Sort added keys in both
producer/checker for the next release; do not rebuild or replace this APK solely
for this checker serialization issue.

**Current authorized priority (October 4, 2026 UTC): reduce server startup
further before the next gameplay milestone.** The user selected options **7
(avoid decoding unchanged world assets), 13 (skip the unused local Launcher
wait), 18 (overlap independent preparation) and 4 (move client texture indexing
after server readiness)**. Preserve the accepted manual task and all earlier
physical gates; do not restart the proposed progression sequence yet.

The published 0.13.3 uses a pinned world reuse receipt, a narrowly guarded
DbServer manual-Atlas launcher-wait bypass, and a single texture preparation
worker after actual Atlas readiness which overlaps only the independent PE32
runtime probe. Server and client heavy initialization remain serial, and the
worker joins before client launch or cleanup. Game, MapServer, renderer,
imported content, prepared definition/message caches and the animation pack
remain retained. This build has not yet established physical speedup.

[Prior warm-run baseline](android-evidence/startup-schedule-0.13.3-baseline.json)
pins the uploaded 0.13.2 reopen: Atlas readiness **11m22.726s** from guest start,
native connection **23m19.616s** from Android run start, DbServer **6m53.111s**,
Atlas **3m20.429s**, client startup **10m09.694s**, and warm texture preparation
**16.585s**. The previous 89.7-second texture observation was a cold preparation,
not a guarantee for every run. World reuse avoids repeatedly decoding 318.6 MB
of unpacked resources. The <=300-second Atlas-readiness target remains open.

The updated source-bound runtime requires **one Set up runtime** to activate
the changed helpers/DbServer. Keep the current installation, imported assets
and saved profile; do not reimport or recreate THORHERO. The prior generation
remains for rollback and can later be retired with reviewed storage cleanup.
Repeated setup of the same new manifest must reuse its installed generation.
[Focused startup instructions](COH-Atlas-Gameplay-0.13.3-testing.txt) request one
startup/connection timing session and its export, without repeated task,
movement, safe-ground, contact, storage or recovery qualification. Main remains
preserved; continue the same draft PR and branch.

**Latest physical acceptance (October 4, 2026 UTC): manual task acceptance and
completion passed on Thor in the installed 0.13.2. The user completed the task
through normal in-game play without the completion helper and explicitly asks
that this be accepted regardless of the diagnostic verdict.**
[Acceptance receipt](android-evidence/thor-0.13.2-manual-task-accepted-20261004.json)
pins `coh-atlas-gameplay-20261004-003136.zip` and preserves the original reports.
Close manual task acceptance/completion as successful; no repeat is required.
The user reports that this prevented use of the left-side helper controls.
Record that as a separate diagnostic UI follow-up, not a failed gameplay gate.

The native connection event confirms the previously saved THORHERO (character
1, COHLOCAL) reopened on Atlas with preserved identity. The wrapper's narrow
authored-task observer reported a task outside its finite simple-task contract;
its accepted/completed events and completion-command receipt were absent. The
run was cancelled and owned cleanup passed. These diagnostic facts do not
overturn the user's manual gameplay acceptance or establish a game regression.
The exact task identity, forced-command path, reward turn-in, combat and mission
maps are not newly qualified by this acceptance. No ordinary Save or task-specific
committed SQL proof was captured in this run. Carry task/progression persistence
into the next ordinary save/reopen checkpoint without repeating the accepted
manual task. Prior character save/persistence acceptance remains valid.

**Proposed next gameplay sequence, not a previously approved numbered plan:**

1. Remove the helper-control obstruction to normal play and ordinary Save;
   validate contact reward turn-in/next-task progression and its save/reopen.
2. Validate training, level/power progression and power-tray behavior.
3. Qualify authentic generated Atlas beacon provenance, structure, world CRC
   and native graph loading before claiming moving-NPC pathfinding/combat.
4. Validate basic combat and power effects, then instanced mission entry,
   objectives, exit/Atlas return and saved progression.
5. Validate ordinary graphical zone transfers and persistence across maps.
6. Complete missing costume assets (including Ms. Liberty), broader terrain,
   materials/minimap and collision coverage.
7. Complete offline-app reliability: backup/restore into a clean profile,
   airplane-mode play, repeated transfers and a sustained two-hour session.

Server startup remains the main performance priority: the <=300-second Atlas
readiness target is open. Retain shipped options 1, 2, 8, 3 and 9 and the accepted
startup improvement; the installed animation pack has no controlled physical
speedup measurement yet. Hardware renderer acceleration remains deferred;
audio, broader services and eventual native ARM64 conversion remain future
scope. Do not reopen accepted setup/import, graphical login/creation, ordinary
save/reopen, movement/camera/jump, indoor/outdoor traversal, contact dialogue,
storage or fresh-profile recovery milestones. No app changes, runtime refresh,
asset import or new APK accompany this documentation acceptance. Main remains
preserved and PR #1 remains draft on the existing continuation branch.

**Prior physical acceptance (October 3, 2026, 23:48–23:50 UTC): 0.13.2 fresh
character recovery and storage inventory passed on Thor. The user reports
“Everything worked including storage, still need to do the tasks.”**
[Accepted evidence](android-evidence/thor-0.13.2-storage-recovery-passed-20261003.json)
pins both uploaded files. Android and guest creation reports both passed with
no guest failures. THORHERO entered Atlas, ordinary logout/timer was observed,
the character was disconnected before read-only SQL proof, and committed rows
contain one character, seven power rows and fourteen costume parts. Three fresh
post-save Android captures passed; Finish and graceful PostgreSQL/Wine/owned
process cleanup completed, with no cleanup block. The profile is READY. Treat
the deleted installation recovery as complete; do not recreate the character.

Storage inventory completed without errors over **578,696 entries**, verified
the current runtime and allowed reviewed cleanup. Allocated app files total
**10,878,041,088 bytes (10.88 GB)**: current runtime 3.81 GB, protected character/
server/Wine/cache state 2.93 GB, and protected imports 3.45 GB. There are no older
runtime generations in this fresh installation. Only two recognized component
downloads and one older report are candidates, totaling **673,447,424 bytes
(673.4 MB)**. This upload is an inventory, not a cleanup-execution receipt:
the user accepts storage functionality, but deleted entries and actual freed
bytes are not measured. Do not call the former 62 GB installation explained or
its missing data reclaimed by this scan. No further scan/recovery repeat is
needed for the task gate. A setup reuse receipt was not included in these files;
keep quantitative repeated-setup growth unclaimed.

This first-profile run reached Atlas readiness at **15m36.196s** after guest
launch and the client startup gate at **25m46.194s**. Client data worktree reuse
took 0.153s; initial Wine setup took 64.872s, DbServer startup 479.574s, Atlas
startup 198.116s and client startup 607.049s. The 5,878-animation pack installed
and loose fallback inputs remained preserved. These are phase observations,
not a controlled option 9 speedup comparison. Preserve prior startup findings.

The next gate after this recovery receipt was the fixed authored-task path in
[0.13.0 task instructions](COH-Atlas-Gameplay-0.13.0-testing.txt). The October 4
manual acceptance above supersedes that request: do not repeat acceptance or
completion merely to satisfy helper-command receipts. The creator run had
`task_gate.required=false` and supplied no task proof; the newer user acceptance
supplies the manual gameplay verdict. Task persistence moves to the next
progression/save checkpoint. Combat, mission maps and contact reward turn-in
remain separate scope.

**Current recovery publication (October 3, 2026): 0.13.2 is published and
independently verified from `c0d10f8cd873449962f5a723d489b9ead18642d0`.
The user reported 62 GB app storage,
a storage scan crash after about two minutes, a subsequent gameplay crash, and
then uninstalled the app. Setup and import succeeded on the new installation;
the uploaded reopen run failed before PostgreSQL, Wine/server or client startup
because the saved character profile was absent.**
[Reviewed evidence](android-evidence/thor-0.13.1-reinstall-failure-20261003.json)
pins the upload. Its 289.23-second client worktree preparation completed before
the missing-profile refusal. No pre-uninstall crash trace or exit reason survives
in this bundle; do not call the earlier crash an established OOM or regression
of the accepted gameplay milestones. Diagnostic exports are not SQL backups.

The 0.13.2 Android recovery derivative is qualified on the existing
continuation, retaining all 65 runtime payloads, manifest bytes and signing key.
Storage traversal now streams descriptor-anchored entries; cleanup planning
uses a bounded on-disk postorder journal instead of retaining every node in
memory. Fixed inode/memory limits fail closed. Progress is persisted every five
seconds and on phase changes; cancellation retains ownership until the worker
finishes, and interruption diagnostics include the last checkpoint plus bounded
own-process Android exit reasons. An incomplete or interrupted scan cannot
authorize cleanup. Current state/import/cache protection is unchanged.

Same-manifest runtime setup already reuses its installed generation. The known
cumulative mechanism is retained full generations across changed manifests,
along with downloads and reports; the source alone does not attribute the
62 GB or prove a new full copy per setup of the same build. New setup receipts
distinguish reuse from installation and record bounded generation counts,
downloads, extraction/copy counters and filesystem available bytes. Filesystem
available-byte differences are not an allocated per-app inventory.

Missing-profile reopen is refused before expensive guest staging. The UI offers
explicit fresh THORHERO creation only when the entire profile is absent; an
existing, incomplete, linked or unreadable profile is protected. The guarded
native creation route uses ordinary logout/save. The task gate remains required
on subsequent reopen. Only this deleted installation needs fresh creation;
prior physical acceptance remains accepted. Install the update in place, keep
the successful setup/import, export the storage/setup receipts and fresh creator
save report, and stop before another long task run. See the
[0.13.2 instructions](COH-Atlas-Gameplay-0.13.2-testing.txt). Device recovery and
storage inventory are now accepted above; measured reclamation remains pending.
Main remains 04d62616 and PR #1
remains draft on `codex/character-persistence-continuation`.

[CI 37147463123](https://github.com/Russianranger/coh-android/actions/runs/37147463123)
passed qualification and APK/publication: **489 checks, 32 suites, zero skips,
209 source pins and all 18 Java sources compiled against Android 35.** Native
animation/task packaging and the historical 0.13.1 publication jobs were
correctly skipped. The public APK was downloaded separately and passed every
actual payload/DEX/resource digest and ZIP CRC, exact manifest conservation,
real server archive extraction, official retained v2/v3 signer, alignment,
ABI/version and version-only Android binary manifest comparison.
[Publication receipt](android-evidence/storage-recovery-0.13.2-publication.json).

[Download 0.13.2](https://github.com/Russianranger/coh-android/releases/download/coh-atlas-gameplay-v0.13.2/COH-Atlas-Gameplay-0.13.2.apk).
Public APK: **675,301,138 bytes**, only 12,288 bytes larger than 0.13.1;
SHA-256 `28e3eda8dbc3982bc42d42dee6ab4f35e985d96af31bff4a2c691b806a207e1f`.
The user-reported 62 GB concerns installed data, not a multi-gigabyte APK.
The host stress scan/deletion covers 300,000 lazy entries and 1,000 hard-link
pairs under a 48 MiB heap. The repeated-setup fixture preserves five identical
setups' runtime bytes/inodes/mtime with zero extraction/copy/download work.
Neither fixture establishes Thor scan responsiveness, actual reclamation or
the cause of the deleted installation's crashes. Existing runtimes/imports and
accepted physical milestones must remain intact.

**Previous storage publication (October 3, 2026): 0.13.1 is published and independently
verified from `5252595717a1965a76251d4110725185bbcbbe20`. It adds idle-only storage
inspection and explicitly reviewed cleanup for the user-reported 57.44 GB app
usage. [Run 37129906760](https://github.com/Russianranger/coh-android/actions/runs/37129906760)
passed both jobs: 384 host checks across 28 suites, no skips and 201 source pins.
PR #1 remains draft on the same continuation; main remains 04d62616. Device
cleanup and actual recovered space remained unmeasured at publication. The
0.13.0 physical task/save test was then underway; the subsequent crashes and
uninstall are recorded in the current recovery findings above.**

[Download the storage update](https://github.com/Russianranger/coh-android/releases/tag/coh-atlas-gameplay-v0.13.1)
with [its instructions](COH-Atlas-Gameplay-0.13.1-testing.txt).
Public APK: 675,288,850 bytes, SHA-256
`7652106de29838389b012aee802ccb784c6fc956dffe66d566773e1eb40bd9d3`.
It adds only 20,480 bytes to the previous APK. All 65 runtime payloads and the
runtime/client manifest bytes are exactly 0.13.0, retaining the signer,
93 startup caches, 5,878 animation pack and all task/input/save behavior.
No runtime refresh, reimport, new native preload or repeated physical test is
required. [Publication receipt](android-evidence/storage-cleanup-0.13.1-publication.json).

Runtime setup creates a new `m2/runtime-<manifest SHA prefix>` for changed
manifests and previously retained older full Linux/Wine/PostgreSQL/asset trees.
Component downloads and completed support-report directories also accumulate.
These are candidates rather than a measured attribution of the 57.44 GB.
Storage and cleanup → Scan storage reports actual allocated blocks and apparent
file lengths. Review selected cleanup lists categories, paths and estimates;
Clean selected performs deletion only after a complete unchanged rescan and
verified current runtime. Unknown or unsafe identities disable or exclude
cleanup. Errors stop remaining deletion and report partial progress. The
separate JSON export preserves the latest gameplay report. Scan/cleanup/export
share idle operation ownership with gameplay/setup/import; fd-anchored deletion
and literal symlink digests guard path changes. Scans have entry/depth/time and
memory bounds; partial scans cannot authorize deletion.

All `client/state` (character/PostgreSQL/Wine, cache/worktree anchors, raw
evidence), all imported generations, current runtime, protected symlink targets,
latest report and newest three report directories remain protected. Cached
component removal can require a future download on a genuine runtime change.
No automatic pruning occurs. The device inventory and Android Settings figures
before/after cleanup will guide any later state/evidence retention work.
Independent downloaded-public-byte audit passes every payload/DEX/ZIP CRC,
actual server archive extraction, original animation envelope/header closure,
official v2/v3 signer, alignment/ABI/version and version-only binary manifest
changes. Original 0.13.0 publication and accepted gameplay progress remain below.

**Retained gameplay publication (October 3, 2026): 0.13.0 is published and independently
verified from `53c885896e9b4d838be0f36a1f09237f04c08a00`. It implements the newly
authorized option 9 and the task acceptance/command-completion/ordinary-save
gate. [Run 37125084672](https://github.com/Russianranger/coh-android/actions/runs/37125084672)
passed all three jobs. PR #1 remains draft on the same continuation branch;
main remains `04d62616e2e1b41b10f35a04d4c798e43680d5ba`. New physical task/save and
Thor startup results are pending; all accepted milestones below remain valid.**

[Download 0.13.0](https://github.com/Russianranger/coh-android/releases/tag/coh-atlas-gameplay-v0.13.0)
with [the new testing instructions](COH-Atlas-Gameplay-0.13.0-testing.txt).
Public APK is 675,268,370 bytes, SHA-256
`18cffb361df26076c10f9c020548f384d10c21f8462ed06e77e9cae5c00de4d1`.
See [the publication receipt](android-evidence/task-gate-0.13.0-publication.json).

The server-private Pig v2 pack preserves all 5,878 retained animation files,
names, timestamps, cached native headers and bodies. Its 97,084,456 bytes have
SHA-256 `465d69a266f2b07afd800b8a7bd3f5e63fa16a24955391f826264d7f8d3a968b`.
Original loose animations remain the fallback. Installation outside the stable
server data cache retains all accepted 93 definition/message bins and cache
identity. Native client/server, runtime, driver, world/avatar data and Wine
component timestamps are unchanged. No FEX upgrade or other startup option is
included in this pass.

Actual stock MapServer loose, cold-packed and warm-packed preloads completed
normally with exact cache/input conservation, packed animation content reads,
no loose animation reads in packed phases and traced Wine-prefix quiescence.
Native proof is reverified before build and publication. Traced host preload
intervals were 232.204s / 192.199s / 191.128s. These establish host consumption
and a host improvement; they do not predict Thor savings. Original inventory
byte preservation does not assert all tracks were selected during preload.

The new gate opens Matthew Habashy's ordinary dialogue through the fixed stock
`/contactdialog Contacts/Atlas_Park/Matthew_Habashy.contact` helper. The user
manually accepts **What Was Lost / Part One: Demons and Gangsters** (`Mission1`,
five Hellions), captures its accepted journal view, and invokes the fixed stock
`/completetask 0` helper once. Native task/arc logs, owned command receipts,
authored SQL attribute mappings, one active task and actual bounded reward
credit must agree before completion. Three fresh captures of each phase are
required before ordinary Save. The same completed task state and credited
XP/contact points must persist with preserved identity, class/origin/level,
powers and costume. The previous final-logout position correction is included.
Combat, missing-NPC clicking, reward turn-in and later story progression are
not required or claimed. Existing tasks are never cleared or replaced to make
this gate pass. Keep the current profile, imports and THORHERO; refresh runtime
once, perform this new gate, then Finish/export after Saved character verified.

Only the task profile's private logging enables stock entity level 2 for
Storyarc:Add; legacy reopen behavior remains unchanged. SQL remains read-only
game evidence. Host qualification passes **308 checks across 24 suites with no
skips and 190 source pins**. Independent actual public-byte verification passes
all 65 payloads, DEX/CRC, donor conservation, original animation/header closure,
real guest archive extraction, retained official v2/v3 signer, alignment,
ABI/version, version-only binary manifest changes and public release assets,
checksum and instructions. Public 0.12.1 remains unchanged. The accepted
physical checkpoint below remains authoritative and must not be repeated.

**Current physical checkpoint (October 3, 2026): The user accepts the 0.12.1
startup improvement and ordinary NPC contact/dialogue test. Sunstorm and Merit
Reward Informant opened readable dialogue and processed normal responses.
Ms. Liberty remains an incomplete female costume asset defect, not a reason to
repeat the accepted general contact test. The app's failed result came from a
stale position comparison during ordinary save. A narrow observer correction
and regression replay are included in the published 0.13.0 update; the published
0.12.1 APK remains unchanged. PR #1 stays draft and main stays 04d62616.**

The supplied `coh-atlas-gameplay-20261003-110806.zip` binds the Thor session
`cb216f7fcefc4ad1b4e9f059b2128df8`. The six exported contact PNGs have verified
hashes and two completed, identity-bound capture batches. Native logs show
Sunstorm opening at 11:04:20 UTC and closing at 11:04:42, and Merit Reward
Informant opening its `MeritReward` script at 11:05:40, processing an information
response at 11:05:55 and closing at 11:06:07. The user's extra screenshot shows
its information page after the initial page. The Patriot exploration badge is
visible and user-attested; its persistence is not independently established.
Mission acceptance/completion, training, NPC pathing and combat remain separate.

| Measured endpoint | 0.12.1 from session start |
| --- | --- |
| DbServer ready | 10m45.471s |
| Atlas server ready | 14m35.812s |
| Client menu/main loop | 23m56.276s |
| Local login verified | 24m15.587s |
| THORHERO connected | 25m39.175s |

The accepted 0.11.6 server baseline was 21m50s; this run reaches Atlas about
7m14s earlier. The user's approximate 24-25-minute boot and 4-5-minute perceived
improvement are retained alongside the measured endpoints. All 93 shipped
server caches appear in native loader traces; 91 were seeded and two existing
bins retained. First-use server staging still costs 410.218s and client startup
556.981s. Wine's expected first-transition registration costs 65.423s. The new
server data cache was returned after owned cleanup with credentials removed,
so a later ordinary run can qualify reuse. No warm-start timing or five-minute
server-target pass is claimed; no extra startup-only physical run is required.

The false save rejection compared committed SQL against the 11:06:08 periodic
sample `(121.10, -768, -702.51)`. Ordinary logout expired and disconnected at
11:06:37; its final native position `(112.468750, -768, -660.765625)` agrees with
SQL `(112.461586, -768, -660.7662)` at 11:07:48, within 0.008 units. Independent
SQL-log analysis preserves the selected `ents`/`ents2` rows, seven powers and
fourteen costume parts except expected LoginCount 7 to 8. Original failed flags
are retained: no Saved-character-verified event or Finish occurred. Cleanup
passed. The fix prefers the final own-player, map-1, same-route/same-timestamp
ordinary-logout location while retaining fresh native producer, request/session,
protected-row, SQL, fall-floor and optional-recovery gates. A regression uses
real exported log lines and explicitly synthetic delivery time because the
private command receipt was not exported. It does not fabricate physical proof.

The optional contact observer also missed stock `BuildNumber` suffixes and the
two NPCs outside its original name list. It now recognizes bounded stock
suffixes and the pinned authored Sunstorm/information-NPC contracts. Merit script
responses use contact handle zero; those are deliberately unclaimed by this
ordinary-handle observer. Visible dialogue/progression remains user-assessed.

Ms. Liberty's live client log reports missing female pants, chest, head, boots,
hair, belt and shoulder geometry plus textures; the retained avatar supplement
covers default male assets. Supply/verify her complete matching costume
requirements in later asset work. Her specific interaction and complete NPC
rendering remain unverified. Missing animations are not claimed.

The observer correction passes **88 focused checks**, including exact native and
authored data contract pins, with no skips. The correction is now packaged in 0.13.0;
the installed/public 0.12.1 behavior is not changed.

See [the physical acceptance and diagnostic receipt](android-evidence/thor-0.12.1-contact-startup-accepted-20261003.json).
Preserve prior accepted camera/jump/outdoor/recovery and persistence milestones.
The next new gameplay gate is bounded task acceptance/completion/save,
using the corrected observer in the published 0.13.0 build; this does not require
replaying accepted contact dialogue. Current published 0.12.1 remains available.

The retained publication checkpoint follows:

**Current (October 3, 2026): 0.12.1 is published and independently verified. It
implements the authorized startup options 1, 2, 8 and 3: exact server/English
message caches, stable verified client/server data roots and cache identities,
and trusted Wine component timestamps. Native client/server, world/avatar,
client caches, driver and contact behavior remain retained. Physical Thor
startup timing, contact dialogue and ordinary Save without recovery remain
pending; no five-minute startup or device speedup is claimed. GPU work remains
deferred. PR #1 remains draft and main stays 04d62616.**

[Download 0.12.1](https://github.com/Russianranger/coh-android/releases/download/coh-atlas-gameplay-v0.12.1/COH-Atlas-Gameplay-0.12.1.apk).
Published from `1fcabfa28f1f32a8c78de2cac496d6647fd376a9` in
[run 37116009802](https://github.com/Russianranger/coh-android/actions/runs/37116009802),
with all four jobs successful. The public APK is **625,055,087 bytes**, SHA-256
`fee8880a53916e4ff746d67c8a6ab22f3f0cf2ab7779198cef59035ef4d6bf29`,
version code 14, with the existing app ID and signer. Independent v2/v3 signature,
public payload/CRC, retained-byte and release checks pass. Focused qualification
passes **344 checks** and binds **199 source files**. See
[the publication receipt](android-evidence/startup-caches-0.12.1-publication.json)
and [the implementation scope](ANDROID_STARTUP_CACHE_REUSE.md).

The exact **29,825,263-byte** cache archive contains **90 Parse6 caches and three
English MessageStores**. Hosted native generation and consumption reached
preload, retained identifier files, exited normally and completed bounded Wine
waiting. Independent consumption evidence shows all 93 cache files read,
unchanged cache bytes, no scoped source-content reads and no cache writes.
An additional host-only Wine helper-lock observer inspected the stock `/tmp`
directory while this Ubuntu host used `/run/user/1001/wine`; that extra lock-path
claim is invalid. It does not invalidate the native exit, wait, identifier,
cache-hash or consumption evidence and is not embedded in the APK. A corrected,
consumption-only supplemental check of the exact public cache bytes passed in
[run 37117800033](https://github.com/Russianranger/coh-android/actions/runs/37117800033)
at `71e4568b5af32c394867e9f779f4d27ee898cf60`. Two independent audits verify
37 source pins, 96 evidence files, all 93 cache reads, unchanged identifiers,
cache bytes and normalized dates, and no scoped source reads or cache writes.
The actual traced `/run/user/1001/wine/server-801-9c3091` lock is unheld after
initialization and after normal owned native exit; bounded `wineserver -w` returns
zero with empty diagnostics. Corrected host qualification passes **365 checks**
and binds **202 source files**, separately from the original APK qualification.
This adds independent consumption quiescence evidence; it does not retroactively
observe the original generation lock or replace runtime timestamp proof.
Public APK/cache bytes and original qualification/build reports remain unchanged.

Install over the existing app, preserve imports and THORHERO, and refresh runtime
once. Follow the
[short 0.12.1 contact test](https://github.com/Russianranger/coh-android/releases/download/coh-atlas-gameplay-v0.12.1/COH-Atlas-Gameplay-0.12.1-testing.txt)
with ordinary Save and verified Finish. Return to Safe Ground remains optional;
F remains Follow. The accepted 0.11.6 camera, jump, outdoor, persistence and
safe-ground tests must not be repeated solely to reconfirm them. The startup
target remains at most 300 seconds from session start through Atlas server
readiness, including required preparation; this build has no physical timing
result yet.

The published 0.12.0 checkpoint follows (its startup deferral is superseded above):

**Current: The physical 0.11.6 run passes existing-character reopen, ordinary save and cleanup. The user accepts the smoother client as adequate for testing. Server startup remains slow and optimization is deferred with a target of five minutes or less. The 0.12.0 stationary-contact candidate removes mandatory ground recovery, keeps its optional button, and records bounded contact views/native initiation evidence. The public APK, retained signer and exact payload/source closure are independently verified. PR #1 remains draft; main stays 04d62616.**

The supplied `coh-atlas-gameplay-20261002-214857.zip` verifies THORHERO ID 1 /
COHLOCAL, seven power rows and fourteen costume rows, ordinary logout and
committed SQL save, verified Finish and clean owned-process shutdown. The
user reports smoother, tolerable client play; no sustained FPS benchmark or
complete terrain/materials acceptance is claimed. See [the accepted physical
checkpoint](android-evidence/thor-0.11.6-client-accepted-20261002.json).

Session start to DbServer readiness took **10m57s**; Atlas server readiness took
**21m50s**, followed by **9m46s** of client startup. First-use server data staging
cost 411.258s. These measurements support the user's unchanged-server-startup
assessment. Future server work should target **at most 300 seconds from session
start to Atlas server readiness**, including required preparation. This work is
explicitly deferred; GPU acceleration remains deferred as well.

The next playable checkpoint is ordinary stationary-contact interaction.
Ms. Liberty beside the Atlas statue and City Representative inside City Hall
are authored `PL_StandStill` contacts. The pinned client's cursor/A-left-click
path sends `CLIENTINP_TOUCH_NPC` to normal contact dialogue processing without
requiring a beacon graph. F is Follow, so no invented Interact binding or chat
command is introduced. Use the [short 0.12.0 checks](COH-Atlas-Gameplay-0.12.0-testing.txt)
to open a readable dialog, record its view, read an information response and
close it normally before Save/Finish. Task acceptance, training, moving NPC
pathing, combat and authentic generated beacon loading remain later milestones.

Movement and normal Save now become available after current native connection,
a bounded play/save budget and three fresh Android views. Return to safe ground
is optional; when requested it still pauses controls until the actual ordinary
`/stuck` receipt, stable native positions and fresh views are verified. Normal
save requires current native Atlas position matching committed SQL, identity,
powers/costume and selected-row preservation, normal logout/disconnection and
fresh saved-character views. A skipped recovery has explicitly false ground
claims. Optional recovery cannot extend the previously established deadline.

Capture contact dialog retains three fresh 800x600 PixelCopy views per manual
request, with at most three requests, current session/PID/character binding,
strict frame/time watermarks and a two-minute request limit. Optional owned
native `ContactInteract` initiation/response records are read once at export,
never in readiness polling. Those logs precede dialog generation and do not
prove that a visible dialog or mission/combat effect succeeded. The user supplies
that assessment. Native contact-state persistence is outside the protected
identity/power/costume selected rows; no database writes are made by observers.

Focused qualification passes **161 checks** and binds **84 source files**.
The candidate retains all native/container, renderer, world/avatar and prepared
cache bytes from the exact public 0.11.6 APK; five Java sources and three guest
helpers change, and one bounded contact-evidence helper is added. Actual guest
extraction of all three server archives remains required before signing and
publication. Device contact interaction and normal save without recovery remain
unverified until the next export. The accepted long camera/jump/ground tests
must not be repeated solely for this checkpoint.

Published [0.12.0](https://github.com/Russianranger/coh-android/releases/tag/coh-atlas-gameplay-v0.12.0)
from source commit `1791a3203ecf662191f2d6e3401cfa9ea4692004` in successful
[run 37071344940](https://github.com/Russianranger/coh-android/actions/runs/37071344940).
The public APK is **595203099 bytes**, SHA-256
`4a507d7d59b3af07be74de4bf47e39b8fd09ac86266a34c4fefd756fb442ee7c`,
version code 13, with the same app ID and signer. Independent verification passes
both v2/v3 signatures, the complete 570-chunk APK digest, all 63 ZIP CRCs,
56 payload hashes, 84 published source pins and the actual 161-check CI receipt.
Exactly 50 donor payloads remain unchanged; all three raw server archives and
their actual packaged guest extraction match public 0.11.6. The public notes,
checksum, asset metadata and release body also close to the build receipt. See
[the publication receipt](android-evidence/contact-interaction-0.12.0-publication.json).

The superseded 0.11.0 Atlas workflow also triggered on the modern UI edit and
rejected a changed historical workflow pin before compiling or publishing an APK.
It is now manual-only, matching the earlier superseded responsiveness workflow;
the dedicated 0.12.0 release workflow completed successfully. This routing change
does not alter the published APK. PR #1 remains draft and main remains unchanged.

The prior published checkpoint follows:

**Current: 0.11.6 repairs the immediate 0.11.5 reopen packaging failure and reduces Android runtime-extraction allocation pressure. The public APK and retained signer have been independently verified. Game/MapServer binaries and their existing performance changes are reused exactly; no new native build or physical performance gain is claimed. PR #1 remains draft; main stays 04d62616.**

The supplied `coh-atlas-gameplay-20261002-203058.zip` failed in less than a
second at `persistent_server_profile`: `Server payload archive metadata differs`.
All 26 members of the published game tar had nonzero timestamps, contrary to the
unchanged guest extractor's canonical metadata contract. Reproducing the exact
public APK rejects the first file before any PostgreSQL, DbServer, MapServer,
Wine or client process starts. The failed operation did not open the persistent
character database. See [the failure evidence](android-evidence/thor-0.11.5-reopen-preflight-failed-20261002.json).

The writer now produces zero timestamps and preserves the strict extractor.
Before signing and again before publication, the actual guest consumer extracts
all three server archives; a JSON/hash-only check cannot substitute for this
proof. Focused qualification passed **118 tests** and binds **116 source files**.
The exact completed native build from run 37048610759 is reused and both actual
Game/MapServer executable bytes are compared against public 0.11.5. Historical
full native/runtime pipelines remain skipped for this bounded repair.

Android tar extraction now reuses one 64 KiB copy buffer per archive, replacing
one 1 MiB allocation per member. A 1,002-member extraction fixture with a 32 MiB
Java heap reduced measured collections from 125 to 1 with identical extracted
bytes. This verifies allocation pressure, not a device crash cause or speedup.
The attachment contained no refresh crash trace. Android 11+ reports now include
up to four own-app historical exit records at the next completed operation,
without trace streams; unavailable exit history cannot block the report.

[Download 0.11.6](https://github.com/Russianranger/coh-android/releases/download/coh-atlas-gameplay-v0.11.6/COH-Atlas-Gameplay-0.11.6.apk).
Built from `6557a21dbd696c9ac8e9b9344a0e8d7553d5a345` in
[run 37063509202](https://github.com/Russianranger/coh-android/actions/runs/37063509202),
with both observer and APK jobs successful. The public download is
**595,194,816 bytes**, SHA-256
`c8a0b2801c6f4ea80ef6df17f7e66f0a90b0ad128ef86fbb39d94c6d54182895`.
Independent v2/v3 signatures and the full 570-chunk content digest, all 55
payload hashes, every ZIP entry CRC, binary app/version manifest and actual
packaged guest extraction pass. The retained native files and qualified source
closure match their expected bytes.

Install over the existing app, preserve imports and THORHERO, refresh runtime once,
then reopen. Use the [short 0.11.6 checks](COH-Atlas-Gameplay-0.11.6-testing.txt)
with ordinary Save/verified/Finish; the accepted long camera/jump tests need not
be repeated. First cold server and texture-index work still take time. Device
startup/FPS gains and saved exterior-position reopening remain unverified.
GPU acceleration and broader cross-session warm-server lifecycle work remain
pending. See [publication evidence](android-evidence/reopen-repair-0.11.6-publication.json).

The prior published checkpoint follows:

**Current: 0.11.5 is published and implements the user-authorized non-GPU performance recommendations. Native immediate ready/position events, a batched texture-header index with normal-loading fallback, transient minimum graphics, and one bounded pre-menu early-client retry are implemented. Native compilation, focused CI packaging and independent public APK verification passed; no device speedup is claimed. Broader warm-server reuse across completed sessions is still pending.**

The physical 0.11.4 export `coh-atlas-gameplay-20261002-172722.zip` showed no
noticeable improvement: interactive startup took 29m54.324s, versus about
29m28s in the accepted 0.11.3 run. Cold data preparation cost 401.760s; Atlas
startup took 639.458s and client startup 583.631s. Client texture headers alone
took 133.526s. Native ready and ground observations arrived through the old
60-second logger queue with measured delays of 62.346s and 71.260s. These
measurements motivated native work rather than another host-only derivative.

The new native event channel is session/PID/main-thread/SQL-identity bound and
flushed immediately. It retains completed MapServer ticks, two actual stable
positions 25–90 seconds apart, ordinary `/stuck`, fall checks and three fresh
Android views. Logout/save still uses its original normal countdown and SQL
proof. The indexed texture header/name/mip pack preserves full textures and
prepared Parse6 caches, validates import/executable/inventory identity, and
falls back to normal reads when unavailable or invalid. Repeated missing-file
diagnostics are deduplicated within load stages; validation is retained.

The default-on performance checkbox applies the existing minimum native
quality preset and 0.75 world render scale at the next launch. Saved graphics
preferences are captured before the overlay and restored before persistence;
unchecking it restores the normal profile. Rendering remains llvmpipe, with
800x600 UI and the existing 10 FPS cap. Actual loading/FPS improvements await
a short physical comparison using [0.11.5 notes](COH-Atlas-Gameplay-0.11.5-testing.txt).

Warm service reuse in this candidate is limited to one natural client early
exit before interactive menu/login, within the same active operation. It
requires proven client shutdown, unchanged SQL rows, live owned servers and
current MapServer ticks; retry gets a fresh attempt ID within the original
startup deadline. Finish/Stop still shut all owned services down. This is
not a fix for every later login-menu bounce or cold session start. GPU
acceleration remains deferred by the user.

[Published 0.11.5 APK](https://github.com/Russianranger/coh-android/releases/download/coh-atlas-gameplay-v0.11.5/COH-Atlas-Gameplay-0.11.5.apk)
was assembled from `bfa5a3da01789c634bdcab8e2d7134f71f54fe24` in
[APK run 37049707089](https://github.com/Russianranger/coh-android/actions/runs/37049707089).
Both observer and APK jobs passed. The separate
[native run 37048610759](https://github.com/Russianranger/coh-android/actions/runs/37048610759)
built Game and MapServer from `0ddd27dfaddf9ac53a6a65548c8199bced767fbe` after the
real Win32 flushed-event fixture and exact overlay staging passed. Received
Windows PG LF/CRLF provenance is validated without relabelling its source chain.
No full native gameplay/physical milestone is repeated. Focused qualification
passes **195 checks**, authenticates the exact 0.11.4 donor's 50 payloads and all
16 Java sources, and binds **120 source files**. The full local interactive suite
passes **434 tests** without skips.

The public APK is **595,194,816 bytes**, SHA-256
`5ba95d45bfbe0a2cda74bb632b80d1499058f5c8b40c48d9d422a9304cdb9941`.
Its complete download matches the build and release asset pins. Independent
v2/v3 signatures, the full signed content digest, ZIP CRC, binary app/version
manifest, all **55 payloads**, qualified source closure and native-container
comparison against the exact donor pass. Only Game, MapServer, the launcher,
six explicitly allowed guest helpers and their manifests change; four guest
helpers plus a native receipt are added. DbServer, DLLs, prepared caches, imported
world/avatar assets, Android native libraries, resources, app ID and signer remain
retained. Only Activity/Runtime Java sources change for graphics preference and
launch environment. See [the publication receipt](android-evidence/responsiveness-0.11.5-publication.json).

PR #1 remains draft and main is independently confirmed at
`04d62616e2e1b41b10f35a04d4c798e43680d5ba`. Install over the existing app, refresh
runtime once, retain imports and THORHERO, and use the short comparison notes plus
ordinary Save/Finish. Physical speed gains and the saved exterior-position reopen
remain unverified. Broader persistent warm-server lifecycle work remains pending;
GPU acceleration is deferred by the user.

The prior published checkpoint follows:

**Current: 0.11.4 is published for the user's startup/readiness priority. The bounded derivative removes whole-data-tree log scans, reuses completed owned private server data on later starts, and buffers RFB input. Focused host qualification, CI packaging and independent public APK checks passed; physical timing and gameplay-FPS gains remain unverified. Physical 0.11.3 outdoor movement, usable presentation, phase deadlines and ordinary save/Finish/cleanup remain accepted. THORHERO, seven powers and fourteen costume parts are preserved; the saved exterior position awaits a subsequent reopen. PR #1 remains draft; main stays 04d62616.**

The accepted run spent about 29 minutes 28 seconds reaching the interactive menu.
Repeated readiness queries then walked roughly 177,000 private data files to find
logs, and server preparation rebuilt the entire private data tree each session.
The performance pass narrows current-session log reads to owned root logs and the
owned logs subtree. Poll cadence is measured from poll start; timing reports retain
launcher start, observer costs and the original ground-verification samples.
Current native identity, complete-record, stable-ground, SQL save and deadline
checks remain required.

Private data reuse is limited to the same source/import/runtime identities after
proven owned-process and Wine shutdown with credential configuration removed.
Session executables, configuration and logs are fresh. Interrupted or invalid
cache generations remain preserved and are bypassed with fresh preparation.
The first launch after the APK/runtime update still constructs the new cache;
later same-generation starts can retain generated private MapServer caches and
avoid recreating the imported leaves. Old unreceipted 0.11.3 trees are not adopted.

RFB input now uses a bounded 64 KiB buffer. The deterministic full 800x600 plus
incremental-frame fixture reduces underlying reads from 658 to 31 with identical
pixels, requests, sequence ownership and cancellation behavior. This measures
transport overhead, not game FPS. Native rendering still uses software llvmpipe;
the observed world rate was well below the existing 10 FPS launcher cap. Native
renderer, cap, display resolution, Surface capture and frame-proof paths remain
unchanged. Device improvement must be assessed from a short comparison run,
using [0.11.4 testing notes](COH-Atlas-Gameplay-0.11.4-testing.txt), rather than
replaying the accepted long movement/camera/jump milestone.

The focused derivative qualification passes 186 unittest methods plus 89 Java
budget scenarios and binds 85 source files. It authenticates the exact published
0.11.3 APK, its 49 payloads, all sixteen Java sources and the four immutable
lineage receipts. CI interactive discovery passes 393 executed tests, with one
existing Tesseract-dependent test skipped (394 methods). The
historical 0.11.3 transform test now uses byte/hash-pinned published helper fixtures
with its original positive and negative assertions; no test suite is filtered.
The required host cache fixture creates 4,002 links cold and zero warm, with 25
directory checks (0.824119 / 0.004263 seconds on this host). These are fixture
measurements, not Thor startup timings. Historical 0.11.2/0.11.3 publication
workflows remain manually dispatchable; the new derivative has its own exact
retained-donor workflow. Native/physical milestones are not repeated for this pass.

[Published 0.11.4 APK](https://github.com/Russianranger/coh-android/releases/download/coh-atlas-gameplay-v0.11.4/COH-Atlas-Gameplay-0.11.4.apk)
was built from `97c5ece986c9ba91825844e648d728ee310ed732` in
[run 37030944557](https://github.com/Russianranger/coh-android/actions/runs/37030944557).
Both observer and APK jobs passed. The public APK is 595,116,556 bytes, SHA-256
`8f5a398f15adc4d94ed1137817a7db696bafa3c03aa0e7a54638e5570bfb0fa3`.
Its complete download matches the build and GitHub release pins; ZIP CRC,
independent v2/v3 RSA signatures and the full 570-chunk content digest pass.
All 50 payloads match the build receipt. Six existing guest/verification payloads
change, one cache helper is added, and DEX is recompiled with only the exact
bounded RFB source wrapper changed. Other Java sources, resources, signer,
application ID, native runtime/client/server and world/avatar bytes are retained.
See [the publication receipt](android-evidence/startup-perf-0.11.4-publication.json).
The actual CI cache fixture records 4,002 to zero link creations and 25 directory
checks, taking 1.085236 / 0.005661 seconds on that host; it is not a device timing.
Generic push tooling runs 37030944503 and 37030944442 passed with all native,
cache-build and APK jobs skipped. No accepted native or physical gate repeated.

Next: use the short 0.11.4 readiness/frame-pace comparison and normal Save/Finish
to establish a completed data-cache generation. A later necessary reopen can
compare warm startup and the saved exterior position. Reports now distinguish
preparation, native readiness and observer costs. Native client/Atlas loading and
software-renderer FPS remain targets beyond the removed host overhead; no device
speedup is accepted until the new export is reviewed. Genuine beacon generation,
NPC pathing/combat and complete materials/minimap remain separate pending gates.

The physical 0.11.3 checkpoint follows:

The returned `coh-atlas-gameplay-20261002-145320.zip` independently confirms
normal `/quittologin` delivery at 14:50:24.531 UTC, native logout timer expiry
at 14:50:27, committed SQL verification at 14:52:01.321, guest receipt of Finish at
14:52:19.993 and complete cleanup at 14:53:14.783. The committed exterior
position is **(104.47185, 31.959229, -531.55786)**. ID 1 / COHLOCAL and all
selected rows remain identical except the expected LoginCount 4 to 5. The
canonical saved selected-row snapshot is
`648b7ca2368748f0bbd5020e7bcd99a6a1b9e040728ac8f73cb525ff323123e0`;
positions are verified by a separate SQL query and matching native records.
See [the physical outdoor movement/save receipt](android-evidence/thor-0.11.3-outdoor-movement-save-passed-20261002.json).

The initial interior is explained by the previous committed position
(133.92833, -768, -594.64825), which still matched the accepted interior save.
The previous outdoor run requested no new normal save. Native resume then chose
the authored nearby-door auxiliary exit (134.5, -768, -575); this is normal
door emergence, with no reset or persistence defect indicated. The prior
selected-row snapshot differs from this run's baseline only in LoginCount 3 to 4.
Do not claim that the new outdoor position has already survived another restart.

All 23 exported Android PNG hashes, sizes and dimensions match; connection,
ground and save each have three fresh sequences after their event watermarks.
They show City Hall, outdoor Atlas Plaza and the login screen after logout.
The user's new screenshots and report accept outdoor movement and usable
presentation. Prior camera/jump and tested-route no-clipping acceptance remains
retained. Flat white ground, purple/blue surfaces, UI placeholders and **Map
Unavailable** remain visible, so complete materials/minimap and broad collision
coverage are not accepted. Automated rendering/controller/input-effect flags
remain false; user acceptance is recorded separately. Runtime/identity manifests
match published 0.11.3, without claiming independent installed-APK byte attestation.

The delivered `/stuck` at 14:44:14.313 anchors movement/Save/proof deadlines at
14:50:14.313 / 14:51:14.313 / 14:54:14.313. Revision 2 shortened the connected
allowance; no renewal or expiry revival occurred. Android recorded input cutoff
558 ms after its deadline, and normal Save delivery arrived 49.782 seconds before
the Save cutoff. Finish and cleanup completed before final expiry. This run also
finished before the original menu deadline, so expired-phase behavior was not
exercised physically. A complete 60-second all-controls-neutral interval is not
proven: the last retained ordinary input preceded Save delivery by 44.728 seconds
and could have been a cursor/release event. Current stable native samples and
ordinary committed-save proof passed; retain the 60-second neutral test guidance.

Responsiveness remains a concrete next target. Guest start to interactive menu
took about 29 minutes 28 seconds: Wine refresh 64 seconds, private data/DbServer
7 minutes 16 seconds, Atlas 10 minutes 43 seconds and client startup 9 minutes
38 seconds. `/stuck` delivery to ground observation took 1 minute 55 seconds,
followed by 2.217 seconds for fresh Android frames. The final pre-save ground
samples at 14:49:45/14:50:15 are refreshed evidence and must not be attributed to
the initial 14:46:09 ground event. This run has no cold-login watchdog/auth failure
or disconnect before normal logout. Do not import the prior failure diagnosis
as a new failure, or blame all user waiting on disabled controls: native records
already show outdoor traversal before `/stuck` was requested.

The menu allowance remains 1200 seconds. A current validated native connection
receives a one-shot allowance up to 1200 seconds, capped at actual launcher start
plus 2040 seconds and overall-operation deadline minus 120 seconds. A current
ordinary `/stuck` receipt anchors movement/save/proof deadlines at 6/7/10 minutes.
The last minute before Save is reserved for neutral standing; the following
three minutes are reserved for the existing normal logout, SQL proof and Finish.
Caps can shorten the visible window. Duplicate events cannot renew it, expired
phases cannot revive it, and the Android shell binds the UTC deadlines to uptime.
Android independently caps event admission at its display announcement plus
35 minutes, providing one minute of headroom between announcement and launcher start;
the guest's actual emitted policy cap remains 34 minutes before the native
36-minute launcher lifetime. Menu/creation behavior and normal-save validators
are unchanged. Input cutoff releases held movement/camera inputs and preserves
a queued ordinary Save command. No automatic logout is requested.

[0.11.3 focused testing notes](COH-Atlas-Gameplay-0.11.3-testing.txt) request a
brief route to a safe outdoor spot, preferably more than 30 units from a door,
60 seconds standing still, normal Save before its cutoff, then verified Finish
and report export. A later reopen can assess the new outdoor saved coordinate.
The existing native cold-load timeout remains in place. The update does not
claim to fix the inferred cold-login watchdog or complete materials/collision.

[Beacon input preflight](android-evidence/atlas-beacon-input-preflight.json)
audits six supplied inventories and pins the loader's expected Atlas v8 graph
and v9 date-sidecar/CRC inputs. Zero generated graphs were found. Optional
supplied files can receive bounded prefix/hash/sidecar checks but always remain
unqualified until provenance, full structure, loaded-world CRC and native graph
loading are established. No fake graph, NPC readiness or combat acceptance is
claimed. [Published 0.11.3 APK](https://github.com/Russianranger/coh-android/releases/download/coh-atlas-gameplay-v0.11.3/COH-Atlas-Gameplay-0.11.3.apk)
was built from `97565b0c28ba27ef79e70d4c04dddb1a8383ec1f` in
[run 37015136168](https://github.com/Russianranger/coh-android/actions/runs/37015136168).
Its observer and APK jobs passed. The exact focused receipt passes 102 unittest
methods plus 89 Java protocol scenarios and binds 61 source files. The complete
Android source closure (16 sources) compiled; only Runtime, Service and Activity
changed and the budget class was added. APK size is 595,108,273 bytes and SHA-256
is `3c97d5c85092ec9aec88de405cea92a91c760db379cdbf66a244714687f35dfd`.
The public download matches this complete pin. Independent RSA/SHA-256 v2 and
v3 signature checks and the full 570-chunk APK content digest passed. [The publication review receipt](android-evidence/session-window-0.11.3-publication.json)
records the independent signing/content/payload review. The existing app ID,
signer, native libraries/client/server, world/avatar assets and unrelated Java
sources are retained. Four existing guest/verification payloads change, one new
budget module is added, and the Android DEX is recompiled. Resources are unchanged.

The previous full client/DbServer native gates did not repeat: push tooling runs
37015135666 and 37015135634 passed and their native runtime/APK/cache jobs were
skipped. The historical 0.11.0 gameplay publication workflow also triggered on
Activity and failed closed at its old donor-source boundary, as expected for this
new derivative; it did not boot a native runtime or replace an old release. The
new 0.11.3 workflow passed its own exact current-source and donor boundaries.

Next: use the archived startup/readiness timeline to reduce expensive preparation
and observation latency while preserving existing data, cache, normal-save and
native guards. Assess the newly saved exterior coordinate on a later necessary
reopen; do not repeat the accepted long physical/native gates solely to record
this checkpoint. Qualify a bounded genuine one-map graph generator, provenance,
full structure and loaded-world CRC before installing an Atlas beacon graph.
NPC pathing/powers/combat still follow genuine graph loading. Rendering/minimap
completeness is a separate gate; beacon data alone does not qualify it.

Previous physical evidence checkpoint follows:

**Previous physical checkpoint: 0.11.2 verifies the prior movement-save survived reopening, normal City Hall door emergence, traversal into outdoor Atlas, usable outdoor rendering and no clipping on the user's tested route. The earlier interior movement/camera/jump and normal-save gate remains accepted. The latest export is correctly failed because the 20-minute menu-based interaction budget expired without a requested outdoor save; cleanup passed. Next development should provide a bounded gameplay/save window after world readiness, trace cold-login loading timeouts and qualify genuine Atlas beacon inputs before NPC/powers/combat. Complete materials/collision and a new outdoor save/reopen remain pending. main stays 04d62616 and PR #1 stays draft.**

The returned `coh-atlas-gameplay-20261002-125646.zip` proves the entire SQL
baseline equals the previous accepted saved snapshot, SHA-256
`be69e921dfafb584ae0fd263693a6f43eb6f1577125dfa5b17b4852576071362`.
THORHERO ID 1 / COHLOCAL, LoginCount 3, seven powers, fourteen costume parts
and the committed position (133.92833, -768, -594.64825) survived the restart.
Initial native records repeat that position at their two-decimal precision.
The user reports the same initial nearby City Hall location, then successful
exit into outdoor Atlas with decent rendering and no observed clipping.
Native periodic records confirm stable outdoor ground near (132.82, 44.04,
-597.78). This accepts the observed route and usable exterior presentation,
while broad terrain/collision coverage and complete materials remain pending.
See [the outdoor observation and incomplete-save receipt](android-evidence/thor-0.11.2-outdoor-observed-save-incomplete-20261002.json).

Native resume intentionally moved the character to (132.5, -768, -576)
before `/stuck`: `resumeCharacter()` calls `prepEntForEntryIntoMap()` with
`EE_USE_EMERGE_LOCATION_IF_NEARBY`. It finds an emergence marker within
30 units and places the player at an authored auxiliary door exit; the
City Hall door transforms give the exact observed coordinate. This is normal
door behavior, not a persistence defect. A later exact outdoor coordinate
test should save more than 30 units from a doorway. The latest run did not
request another save, so no newly committed exterior position is claimed.

The first cold MapServer connection began at 12:36:07 UTC; world loading
continued through actor-spore initialization at 12:38:29 before the client
returned to login with **Lost connection to server** around 12:38:32.
`commLinkLooksDead()` uses a 120-second stale-link threshold during loading,
and `commCheck()` contains the matching return-to-login branch. The successful
retry took about 115 seconds. These facts support a cold-load watchdog
diagnosis, but the export contains no explicit 120-second alarm. The later
**Unknown auth code: -1** disconnect is not evidence of a MapServer crash.
Do not add an unqualified `-notimeout` bypass or reset the preserved profile.

The diagnostic's 1200-second interaction budget started at menu/input
readiness, 12:34:42 UTC. Connection observation arrived at 12:44:54 and
ground verification at 12:49:01, leaving only 5 minutes 41 seconds before
the 12:54:42 Android deadline. The guest emitted `interaction_timeout`
at 12:54:51, then correctly failed **Character save was not verified**.
No Save character / log out or Finish request was sent. The display-closure
error accompanies producer shutdown; cleanup completed with no remaining
owned workers or inspection failures. The prior successful normal save is
not invalidated by this unfinished new save.

All 20 retained Android PNG hashes match their files, with three fresh frames
after connection and ground verification. Those retained frames show the
interior/EXIT doorway. The guest final frame shows outdoor statue, plaza,
buildings and vegetation, with purple/overbright surfaces and a white sky
still visible. The user's physical observations support delivery to Thor;
no fresh retained outdoor Android PixelCopy proof is claimed. The attached
06:45 interior screenshot duplicates the previous run and is excluded from
new outdoor evidence.

Next implementation scope:

1. Give the reopened character a phase-aware, bounded gameplay/save budget
   after native connection/ground verification. Synchronize the Android
   countdown with the guest deadline and retain the overall runtime cap.
   Reserve time for the existing 60-second neutral wait and normal logout;
   keep recovery-receipt age, identity, stable-ground and SQL save checks.
2. Investigate the cold world-loading watchdog using the archived timings;
   preserve native timeout behavior until a bounded correction is qualified.
   Do not rerun the accepted physical route solely for this diagnosis.
3. Audit authentic generated Atlas beacon data or a bounded one-map generator.
   No generated `.bcn` is in the repository/shipped package; the authored
   beacon layer is placement data, not the combat graph. The generation chat
   commands are disabled in the native command table, so there is no supported
   manual `/beacongenerate` or `/beaconprocess` procedure for the current APK.
   The native loader expects `server/maps/City_Zones/City_01_01/City_01_01.txt.v8.bcn`
   and uses map CRC/date metadata. A genuine graph needs a separate verified
   server-only installer: the current world supplement accepts only geometry
   and textures. Prove graph loading and CRC compatibility before NPC/combat.

No APK was changed or published for this evidence checkpoint. The earlier
saved-position/outdoor procedure below is historical; no unchanged Thor boot
is requested. The previous interior acceptance and publication are preserved.

The returned `coh-atlas-gameplay-20261002-115211.zip` passed the composite
existing-character recovery and normal-save gate with zero failed input sends.
The user explicitly reports successful movement, camera and jump and adequate
interior rendering. The screenshots show the City Hall floor, walls, columns
and character and the **Atlas position verified** status with movement enabled.
This accepts the focused physical input/interior gate; the report's broad
automated gameplay/controller/rendering booleans remain false by design and
are not reclassified as automatic visual or gameplay proof.

Native evidence and committed SQL independently support the normal save.
The prior saved position was (123.5, -768, -579); the character moved about
18.80 horizontal units to (133.92833, -768, -594.64825). Two native observations
at 11:46:30 and 11:47:00 UTC agree at their two-decimal precision. The real
`/quittologin` receipt precedes **Logout timer expired** at 11:47:12 UTC,
followed by the committed-save proof at 11:49:07 UTC. LoginCount advanced
2 to 3; identity, selected entity fields, powers and costume remained intact.
Three fresh Android PixelCopy captures after each connection, ground event
and save match their exported PNG hashes and exceed the corresponding frame
watermarks. Guest and Android cleanup passed with no remaining owned workers.
See [the accepted physical receipt](android-evidence/thor-0.11.2-interior-movement-save-passed-20261002.json).

Use [the saved-position and outdoor procedure](COH-Atlas-Gameplay-0.11.2-saved-position-outdoor-testing.txt)
on the already installed 0.11.2 APK. Preserve the existing runtime and character.
Leave controls neutral for 60 seconds after gameplay appears and capture the
initial view **before** Return to safe ground. The current app's reopening
status verifies identity and native readiness, not coordinate restoration;
review the initial native records against baseline SQL separately. Then use
one ordinary recovery command to unlock movement, test a bounded City Hall
route and the ordinary exit into outdoor Atlas, and perform another normal
save. Complete the route and 60-second neutral settling within the existing
ten-minute recovery window. No new APK, character creation or hosted game
session is required for this gate.

The following preserves the 0.11.1 failure diagnosis and 0.11.2 publication
history. Its pending focused movement/save retry is now accepted above.

The returned `coh-atlas-gameplay-20261002-095609.zip` records native connection
and existing identity verification for THORHERO ID 1 / COHLOCAL. Baseline
SQL contains seven powers and fourteen costume parts. `/stuck` moved the
character from the -2000 synthetic floor to City Hall's authored interior
spawn, then the native logger repeated that exact position every 30 seconds.
The old verifier rejected negative elevations below -100 in both the live
and committed-save observers, so it never announced character_relocated.
Controls and save remained disabled until the recovery receipt expired;
the shared receipt reader's generic logout/save-window error is secondary.
The final report therefore fails the composite gate despite successful
physical reopening. No requested normal save was performed. Cleanup passed.
See [the physical failure receipt](android-evidence/thor-0.11.1-ground-verifier-failed-20261002.json).

The source correction changes only `local_character_server.py`: a shared
height predicate rejects Atlas's synthetic -2000 fall floor with one unit
of clearance, accepts genuine subterranean Atlas rooms, and keeps the
existing identity, owned log route, freshness, latest-pair stability and
SQL position matching. Two numerical observations do not prove all collision
geometry; that remains explicitly false in the evidence. Eight new regressions
replay unmodified physical native records and exercise save/identity/fallback
boundaries, alongside the fourteen existing observer regressions. The receipt
used for archived replay is labeled synthetic because the original private
delivery file was not exported. No new hosted game session is claimed.

The dedicated `android-ground-repair.yml` packages a 0.11.2 derivative of
the exact published 0.11.1 APK, retaining the PRoot avatar repair, DEX, resources,
world, native libraries, client/server binaries, application ID and signer.
Only the observer and its client/runtime verification manifests may differ;
Android package metadata advances to version code 8. No unchanged server
rebuild, character creation or hosted seed/reopen gate is requested.
[Publication run 36994687459](https://github.com/Russianranger/coh-android/actions/runs/36994687459)
passed both observer and APK jobs at `7e2f44b122417192ec1d9dd6d973b27b594e0a82`.
The public signed APK is 595,104,089 bytes, SHA-256
`1e8b9ffd09dcfa6967685e31b1ccbff1acf200b892614e6ec2f6092d533e8adb`.
Independent public-download review checked all payload pins and ZIP CRC,
unchanged DEX/resources and the exact three-member derivative boundary.
The complete build receipt and review are archived in the physical failure
receipt's corrective_publication section. Ten qualification source pins
match the packaged code commit; the 22 observer and 13 packaging tests passed.
[Download COH Atlas Gameplay 0.11.2](https://github.com/Russianranger/coh-android/releases/download/coh-atlas-gameplay-v0.11.2/COH-Atlas-Gameplay-0.11.2.apk).

Commit `88c8b9a9` narrows the old retained-reopening fixture wildcard to its
original name-row image. Its routing-only run `36994935181` passed tooling
and skipped the unchanged runtime. The broad wildcard had queued old run
`36994687391`; it failed the retained 0.10.0 Java-source boundary before a
graphical session started. No accepted character seed/reopen session was
repeated. Preserve that failure receipt as a routing issue, not as evidence
against the separately successful 0.11.2 observer/package publication.
[The original focused physical procedure](COH-Atlas-Gameplay-0.11.2-testing.txt)
was the in-place update and one runtime refresh used for the now accepted
ground verification, brief movement, jump/camera and normal-save gate. Its
installation/refresh step should not be repeated for the next saved-position
and outdoor test. Sustained collision/outdoor scenery precedes map beaconing
or native NPC/powers/combat.

The following preserves the completed 0.11.1 publication and earlier history.
Its formerly pending physical reopening and focused interior input/save gate
are now accepted as described above; sustained outdoor rendering/collision
and NPC/powers/combat remain pending.

[Download COH Atlas Gameplay 0.11.1](https://github.com/Russianranger/coh-android/releases/download/coh-atlas-gameplay-v0.11.1/COH-Atlas-Gameplay-0.11.1.apk)
as an in-place update, then Refresh runtime once and Reopen saved THORHERO.
Do not clear storage, reimport data or create a replacement character.
[Run `36944389469`](https://github.com/Russianranger/coh-android/actions/runs/36944389469)
at `34b763a5518e3fa3740c197c0e824c17da088536` passed all three jobs:
tooling (15 installer regressions, 12 package boundary tests and routing),
actual native ARM64 PRoot migration, and retained-signer packaging/publication.
The migration reproduced ELOOP, verified/repaired 21 old avatar files,
reused all 21 on repeat, removed hidden backing entries, preserved sentinel
state and passed six refused-invalid cases plus both interrupted-repair retries.

The public APK is 595,104,089 bytes with SHA-256
`f4e30c728046771cb91beece46fb54663b0fcd57a28b8e055f6fc8918dd3c899`.
It retains application ID `io.github.russianranger.cohclientinteractive` and
signer `92955353965f118a748f1f2cadc00dfb39b3e8ade0a6cdd7d44058a3a776c282`,
and advances to version code 7. Independent download review verified the
complete public APK digest and every payload pin against the signed build.
Only the avatar helper and its client/runtime verification manifests change;
Android package version metadata is updated. The DEX, resources, world,
native runtime, client and server remain byte-identical to published 0.11.0.
See [the complete reviewed qualification/publication receipt](android-evidence/avatar-repair-36944389469-reviewed.json)
and [the focused physical instructions](COH-Atlas-Gameplay-0.11.1-testing.txt).
The existing screen heading still says v0.11.0 because the controls are retained;
Android app version and exported reports identify the new 0.11.1 candidate.
No physical reopening, rendering, ground recovery or gameplay acceptance is
claimed by this hosted file-migration check.

The user's `coh-atlas-gameplay-20261001-233407.zip` contains a 0.11.0
`character_reopen` failure after about 2.5 seconds. Inputs, the reused private
worktree, persistent server profile and durable PostgreSQL startup passed.
The first avatar verification then failed with `Errno 40` at
`data/player_library/male_boot.geo`. Wine, DbServer, Atlas and the game client
never started; no rendering, ground recovery, movement or normal second save
was reached. The report records `before_character_id=1` but leaves
`existing_character_verified=false`; this attempt did not verify reopening.
PostgreSQL stopped
gracefully and Android verified cleanup. See
[the physical failure receipt](android-evidence/thor-0.11.0-reopen-failed-20261001.json).

The accepted older avatar installer used `os.link` under PRoot
`--link2symlink`. Its two hidden backing entries embed absolute paths. A later
wrapper-only directory rename preserves bytes but breaks those embedded paths;
strict `O_NOFOLLOW` then reports the observed `ELOOP`. The corrective helper
recognizes only the relocated old avatar publisher's exact link layout,
verifies the pinned payload, mode, timestamp and ownership, and atomically
materializes its logical leaf. Verified hidden backing entries are removed
before MapServer staging. Imported files, caches, worktree identity and the
saved database are untouched. Focused qualification must reproduce this with
the actual pinned ARM64 PRoot; source-equivalent unit tests alone do not close
that gate. The successful run above now closes that focused repair gate;
physical results remain pending.

The corrective checkpoint adds 15 avatar installer regression cases, including
the moved emulated-link layout, refused invalid chains and cleanup retry. The
new retained-donor packaging boundaries pass 12 tests; routing passes its
focused check. Independent extraction of the actual published 0.11.0 APK
verified all donor pins and exactly three revised payloads: the avatar helper,
client verification manifest and runtime verification manifest. The other 48
APK members, including the DEX, are retained. The bounded
`android-avatar-repair.yml` workflow must first reproduce the legacy failure,
repair and retry under native ARM64 PRoot, then package/sign/publish 0.11.1
(version code 7) using the retained key. No Wine/server/world rebuild or passed
two-session graphical requalification is requested. The workflow and corrective
publication now pass. Resume physical testing with
[the 0.11.1 instructions](COH-Atlas-Gameplay-0.11.1-testing.txt).

Focused ARM64 run `36943167422` built the matching PRoot successfully but
stopped the migration gate on a hidden `.l2s..avatar-pending-*.0001` file's
owner check; no corrective APK was built or published. Pinned PRoot's hidden
backing stat hook restores the physical host UID after guest UID mapping.
The narrow backing-file reader now accepts the mapped owner or the same real
UID from `/proc/self/status` as existing owned-process cleanup, since extension
order can reverse across fork. Ordinary payload reads
still require the mapped guest owner; only the exact recognized legacy backing
names may use the real-owner check. The fixture compares the same underlying
owner across this virtual stat difference and preserves detailed failure
tracebacks. The successful focused retry above fulfills that requirement;
the completed 0.10.0 graphical gate is not repeated.

Retry `36943898161` at `fa104426` passed the checked 21-file repair and exact
payload/metadata comparison, then caught physically remaining intermediate
links. PRoot's virtual `lstat` reports those broken intermediates as missing,
so `lexists` cannot determine their physical presence. Cleanup now unlinks only
the preflighted intermediates directly and handles actual ENOENT, then removes
their verified backing files. Orphan preflight likewise uses bounded readlink
instead of virtual lstat. The added regression reproduces this missing-stat
view. No APK was built or published by either failed focused attempt.

The retained-APK [run `36929550592`](https://github.com/Russianranger/coh-android/actions/runs/36929550592)
passed tooling and the full native ARM64 runtime on host-driver commit `f7c6c3a6`.
The APK is byte-identical to run `36920583713` / source `204615c6`; no client,
server, native library or APK was rebuilt for the host OCR correction.
Independent review checked all 355 artifact members, 195 source pins, both
raw SQL/report/observer contracts, native CLIENT_READY and normal logout lines,
27 proof PNGs, ten raw PPMs and graceful cleanup. The same THORHERO ID 1 retained
seven powers and fourteen costume parts; LoginCount incremented from 1 to 2.
Ordinary `/stuck` produced fresh stable native positions near `(106.45, 0.25,
-114.45)` over 30 seconds; the second normal save committed that Atlas position
with MapId/StaticMapId 1. Both sessions stopped all owned workers.
See [the reviewed gate receipt](android-evidence/atlas-world-reopen-reviewed.json).

The [0.11.0 release](https://github.com/Russianranger/coh-android/releases/tag/coh-atlas-gameplay-v0.11.0)
is published from code commit `1649e807d2b2310170e775c53bafa24cd932638a`.
[Build/publication run `36937373454`](https://github.com/Russianranger/coh-android/actions/runs/36937373454)
passed its actual qualification gate, Java/D8/resource build, payload comparison,
package badging, retained-key signing and release upload verification. The APK
is 595,099,993 bytes with SHA-256
`e3a0760d23ef57747343ee8fd0c76e68a92194df040062266f3dc282cd15a924`.
All three public assets are present: APK, checksum and focused testing notes.
Independent packaging review confirmed exactly five world-bound payload changes
and two Java UI/input changes, unchanged native/client/server payloads and the
same application ID/signing certificate. The complete build receipt and release
pins are retained under `publication` in
[the material receipt](android-evidence/atlas-material-inputs-0.11.0.json).
Both legacy workflows passed tooling and skipped duplicate APK/runtime jobs.
PR #1 remains draft and main remains `04d62616`.

A separate continuation review downloaded the **public release APK itself**
and independently matched its complete digest to the signed build receipt.
Every packaged payload pin, shipped Java source pin and preserved backend source
pin matched. All 2,904 decoded world files passed their recorded hashes; all
2,877 original world files were preserved and exactly 27 texture files were
added. The public testing notes also match the build pin. No passed runtime or
controller test was re-run, and no new APK was built. See
[the public-download review](android-evidence/atlas-gameplay-publication-36937373454.json).
The new materials' appearance and physical walking/jump/collision remain pending
until the focused Thor test. After accepting that report, reopen the movement-saved
position and qualify sustained Atlas movement/collision before first power/combat
work; that is new gameplay coverage, not a repeat of the accepted creation gate.

The earlier publication completed packaging, while the physical report now
requires the avatar reuse correction above. Preserve the
accepted physical 0.9.0 behavior and the healthy hosted 0.10.0 reopening gate.
Do not re-run either gate merely for completeness. Resume with the corrective
candidate's single focused Thor report covering reopening, scenery, neutral movement stop, jump/camera,
ground contact and normal save. Fix the exact observed defect next; after
initial world/movement acceptance, advance collision completeness, map beaconing
and native NPC/gameplay behavior sequentially.

Earlier hosted frame inspection confirms the avatar, ground, stairs, statue and building
geometry in the reopened Atlas frame. Materials remain flat or poorly textured,
and native UI still reports an unbeaconed map. This proves visible geometry and
recovery, not complete graphics, NPC pathfinding or physical gameplay acceptance.

The sequential 0.11.0 milestone adds only 27 texture targets named in the
retained material/shader warnings, preserving all 2,877 existing world files.
The revised supplement is 2,904 files / 318,611,871 decoded bytes. Exact public
range reconstruction fetched 4,357,758 bytes and reproduced its pinned ZIP;
[the material receipt](android-evidence/atlas-material-inputs-0.11.0.json) records
all old-payload preservation and new source/header checks. The finite MapServer
staging cap accounts for exactly the extra 27 files / 8,955,931 payload bytes.

The new Android controls map the left stick to forward/back and strafe, X to
jump, and held on-screen movement buttons to the same keys. Movement becomes
available only after native ground verification and fresh Android views. Keys
share ownership with keyboard/touch, use stick hysteresis, and release on neutral,
focus/dialog/disconnect/save transitions. Existing right-stick cursor, A click,
text input, D-pad and shoulder mouse-look behavior are preserved. Saving checks
the latest stable position after walking; stand still for 60 seconds and request
Save within ten minutes of Return to safe ground.

The gameplay builder retains the exact qualified APK backend and signing key.
Only two Java UI/input files may differ, and only five APK world-bound payloads
may change: the supplement ZIP/manifest, six immutable helper pins and their two
verification manifests. New materials and the complete 0.11.0 APK remain
host/device-unvalidated. The original reopening and legacy DbServer workflows
route these bounded derivatives to the gameplay builder; unknown/backend changes
and manual dispatches still request full qualification. No repeat seed/reopen or
unchanged DbServer rebuild is needed for this milestone.

Install the new candidate as an in-place update from accepted 0.9.0, keep the
private database/Wine/imports and THORHERO, and Refresh runtime once. Accepted
0.9.0 has no world marker; its first missing-only world install narrowly refreshes
private Atlas/affected geometry caches. No marker migration or cache-archive
replacement is needed. The focused [0.11.0 Thor instructions](COH-Atlas-Gameplay-0.11.0-testing.txt)
cover only reopening, visible Atlas materials, a brief walk/jump/camera check,
then normal save and export. Do not repeat character customization.


The following resolved regression notes preserve the path to the passed gate.

Run `36920583713` at `204615c6` proves the narrow NULL MapId baseline fix.
Its seed session passed in 1,845.046 seconds. The second session preserved
identity, authentication, powers, costume and the exact Atlas SQL position,
started Atlas and the graphical client, logged in locally, and reached the
existing character roster. The retained frame clearly shows THORHERO and the
default costume, but wide-region OCR misread the name as THOAMERG and refused
selection. No reopened CLIENT_READY, ground recovery or second save was reached.
Both sessions cleaned up their owned workers normally. See
[the preserved OCR failure receipt](android-evidence/character-reopen-hosted-36920583713-ocr-failed.json).

The host correction crops the character name row and uses grayscale single-line
OCR, retaining exact THORHERO matching and clicking only recognized bounds.
Retained attempts 1, 10 and 21 each recognize THORHERO at 70% confidence.
The dedicated retained-APK workflow downloads the unchanged signed 0.10.0 APK
from run `36920583713`, verifies all donor pins, and records the separate host
driver commit/source inventory. It performs two real sessions with a fresh
PostgreSQL profile; the failed run did not archive a reusable database cluster.
It does not rebuild client, server or APK components. The original full-build
workflow routes bounded host-only pushes to this qualification, avoiding a
duplicate runtime and rebuild. At that point, reopening remained pending until the normal
second save, persistence comparison and cleanup passed. Run `36929550592` above
now satisfies this gate.

Run `36913457461` at `07eb3ecb` completed with a runtime failure. Its first
graphical session passed in 1,840.069 seconds, reached CLIENT_READY, displayed
Atlas ground/stairs/statue/building geometry, and committed rows 1/1/7/14.
Native position stayed around `(106.45, 0.25, -114.45)` rather than falling to
Y=-2000. World surfaces and the avatar remain poorly textured/lit; this is
visible geometry, not complete graphics or device gameplay acceptance.

The second session reused PostgreSQL/Wine and all world/avatar files. Its read-only position after
normal DbServer startup was `MapId=NULL`,
`StaticMapId=1`, `(106.454605, 0.251066, -114.45343)`. The pre-entry guard
incorrectly required the temporary live map to be 1 and stopped before launching
Atlas/client. The outer RFB error is a consequence of that guest refusal. Both
sessions shut down PostgreSQL/Wine gracefully with no surviving owned workers.
See [the preserved failed receipt](android-evidence/character-reopen-hosted-36913457461-failed.json).

Pinned native source explains the NULL: first creation assigns MapId in memory
but writes StaticMapId to SQL; ordinary MapServer saves omit the read-only map
fields. Reopening an existing character writes its active MapId assignment.

The now-proven narrow correction accepts NULL temporary MapId only in the existing
character baseline, while requiring persisted Atlas StaticMapId, exact ID and
finite coordinates. Post-save live-map verification stays strict. The fresh
corrected candidate still uses version 0.10.0/code 5: none of the failed 0.10.0
APKs has been delivered for a Thor test. Existing creation, imports, costume,
powers and runtime components remain unchanged.

The first two hosted attempts stopped before client launch while mirroring the
private MapServer data. The initial staging budget omitted the pinned world and
avatar supplements; adding their exact inventory exposed the deeper cause:
PRoot's `--link2symlink` emulates each newly published hard link with hidden
backing entries. The 2,877 world files therefore left 5,754 extra entries and
619,311,880 extra bytes of staging accounting. Run `36905387168` refused entry
180,006 against the corrected 180,005-file cap and stopped all owned workers,
PostgreSQL and Wine cleanly. Preserve both failed receipts; neither APK is a
qualified Thor candidate.

World/avatar payloads and the world marker now publish through Linux
`renameat2(RENAME_NOREPLACE)`, retaining permissions, timestamps and fsync while
avoiding the emulated hard-link backing files. Existing paths are refused before
the PRoot rename hook, and the kernel refuses concurrent replacement. Publication
fails closed if that operation is unavailable. The finite inventory budget still
includes both pinned supplements. These changes required a fresh signed APK and real ARM64 hosted
qualification before the one-session Thor test; the retained-APK gate above
now completes that qualification. Dependency downloads
are bounded and reuse SDK 35 when already present on the runner.


Run `36909118523` passed tooling and prepared caches but its bounded compiler
install timed out on a throttled Azure Ubuntu mirror before APK packaging.
The build now uses Ubuntu's canonical signed mirror and only the required
MinGW POSIX compiler variant, with an eight-minute overall step bound.

The next candidate defaults to reopening the existing COHLOCAL / THORHERO ID 1.
It compares a read-only pre-login baseline with the ordinary committed save,
preserves identity, powers and costume, and requires LoginCount to increment
once. Its pinned Atlas supplement adds missing geometry and referenced textures
to the private client/server trees. A one-time refresh removes only affected
private compiled map caches; the original import and accepted cache archive are
preserved. The large supplement ZIP is reconstructed from exact reviewed public
PIGG ranges rather than committed as a Git blob.

The [static world review](android-evidence/atlas-world-static-review-20261001.json)
verified exact reconstruction of the 203,438,405-byte ZIP, all 2,877 decoded
files (309,655,940 bytes), a complete first install and repeat reuse, and narrow
cache refresh. The 4,209,334-byte manifest records 488 geometry and 2,389 texture
files with no accepted-import/avatar overlap. These are static checks; runtime
appearance and recovery still require the candidate's hosted/device evidence.
The complete install replay also used the accepted import's original directory
case plan, preserving all 741 existing directory spellings and inodes. The
[Android compile](android-evidence/character-reopen-android-compile-20261001.json)
passed resource linking, all 15 Java sources and D8 bytecode generation using
the official checksum-verified SDK 35 platform and build tools.

After native connection and three fresh Android views, the app enables
**Return to safe ground**, delivering ordinary `/stuck`. It requires two fresh,
stable native positions at least 25 seconds apart, then three fresh Android
views before enabling ordinary save/logout. The committed safe position and
preserved selected rows are required before three fresh post-save captures
enable Finish. Stable native position is a bounded recovery check; actual Atlas
appearance needs visual inspection, and full collision/gameplay remain pending.

The hosted candidate creates a seed through the actual graphical client, saves,
fully stops the owned stack, then reopens and saves the same character through
a second real session with the same PostgreSQL/Wine profile. This hosted seed
does not change the accepted Thor test. The user's next test is only the
[one-session reopen flow](ANDROID_CHARACTER_REOPEN_TEST.md), with the existing
character and app storage preserved.

The user completed `coh-character-creation-20261001-162621.zip` on Android 13 / AYN
Thor and confirmed the default Male costume, visible character/UI, normal save
and return from the game. The [device review](android-evidence/character-creation-thor-20261001.json)
accepts this session without another boot. Native evidence verifies COHLOCAL,
THORHERO ID 1, current CLIENT_READY, requested `/quittologin`, the live logout
timer and committed rows (`ents=1`, `ents2=1`, `powers=7`, `costumeparts=14`).
All 17 Android PNG records and four SQL table hashes were checked; three fresh
post-save captures show the login screen. Cleanup completed with zero remaining
owned workers and zero inspection failures.

The original wrapper remains `client_incomplete`: its final window check accepts
only the login title, whereas the same PID 672 retains
`City of Heroes : City_Zones/City_01_01/City_01_01.txt  PID: 672` after entering
Atlas. The corrective Android source accepts that exact map title with the owned
PID and valid mapped window dimensions. It preserves every import/asset,
SQL/logout, fresh capture and cleanup requirement. All 188 interactive tests
passed, including the actual retained title and rejection regressions. This fix
is for the next APK; the installed 0.9.0 report and uploaded evidence are unchanged.

The scene is still an empty flat backdrop with a visible avatar and HUD.
Native position records show THORHERO falling to Y=-2000 before ordinary logout,
and the logout location is map 1 `(106.453125, -2000, -114.453125)`. This is a real
world/collision issue, separate from the reporting bug; its complete cause is
not established. Keep the existing database and character. The next candidate
must reopen this exact saved character, resolve Atlas geometry/collision and
provide safe relocation of the retained character if required. No character
deletion, recreation or SQL synthesis, and no repeat creation-only device test.

The delivered signed APK is from source `bc4d750deab00f0fdbbd084b32b563aa3abdddce`,
[run 36862027713](https://github.com/Russianranger/coh-android/actions/runs/36862027713),
386,658,292 bytes, SHA-256
`001e1dc4db87f1184814a8f75a33953504d6ee06b238490a8c26c71c4ca7f963`.
Independent [package](android-evidence/character-package-review-36862027713.json)
and [hosted](android-evidence/character-hosted-36862027713.json) reviews passed.
The Male/Clear creator renders its full body and both hands. The owned client
reached CLIENT_READY on Atlas, submitted `/quittologin`, ran the live logout
timer and committed one ents row, one ents2 row, seven power rows and fourteen
costume-part rows. Three fresh host captures follow login, connection and save;
the final view returns to login. Cleanup completed with no remaining workers.

Atlas reaches its HUD and welcome, but the scenery is black without visible
ground or buildings; the in-world avatar is a dark silhouette. Missing Atlas
geometry is consistent with this result, but sole cause is not proved. This is
creation/connection/save qualification, not rendered Atlas or playable gameplay.
The [one-session Thor instructions](ANDROID_CHARACTER_CREATION_TEST.md) are now
historical reference: their creation/save session is accepted above.

The user confirmed local login and supplied `coh-local-login-20261001-010523.zip`.
Independent review matched the 0.8.1 APK and runtime identities, verified all
14 Android PNG and four guest image records, and reviewed the empty 0/12
character-selection screen. Three post-login Android captures, 272 successful
inputs, preserved database/profile/assets/caches and clean owned cleanup are
recorded in the [acceptance receipt](android-evidence/local-login-thor-20261001.json).
The session ended at its 180-second interaction limit. No repeat is requested.

The accepted creation candidate retains package `io.github.russianranger.cohclientinteractive`,
the accepted signing key and profile `android-local-login`. It adds the accepted
Atlas MapServer package because actual character data is sent during the map
handoff. The new target is graphical creation of **THORHERO**, a first connection
to map 1, ordinary logout and read-only verification of committed character,
power and costume records. The interaction window is 1,200 seconds. No existing
character is deleted or synthesized in SQL. A preexisting THORHERO stops this
creation-only candidate while preserving its data.

Thor 0.9.0 creation/save qualification is accepted by the device review above.
Exact-character reopen, Atlas scenery/collision asset closure, gameplay controls
and performance remain pending. Initial map entry completes creation/save; it
does not establish sustained gameplay or hardware acceleration. The following
0.9.0 attempt notes preserve historical checkpoints.

The first 0.9.0 [hosted attempt](android-evidence/character-hosted-36801130531-failed.json)
failed before client launch: Wine could not enumerate directory links in the
new server data tree. The correction uses real directories and the accepted
client's individual immutable file-link pattern. It also waits for the real
client's world-ready record and binds the completed logout command delivery to
fresh logout-timer and SQL evidence; the unmodified server does not log the
individual logout packet. Keep the failed candidate's receipt and clean cleanup
result. No device test of that APK is requested.

The second 0.9.0 [hosted attempt](android-evidence/character-hosted-36802634099-failed.json),
run 36802634099 at source `ae8054d6430c194e32344f47678e134395419046`,
started Atlas, verified local login and reached the creator's Register page for
THORHERO. Host OCR timed out after 20 seconds on the actual tutorial Yes/No
prompt. No character creation, character map entry or committed save is accepted.
PostgreSQL stopped gracefully, but the host killed PRoot before a final guest
report was exported, so full cleanup is unverified. The male avatar preview was
absent, with missing geometry and texture errors: base avatar geometry/textures
are outside the accepted import. Avatar assets remain separate work before
costume rendering or gameplay claims; this candidate keeps the existing assets
and targets registration, Atlas environment loading and ordinary logout/save.
No extra import or device test is requested for this failed candidate.

The subsequent [protocol-flow attempt](android-evidence/character-hosted-36805992804-failed.json),
run 36805992804 at source `335688677eb1fe67e31089b35b3f685bebaf04f6`,
started Atlas and verified login, declined the tutorial and selected Hero.
Its final frame shows the creation confirmation with the pointer covering Yes;
host OCR reported `Rendered Yes button not found`. The guest also failed its
inherited 2 MiB server-log bound during observation and evidence collection.
No character map connection or committed save was proved. This time the guest
report was retained and confirms graceful PostgreSQL shutdown, stopped Wine,
zero remaining owned workers or inspection failures, and preserved database;
the host needed no forced quit or kill. Keep this failed result separate from
qualification of the later avatar-supplement candidate.

The next retry parks the pointer outside each dialog before OCR and waits for a
fresh settled frame. Character mode now retains complete bounded server logs in
one archive with per-file hashes and redaction metadata; final cleanup replaces
live snapshots with closed logs. Its support-evidence budget is 256 MiB with a
260 MiB ZIP guard, while login-only defaults remain unchanged. Local validation
passed 168 interactive tests, 26 client/cache tests and the full Java compile.
Hosted creation, save and avatar rendering still require a passing runtime run.

The [13-file avatar attempt](android-evidence/character-hosted-36807202335-failed.json)
at source `80e776f30de896605b6db4101baa5ab16957a29a` hit the same confirmation
OCR and log-export failures, with full graceful cleanup. All 13 supplement files
installed correctly, but screenshots show a head and fragmented white torso,
without a complete body. Source review explains why: entering the costume screen
applies a random preset. This run selected Military, whose parts were absent.
The normal **Clear** control resets to deterministic tights, smooth gloves/boots
and Martial Arts hair, without a confirmation or another random choice. The next
candidate adds that explicit test step and its seven missing asset dependencies;
partial installation or a partial preview is not a visual qualification.

That candidate contained a pinned 20-file supplement for the Male body
and the costume selected by **Clear**. A bounded source audit recovered only
the missing entries from the original project's PIGG donors;
[entry integrity and format checks](android-evidence/character-avatar-source-review-20261001.json)
passed. The 1,722,790-byte ZIP adds 2,737,564 bytes to the private client worktree,
preserving the imported archive, client prerequisites, cache identity and saved
profile. Installation rechecks all files on reuse and refuses conflicting files
or links. The 13-to-20-file upgrade also preserves the original files' inodes,
bytes, modes and timestamps. Male rendering after reset and character saving still require hosted
qualification; other bodies and costume choices remain outside this small
supplement. The next Thor instructions explicitly use **Male → Costume → Clear**.

The [confirmation retry](android-evidence/character-hosted-36809680532-failed.json)
at source `b17457ec83aa705b1c265f8d511da08b5823c382` passed all three dialog OCR
steps and delivered the final Yes. DbServer then reported THORHERO assigned to
map 1, loaded and connected. The guest stopped during world loading because the
client changed its window title to include the map path; the inherited check
accepted only the menu title. The same owned client and display were still
running. No CLIENT_READY, rendered Atlas environment or ordinary logout/save is
accepted. Full bounded server logs were retained, PostgreSQL stopped gracefully,
and zero owned workers or inspection failures remained. The next candidate
recognizes the source's two PID-bound title forms and preserves rejection of
unrelated windows, while retaining the existing renderer and startup checks.

The [owned-window retry](android-evidence/character-hosted-36846149988-failed.json)
at source `e00f04970fa438864c08c339e5f6c65515b7ecdc` kept the map-title window
observed and delivered the same creation steps. Clear rendered textured tights,
boots and head/hair, but the forearms and hands were absent. The native launcher
then returned 67 at its inherited 1,200-second deadline from launch; the guest's
1,200-second interaction window starts after client readiness, reached at
419.223 seconds. This cutoff is not evidence that the game process crashed.
The last console stage was `AutoGroup..` during map loading. No CLIENT_READY,
rendered Atlas or ordinary logout/save is accepted. Guest cleanup completed
without forced host termination, remaining owned workers or inspection failures.
The next correction gives only character mode a 2,160-second launcher bound
(900 startup + 1,200 interaction + 60 completion grace), and adds the missing
smooth glove geometry using its source-pinned donor entry.

The corrected supplement contains 21 files in a 1,842,488-byte ZIP, adding
2,980,122 bytes to the private worktree. Its only new file is
`data/player_library/male_glove.geo`, containing the two Smooth forearm/hand
models used by Clear; the matching glove texture was already included.
The source entry MD5 and decoded GEO model names were checked, and all original
20 file bytes and provenance records remain unchanged. Installation tests cover
both 13-to-21 and 20-to-21 upgrades without replacing accepted files or changing
the import, worktree identity or caches. Visual completeness and the full
creation/save milestone still require the corrected hosted run.
The combined correction passed all 173 interactive and 27 client/cache tests.
Independent review checked the exact glove model names, previous file pins and
provenance, strict launcher modes and the production deadline regression.

Source review also found an existing native MapServer option for the costly
`AutoGroup..` stage: **`-donotautogroup`**. Production servers already default to
this setting; the development server used by character mode does not. The stock
world packet sends the setting to the client before map loading, so both sides
use the same load policy. The next candidate requests this option only for its
owned Atlas launch and records the policy in its report. Normal map parsing,
tracker activation, welding, collision setup, CLIENT_READY and ordinary
logout/committed-save gates remain. No binaries or imported assets are rebuilt
for this change. The development client also sets `iAmAnArtist` under this stock
policy; do not claim identical internal group topology or physical visual and
collision acceptance before runtime review. See the
[source review](android-evidence/character-atlas-autogroup-policy-source-review-20261001.json).
The [full-budget retry](android-evidence/character-hosted-36852214162-failed.json)
at `cdff43b4` exhausted its full twenty-minute interaction window while the client
remained at `AutoGroup..`. Both forearms and hands visibly rendered after Clear,
alongside the tights, boots and hair. The owned client was still alive; its
1,641.351-second launcher lifetime was below the new 2,160-second bound.
No CLIENT_READY or requested ordinary logout/save was obtained. A later server
logout-timer expiry followed no logout input and is consistent with the normal
connection timeout, so it is not accepted save evidence. Guest cleanup completed
with no remaining owned workers, inspection failures or forced host termination.
The production-policy candidate at `19879ed5`,
[run 36855035567](android-evidence/character-hosted-36855035567-failed.json),
failed before login because the external host driver opened Settings and never
dismissed its overlay. The tiny red-X click failed visibly before Escape was
sent; fresh frames continued but never matched the restored login panel. No
credentials were entered, creator opened or Atlas client policy exercised.
Its full interaction-bound failure therefore does not establish that the Atlas
policy failed. Cleanup again completed without remaining workers, inspection
failures or forced host termination.

The signed APK is already built and
[independently verified](android-evidence/character-package-review-36855035567.json):
386,658,292 bytes, SHA-256
`1da4719cf7af825092199c73067fb5fd3423fcaa8543a37d366ad1a0557ed681`.
The next qualification uses that immutable APK. The corrected character-only
host driver omits the previously accepted optional Settings probe, preserves
ordinary login actions, and requires the current login event plus three fresh
post-event captures within 180 seconds. The login-only driver remains unchanged.
Full map-ready, ordinary logout and committed-save acceptance remain pending.
The dedicated `android-character-qualification.yml` workflow checks the exact
donor run, successful APK job and artifact digest before reusing the APK and
its build receipt. It records the current external-driver commit separately
from APK source `19879ed5`; packaged Java/native/guest source closure remains
checked, and neither the APK nor prepared caches are rebuilt. This host-only
correction passed all 181 interactive and 27 client/cache tests, including
failed/forged donor rejection and login event/fresh-frame/deadline regressions.
All 174 interactive tests passed after the policy change, including an integrated
Atlas startup regression that rejects tick zero and NotReady, and requires
advancing completed ticks around the successful current-map protocol query.

The [immutable retry](android-evidence/character-hosted-36862027663-failed.json)
at driver `bc4d750d` reached an empty character list using **OHLOCAL**: the host
lost the initial C during typing. Exact COHLOCAL identity proof correctly failed
at the new 180-second login bound. No character or Atlas client policy was tested
in that retry. Its already-verified source-19879ed5 APK remains unchanged.
The parallel normal run at the same driver did enter COHLOCAL and passed the
full flow; its reviewed APK and scope are the current result above.

The subsequent host-only typing correction separates focus and Ctrl-release
from text by fresh frames, uses longer key settles and requires the entire
rendered account field to read COHLOCAL before submitting login. Replacements
are bounded to three attempts within the existing login deadline. All 186
interactive tests passed; the 27 client/cache checks remain unchanged and passed.
Actual OCR rejects the failed OHLOCAL frame and accepts a correct COHLOCAL frame.
This correction changes no packaged APK payload. It is a future host-driver
improvement, not the tested `bc4d750d` driver: the historical passed report lacks
the newer OCR receipt fields and must remain bound to its original validator.

**Historical hosted 0.8.1 qualification — the following device instruction is superseded by the accepted report above.**

**0.8.1 passed the hosted saved-Wine-profile refresh regression and graphical local login. It is ready for one Thor login session as an in-place update.**

Qualified source `1fb4c6057fda579da1913670889922ba8e53bbdc`,
[run 36785793934](https://github.com/Russianranger/coh-android/actions/runs/36785793934),
passed all 11 guest stages. The test first created a genuinely ready Wine profile
using the exact APK and real PE32 probe, stopped it cleanly, then made only its
stored registration timestamp stale. The login run performed exactly one real
registration pass (3/1/1) in 38.481 seconds, retained the prefix inode and sentinel,
matched the new timestamp, and renewed readiness after the real PE32 probe.
The seed's retained raw timestamp bytes confirm CRLF (`0d0a`) line endings.

Root screenshot review confirms **Server Used/Total: 0/12** with twelve empty
Create Character slots. Local authentication, the sent character list and SQL
account identity agree. Client startup took 439.248 seconds, followed by 48.585
seconds of observation. All 63 login-run child records closed with zero remaining
owned workers or inspection failures; PostgreSQL stopped gracefully and retained
its database. The separate prefix seed also cleaned up successfully.

The qualified `COH-Local-Login-0.8.1.apk` is 373,849,564 bytes, SHA-256
`2f9663f43c24b071714a7ea2f63a2f8abd624a49bca4b64298f58c7e56278a20`.
It retains the installed app identity and signing certificate, increments version
code to 3, and preserves the imported assets, client caches and Wine state.
All 86 interactive and 26 client/cache automated checks passed. See the
[hosted review](android-evidence/local-login-hosted-36785793934.json),
[package review](android-evidence/local-login-package-review-36785793934.json)
and [one-session Thor instructions](ANDROID_LOCAL_LOGIN_TEST.md).
Physical Thor local login remains pending; no new Atlas, Settings, general input,
character creation, or restart/reopen device test is requested in this pass.

**Historical Thor 0.8.0 failure: Wine profile refresh was rejected before DbServer or the game launched. No repeat of 0.8.0 is requested.**

The supplied `coh-local-login-20260930-220534.zip` records a 76.956-second
operation. Imported assets and the generated client caches were successfully
reused through the wrapper-only migration. PostgreSQL initialized its persistent
profile and started successfully. Wine then exited initialization with code 0,
recording one complete registration pass (three registration processes, one
WoW64 process), but the reused-prefix validator expected no registration and
reported `Wine initialization registration evidence differs`. No client inputs
were sent. All 21 child records closed; PostgreSQL stopped gracefully, its
database remained intact, and no owned workers or inspection failures remained.
See the [device failure receipt](android-evidence/local-login-thor-review-20260930.json).

Source review explains the upgrade-specific mismatch: the Android extractor
recreates Wine files with extraction-time modification dates on a new runtime
generation. Wine compares the installed `wine.inf` modification time with the
decimal value inside the preserved prefix's `.update-timestamp`. Our marker
only compared the unchanged runtime archive identity. The device report did
not contain those timestamp values, so the timestamp mismatch is a source-based
explanation; the complete unexpected registration pass is directly recorded.
The correction reconciles this metadata before calling the existing strict
initializer, preserves the prefix, and requires the real PE32 runtime probe before
writing readiness. The hosted stale-timestamp regression seeds a real prefix
using the exact APK's Wine and PE32 probe, proves cleanup, changes only the
stored timestamp, and requires a real registration refresh before graphical
login. Prefix inode/sentinel and Wine input hashes must survive. This regression
passed in corrected run 36785793934, as recorded above.

The first corrective hosted run
[36784616495](https://github.com/Russianranger/coh-android/actions/runs/36784616495)
successfully seeded a real Wine profile and performed the required saved-profile
refresh. It then failed because the new timestamp reader accepted only LF line
endings. Pinned Wine writes this file through CRT text mode, which uses CRLF.
Corrected source `1fb4c6057fda579da1913670889922ba8e53bbdc` accepts complete decimal
timestamps ending in LF or CRLF, retains all registration/probe checks, and adds
raw timestamp-format evidence to the hosted seed receipt. Keep the
[failed hosted receipt](android-evidence/local-login-hosted-36784616495.json);
that candidate was not delivered for a device test. All 86 interactive and 26
client/cache automated tests pass; corrected hosted run 36785793934 passed.

**Historical 0.8.0 fresh-profile hosted qualification passed; the Thor result above supersedes its device-test recommendation.**

Accepted source `a80bc9c9df684779987dd6d1c146c66960db9458`, run
[36779011148](https://github.com/Russianranger/coh-android/actions/runs/36779011148),
passed all 11 guest stages and independent package review. Root visual review of
fresh post-response screenshots confirms **Server Used/Total: 0/12** and twelve
empty Create Character slots. The owned local DbServer authenticated `COHLOCAL`,
sent the character list, and matched SQL account ID `1353310574` with zero
characters. The graphical client became ready in 441.389 seconds; total hosted
execution took 671.270 seconds. Finish completed after 49.235 seconds of live
observation. All 63 child records closed, PostgreSQL stopped gracefully, the
database was retained, and no owned workers or inspection failures remained.
The same run also recovered the login screen after Settings X/Escape.

The accepted `COH-Local-Login-0.8.0.apk` is 373,845,468 bytes, SHA-256
`76723c1b2f52d351f48d3b46a15625414c3977fdb8230965d83ec939d2af88fd`.
It retains app ID `io.github.russianranger.cohclientinteractive` and the 0.7.0
signing key, increments version code to 2, and preserves imported assets, Wine
state and compatible prepared/generated caches. All 77 interactive and 26
client/cache automated checks passed. See the [hosted receipt](android-evidence/local-login-hosted-36779011148.json),
[package review](android-evidence/local-login-package-review-36779011148.json)
and [one-session Thor instructions](ANDROID_LOCAL_LOGIN_TEST.md).

The scope is hosted graphical local login and an empty character list. Android
local login, account reopening after restart, character creation and world entry
are not yet accepted. This hosted run initialized a fresh persistent profile;
retaining its database at cleanup does not prove a subsequent reopen. Raw
automation reports intentionally leave visual-validation flags false; the
separate review receipt records the screenshot assessment.

Sequential targets:
1. Confirm this APK's local login and clean Finish on Thor in one session.
2. Create and save one graphical character against the persistent profile.
3. Restart and reopen that exact saved character, proving durable persistence.
4. Enter a local map with MapServer and verify initial world interaction.
5. Refine gameplay controls, performance, audio and hardware acceleration.

The first hosted attempt below remains a failed historical result.

Candidate source `8d8ebd35396e193f426df686167c87e3d2eeee7a`, run
[36775940197](https://github.com/Russianranger/coh-android/actions/runs/36775940197),
passed signed packaging and independent package review. PostgreSQL and the pinned
loopback DbServer started, and the graphical client reached its login screen in
438.599 seconds. Root screenshot review confirmed Settings X/Escape recovery,
`COHLOCAL`, masked password entry and the single `127.0.0.1` shard. The client
then displayed **Wrong game version** and the bounded interaction timed out.
All 67 owned child records closed; PostgreSQL stopped gracefully, its profile
was retained, and no owned workers or inspection failures remained. Preserve
that failed result: see the [runtime review](android-evidence/local-login-hosted-36775940197.json)
and [package review](android-evidence/local-login-package-review-36775940197.json).

Pinned source explains the malformed development version strings: its getter
expects `Ouroboros.exe`, ignores the failed timestamp lookup in these differently
named executable layouts, then formats uninitialized date fields. The accepted
headless TestClient already requests the supported development version exception.
The correction adds `--local-login` to the native launcher, which alone appends
`-noversioncheck 1`; ordinary startup and cache generation are unchanged. The
separate DbServer wire-protocol check and exact source/executable/data pins remain
enforced. Corrected run 36779011148 passed as recorded above.

The update keeps the installed app identity/signature, imported assets, Wine
prefix and compatible prepared/generated caches. The new persistent
`android-local-login` profile starts PostgreSQL/DbServer with no MapServer. Login
acceptance requires current owned-server authentication and a sent character-list
response, matching SQL account identity and fresh captures; actual empty-character
selection requires visual review. The [one-session Thor instructions](ANDROID_LOCAL_LOGIN_TEST.md)
now identify the accepted APK receipt/hash. Do not repeat earlier
startup, menu input, Atlas, or synthetic display device tests.

**Physical Thor startup and basic menu input are accepted within their reviewed scope. The 0.7.0 device session failed its final-frame check during a graphics reload; cleanup passed.**

The supplied `coh-client-interaction-20260930-201926.zip` records 174 input
events with zero transport failures. The user confirmed touch and right-stick
pointer movement, A as left click, and text entry; retained Android captures
show `COHINPUT` in Account Name with Settings open. All 40 owned child records
closed, with zero remaining owned workers or inspection failures. Preserve
the original failed result: Finish captured an all-black guest desktop after
58.427 seconds of observation, reporting `Observed client desktop became blank`.
See the [device interaction review](android-evidence/client-interaction-thor-review-20260930.json).

The last Android capture shows loading artwork. The console continues through
shader compilation. Source review shows that the Settings red X invokes the
settings-close path, which reapplies graphics settings and can show loading
artwork while rebuilding rendering resources. This supports a graphics-reload
explanation; it does not prove eventual recovery or that B caused the blackout.
B maps to Escape; its separate visible effect remains unverified. Do not call
the complete session passed or suppress the blank-frame acceptance check.

No repeat device menu test is requested. Carry the confirmed input results
forward. The source correction now adds bounded final-frame settling within the existing
interaction deadline, retaining blank samples and checking the exact client
window/process, display and complete console evidence. Fresh nonblank output
is required before acceptance; permanent blank output, client exit, window loss
and deadline expiry still fail. At most three raw blank images are retained to
preserve the existing support archive limit. All 53 interactive automated tests
passed after this correction, including transient blank recovery, permanent
blank output, deadline, process/window loss and truncated console cases.
Hosted run 36775940197 now demonstrates the Settings-close/Escape sequence
returning to the login screen; corrected run 36779011148 also passed local-login
qualification. Install 0.8.0 over 0.7.0 and retain its imported/runtime state.

The supplied `coh-game-client-test-20260930-141120.zip` passed the exact shipped
Java cleanup and PixelCopy acceptance checks. Its pinned actual client reached
renderer, all-data completion, main loop and the exact-PID window. All three
Android screenshots show the Freedom login screen and first-launch graphics
prompt; they span 2.037 seconds after current-session readiness. The client
remained observable for 34.810 seconds, and all 38 child records closed with
zero remaining owned processes and zero inspection failures. Renderer startup
at about 5m56s explains the user's reported first visible boot; full readiness
was 10m20s after client launch and the entire first operation took 16m24s,
including private-data preparation and Wine initialization. See the
[physical client receipt](android-evidence/accepted-client-startup-thor-20260930.json).
No repeat startup, Atlas, synthetic presentation, Stop/rerun or screen-lock
acceptance test is requested.


The corrected interactive APK from source
`fdd0acc492485455ce0fc8b43eb4b406da529ba1`, run
[`36736910061`](https://github.com/Russianranger/coh-android/actions/runs/36736910061),
passed all seven guest stages and independent package/session checks. Root visual
review confirmed that Cancel dismissed the graphics prompt, `COHINPUT` appeared
in Account Name, and Settings opened. Startup took 362.627 seconds, followed by
33.543 seconds of live observation; all 27 child records closed, with zero
remaining processes or inspection failures. The APK is 370,560,140 bytes,
SHA-256 `8ada2e23cf8cf4986b4faacdff1839233ef6538cf4eb12602d2e11d1cb3d36ca`.
All 44 automated checks passed. See the
[hosted interaction receipt](android-evidence/client-interaction-hosted-36736910061.json),
[package review](android-evidence/client-interaction-package-review-36736910061.json)
and [one-session device instructions](ANDROID_CLIENT_INTERACTION_TEST.md).
The later physical review above accepts the user-confirmed basic menu inputs;
input counts alone do not establish a visible game response.

The **COH Client Interaction 0.7.0** milestone adds touch, text and basic
Thor controller menu input, then Finish and verified cleanup in one session.
It starts no server. The old 0.6.0 development signing key was not retained,
so its installed package cannot be updated while preserving private state.
The new package `io.github.russianranger.cohclientinteractive` installs beside
it and requires its own one-time runtime setup and asset import. The new
development signing identity is retained, backed up and pinned to certificate
`92955353965f118a748f1f2cadc00dfb39b3e8ade0a6cdd7d44058a3a776c282`;
future builds fail rather than silently generate another certificate.
The accepted old apps stay installed. Login, world entry, audio, hardware
acceleration, B/Escape behavior and recovery after a settings reload remain
separate unproven outcomes.


The first interactive hosted candidate, run `36732627939`, passed startup,
observation, Finish and cleanup, but failed visual input qualification: Settings
opened while the graphics prompt remained and `COHINPUT` was absent. That APK
was not delivered. Source review found that Cancel and account focus use stored
button-down coordinates, while Settings uses the current cursor position. CoH
polls the absolute pointer at the end of its input frame, so a combined pointer
warp and press can leave stored click coordinates stale. The correction sends
neutral pointer movement before a bounded settling interval and button-down;
the hosted check also waits for fresh frames before clicks and text entry.
No game binary, accepted startup gate or window-focus behavior is changed.


With basic physical menu input now accepted, the next smallest gate is graphical
loopback login to an empty character-selection screen using PostgreSQL/DbServer;
MapServer and world entry can follow later. Update the retained-signature 0.7
package so its imported generation, Wine prefix and prepared caches survive.
Start the server pair once for that client session and initialize a persistent
server profile once. The accepted Atlas diagnostic dropped its database and
deleted its run tree during cleanup; it preserved import data and evidence, not
a resumable `TEST50056` character. Reuse the accepted implementation and receipts,
not a nonexistent live database or another app's private files. Verify the actual
client protocol and local `-db` authentication path in a hosted session before
requesting this later device gate.


**Historical hosted qualification for the accepted 0.6.0 build follows.**

Exact APK source `5e4e8f2f0acc78e397a3ee8c1eb7df6f661953cb`, run
[`36719533060`](https://github.com/Russianranger/coh-android/actions/runs/36719533060),
passed all six guest stages. Startup reached the renderer, all-data completion,
main loop and exact-PID 800×600 window in 362.742 seconds, then remained live
for 33.433 seconds. Three fresh external frames span 2.566 seconds after
readiness, and final cleanup left zero owned processes or inspection failures.
Root visual review sees the Freedom login screen with its first-launch
Quality/Ultra graphics prompt. Interaction remains untested; leave that prompt
untouched for the physical run. The full 39,463,670-byte console is retained.
The exact APK is 370,539,567 bytes, SHA-256
`ca506e5c22369de04d80cb98b6a747bd818ef20c81245806b6d7271357f3377d`.
See the [hosted qualification receipt](android-evidence/client-startup-hosted-36719533060.json)
and [one-run device instructions](ANDROID_CLIENT_DEVICE_TEST.md). Hosted evidence
does not establish Android execution, PixelCopy, input, world entry, hardware
acceleration or playable performance for this actual-client build.

**Physical Thor presentation 0.5.0 passed and remains accepted.**
The supplied `coh-client-test-20260930-094646.zip` verifies all 120 current-session
PixelCopy frames over 62.758 seconds. The full operation took 128.592 seconds;
all five guest stages and six child records passed, and cleanup left zero
owned processes or inspection failures. Exact shipped Java acceptance and
runtime identities were independently replayed. See the [physical presentation
receipt](android-evidence/accepted-presentation-thor-20260930.json).

The separate **COH Game Client Test 0.6.0** packages the pinned actual
`CityOfHeroes.exe` and matching DLLs. Reuse the reviewed asset ZIP for one
private import, then attempt visible game loading/login without a server boot.
The one-run instructions are in [the client device test](ANDROID_CLIENT_DEVICE_TEST.md).
Earlier hosted attempts below are historical; their proposed next actions are
superseded by the exact-APK qualification above.

The initial actual-client hosted attempt [36700734062](https://github.com/Russianranger/coh-android/actions/runs/36700734062)
displayed the Freedom loading artwork but timed out before `game_mainLoop`;
cleanup was complete. Do not deliver that APK as qualified. Its later console
output was redirected away from the inherited pipe. See the
[first failed startup receipt](android-evidence/client-startup-hosted-36700734062.json).
The next diagnostic [36704251918](https://github.com/Russianranger/coh-android/actions/runs/36704251918)
confirmed owned-console capture and a correctly fitted 800×600 loading screen.
Renderer, texture headers, fonts, group libraries and LOD data completed; the
300-second diagnostic deadline expired during sequencer text parsing. Nine
private caches were generated and cleanup was complete. This establishes cold
data processing, not a rendering deadlock or complete startup. The next work
is to prepare compatible client caches off-device and qualify a normal startup.
See the [second failed startup receipt](android-evidence/client-startup-hosted-36704251918.json).
Native x86 cache generation then finished in 221 seconds with the game completion
marker, but correctly failed its output checks because three badge/pophelp
attributes were absent. The next candidate includes those exact accepted lookup
files for both cache generation and normal startup. See the
[cache generation receipt](android-evidence/client-cache-generation-36706745544.json).
The corrected candidate `a40250b0032bd05a333514920722ddffa4427730` produced
100 verified caches and a verified 0.6.0 APK in run `36707839624`. Its short
300-second hosted diagnostic consumed those caches without rebuilding them and
continued through powers, NPCs and items to FX loading when the diagnostic
deadline expired. Cleanup was complete. The next qualification uses this exact
APK and its existing normal 900-second startup budget, with all readiness,
observation and cleanup checks unchanged; do not rebuild or repeat phone tests.
See the [cached diagnostic receipt](android-evidence/client-startup-hosted-36707839624.json).
The full-budget run `36710174172` advanced through FX, villains, cape FX and
body parts, then hit the diagnostic 1 MiB console limit during NPC costume
missing-texture warnings. It did not exhaust the startup deadline, and cleanup
was complete. The next wrapper increases bounded observation capacity, preserves
all failure/readiness checks, and reuses the exact verified caches. See the
[observation-budget receipt](android-evidence/client-startup-hosted-36710174172.json).
Run `36711916066` then retained the complete 5.79 MB console capture but reached
the 900-second startup limit just after mission-maker data, at the start of
player geometry preload. NPC and costume checks consumed about 514 seconds;
the main loop was not reached and cleanup was complete. See the
[full-budget receipt](android-evidence/client-startup-hosted-36711916066.json).
The next wrapper reduces repeated parsing of the same diagnostic log and uses
the client's native-diagnostic-UI mode to preserve direct pipe logging. This
changes native prompts and the small initial splash, while retaining actual
game window creation, graphics, data loading and texture validation. It needs
fresh hosted qualification; no phone rerun is requested for failed candidates.
See the [console profile review](android-evidence/client-console-profile-20260930.md).
The profile worked in `36716064689`: the child attached to the real parent
console and preserved direct logging. The full warning stream exceeded the
10 MiB guest limit during NPC validation, about 321 seconds into startup;
the deadline was not reached and cleanup was complete. NPC warnings alone
are estimated to exceed 20 MiB. The hosted Raw-only RFB viewer also disconnected
on a desktop-size change; Android's existing viewer already handles that event.
The next candidate retains up to 128 MiB of complete raw output, streams the
bounded support archive into the Android export, and fixes the hosted viewer's
resize and post-readiness frame checks. It keeps the same startup deadline,
full data validation, and exact game/cache inputs. See the
[direct-output receipt](android-evidence/client-startup-hosted-36716064689.json).
Physical synthetic presentation is closed; do not request another pattern,
Atlas, Stop/rerun or screen-lock test. Actual client, menu, input, hardware
acceleration and gameplay claims remain separate.

**COH Atlas Test 0.4.4 also passed on the physical AYN Thor.**
The supplied `coh-atlas-test-20260930-003609.zip` verifies all 18 stages in
55 minutes 52.7 seconds: both protocol saves committed, `TEST50056` resumed in
the same cluster with 12,345 influence and login count 1 → 2, and all 102 child
captures closed. Restart and final owned cleanup had zero inspection failures
and zero remaining processes. The device exercised the EACCES exit recovery;
the separate ESRCH path was not exercised. The exact original report also passes
the Java acceptance/cleanup checks and Python capture/startup checks.
See the [physical acceptance receipt](android-evidence/accepted-atlas-test-thor-20260930.json).

The user explicitly asked to advance without manual Stop/rerun or another long
server boot. Manual Stop/rerun and screen-lock checks remain **skipped at user
request, unvalidated** for 0.4.4; they are not prerequisites for the next APK.
The 177 ms activity visibility gap does not prove sustained background operation.
Do not request another full Atlas test to close those checks.

Keep the accepted Atlas app and its private runtime installed. The separate
**COH Client Test 0.5.0** implements the next [presentation gate](NEXT_ANDROID_PRESENTATION_GATE.md):
a session-bound animated Wine/OpenGL fixture, app-private Unix RFB, an Android
SurfaceView, and actual PixelCopy frame verification. It starts no game server
or SQL service and imports no game data. The exact signed APK passed hosted qualification in
[run 36654262400](https://github.com/Russianranger/coh-android/actions/runs/36654262400):
the external private RFB viewer observed all 120 frames in 109.26 seconds, and
all six children and the socket cleaned up. The APK itself is from build
`36653423058`, source `6fdeef4494dd41f6137ee51d80ec4e39cf687b01`; only the
host viewer changed for qualification. See the [receipt](android-evidence/accepted-presentation-hosted-36654262400.json).

That physical [display test and export](ANDROID_PRESENTATION_DEVICE_TEST.md) has now passed,
as recorded above. Its installation instructions are retained as historical evidence.
A visible fixture does not establish actual CoH menus, world rendering, controls
or gameplay. Preserve the separate APK and do not repeat the accepted server test.

The 0.4.4 exact signed APK remains hosted-qualified in
[run 36638344040](https://github.com/Russianranger/coh-android/actions/runs/36638344040)
at `e30c0b58b0e53534f92e77cdb7b8b93fe3ddc5ce`.
See the [hosted receipt](android-evidence/accepted-atlas-test-hosted-36638344040.json).

The earlier checkpoints below preserve their original successes and failures.
Their installation and retry directions are superseded by the physical pass and next-step direction above.

**Qualified MapServer diagnostic donor: run 36630872719.**
Run `36630872719` passed all six real Windows producer contracts and all eighteen
ARM64 game stages in 31 minutes 23.5 seconds. Independent review verified both
committed saves, exact-name resume, 122 closed children and zero ownership
inspection failures at restart and final cleanup. Raw records show 8,226 completed
ticks on the first launch and 2,425 on restart, with distinct file identities.
Only the separately identified MapServer changed; accepted supporting binaries
and their original source identities remain exact.

The successful run also captured a 114.233-second interval inside the first
`FolderCacheDoCallbacks` call, with one tick started and none completed. Existing
freshness checks rejected protocol-ready samples aged 23 and 85 seconds. This
does not prove the cause of earlier uninstrumented failures or repair the folder
work. The qualified 0.4.4 profile additionally requires a freshly validated
completed tick and the two-phase startup guard described above, preserving
startup deadlines, 20-second freshness and 30-second observation.

0.4.4 carries these diagnostics from donor commit
`003b07bcd98cb100c1505c15670c07d11a240c8f`, separately from its Android
wrapper and guest-adapter commit. Only the instrumented MapServer is replaced;
accepted supporting binaries and their original source identities remain exact.
See the [hosted diagnostic qualification](android-evidence/accepted-mapserver-progress-hosted-36630872719.json).

**0.4.3 remains unqualified after two hosted Atlas heartbeat failures.**
All 113 candidate checks and exact APK verification passed. Both runtime attempts
of the same signed APK in run `36621227369` passed nine stages, then failed
`Atlas lost current readiness during observation`, before character creation or
restart. DbServer kept dispatching and both services were alive at capture.
Both final cleanups completed with zero ownership inspection failures and zero
remaining owned processes. Neither attempt exercised the targeted restart race.

Identical 0.4.3 retries are stopped. The separately receipted MapServer diagnostic
above now exposes fresh late-startup and main-loop stages while preserving all
readiness, listener and cleanup checks. Buffered stdout and saved thread contexts
from these failures do not prove the blocked operation. Do not install 0.4.3 as
a qualified candidate. The 0.4.4 hosted pass does not establish the root cause or
repair of either earlier uninstrumented failure.
See the [attempt 1 review](android-evidence/atlas-test-review-36621227369-attempt1-failed.json),
[attempt 2 review](android-evidence/atlas-test-review-36621227369-attempt2-failed.json),
and [observer design](android-evidence/atlas-test-heartbeat-observer-plan-20260929.md).

**Thor 0.4.2 follow-up (2026-09-29, 18:57 UTC): cleanup is blocked again.**
The first 13 stages passed, including Atlas live-heartbeat observation and the
committed save of `TEST24402` with 12,345 influence. `game_restart` failed with
`Cannot verify Wine descendant ownership` after Wine stop/wait both returned 0.
Final cleanup subsequently found zero remaining owned processes and closed all
84 child records, but one earlier inspection failure remained latched. The app
correctly refused reuse. This run did not reach PostgreSQL restart, the new
restart startup budget or exact-name resume. No Stop or cancellation was recorded.

The report has zero permission-read retries and no permission observations. Its
message comes from the generic OS/parse-error path and omits the underlying
exception, errno and process identity. A reproduced proc-file exit race is a
candidate mechanism, not a proved explanation of this particular device run.
The narrow correction introduced in 0.4.3 and retained in 0.4.4 handles
ESRCH from status/stat as task disappearance.
Environment/namespace ESRCH requires a fresh exact-identity check and preserves
inspection of live workers behind a stopped leader. Live unreadable ownership
still fails; retries and diagnostic records are bounded. The original operation,
exception type, errno and process/thread IDs are retained without raw contents.
See the [owned-child reproduction](android-evidence/atlas-test-proc-exit-reproduction-20260929.json).
The accepted base runtime, identity/token signaling checks and Java cleanup
gates remain intact. Do not repeat 0.4.2. The current 0.4.4 procedure supersedes
that failed app's recovery and retry sequence: one full Thor test/export first,
with Stop/rerun and lifecycle checks held until report review.
See the [device failure review](android-evidence/atlas-test-thor-cleanup-failure-20260929-185717.json).

**Previous hosted checkpoint: COH Atlas Test 0.4.2 passed on attempt 2.**
The exact signed APK completed import and all 18 create/save/restart/resume stages
in 32 minutes 11 seconds, with both committed saves and complete owned cleanup.
All 100 candidate checks passed. That checkpoint qualified the bounded
DbServer startup correction; the subsequent failed Thor run is preserved above.
Attempt 1's separate Atlas heartbeat failure remains preserved. The unchanged
repeat passed, but does not establish a repair or root cause for that failure.
See [run 36599606621, attempt 2](https://github.com/Russianranger/coh-android/actions/runs/36599606621/attempts/2)
and the [acceptance receipt](android-evidence/accepted-atlas-test-hosted-36599606621.json).
That 0.4.2 candidate code was `ea5c0e18d2971d8ae9ade3f6655cea7da87e30f5`.
Its installation instructions are superseded by the current 0.4.4 procedure;
the acceptance and subsequent device failure remain separate historical records.

Previous device checkpoint (2026-09-29, 16:32 UTC): **0.4.1 recovered the ownership
read race and passed 15 stages, then hit a separate DbServer startup deadline.**
The first committed save, owned service stop and PostgreSQL restart passed.
Both restart and final cleanup reported zero inspection failures and zero
remaining owned processes. Two denied worker-environment reads ended in verified
disappearance; the app was not cleanup-blocked. The report records a timeout,
not cancellation. Screen off/on events were recorded during the earlier startup,
but the full lifecycle/device milestone remains unaccepted.

At restart the retained 5,935-column schema was ready at 16:31:28; this started
the inherited 30-second dispatch deadline while DbServer was still initializing.
Its normal minimum 15-second launcher wait began at 16:31:50. The deadline fired
at 16:31:58.99, before that wait could finish. Pre-cleanup publication was valid
but still at SQL_KEEPALIVE_QUEUE with loop count zero. The test correctly refused
to call this ready. The 0.4.2 adapter correction uses one shared 600-second startup
budget across schema/listener readiness and positive-loop dispatch, retaining
the existing overall deadline, cancellation, health and readiness predicates.
Accepted base payloads and Java guards remain unchanged. See the
[failure receipt](android-evidence/atlas-test-thor-dispatch-failure-20260929.json).
The 0.4.2 APK built successfully and its 30 payloads and 12 Java source identities
match candidate commit `ea5c0e18d2971d8ae9ade3f6655cea7da87e30f5`. All 100 candidate
checks passed. Hosted run `36599606621` attempt 1 passed nine stages, then failed
`atlas_ready_observation`: Atlas heartbeat ages reached 29 seconds while DbServer
dispatch continued. The first DbServer startup milestones passed in 42.468 and
57.217 seconds. Final cleanup completed with zero inspection failures and no
remaining owned processes. This is a separate failure, not accepted runtime
qualification. The [failed evidence](android-evidence/atlas-test-evidence-36599606621-attempt1-failed.zip)
and [partial review](android-evidence/atlas-test-review-36599606621-attempt1-failed.json)
are preserved. Atlas publishes readiness before its final startup work, and the
stdout tail can be buffered; these observations do not establish an SG permission
verification defect. The runtime-only retry of the exact same signed APK and
unchanged guards passed as attempt 2, as recorded above. That repeat does not
establish a repair of this separate failure.

The DbServer startup correction remains part of 0.4.4. Follow the current
0.4.4 procedure above for the next physical check; the older 0.4.2 installation
sequence is superseded.

For any repeated Atlas heartbeat failure, preserve the existing 20-second
freshness requirement and 30-second observation. `dbReadyForPlayers` precedes
late initialization; registration sets the initial age timestamps. Later stats
come from `dbComm` inside `svrTick`. Unbounded directory/callback draining later
in that tick is a plausible source of delay, not an established cause. The
[exact-PDB context review](android-evidence/atlas-test-context-review-36599606621-attempt1.json)
identifies folder/path/hash words but explicitly cannot prove current execution.
The separately qualified MapServer donor now supplies bounded, fresh
main-thread stage/tick publication around late startup, `dbComm` and folder
callbacks. The completed-tick guard is integrated in 0.4.4. Callbacks and the
original heartbeat requirements remain intact; earlier root causes remain unknown.

Previous hosted checkpoint (2026-09-29, 14:49 UTC): **COH Atlas Test 0.4.1 passed hosted
qualification** in [run 36579726816](https://github.com/Russianranger/coh-android/actions/runs/36579726816)
at `6b50467a1b96133acc92a378617ff961733f288c`. All 91 candidate checks, 65 import
checks and 142 of 143 existing game checks passed (one Windows-only skip).
The exact signed APK's import and all 18 stages passed in 1,968.534 seconds.
Independent review verified 25 capture files, both committed saves, same-cluster
restart, exact-name resume and all 122 closed process records. Restart and final
cleanup each had zero inspection failures and zero remaining owned processes.
The Java gate compatibility replay also passed while retaining the original
report's hosted identity. See the
[acceptance receipt](android-evidence/accepted-atlas-test-hosted-36579726816.json).

The candidate-only scanner correction handles identity-verified worker exit
during ownership reads and bounded full-read retries; persistent live denial
still fails. It adds sanitized failure details without changing accepted base
payloads or Java acceptance guards. Hosted cleanup needed no permission retry;
the later Thor run above exercised that recovery successfully. Its new startup
failure supersedes the old 0.4.1 retry instructions. Keep the accepted
0.1.5/0.2.0/0.3.0 apps installed.
After the first pass is reviewed, complete Stop during active services and a
successful rerun with app switching and screen lock/unlock. Graphical client
work remains later. See the [device procedure](ANDROID_ATLAS_DEVICE_TEST.md).

Thor follow-up (2026-09-29, 13:50 UTC): **0.4.0 reached Atlas Park and committed
the first character save, then failed the restart ownership check.** The first
13 stages passed; `TEST-47452` (container 1) saved influence 12,345. Wine stop and
wait finished, but the process scanner reported `Cannot inspect same-UID Wine
ownership`. Final cleanup subsequently reported zero remaining owned processes
and closed all 86 child records; the cumulative inspection failure correctly
kept the Android guard blocked. The full restart/resume milestone is not accepted.
The failed PID/read is absent from this report; a worker-exit race in the scanner
is consistent with the captured zombie leaders and surviving Wine workers.
The isolated 0.4.1 correction is now hosted-qualified above, retaining strict live
ownership checks and adding bounded failure context. Do not repeat the remaining
device tests on 0.4.0. See the
[failure receipt](android-evidence/atlas-test-thor-restart-failure-20260929.json).
The user confirms following the force-stop instruction at the end, probably
after exporting the report. This was recovery after the recorded failure.

Previous hosted checkpoint (2026-09-29, 12:18 UTC): the separate
[COH Atlas Test 0.4.0 candidate](ANDROID_ATLAS_DEVICE_TEST.md) **passed hosted
qualification** in [run 36563104664](https://github.com/Russianranger/coh-android/actions/runs/36563104664)
at `4a8534b46ec024ca8f97bcbdc689f5fe23746a69`. The exact APK passed full import,
all 18 server stages, two committed saves, same-cluster restart, exact-name
resume and cleanup of all 122 captured process records. Import plus runtime
took 1,947.999 seconds. All 77 new contract tests and existing regression gates
passed (one existing Windows-only test skipped on Linux). The downloaded APK,
payloads and source identities match their receipts; the current report also
passed the scratch JVM validator compatibility check without being relabelled
as device evidence. See the
[acceptance receipt](android-evidence/accepted-atlas-test-hosted-36563104664.json).
The next gate at that checkpoint was Thor success/Stop/success with lifecycle
checks. Later failed runs superseded that sequence: follow the current candidate's
full run/export and pause for review, as directed in the current checkpoint above.
The candidate combines content import with the accepted local server/runtime
package and the automatic Atlas Park create/save/restart/resume test. It uses a new
application ID, so its private content must be imported once; accepted 0.3.0 data
cannot be read across Android app sandboxes. The unchanged accepted executable
package is reassembled from run `36510836956`; current wrapper/guest provenance
is recorded separately. The new workflow is `android-atlas-game.yml`.

Latest device checkpoint (2026-09-29, 11:11 UTC): **COH Atlas Setup 0.3.0 passed
physical import/Stop/retry on Thor (Android 13 / SDK 33)**. Both full imports
verified 173,011 files / 2,977,730,517 bytes, taking 56.610 and 61.822 seconds.
The intervening cancelled import stopped during extraction after 4,552 files
and retained the first completed generation. Retry published a new complete
generation. All three raw contracts exactly match hosted-qualified build
`2f828ca3e626245ea9fd60055745980bc3f32001`. Original report ZIPs and their hashes
are preserved in the [device acceptance receipt](android-evidence/accepted-asset-import-thor-20260929.json).
No repeat of import/Stop/retry is required. The reports do not separately record
app switching, screen locking, a reopen, process death or Stop latency; carry
explicit lifecycle/resource checks into the next combined game-service candidate.
That combined server candidate is now hosted-qualified above; its physical
create/save/restart/resume and Stop/rerun checks are next. Graphical client
execution remains later work. Keep all existing diagnostics installed.

Earlier hosted import checkpoint (2026-09-29): **COH Atlas Setup 0.3.0 passed hosted
qualification** in [run 36556279364](https://github.com/Russianranger/coh-android/actions/runs/36556279364)
at `2f828ca3e626245ea9fd60055745980bc3f32001`. All 65 checks, the signed APK
build, full 173,011-file import, cancelled re-import and abandoned-stage recovery
passed. The complete inventory matches the accepted game data. The downloaded
APK and all four payloads were independently rehashed against the reports.
See the [acceptance receipt](android-evidence/accepted-asset-import-hosted-36556279364.json)
and [candidate/device instructions](ANDROID_ASSET_IMPORT.md).
Physical Thor import/Stop/retry is now accepted above. The subsequent 0.4.0
candidate failed its first restart check; the current candidate's retry instructions
above supersede its device test sequence. The 0.3.0
app imports content only; Android Atlas game services and graphical
gameplay remain unvalidated. Accepted listener and diagnostic evidence below
remains unchanged. The candidate uses a development/ephemeral signing certificate.

Continuation recovery (2026-09-29 UTC): recovered branch head `7aea5ee` and
confirmed its completed GitHub checks. Independently replayed the preserved
Thor and hosted loopback evidence: both 28-stage physical runs, clean Stop,
and the hosted 18-stage create/save/restart/resume sequence remain accepted.
The original uploaded ZIP downloads returned HTTP 502 during this recovery;
the replay used the receipt-bound reports and captures already in this repo,
not newly downloaded archives or fresh device execution.

**Previous hosted runtime milestone accepted:** the separate [MapServer/TestClient
listener profile](ANDROID_GAME_RUNTIME.md#mapserver-and-testclient-listener-candidate)
passed all four jobs in
[run 36510836956](https://github.com/Russianranger/coh-android/actions/runs/36510836956)
at `ac4c1f7978be444a893f65f5177641191861d42f`. Windows passed 17 native Winsock
contracts; all 18 ARM64 stages and final host validation passed in 1,873.269766
seconds. Both DbServer starts proved 14 local endpoints, both Atlas starts
proved UDP `127.0.0.1:7001`, and each TestClient session proved two loopback UDP
bindings. Character `TEST33790` / container 1 retained influence 12,345 and
selected SQL rows across both committed saves, same-cluster restart and
exact-name resume with creation disabled. LoginCount progressed 1 → 1 → 2.
All 122 process captures closed, with zero remaining owned processes or
inspection failures. The
[acceptance receipt](android-evidence/accepted-game-listeners-hosted-36510836956.json)
binds the [raw report](android-evidence/game-listeners-arm64-36510836956.json)
and [preserved captures](android-evidence/game-listeners-evidence-36510836956.zip).

Verified file-picker import is implemented and accepted on Thor above. The
separate Android Atlas runtime/lifecycle integration was subsequently built and
hosted-qualified; the current candidate's physical retry is the next gate. The hosted
namespace remains mandatory;
the local binding policy does not establish device-wide network isolation.
Keep installed 0.1.5 and 0.2.0; no repeat of their passed diagnostics is needed,
and the listener milestone itself supplies no physical Atlas result.
Local verification: 162 checks ran (161 passed, one Windows-only observer
skipped), including 17 actual socket contracts and eight source-preparation
checks. Both complete creation/resume staging commands verified the immutable
5,995-file source snapshot and produced the expected separate receipts.
The three new game executables were also downloaded and independently checked
against their source receipts, byte hashes and PE metadata. Existing Wine,
DbServer console/launcher and orphaned Atlas door-point warnings match the
previous accepted run; no new failure diagnostics were found.

Previous device checkpoint (2026-09-28, 22:28 UTC): **COH Server Test 0.2.0 passed
on Thor**. The [receipt](android-evidence/accepted-dbserver-thor-20260928.json)
records two complete 28-stage real DbServer passes, a clean cancellation between
them, exact local listener coverage and complete owned cleanup. App switching
and screen locking are user-attested; peak memory is unmeasured. The subsequent
hosted Atlas loopback integration passed in `36493722153`, including both local
DbServer starts and both committed saves. MapServer/TestClient local bindings
subsequently passed hosted qualification in `36510836956`. Asset import has
since passed on Thor with 0.3.0; Android Atlas integration remains next.
Physical Atlas execution and rendering remain unvalidated.

Updated: 2026-09-29 (UTC). PostgreSQL controlled persistence, targeted stage1 inspection,
matching Windows packaging, base runtime assembly and data-only database schema
generation have passed their current checks. Normal fixture-OFF DbServer schema
initialization/export/reload and normal MapServer network save acknowledgements
have also passed against fresh PostgreSQL clusters.
The refreshed runtime and schema artifacts share repository commit
`775a0dd770adac045484805dbbb5f68054c7a354`. Ordinary asset-backed reference
comparison and Atlas Park protocol readiness have now passed. Fresh fake-auth
character creation, live currency change, protocol logout/save, database and
game-service restart, and exact-name short resume also passed in
[run 36282414135](https://github.com/Russianranger/coh-android/actions/runs/36282414135).
The follow-on [sustained-session run 36295176484](https://github.com/Russianranger/coh-android/actions/runs/36295176484)
also passed: exact-name resume, missing-name refusal without mutation, 66.953
seconds connected, restored live currency and a second protocol save.
The follow-on [Atlas transfer run 36297542986](https://github.com/Russianranger/coh-android/actions/runs/36297542986)
also passed: the same character moved map 1 → prestarted clone 101 → map 1,
preserved committed state at each arrival and completed the final protocol save.
The [primary M2 device diagnostic and headless client capability gate](THOR_DEVICE_ACCEPTANCE.md)
is now accepted on Thor with 0.1.5. The supplied combined report passed all twelve
stages, reused the database cluster and ready Wine prefix, and completed owned
cleanup with all 30 process input/output captures closed. The user also attests to
a preceding database-only pass; its separate archive was not supplied. Device
cleanup observed exited leaders with live owned workers, while the exact writer
of the earlier pipe was not inventoried. The subsequent 0.2.0 device gate now
proves Stop followed by a successful fresh rerun; app switching and screen
locking are user-attested, while peak memory remains unmeasured.
The [first hosted M3 DbServer gate](ANDROID_DBSERVER.md)
also passed in run 36369485666: 21 persistence check groups across 14 fixture
invocations, then two fixture-OFF schema exports with 99 tables, 5,935 ordered
columns, 58,272 exact attribute IDs/names and a stable catalog on reload.
All 28 ARM64 stages passed, with all 111 process input/output captures closed and
zero remaining owned processes or inspection errors. The
[acceptance receipt](android-evidence/accepted-dbserver-hosted-36369485666.json)
binds the reports and inputs. Physical Android DbServer execution has since
passed with 0.2.0; Android presentation and game rendering remain unvalidated. The separate
[hosted Atlas gate](ANDROID_GAME_RUNTIME.md#accepted-full-hosted-workflow)
passed its full workflow in run `36460005201`: all three jobs, all 18 guest
stages and the final host validator succeeded, including both protocol saves,
same-cluster restart and exact-name resume. The
[acceptance receipt](android-evidence/accepted-game-hosted-36460005201.json)
binds independently verified reports and captures. The earlier `36454174481`
workflow failure and separate post-correction acceptance remain preserved,
alongside the first-save, restart-port and startup-timeout history below.
The follow-on diagnostic DbServer package passed all three jobs in run
`36425508780`. Windows verified enabled dispatch-record publication; the ARM64
fixture/schema gate used the observer disabled. Atlas run `36428915900` then
verified enabled ARM64 publication with this qualified donor and captured the
folder callback boundary during the intermittent timeout.
The current fixed-input successor is qualified in run `36451873322` at
`53c6270dff8a0efcc6be09da756408504d8313bd`: all three jobs passed, including
default normal-schema startup and acknowledged fixed-input reload on ARM64.
This remains the default Atlas donor; preserve the earlier first-save and
dispatch evidence. The accepted device diagnostics are 0.1.5 and 0.2.0.
The separate opt-in loopback listener package passed all three hosted jobs in
[run 36460867428](https://github.com/Russianranger/coh-android/actions/runs/36460867428)
at `eed2ce1f5388195f65a07853919761a93657aca6`. Its
[acceptance receipt](android-evidence/accepted-dbserver-hosted-36460867428.json)
records 28 ARM64 stages in 191.502348 seconds, all 13 required loopback binds
(12 TCP plus UDP 7000), and the optional asynchronous TCP 6992 bind. Windows
passed all eleven native loopback contracts and the existing persistence,
dispatch and fixed-input checks. Both schema exports and the catalog were
stable; all 111 captures closed with zero owned processes or inspection errors.
The first attempt `36460005041` failed before DbServer builds or runtime execution
because its Windows test fixture applied a CRLF patch to LF source files.
The correction normalizes only that fixture's patch input and adds a CRLF
regression; preserve the
[failure receipt](android-evidence/dbserver-qualification-failure-36460005041.json).
This qualifies the hosted listener prerequisite. Physical DbServer listener
execution and app integration subsequently passed with 0.2.0. The default Atlas
donor remains `36451873322`; its separate loopback profile uses `36460867428`.
The first attempt with the preceding diagnostic donor `36425508780`, run
`36427680960`, stopped before game execution
when the pinned talloc download timed out during the PRoot build. A bounded
download retry is now applied. The next run passed dependency preparation with
no retry line observed; the transport remedy supplies no startup-fix evidence.
The reviewed asset ZIP has been uploaded to a draft release and downloaded by
the hosted runner with its exact size/hash verified. That attempt then stopped
on Windows manifest line endings before game execution. The byte-preserving
checkout fix is applied and run 36176806895 completed successfully: all 56 fresh
template outputs matched, then Atlas Park remained ready for 62.235 seconds.
Earlier character attempts exposed harness status parsing and console capture
issues; the final corrected run completed all eight phases with no failures.

Continuation on 2026-09-26 recovered the completed 2026-09-25 run after this
handoff had retained an in-progress status. At recovery, GitHub showed no queued
or running workflow and the latest commit was `04d62616e2e1b41b10f35a04d4c798e43680d5ba`
(2026-09-25 19:05:39 UTC). The workflow finished at 19:16:38 UTC. These observations
do not reveal the internal status of the other Codex session.

## Earlier hosted DbServer-loopback checkpoint (2026-09-28)

[Run 36493722153](https://github.com/Russianranger/coh-android/actions/runs/36493722153)
at `708878f78a3361b595dcc03a0c4b14fb6cd2e6c3` **passed the separately identified
Atlas loopback DbServer profile**: all three jobs, all 18 guest stages and final
host validation. The [receipt](android-evidence/accepted-game-loopback-hosted-36493722153.json)
binds independent replay of the unchanged reports and captures. Runtime took
1,883.535869 seconds; first service readiness took about 17 minutes 32 seconds
and restart readiness about 3 minutes 13 seconds.

Both DbServer starts proved all 14 observed local endpoints, including optional
TCP 6992. Character `TEST-60538` / container 1 retained influence 12,345 and its
selected committed SQL rows through same-cluster restart and exact-name resume
with creation disabled. LoginCount progressed 1 → 1 → 2 across both protocol
saves. Both fixed-input acknowledgments and all four inventory checks passed.
All 122 process input/output captures closed, with complete cleanup and zero
remaining owned processes or inspection failures. Preserve the
[raw report](android-evidence/game-loopback-arm64-36493722153.json) and
[captured evidence](android-evidence/game-loopback-evidence-36493722153.zip).

The workflow explicitly selects loopback donor `36460867428`; default assembly
and the earlier accepted profile retain `36451873322`. This qualifies DbServer
binding within that earlier Atlas sequence. The subsequent `36510836956`
profile qualified MapServer and TestClient local bindings as well. The private
hosted network namespace remains mandatory; outgoing TCP and device-wide
isolation are outside the binding proof. Physical Atlas execution remains
unvalidated. Follow
the [remaining device preparation](ANDROID_GAME_RUNTIME.md#remaining-preparation-for-a-physical-atlas-candidate),
keeping accepted 0.1.5 and 0.2.0 installed.

### Earlier accepted default-profile workflow

[Run 36460005201](https://github.com/Russianranger/coh-android/actions/runs/36460005201)
at `cfc8ac477e449037213d5242f43480acf4f1cb85` **passed all three jobs and the
complete hosted Atlas gate**. The [raw report](android-evidence/game-arm64-36460005201.json)
records all 18 stages in 1,963.43549 seconds, `TEST48625` / container 1 /
account `CohAa82e8aaa56`, live influence 12,345, first protocol save, Wine and
same-cluster PostgreSQL restart, exact-name resume at slot 0 with creation
disabled and a processed server update, and the second protocol save.
LoginCount progressed 1 → 1 → 2; selected SQL retained one `ents` row, one
`ents2` row, seven powers and 13 costume parts. Atlas readiness was independently
observed for 31.421914 seconds with current heartbeats.

Both fixed-input acknowledgments and all four unchanged input checks passed
(62 files / 4,402,846 bytes). Schema, attribute IDs/names and the full catalog
stayed stable. All 123 process input/output captures closed; graceful PostgreSQL
and Wine cleanup left zero owned processes or inspection failures. Independent
full report, character/SQL capture and service-capture checks passed with the
exact tested validator modules. Preserve the
[acceptance receipt](android-evidence/accepted-game-hosted-36460005201.json) and
[captured evidence](android-evidence/game-evidence-36460005201.zip).
Atlas donor `36451873322` at `53c6270dff8a0efcc6be09da756408504d8313bd` and
APK 0.1.5 remain unchanged. Physical Android game execution, presentation and
rendering remain unvalidated.

### Testing takeover verification (2026-09-28)

A fresh checkout at `d1907db` independently replayed the accepted `36460005201`
evidence. All 43 preserved archive members matched their recorded sizes and
hashes; the raw report was byte-exact. The exact tested validator modules passed
`validate_report`, `validate_capture_files` and `validate_service_captures`.
The [verification record](android-evidence/atlas-takeover-verification-20260928.json)
delimits the retained-evidence scope: no fresh runtime or device execution,
and no recomputation of the omitted full data inventory or executable payloads.
The current focused suites passed 103 tests with one Windows-only observer test
skipped locally; the accepted hosted Windows job covers that observer.

Live GitHub inspection confirmed the successful full Atlas run and zero queued
or running repository workflows. This does not reveal another agent's internal
session status. README and Thor next-work instructions now point to Android
integration and physical device qualification instead of repeating the accepted
hosted Atlas milestone. The 0.1.5 APK and Atlas donor are unchanged.

### Earlier acceptance after host validator correction

[Run 36454174481](https://github.com/Russianranger/coh-android/actions/runs/36454174481)
at `8944bd598990b33b63a750a64ae448403e4542cd` has an **accepted runtime sequence
after host revalidation; the original workflow conclusion remains failure**.
All 18 guest stages passed in 1,867.229988 seconds. The
[raw report](android-evidence/game-arm64-failed-36454174481.json) records
`TEST01443` / container 1 / account `CohA318dc5a821`, live influence 12,345,
first protocol save, Wine and same-cluster PostgreSQL restart, restarted Atlas
readiness, exact-name resume at slot 0 and the second protocol save. LoginCount
progressed 1 → 1 → 2; selected SQL retained one `ents` row, one `ents2` row,
eight powers and 14 costume parts. Atlas readiness was independently observed
for 31.564746 seconds.
Both DbServer fixed-input acknowledgments and all four unchanged input checks
passed (62 files / 4,402,846 bytes). All 122 input/output captures closed;
cleanup left zero owned processes or inspection failures.

The original host validator incorrectly required `child_exited: true`, which
the bridge does not serialize. The correction requires the existing exit code
to be a terminal DWORD and rejects `STILL_ACTIVE` (259). Both clients recorded
exit code 125 after forced termination following independently committed
protocol saves. Strict full report, character-capture and service-capture
validation passed against unchanged evidence. Preserve the separate
[acceptance receipt](android-evidence/accepted-game-hosted-36454174481.json),
[failure receipt](android-evidence/game-runtime-failure-36454174481.json) and
[captured evidence](android-evidence/game-evidence-36454174481.zip).
The actual C serializer, real guest stop validation and host consumer are
covered by a regression; the runtime, bridge producer and evidence bytes are
unchanged. The original Actions run remains failed. Keep donor `36451873322` at
`53c6270dff8a0efcc6be09da756408504d8313bd`
and the accepted 0.1.5 APK unchanged. Physical Android game execution,
presentation and rendering remain unvalidated.

The separate sibling DbServer [run 36454174374](https://github.com/Russianranger/coh-android/actions/runs/36454174374)
failed attempt 1 with SIGSEGV (`-11`) after `PG_TEST_COMPLETE rebuild` and
teardown messages. Attempt 2 reused the byte-identical package and passed all
28 stages in 190.362494 seconds, with all 111 captures closed and complete
cleanup. The [failure](android-evidence/dbserver-runtime-failure-36454174374.json)
and [repeat](android-evidence/dbserver-runtime-repeat-36454174374-attempt2.json)
receipts preserve both outcomes. The failure remains intermittent and
unexplained; the passing repeat does not establish a repair or replace the Atlas
donor.

### Earlier hosted ARM64 checkpoints

[Run 36416020268](https://github.com/Russianranger/coh-android/actions/runs/36416020268),
commit `324823be6ca9713bdc60446eb31596004ff6286a`, is an **overall failure with
new partial runtime evidence**. Atlas stayed independently ready for 31.519
seconds. Stock TestClient created `TEST02279` / ID 1, entered Atlas, changed live
influence to 12,345 and completed protocol logout with an independent committed
SQL snapshot (LoginCount 1) before forced cleanup. Wine and PostgreSQL shut down
cleanly; the same PostgreSQL cluster restarted. The next service-launch
preflight failed immediately with `[Errno 98] Address already in use`, before
replacement game services started. No exact-name resume or second-save proof
was obtained. Preserve the [raw report](android-evidence/game-arm64-failed-36416020268.json)
and [detailed evidence](ANDROID_GAME_RUNTIME.md#first-arm64-creation-and-protocol-save-restart-gate-failed).

The bounded fallback snapshot found no owned Wine processes or game-role SQL
sessions after the verified shutdown. Review confirmed that the TCP preflight
lacked the native `SO_REUSEADDR` behavior used by pinned Wine. An isolated Linux
experiment reproduced the bare-bind error with TIME_WAIT and passed with TCP
reuse while retaining rejection of live listeners and occupied UDP ports. The
hosted report has no socket table proving that state, but the behavior is
consistent with its failure. The narrow harness correction and tests were
applied for the subsequent run described below; restart validation was still required. The
prior startup timeout did not recur: one query returned after 78.833 seconds and
AutoCommands retrieval completed after 82.71 seconds. This does not establish
that intermittent startup delay as fixed. Do not repeat the successful first
save as if it were still unknown, or mark the full hosted gate accepted before
restart/resume/second-save pass. Keep the accepted 0.1.5 device diagnostic;
Android game presentation and gameplay remain unvalidated.

The subsequent [run 36420158506](https://github.com/Russianranger/coh-android/actions/runs/36420158506)
at `04b9771120737f3e8daf7b4740d2a9fcd6850f28` failed a startup query in the first
service phase after 13 preceding readiness queries had completed. The failing
query reached 90.041 seconds, so it did not exercise the restart-port correction.
Preserve the prior first-save evidence above. The new
[failure receipt](android-evidence/game-runtime-failure-36420158506.json),
[raw report](android-evidence/game-arm64-failed-36420158506.json) and
[pre-cleanup snapshot](android-evidence/game-hang-36420158506/snapshot.json)
show live DbServer/Atlas/query processes and 65 idle SQL sessions. All Windows
capture APIs completed (three processes, 72 threads, 114 modules, zero errors),
but inspection of pinned Wine/FEX shows `GetThreadContext` supplies saved WOW64
context rather than current translated x86 execution state. Decoded DbServer
pointers lead to an already-completed startup path, so they do not identify the
live blocker or justify a main-loop change. Final cleanup passed with all 59 process
captures closed and zero remaining owned processes or inspection failures.
This run did not validate the full hosted restart/resume/second-save gate or
Android gameplay.

[Run 36425508780](https://github.com/Russianranger/coh-android/actions/runs/36425508780)
at `41f3aff596826e22e2774375e11590de895ca33d` qualified the separately receipted
DbServer package containing [opt-in source dispatch markers](../database/wine-dbserver/DISPATCH_PROGRESS.md):
all three jobs passed, including the Windows enabled-record contract. The ARM64
fixture and normal schema checks ran with the observer disabled. Preserve the
[new acceptance receipt](android-evidence/accepted-dbserver-hosted-36425508780.json)
alongside the original acceptance. The donor manifest SHA-256 is
`656c7e764798dc7ecee01cef836cd758177fd9cdcf1477799517e9d5a959c632` and the normal
executable SHA-256 is
`3d6098da1655a380f09d7c0ba5b984c98b68b1294f75128c28b08be851cf1830`.

Atlas adopted donor `36425508780`, with separate fresh records required for
first startup and restart. Enabled publication on live ARM64 was subsequently
verified in run `36428915900` below. Bounded stage/sequence observations distinguish progress
through startup, dispatch, SQL keepalive and console handling without relying
on stale WOW64 contexts. A stopped marker identifies an operation and its nested
calls; it does not prove a deadlock or gameplay success. No startup blocker fix
has been established, and the accepted device APK remains 0.1.5.

[Run 36427680960](https://github.com/Russianranger/coh-android/actions/runs/36427680960)
at `82386fd48c2352a2ce65d5920f7857e8b92ec442` passed source, package and data
staging, then failed on a read timeout downloading pinned talloc for the PRoot
build. No game diagnostic ran, and no runtime report or dispatch sample exists.
The [infrastructure failure receipt](android-evidence/game-infrastructure-failure-36427680960.json)
preserves this result. It adds no evidence about the intermittent startup
stall. The isolated retry correction allows at most three transport attempts,
discards partial downloads and preserves the size/SHA-256 gates; Atlas tooling
now explicitly runs its regression tests. The next run passed dependency
preparation without an observed retry. This download remedy is not a game
startup fix; this attempt did not reach restart/resume/second-save.

[Run 36428915900](https://github.com/Russianranger/coh-android/actions/runs/36428915900)
at `f32ccd7c0f1aa950d1f87ceb81ab09b2dba4e2ac` failed a first-phase startup query
after 90.030 seconds, following 13 completed readiness queries. Enabled ARM64
source markers are now validated: the initial record had sequence 28 / loop 1
at `NM_MONITOR`; the same DbServer PID 412 / main thread 416 and mapped file
later held `FOLDER_CALLBACKS`, sequence 2,449,552 / loop 43,741. Identical before
and after records span 13:55:20.897–13:55:23.957 UTC. This localizes the observed
work to folder callbacks or nested calls. Separate non-atomic native snapshots
showed `read` and `fchdir` operations under PRoot, so a deadlock is not established.
The specific nested operation and throughput remain unknown.

The query, DbServer and Atlas were alive before cleanup, and the query remained
alive after the 3.061-second capture. All 65 SQL sessions were idle in
`ClientRead`, without active transactions; the foreground last query was `;`,
about 134.9 seconds old. Atlas ended at `Retrieving AutoCommands..`. Preserve the
[failure receipt](android-evidence/game-runtime-failure-36428915900.json),
[raw report](android-evidence/game-arm64-failed-36428915900.json) and
[snapshot](android-evidence/game-hang-36428915900/snapshot.json). Archive and all
eight service/hang capture hashes were independently verified. Final cleanup
passed with all 57 process input/output captures closed and zero remaining owned
processes or inspection failures. No new character or restart result was obtained.

The opt-in [fixed-input DbServer mode](../database/wine-dbserver/FIXED_INPUTS.md)
is now qualified in [run 36451873322](https://github.com/Russianranger/coh-android/actions/runs/36451873322)
at `53c6270dff8a0efcc6be09da756408504d8313bd`. It prevents watcher registration
before the first cache while preserving initial reads and lookup mode; it does
not establish a generic Wine notification fix. All 28 ARM64 stages passed in
192.280590 seconds, including 21 persistence groups across 14 fixture phases,
default normal-schema startup and acknowledged fixed-input reload. Both fresh
empty exports preserved 99 tables, 5,935 ordered columns, 58,272 exact attribute
IDs/names and the full catalog. All 111 process captures closed; cleanup left
zero owned processes or inspection errors. Preserve the
[acceptance receipt](android-evidence/accepted-dbserver-hosted-36451873322.json).
The donor manifest SHA-256 is
`e4f8a66802f29643b13aec2228ada1549a80c22efa11de1549a9b145bb43e06b`;
normal executable SHA-256 is
`659e9072234f75ad02c8cac2636df93f5249ff1de385c1ed7d6c6fc0c04a453a`.

Earlier fixed-input qualification `36434692816` passed Windows/source checks,
but both ARM64 attempts failed before DbServer execution on talloc HTTP 503
after all three transport attempts. Successful qualification `36451873322`
recovered the identical archive from accepted runtime `36364550345`'s verified
corresponding-source bundle. Atlas uses the same source recovery; the build
recipe and source pins are unchanged.

The Atlas harness now enables this mode only for DbServer and requires its exact
startup acknowledgment on both launches. After private `servers.cfg` generation,
it binds all 62 accepted schema inputs plus the entire staged `data/server/db`
tree. Four unchanged snapshots are required: before first startup, after first
save, before restart and after second save. Run `36454174481` subsequently
completed this sequence; its unchanged evidence passed strict host revalidation
after correction of the bridge exit contract. Preserve the original failed
workflow, earlier first-create/save evidence and accepted 0.1.5 APK; Android
game execution and rendering remain unvalidated.

## Continuation validation checkpoint

The accepted character run is **36282414135**, tested commit
`86e512e85c8350714bc7b58668bf11443dc164f8`, completed 2026-09-27 00:40:07 UTC.
It verified `TEST20636` / container ID 1 with live influence 12,345, committed
protocol logout before forced cleanup, restart of the same PostgreSQL cluster
and game services, and exact-name short scene resume with creation disabled.
Selected identity/rows remained unchanged (1 parent, 1 `ents2`, 7 powers,
13 costume parts); `LoginCount` progressed 1 → 1 → 2. The resume exited
naturally with code 0 and both console observers finalized successfully.
The [report](postgresql-evidence/character-persistence-36282414135.json),
[complete artifact](postgresql-evidence/character-persistence-36282414135.zip) and
[acceptance/provenance record](postgresql-evidence/accepted-character-persistence-36282414135.json)
are preserved. Windows passed 67 tooling/map checks; Linux passed 62 with five
Windows-only skips. All four same-commit
[PostgreSQL regression jobs](https://github.com/Russianranger/coh-android/actions/runs/36282414187)
passed. The short resume does not establish sustained gameplay or Android execution.

### Accepted next milestone: sustained second session

The [sustained-session implementation](SUSTAINED_SESSION_VALIDATION.md) adds a
separately identified diagnostic TestClient with creation disabled and a normal
connected command loop. [Run 36295176484](https://github.com/Russianranger/coh-android/actions/runs/36295176484)
passed all 12 phases at `4e8058c3ffe20acda61b55023202d409ed1d0df1`, completing
2026-09-27 05:08:11 UTC. `TEST-37762` / ID 1 resumed with live influence 12,345
and a processed server update confirming its identity. Ten samples covered
66.953 seconds connected on Atlas Park, with a maximum gap of 7.625 seconds.
The second live influence command produced 23,456 and committed through protocol
logout before forced cleanup. Missing-name refusal exited naturally with code 3
and left the entire character inventory and selected SQL unchanged.

`LoginCount` progressed 1 → 1 → 1 → 2 across first logout, restart, missing-name
probe and second logout. Selected identity/rows stayed identical except for the
intended influence change (1 parent, 1 `ents2`, 7 powers, 16 costume parts).
All three console observers finalized successfully. The [raw report](postgresql-evidence/character-session-36295176484.json),
[complete artifact](postgresql-evidence/character-session-36295176484.zip) and
[acceptance record](postgresql-evidence/accepted-character-session-36295176484.json)
are preserved. Windows passed 103 tooling checks; Linux passed 98 with five
Windows-only skips. The same-commit [stock regression](https://github.com/Russianranger/coh-android/actions/runs/36295176352)
and all four [PostgreSQL regression jobs](https://github.com/Russianranger/coh-android/actions/runs/36295176473)
passed. The accepted stock TestClient and server reference binaries remain
unchanged; the diagnostic client has separate source/build receipts.

The first hosted attempt
[36293644180](https://github.com/Russianranger/coh-android/actions/runs/36293644180)
passed stock creation/save/restart and missing-name refusal without mutation,
then rejected the positive selection because the character-list packet does not
populate its `db_id` field. The correction checks exact name/slot there and binds
the actual MapServer entity ID after the processed update to independent SQL.
The [failed evidence](postgresql-evidence/character-session-36293644180.json) is
preserved. The corrected retry above proves the sustained resume and second save;
the failed attempt remains identified as a failure.

### Accepted next milestone: Atlas instance transfer

The [Atlas instance transfer gate](MAP_TRANSFER_VALIDATION.md#accepted-hosted-validation-36297542986)
passed all 15 phases in run `36297542986`, tested commit
`5f2c561058a186de59d3f27301eea210bd4bb66d`; terminal success was recorded
2026-09-27 05:56:06 UTC. `TEST59440` / ID 1 stayed in the same client process
for map 1 → clone 101 → map 1. Fresh player updates carried transfer epochs 1
and 2 on ports 7002 and 7001, while independent character status confirmed
MapId/SmapId 101 then 1. Each arrival had current heartbeats, live influence
12,345 and unchanged committed selected state. Per-leg SQL reads establish that
state, not a fresh identical-write acknowledgement. The subsequent live change
to 23,456 and protocol logout supplied a fresh final-save proof before cleanup.
LoginCount stayed 2 across both transfers and final logout; no extra character
was created. All three console observers finalized successfully.

The [raw report](postgresql-evidence/character-transfer-36297542986.json),
[artifact](postgresql-evidence/character-transfer-36297542986.zip) and
[acceptance record](postgresql-evidence/accepted-character-transfer-36297542986.json)
are preserved. Windows passed all 119 tooling checks; Linux passed 114 with
five Windows-only skips. The same workflow passed the 12-phase sustained
regression using the same diagnostic bytes (62.532 seconds over 10 samples).
The stock-client and all four PostgreSQL regression jobs also passed at
`3848133e5e644f4c166cc9e7f3e027288d06c2fd`, with identical runtime code;
the retry changed only the test fixture and documentation.
The first transfer attempt stopped before the build on a Windows C-test fixture
portability error. The fixture now uses Winsock on Windows; client and server
code are unchanged by that correction. The [tooling failure record](postgresql-evidence/character-transfer-tooling-36297326622.json)
is preserved separately from the successful retry.

### Historical hosted M2 gate (0.1.0)

[Run 36336644450](https://github.com/Russianranger/coh-android/actions/runs/36336644450)
passed all four jobs at source `0b61d7455f40f05709f912338cd5de8b1d72d750`,
completing 2026-09-27 17:29:16 UTC. All 80 tooling tests passed without skips.
The APK's exact guest assets passed eleven stages on Linux ARM64, including
real PE32 DLL/driver loading, all 65 stock ODBC connections, transactions,
rollback, UTF-16/binary values, column metadata, schema rebuild/reopen, graceful
same-cluster restart and a second Win32 verification of persisted data. All
three cleanup checks passed. The same-source [PostgreSQL regression run](https://github.com/Russianranger/coh-android/actions/runs/36336644454)
also passed all four jobs. Preserve the [acceptance receipt](android-evidence/accepted-hosted-36336644450.json)
and [raw guest report](android-evidence/runtime-smoke-report-36336644450.json).

`COH-Diagnostic-0.1.0.apk` is 13,309,477 bytes, SHA-256
`80e53b03d95ec851623b8b743b067e87642e392a387d24679adcd81d119d38ac`.
Download the `coh-diagnostic-apk` artifact from the accepted run. It contains
no game binaries or assets. The native Java app and owned PRoot session combine
pinned Bookworm/Wine 10/FEX inputs with PostgreSQL built from official pinned
source; its ephemeral CI signing certificate is not a stable update identity.

Physical Thor acceptance was pending at this checkpoint. The current
[device acceptance record](THOR_DEVICE_ACCEPTANCE.md) preserves the later 0.1.5
pass and remaining lifecycle checks. Hosted Linux execution alone does not prove
Android SELinux, foreground-service lifecycle, device shutdown, performance or
gameplay. Mission/new-zone transfers, automatic Launcher startup and combat remain
separate unfinished scope.

### Accepted hosted client prerequisite milestone (0.1.1)

Continuation on 2026-09-27 found the hosted M2 gate complete, with physical Thor
acceptance still pending. The branch had no unfinished result to recover from its
latest completed workflows; this does not expose another Codex session's internal
state. Work advanced to the independently permitted
[basic client capability probe](CLIENT_RUNTIME_PROBE.md).

Commit `c1097bdc0aab433fd3cb1560fd07175c6c3dc6b0` adds a separate **Run client probe**
operation to 0.1.1. It exercises a real PE32 WGL context, a textured quad with four
verified RGB readbacks, buffer swap, own-window keyboard/mouse messages and
DirectInput device creation. Audio enumeration and extension availability are
observations only. The original database-only operation remains available and
both modes require complete owned cleanup. The app now scrolls on short displays.

Local validation passed 93 tests with two environment-dependent skips; the actual
PE32 program also cross-compiled warning-free with `-Werror` and its Windows
imports were verified. Hosted workflow [36349552245](https://github.com/Russianranger/coh-android/actions/runs/36349552245)
passed all five jobs at 20:59:41 UTC, including all 93 tooling tests without skips.
Database mode passed eleven stages; client mode passed twelve. The observed
renderer was llvmpipe/Mesa 22.3.6 OpenGL 4.3, all four RGB readbacks were exact,
and synthetic input plus DirectInput device creation passed. Both modes proved
graceful PostgreSQL restart and complete cleanup. DirectSound enumerated zero
devices, with no playback claim. All same-source PostgreSQL regressions passed.
The [acceptance record](android-evidence/accepted-client-probe-36349552245.json)
preserves report hashes, observed capabilities and the verified 13,477,490-byte
APK. Preserve it as the historical 0.1.1 result; the later
[Thor acceptance record](THOR_DEVICE_ACCEPTANCE.md) describes current device evidence.
A fixture result cannot establish CoH rendering, Cg shaders, physical controls,
audio playback, Android presentation or GPU acceleration. Thor reports were still
needed at this checkpoint; M3 minimal game-server/device execution remains unfinished.

### Historical Thor wineboot failure and hosted 0.1.2 result

The user supplied two Thor/Android13 reports from 0.1.1. Both passed native
PostgreSQL initialization, restricted fixture SQL and owned cleanup, but failed
at the 150-second wineboot wait before Windows ODBC or graphics. The second run
reused the same diagnostic database cluster. This is partial real-device database
evidence; complete M2/device acceptance remained pending at this checkpoint.

[The selected device evidence](android-evidence/thor-wineboot-failure-20260927.json)
records both failures. Their exit-code0 values were captured after forced cleanup
and do not establish the initializer's status before the timeout. A real subprocess
regression reproduced a false timeout when a successful initializer's background
service retains stdout. Commit `1afb0610095ebe3cb8aba591ea22d749613b7276` applies
[the narrow 0.1.2 fix](ANDROID_WINEBOOT_RETRY.md): wineboot alone may complete on
its own exit, with captured background output retained under owned cleanup. Live
initializer timeouts, nonzero exits, cancellation and output limits remain errors.
Receipts now record pre-signal state and require capture/writer shutdown too.

[Hosted run 36352420585](https://github.com/Russianranger/coh-android/actions/runs/36352420585)
passed all five jobs at this commit on 2026-09-27 21:44:41 UTC: all 99 tests
without skips, eleven database stages, twelve client stages and complete owned
cleanup. The [acceptance receipt](android-evidence/accepted-wineboot-retry-36352420585.json)
preserves that historical build and reports. Hosted wineboot exited with output
capture still open; capture closed during cleanup. This proves the corrected
wait path was exercised, not that inherited output caused the Thor failures.
The subsequent Thor retry failed; the inherited-output correction alone did not
resolve device initialization.

### Historical 0.1.3 cold initialization qualification

[The 0.1.2 device report](android-evidence/thor-initializer-timeout-20260927.json)
records wineboot still running at 150.040 seconds before cleanup signals. Four
early native database stages passed; Windows ODBC and graphics were not reached.
PostgreSQL and prefix shutdown passed, but output capture remained open, so
complete cleanup was not proved.

Commit `49c1626c10636e46a38493047f34ab61a9a5d5ca` applies the
[0.1.3 initialization correction](ANDROID_WINE_INITIALIZATION.md): use `wineboot -i`
to avoid a forced second registration pass, invalidate only the timestamp of an
unready prefix, allow 600 seconds with progress every five seconds, and write a
readiness marker only after the real PE32 fixture passes. Successful warm runs
preserve the timestamp. Wine bootstrap errors, fixture failures and open captures
still fail the diagnostic; Stop and the overall fifteen-minute limit remain.
This addresses startup behavior without identifying the exact internal component
delayed on Thor.

[Hosted run 36354263676](https://github.com/Russianranger/coh-android/actions/runs/36354263676)
passed all five jobs on 2026-09-27 22:16:35 UTC at this source. All 109 tests passed
without skips. Fresh and repeat runs each passed eleven database stages or twelve
client stages, including all Windows fixtures and complete cleanup. Cold Wine
initialization took 39.911 seconds in database mode and 40.305 seconds in client
mode, with one registration pass each; both warm runs took 4.629 seconds with zero
registration passes. These timings describe the hosted environment. The
[same-source PostgreSQL regressions](https://github.com/Russianranger/coh-android/actions/runs/36354266044)
also passed. The [acceptance receipt](android-evidence/accepted-wine-initialization-36354263676.json)
binds the verified APK, payload hashes and runtime evidence.

The subsequent device run passed initialization and all eleven functional stages;
its remaining cleanup failure is recorded below. Preserve the 0.1.3 artifact and
receipt as historical evidence.

### Historical 0.1.4 Wine helper cleanup qualification

[The 0.1.3 Thor report](android-evidence/thor-functional-pass-cleanup-failure-20260927.json)
completed initialization in 90.927 seconds with one registration pass, then passed
native PostgreSQL, real PE32 DLL loading, all 65 ODBC sessions, SQL/value/metadata
checks and durable same-cluster restart verification. The sole recorded failure
was `Owned process input/output capture did not close: wineboot`. The Wine prefix
lock and socket were inactive, and PostgreSQL shut down cleanly; that does not
prove every detached Unix helper exited. The remaining pipe writer is unidentified.
Client graphics were not requested.

Accepted source `83f132ddb8077c9d5175ae7cd039e0754b70074e` applies the
[0.1.4 cleanup correction](ANDROID_WINE_CLEANUP.md). Wine helpers carry an exact
per-run ownership token; bounded cleanup verifies the real UID and PID identity
before signaling. Output captures must actually reach EOF, and unrelated processes
must survive. The menu-helper override is corrected to `winemenubuilder.exe`;
its earlier launch does not prove it caused the retained pipe.

The initial [hosted attempt 36356073708](https://github.com/Russianranger/coh-android/actions/runs/36356073708)
stopped on ownership inspection of an unreadable, unrelated same-UID CI process.
The accepted correction safely excludes processes strictly older than diagnostic
startup, which cannot inherit the new child-only token; current or newer processes
still require inspection.

[Run 36356283176](https://github.com/Russianranger/coh-android/actions/runs/36356283176)
passed all five jobs on 2026-09-27 22:50:49 UTC. All 116 tests passed in 11.510 seconds
without skips. Database fresh/repeat runs passed all eleven stages; client
fresh/repeat runs passed all twelve. Every owned input/output capture closed,
ownership cleanup completed and no helpers remained. Cold initialization took
39.397 seconds in database mode and 37.973 seconds in client mode; warm runs took
4.276 and 4.126 seconds respectively. These are hosted timings.

Both detached-helper fixtures exercised one TERM and one KILL through two pidfd
signals, with zero remaining helpers or inspection failures. The unrelated
sentinel survived and the capture reached genuine EOF. All twelve embedded APK
assets and all six hosted reports were hash-verified. The
[same-source PostgreSQL regressions](https://github.com/Russianranger/coh-android/actions/runs/36356285898)
also passed. The [acceptance receipt](android-evidence/accepted-wine-cleanup-36356283176.json)
preserves the build identity, payload hashes and reports.

The subsequent 0.1.4 Thor run again failed capture closure; the hosted receipt
and APK remain historical evidence.

### Hosted 0.1.5 Wine thread cleanup qualification

[The 0.1.4 device report](android-evidence/thor-capture-still-open-20260928.json)
passed all eleven functional stages and initialized Wine in 85.957 seconds. The
same wineboot capture failure remained after graceful PostgreSQL and Wine prefix
shutdown. Ownership scanning reported zero candidates, zero inspection failures
and completion, so its accounting did not explain the still-open pipe. Graphics
was not requested.

The [thread cleanup investigation](ANDROID_WINE_THREADS.md) reproduced a native
thread-group leader in `Z` state while a live worker retained the exact ownership
token and inherited output pipe. The old policy skipped that group, reported zero
candidates and left the capture open. Signaling the authenticated group allowed
genuine EOF. This confirms a real cleanup defect; the physical report has no
thread inventory and cannot identify its remaining writer.

Version 0.1.5 inspects surviving tasks of an exited leader and verifies UID,
thread-group ID, start time, PID namespace and the exact run token before group
signaling, preferring a group pidfd. A true zombie without live tasks needs no signal.
Unknown ownership, surviving owned tasks or missing output EOF must still fail.
Thread observations in reports exclude environment contents and ownership tokens.

Accepted source `9dc58f62c58dc4fc5c01288071429bf2aa06d2f4` includes the final
state-transition race and missing-task checks.
[Run 36364550345](https://github.com/Russianranger/coh-android/actions/runs/36364550345)
passed all five jobs on 2026-09-28 01:12:14 UTC. All 125 tests passed in 15.591
seconds without skips. Fresh/repeat database runs passed eleven stages each;
client runs passed twelve each. Cold initialization took 39.343 seconds in
database mode and 39.747 seconds in client mode; warm runs took 4.176 and 4.277
seconds respectively. These timings describe the hosted environment.

The ordinary detached-helper and exited-leader/live-worker fixtures passed in
both modes under the pinned PRoot. Each thread fixture observed a zombie leader
with an authenticated worker holding the exact inherited pipe, which the old
policy would miss. Cleanup exercised one TERM and one KILL through two pidfd
signals and reached genuine EOF. An unrelated, TERM-sensitive sentinel running
the same executable survived. These are direct fixture observations, not evidence
of the identity of Thor's remaining writer.

All twelve APK payloads and all eight hosted reports were hash-verified. The
[same-source PostgreSQL regressions](https://github.com/Russianranger/coh-android/actions/runs/36364553676)
also passed. The [acceptance receipt](android-evidence/accepted-wine-threads-36364550345.json)
preserves build identity, payload hashes and reports.

### Accepted primary M2 Thor diagnostic and headless client gate

The [device acceptance record](THOR_DEVICE_ACCEPTANCE.md) and
[selected evidence](android-evidence/accepted-thor-20260928.json) preserve the
supplied `coh-diagnostic-20260928-012426.zip` report. It identifies app 0.1.5 on
AYN Thor/Android 13 and runtime manifest
`fba5afaeb8ceaa4fb113102e436f3677d957a1c09d1d20f543cca630979d4203`, matching the
accepted hosted build. The `database_and_client` run completed at
2026-09-28 01:24:05.958172 UTC with all twelve stages passed, no failures and
complete owned cleanup.

This report proves a successful subsequent combined run: the existing database
cluster and ready Wine prefix were reused. The user says both operations passed, including
the preceding database-only run; the supplied archive directly documents only
the subsequent combined run. It verifies native PostgreSQL, real PE32 DLL and ODBC driver
loading, all 65 ODBC sessions, SQL/value/metadata fixtures and durable same-cluster
restart. Headless WGL rendering through llvmpipe/Mesa 22.3.6 returned all four
expected pixel colors; synthetic window input and DirectInput device creation
passed. This is a software renderer. DirectSound enumerated zero devices, with
no audio playback claim.

Device cleanup now observed three exited-leader groups and three authenticated
live-worker witnesses. It issued three TERM signals and one KILL signal through pidfds,
finished with zero remaining helpers or inspection failures, and closed input and
output for all 30 recorded processes. This observes the reproduced dead-leader/
live-worker condition on Thor and completes cleanup successfully. The report does
not inventory the exact earlier pipe writer, so that identity remains unknown.

**The primary M2 device diagnostic and headless client capability gate are
accepted.** Android surface presentation, hardware acceleration, physical input,
audible playback and CoH gameplay remain unvalidated. The subsequent 0.2.0
DbServer test passed two full runs with a clean Stop between them. App switching
and screen locking are user-attested; peak memory remains unmeasured. Keep both
accepted installations. The next device work is verified asset import and the
combined Atlas runtime with Android lifecycle handling. The
[first hosted M3 DbServer gate](ANDROID_DBSERVER.md) subsequently passed in
run 36369485666. The latest managed Atlas result above accepts hosted
MapServer/client local bindings; Android packaging, network integration and
app lifecycle checks remain before physical Atlas acceptance.

### Earlier attempts and corrections

The recovered evidence and new character harness are on
[`codex/character-persistence-continuation`](https://github.com/Russianranger/coh-android/pull/1)
in draft PR #1. Implementation commit: `3d61ca929dc825ba9424279553797b66498df418`.
[Hosted run 36269025801](https://github.com/Russianranger/coh-android/actions/runs/36269025801)
passed both tooling jobs: all 55 Windows checks, including three live named-pipe
checks; Linux passed 52 with those three platform checks skipped. The game
experiment failed with `Unknown character status flags`: a multiline whitespace
match consumed process output after a valid status line. Character ID 1 and its
name agreed between TestClient, stock `-find` and independent SQL, but no save or
restart pass was reached. The [full failed attempt](postgresql-evidence/character-persistence-36269025801.zip)
and [report](postgresql-evidence/character-persistence-36269025801.json) are preserved.
The status parser is corrected at `cc3c82a87e2c3eabe1478b13ea031e3923423b10`,
without relaxing identity or flag checks. The reproducing regression passed;
all 40 portable character checks passed, with three Windows transport checks
skipped locally. [Fresh retry 36270565732](https://github.com/Russianranger/coh-android/actions/runs/36270565732)
failed after the status fix worked: character ID 1/`TEST-43027` was connected on
Atlas Park, but TestClient's GUI entry allocated its own console and reopened
stdout/stderr to `CONOUT$`. The harness could not see the required creation
branch text. The [artifact](postgresql-evidence/character-persistence-36270565732.zip)
and [report](postgresql-evidence/character-persistence-36270565732.json) are preserved.
The attempted console preallocation fix was rejected by its Windows GUI
regression in [run 36280623154](https://github.com/Russianranger/coh-android/actions/runs/36280623154):
`AllocConsole` still succeeded, so the runtime job was skipped. The replacement
uses a bounded observer attached to the actual TestClient console before the
launcher version exchange, preserving the console across the short client exit.
[Run 36281372316](https://github.com/Russianranger/coh-android/actions/runs/36281372316)
then passed all 66 Windows tooling/map checks and reached real character creation,
live currency 12345, protocol logout and independently committed SQL. The first
saved snapshot contains one parent, one secondary row, seven powers and twelve
costume parts. It failed on observer cleanup before restart acceptance: forced
client-tree termination closed the console before its final snapshot. The
[artifact](postgresql-evidence/character-persistence-36281372316.zip) and
[report](postgresql-evidence/character-persistence-36281372316.json) are preserved.
The follow-up finalizes the observer after proven logout/save but before residual
client cleanup; exact resume acceptance remains required.
All four [PostgreSQL regressions](https://github.com/Russianranger/coh-android/actions/runs/36269025871)
also passed on the implementation commit.

The final cleanup-order correction in `86e512e8` completed the restart/resume
gate. Its accepted evidence and remaining scope are recorded above; earlier
failed attempts remain as diagnostic history.

## Active direction

Use the original public OuroDev-derived Issue 24/Volume 2 source fork at
`0b75ade0c801735e10c5798f641948a45cc50488`, under `upstream/ouroboros`. The user has
no Windows PC: use hosted Windows builds/reference tests and Thor testing.
Canonical i25 acquisition is deferred.

## Current database work

PostgreSQL is the selected database alternative. The implementation lives in
`database/postgresql`, with an immutable-source patch under `patches/postgresql`.
The actual Win32 DbServer now has an opt-in, asset-independent persistence test
entry. It exercises the original container parser, writer, SQL FIFO/worker pool,
reader and template updater with controlled templates and records. PostgreSQL
saves commit before completion; serialization/deadlock retries replay the whole
transaction. Permanent or uncertain failures stop without acknowledging the
failed command. Child/parent deletion is atomic.

All four jobs in the current [regression run 36088012670](https://github.com/Russianranger/coh-android/actions/runs/36088012670)
passed at repository commit `775a0dd770adac045484805dbbb5f68054c7a354`:
Linux PostgreSQL 16/18, Windows x86 ODBC/PostgreSQL 17, and the actual Win32
DbServer. The latter passed 21 check groups across 14 process invocations,
including connection loss, failed-save rollback, restart/WAL recovery, template
rebuild, backup/restore and foreign-key removal against absent tables. The
narrow PostgreSQL guard fixes the fresh-database initialization failure without
changing the preserved source snapshot.

The earlier [20-group implementation run 35962572993](https://github.com/Russianranger/coh-android/actions/runs/35962572993)
at `0827ccc992daa7530d9f98d742122238197847df` and
[regression refresh 36071558686](https://github.com/Russianranger/coh-android/actions/runs/36071558686)
remain historical evidence. The separate normal fixture-OFF DbServer
[startup/export/reload run 36125829298](https://github.com/Russianranger/coh-android/actions/runs/36125829298)
also passed using the accepted schema/runtime pair and a fresh disposable
PostgreSQL database. This exercises normal game-schema initialization in addition
to the controlled persistence fixtures; it does not create or save characters.

**Normal network acknowledgements passed:** [run 36125829311](https://github.com/Russianranger/coh-android/actions/runs/36125829311)
verified creates, an update after restart, and a two-container request held behind
an actual PostgreSQL row lock. No ACK arrived during the 2.078-second observed
write block. After release both rows were committed; an injected COMMIT failure
then produced zero ACKs, preserved the previous row, and stopped DbServer with
exit 3. The normal reference package had fixture mode OFF. The report and all
redacted logs are [preserved](postgresql-evidence/network-ack-36125829311.json).
Batches are not atomic as a whole, and player-session completion is untested.

The latest test drivers distinguish the specific observed benign PostgreSQL
catalog notices from real errors. Both new normal-process gates passed at
`a0ae66d72648d33a7f70b3116d1e1800d9164184` using the accepted `775a0dd...` builds.

Migration 2 adds transactional table rebuilds preserving sequence high-water,
indexes and foreign keys, explicit ASCII case-insensitive name equality, and the
PostgreSQL auction timestamp filter. Stop DbServer, back up and run
`pg_local.py migrate` for an existing development cluster. See the
[persistence design and test scope](POSTGRESQL_PERSISTENCE.md),
[database instructions](../database/postgresql/README.md) and
[validation record](VALIDATION.md). This database milestone does not establish
gameplay; the separate diagnostic APK's current acceptance is recorded above.

**Stage1 asset inspection complete:** `stage1a.pigg`, `stage1b.pigg` and
`stage1f.pigg` have been received. All **14,814 entries** passed archive integrity
and offline structural checks; 5,878 animations and 8,936 textures were staged
separately. All seven startup texture names and MALE/THUMBSUP are present.
Every base-animation reference resolves within `stage1a.pigg`. Preserve warnings
for 216 legacy hierarchy layouts and 193 DDS surplus-byte cases; runtime use
remains unvalidated. See [the stage1 assessment](STAGE1_ASSET_ASSESSMENT.md).
No repeat index run, repeat upload or custom `i26/geobin.pigg` upload is needed.

**Reference runtime refreshed:** [run 36088012664](https://github.com/Russianranger/coh-android/actions/runs/36088012664)
passed with the exact source pin, PostgreSQL patch and fixture mode OFF at
repository commit `775a0dd770adac045484805dbbb5f68054c7a354`.
Download `reference-win32-runtime` (artifact `10843979104`) from this run;
it supersedes [the earlier package 36069123663](https://github.com/Russianranger/coh-android/actions/runs/36069123663).
Client, MapServer, DbServer, TestClient, pig and Launcher are packaged with
required supplied DLLs and app-local x86 MSVC runtime libraries. The package
passed hash, PE and dependency checks. The verified base assembly contains
173,011 data files / 2,977,730,517 bytes, with no conflicting donor paths.
The preflight's earlier 173,008 count excluded three additional source-pinned DB
config files added by final assembly. See [current assembly evidence](reference-runtime-evidence/assembly-775.json)
and [reproduction/build instructions](REFERENCE_RUNTIME.md).

Local game execution is blocked by this environment's wineserver IPC restriction.
Use hosted Windows for further runtime validation. The separate data-only schema
patch remains isolated from the reference package and retains error/output
gates. Its incidental caches must not be reused as gameplay caches.

**Data-only schema generation refreshed:** [run 36088012666](https://github.com/Russianranger/coh-android/actions/runs/36088012666)
passed at the same repository commit as the current reference package. Bootstrap
took 31.468 seconds and strict reload 5.750 seconds, with zero queued errors and
identical bytes for all six attribute maps. All 51 required outputs plus five
dbidmaps are preserved in [the current accepted artifact](schema-generation-evidence/accepted-36088012666.zip).
Every one of these 56 generated payloads is byte-identical to the
[earlier accepted run 36072787971](schema-generation-evidence/accepted-36072787971.zip),
which remains historical evidence. Keep the accepted attribute-ID mappings with
any database initialized from them.

**Normal DbServer schema startup/reload passed:** the first hosted attempt
exposed a fresh-database FK-removal ordering bug. The narrow correction passed
its regression suite and is included in both current artifacts. With that pair,
[run 36125829298](https://github.com/Russianranger/coh-android/actions/runs/36125829298)
completed fresh initialization/export in 13.219 seconds and a second pass in
5.718 seconds. Both exited successfully with no failure diagnostics and produced
fresh empty dumps. Both passes found 99 tables and 58,272 attribute rows
(56,411 general, 1,771 badge-stat and 90 pop-help IDs), with identical catalog
hashes and attribute mappings. Both catalogs contain the verified 5,935 columns,
119 indexes and 734 constraints.
The tested DbServer has persistence fixture mode OFF; its executable SHA-256 is
`fb62028b24bf3165bdcf09e80909d02df5391f89986b9e0454934909a67d93f8`.
See the [downloaded evidence](postgresql-evidence/generated-schema-36125829298.zip)
and [summary](postgresql-evidence/generated-schema-36125829298.json).
The later asset-backed comparison and Atlas Park gate below passed. Complete
serializer semantics, complete asset coverage and character gameplay remain
unvalidated.

**Normal templates and Atlas Park readiness passed:**
[run 36176806895](https://github.com/Russianranger/coh-android/actions/runs/36176806895)
used the accepted reference/schema pair and all 16,721 reviewed binary assets.
Ordinary `MapServer -templates` freshly reproduced **56/56** accepted files
byte-for-byte in **25.89 seconds**. A separate fresh runtime, without comparison
caches, then started normal DbServer and Atlas Park against PostgreSQL. Independent
DbServer status queries confirmed the initial not-started state and subsequent
ready state with continuing updates for **62.235 seconds**. Both reports have
empty failure lists. Preserve the [comparison report](reference-runtime-evidence/reference-template-comparison-36176806895.json),
[comparison artifact](reference-runtime-evidence/reference-template-comparison-36176806895.zip),
[map report](postgresql-evidence/one-map-36176806895.json),
[map artifact](postgresql-evidence/postgresql-one-map-36176806895.zip) and
[accepted gate identities/hashes](reference-runtime-evidence/accepted-gates-36176806895.json).
The normal executable does not report queued startup error counts; these gates
do not establish complete assets, character login/persistence or gameplay.

## Completed

- All 5,995 source files verified; exact-commit upstream Windows build and nine
  utility/archive/codec tests passed, as previously audited.
- Imported the entire `Thunderspies/i24` tree at
  `d51533ec8e6a9cf726b9214968077a05fdcf19f3` under `upstream/i24`: 156,297 files,
  1,992,097,492 bytes, no exclusions. Local and hosted integrity/tree checks passed.
  Import commit: `1768775ab3608cdd852ec7119bbf0139a91248c6`.
- Added `content-lock.json`, data inventory and per-file manifest. The importer
  and verifier accept `--lock content-lock.json`; existing source defaults remain.
- Added the exact 72-archive upstream catalog and portable `content_assets.py`
  probe/fetch/record/verify tool. Receipt checks detect changed/missing bytes.
- Added `prepare_runtime.py`; full text-only staging passed. It keeps imports
  immutable, fixes `Game.exe` to `CityOfHeroes.exe` in staged launchers and uses
  source-pinned configs. It accepts extracted asset data and exact-pin build
  outputs separately; it does not execute programs or install SQL.

## External content result

The user's `small_i26_piggs.zip` has now been inspected: all **17 archives /
8,864 entries** passed size, decompression, MD5 and cached-header checks.
**549 compiled files use Parse7; the pinned source expects Parse6**, so these
caches cannot be reused unchanged. Staged **665 candidate binary assets**
(141 geometry, 445 textures, 79 audio files; 152,755,341 bytes) separately,
with runtime compatibility still unverified. No raw client binaries/assets were
published. The original ZIP plus the new portable inspector reproduce staging.
See [client content assessment](CLIENT_CONTENT_ASSESSMENT.md) and its
[per-archive hashes/counts](client-content-assessment.json). Eight inspector
regression tests passed in that initial pass.

The subsequent **`geomBC.pigg`** also passed: 1,232 entries, comprising 584
geometry files and 648 Parse6 caches. All geometry files use versions accepted
by the source and passed compressed-header/data-bounds checks; meshes/collision
and runtime loading are untested. Staged geometry separately under
`imports/base-geomBC-candidate-assets`. Cumulative result: **18 archives,
10,096 verified entries, 1,249 distinct candidate assets / 318,908,734 bytes**.
The inspector now records geometry header checks; eleven regression tests pass.
See [base geometry evidence](base-geometry-assessment.json).

The later `fonts.pigg`, `player.pigg`, `misc.pigg` and `geom.pigg` batch also
passed: **2,774 additional entries**. Cumulative result is now **22 archives /
12,870 entries / 2,487 distinct candidate asset paths**, with two conflicting
custom/base geometry variants kept separately. All 46 fonts are staged, including
TTC collections; every one of the 16 startup font filenames is present. All
1,277 new geometry headers passed. `misc.pigg` mostly duplicates the pinned text.
At that earlier stage there were **zero skeletal .anim tracks** in the supplied
set and none of seven requested basic renderer texture names. The subsequent
stage1 uploads below supply those candidates; runtime startup remains untested. See [asset coverage history](BASE_ASSET_COVERAGE.md)
and [machine-readable evidence](base-assets-assessment.json).

The subsequent **`coh-asset-index.json`** has now been received from Thor and
preserved as [thor-asset-index.json](thor-asset-index.json). It reports 73 base
archives and 22 custom-folder archives, with 96,379 entries across those tables
(not deduplicated). Base `stage1a.pigg` lists 5,878 animation tracks, including
MALE/THUMBSUP; `stage1b.pigg` and `stage1f.pigg` list all seven startup texture
names. This locates candidates on the device; it does not add to the 22
payload-verified archives or establish source-format/runtime compatibility.
The indexer previously matched full-inspection counts/extensions for all 22
available archives; thirteen regression tests passed in that earlier pass.

The three selected **stage1 archives** then passed integrity and offline format
checks. Cumulative payload-inspected count: **25 archives / 27,684 entries**.
New staging contains 14,814 distinct paths within the batch and 654,699,284 bytes;
its overlaps with earlier custom assets have not been recomputed. The 20 new
format/staging tests passed. All animation base references resolve, including
the fallback, and all seven startup textures pass structural checks. Native
ARM64 needs explicit decoding of 32-bit animation records; the renderer must
handle the observed DDS formats. Runtime compatibility remains untested. See
[stage1 evidence](stage1-assets-assessment.json) and the
[reproducible checks](STAGE1_ASSET_ASSESSMENT.md#reproduce-without-windows).


[Hosted import/probe run](https://github.com/Russianranger/coh-android/actions/runs/35940141238)
completed successfully. All 72 archive HEAD requests to `dists.thunderspy.org`
returned HTTP 403. Local sample GET and the current live manifest also returned
403. Binary assets were not downloaded from that host. `docs/asset-availability.json` contains
the complete observations.

[Content acquisition instructions](CONTENT_ACQUISITION.md) identify the canonical
recipe and OuroDev's base/binning-data archive listings as an unverified fallback.
The original fallback was an accessible compatible archive/mirror/magnet or
existing asset folder; the user has since supplied the targeted assets above.
No additional broad asset upload or Windows VM is required for this assessment. Do not silently substitute the current
customized Thunderspy/Homecoming live client or reuse unrelated generated bins.

## Next implementation priority and remaining scope

The accepted device build is [COH Server Test 0.2.0](ANDROID_SERVER_DEVICE_TEST.md),
installed alongside 0.1.5 as `io.github.russianranger.cohdiagnostic.m3`.
It packages the exact accepted M2 payloads and qualified loopback DbServer donor
`36460867428`, with a device policy enabling loopback for every DbServer process
and fixed inputs for both normal schema launches. The original Atlas donor is
not changed. Each real test has disposable state and each operation an immutable
support ZIP. The candidate workflow builds the APK and runs its exact packaged
guest/bundles on hosted ARM64 with the device policy. All three jobs and all 28
runtime stages passed in
[run 36483331900](https://github.com/Russianranger/coh-android/actions/runs/36483331900)
at `f7dbba42ec29a1c054d856d71810146f5b53bac6`. Tooling passed 233 checks with eight
Windows-only skips. The APK is 16,668,615 bytes, SHA-256
`cb5cf453af1b81cbaa02917a6d7cb55ab8b8f2a910a46b0a85f4ae399883188b`.
The [candidate receipt](android-evidence/accepted-device-candidate-hosted-36483331900.json)
binds the build, independently checked APK payloads and hosted reports.
The [physical Thor receipt](android-evidence/accepted-dbserver-thor-20260928.json)
records two full passes in 325.763 and 338.326 seconds, surrounding a clean Stop
during active Wine setup. Both passes verified 14 local endpoints, all 21 fixture
groups, both schema passes and all 111 closed process captures. The stopped run
closed all 22 captures and correctly reported cancellation. All three ended with
zero owned processes and inspection failures. App switching and screen locking
are user-attested; peak memory is unmeasured. The subsequent hosted Atlas loopback
integration passed in `36493722153`, preserving the earlier accepted default.
MapServer/client local bindings then passed Windows and hosted ARM64
qualification in `36510836956`. Verified asset import and separate Android
Atlas runtime/lifecycle integration are next; none of these hosted results
establish physical Atlas acceptance.

**The primary M2 device diagnostic, hosted M3 DbServer and hosted Atlas
create/save/restart/resume/second-save sequence are accepted.** The Atlas
[acceptance receipt](android-evidence/accepted-game-hosted-36460005201.json)
records the successful full workflow `36460005201`, including the final host
validator. Preserve the earlier `36454174481` workflow failure and its separate
post-correction acceptance.
The isolated Wine-compatible DbServer fixture
and normal schema startup/export/reload have passed; preserve their
[accepted evidence](android-evidence/accepted-dbserver-hosted-36369485666.json).
The current fixed-input DbServer successor is also
[qualified](android-evidence/accepted-dbserver-hosted-36451873322.json).
Keep default donor `36451873322` and retain both DbServer
activation acknowledgments and all four schema/configuration snapshots.
Enabled ARM64 dispatch publication was already verified in run `36428915900`.
The separate sibling DbServer failure remains unexplained despite the successful
byte-identical repeat; retain both receipts and the qualified donors.
The separate loopback listener package is
[hosted-qualified](android-evidence/accepted-dbserver-hosted-36460867428.json)
in run `36460867428` and accepted for the explicit Atlas loopback profile in
`36493722153`; the historical default donor is retained. Preserve its earlier
CRLF fixture-setup failure and correction. The 0.2.0 device results accept this
listener package and Stop/rerun handling on Thor. The separate
[hosted game listener receipt](android-evidence/accepted-game-listeners-hosted-36510836956.json)
accepts both MapServer starts and both TestClient sessions with actual local
UDP bindings and the complete persistence sequence. Its opt-in donor profile
preserves the historical defaults and accepted device APKs.
Keep the existing 0.1.5 and 0.2.0 APKs and runtimes. See the
[concrete next steps](THOR_DEVICE_ACCEPTANCE.md#next-work).
Peak memory remains unmeasured. The following items preserve
completed reference gates; no repeated Windows-only milestone is needed.

1. Preserve the accepted results from corrected manual [asset run 36176806895](https://github.com/Russianranger/coh-android/actions/runs/36176806895).
   It passed ordinary template comparison and Atlas Park readiness with schema
   run `36088012666`, reference run `36088012664`, asset `588984151` and
   `run_one_map=true`. No rerun is needed to establish those completed gates.
   Upload is complete: unpublished draft release
   `396839391` contains the accepted **615,541,018-byte** ZIP, SHA-256
   `28b4aa8f0b3a71287e9a596df23097722bd71db9ddb9a5a906b5af9d6152cc07`.
   Ignore incomplete asset `588979946`. No repeat PIGG or ZIP upload is needed.
   The initial manual [run 36174562963](https://github.com/Russianranger/coh-android/actions/runs/36174562963)
   failed during download before any game process, suspected to be the draft
   release's rejection of the read-only token. Its HTTP status was not logged.
   [Fix 5f37d7c](https://github.com/Russianranger/coh-android/commit/5f37d7c)
   scopes `contents: write` to the manual comparison job; global/tooling tokens
   stay read-only. It also adds safe numeric HTTP status and stage diagnostics;
   all 12 downloader tests and [tooling run 36175800522](https://github.com/Russianranger/coh-android/actions/runs/36175800522)
   passed. [Run 36175960917](https://github.com/Russianranger/coh-android/actions/runs/36175960917)
   then successfully downloaded and verified the exact ZIP, confirming hosted
   draft access. It failed `Manifest must use canonical JSON` before game
   execution: Windows checkout changed the manifest's LF bytes to CRLF.
   [Fix fe98dd5](https://github.com/Russianranger/coh-android/commit/fe98dd5a9761fb05d79b9b3f9f39a771eb9ea687)
   marks `assets/reference-inputs-*.json -text`; a temporary Git checkout with
   `core.autocrlf=true` reproduced the accepted canonical bytes, and
   [tooling run 36176404244](https://github.com/Russianranger/coh-android/actions/runs/36176404244)
   passed. The successful manual run used that fix. The release remains unpublished
   and raw assets are not uploaded as Actions artifacts. See the
   [concrete handoff](NEXT_SERVER_VALIDATION.md) and
   [transfer evidence](reference-runtime-evidence/asset-transfer-20260925.json).
   The matching reference package and coherent base assembly are ready. Preserve the accepted attribute-ID mappings; do not
   substitute the separate schema executable or its incidental caches for the
   reference runtime.
2. Preserve the accepted [character persistence result](CHARACTER_PERSISTENCE_VALIDATION.md#accepted-hosted-validation-36282414135).
   Fake-auth creation, live currency change, explicit logout, committed SQL,
   same-cluster/service restart and exact-name short resume have passed.
   The [sustained resume and second-save result](SUSTAINED_SESSION_VALIDATION.md#accepted-hosted-validation-36295176484)
   has also passed, including missing-name refusal without mutation. Preserve
   the separate diagnostic TestClient receipts alongside the stock reference.
   The [Atlas round trip](MAP_TRANSFER_VALIDATION.md) has also passed with
   independent destination identity, fresh player updates, current heartbeats,
   live currency and a final committed protocol save. New-zone assets, mission
   transfers and automatic Launcher startup remain unvalidated.
   Separate remaining server work includes player-session completion callbacks, game-level
   name uniqueness and auxiliary-service persistence. Generic-container network
   ACK ordering is now verified. Fake auth is only the minimal local diagnostic route; no SQL
   Server save migration has been attempted. Empty-database startup/export and
   controlled persistence fixtures do not establish these gameplay behaviors.
3. Generate further server/client caches with the bounded harness when the runtime
   has the required graphics. Resolve legacy animation hierarchy/DDS warnings
   through reference runtime use. Keep custom variants separate and request
   further archives only when runtime evidence identifies a concrete missing
   input. The older upstream v2i3 release is not the locked build; use the current
   reference artifact.
4. Keep the accepted 0.1.5 and [0.2.0 server](ANDROID_SERVER_DEVICE_TEST.md)
   installations. The real DbServer, Stop/rerun and requested background checks
   are complete within their documented evidence scope; do not request another
   run of these passed diagnostics. Peak memory remains unmeasured.

Do not run the unmodified upstream asset fetcher inside `upstream/i24`; it assumes
a standalone Git checkout. Never modify the preserved snapshot to fix a launcher.

The manual i25 discovery workflow and its prior TLS findings remain historical.
`odtoken` is not required for current work and must not be printed or sent to the
asset host. No background import is running. The current APK status is recorded
in [ANDROID_DIAGNOSTIC.md](ANDROID_DIAGNOSTIC.md); gameplay remains unvalidated.
