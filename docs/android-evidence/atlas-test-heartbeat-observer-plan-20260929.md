# MapServer heartbeat diagnostics: hosted qualification complete

Hosted runs `36599606621` attempt 1 and `36621227369` attempts 1 and 2
failed Atlas freshness observation. Both 0.4.3 attempts had advancing DbServer
dispatch, live services and clean final cleanup, but never reached character
creation or restart. Identical retries are stopped. The separately receipted
observer described below passed all six real Windows producer contracts and
the eighteen-stage ARM64 runtime in run `36630872719`. Independent review verified
raw tick progress, both committed saves, exact-name resume and complete cleanup.
No qualified replacement APK or repair of earlier heartbeat failures is claimed.

The current evidence cannot identify the blocked Windows operation. MapServer
publishes readiness before completing late startup. Buffered stdout ending at SG
permission verification, Linux thread states and saved WOW64 contexts are not
proof of the current instruction. Folder/callback draining is a hypothesis.

Use a separate opt-in MapServer main-thread progress mapping, following the
existing DbServer producer's disabled-by-default, unique-file and seqlock design.

| Source | Bounded stage markers | Question answered |
|---|---|---|
| `upstream/ouroboros/MapServer/src/svr/svr_init.c` | Before/after readiness publication, priority, heap/SG checks, callback enable, ItemOfPower request, error queue drain, launcher contact, main-loop entry and sleep | Did late startup finish? |
| `upstream/ouroboros/MapServer/src/svr/svr_tick.c` | Tick entry/completion, before/after `dbComm`, folder callbacks, tick-top, entity update, game logic and tick-bottom | Where did heartbeat progress stop? |
| New MapServer producer `.c/.h` | Version, PID/TID, sequence, stage, started/completed tick counters | Is the observed record fresh and from the expected process? |

Use `CREATE_NEW`, a 4 KiB mapping, fixed-size records, one main-thread writer and
saturating counters. Markers must perform no clocks, allocations, flushes, locks
or system calls. A stage means the named operation is about to run, not complete.
Use separate first/restart files, exact source/record identity checks, bounded
sample history and before/after-failure captures. Producer progress must never
replace protocol readiness, the 20-second freshness requirement or the 30-second
observation period.

Keep the first overlay MapServer-only. If fresh evidence points to folder work,
then consider a separate UtilitiesLib hook to distinguish directory draining
from callback bodies. Do not suppress callbacks or relax readiness from these
current observations.

The implementation uses `tools/prepare_mapserver_progress_source.py` and a
separate three-file patch plus two-file producer overlay, preserving the existing
six-file game-loopback contract. `package_mapserver_progress.py` receipts the
fresh Win32 MapServer and symbols. Composite packaging permits that MapServer
override only with the exact accepted supporting donors. The explicit profile is
`dispatch_progress_v1`; its first workflow is `android-map-progress.yml`.

Windows contracts compile the actual producer and verify external live reads,
disabled behavior, no added thread, refusal to overwrite evidence, and compiled
markers without calls or synchronization. Guest evidence binds raw record bytes,
identity, sequence, stage and tick counts to bounded observations. Full observer
qualification requires valid records and positive completed-tick advancement
for both launches in addition to the unchanged eighteen game stages.

The successful run captured a 114.233-second interval between first-tick folder
entry/completion markers. Protocol-ready samples aged 23 and 85 seconds were
correctly rejected by existing freshness checks. Once the first tick completed,
current readiness and the remaining stages passed. This does not establish the
cause of earlier uninstrumented failures or repair the folder work.

Next: integrate the qualified explicit profile into 0.4.4 and require a fresh,
valid, same-launch publication with a completed tick before accepting the normal
protocol-ready sample. Revalidate identity after that query, never fall back to
cached progress, and preserve startup deadlines, freshness and observation.
Run the exact-APK gate with that additional startup proof. Preserve all
accepted donors and the candidate-only cleanup correction separately. Do not
request another physical Thor test until that candidate qualifies.
