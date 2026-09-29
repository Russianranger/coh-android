# Pending MapServer heartbeat diagnostics

This is a read-only design checkpoint, not an implemented correction or accepted
runtime result. Hosted runs `36599606621` attempt 1 and `36621227369` attempt 1
failed Atlas freshness observation. The latter had advancing DbServer dispatch,
live services and clean final cleanup, but never reached character creation or
restart. The exact-APK retry must retain all current acceptance checks. A retry
pass does not resolve intermittent startup reliability; another matching failure
should trigger fresh MapServer diagnostics before further identical retries.

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

Implementation needs an explicitly receipted source overlay/profile: the current
`tools/prepare_game_loopback_source.py` contract permits only six patched files.
Add Windows producer contracts for disabled behavior, existing-file refusal and
external visibility; guest parser/capture checks; a fresh Win32 donor and package
identity; full ARM64 qualification; then exact-APK qualification. Preserve all
accepted donors and the candidate-only cleanup correction separately.
