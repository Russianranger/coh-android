# Source observation lease before the first resource capture

The existing startup hook alone does **not** establish model/GEO quiescence.
Original `svr_init.c` calls `initBackgroundLoader()` well before the normal map
load. Original `groupLoadMap` completes synchronous world loading, but neither its
body nor the hook after `dbSetupMap` calls `forceGeoLoaderToComplete`. Therefore a
source-only diagnostic cannot infer zero loader work from startup sequencing.

The new private resource role adds a nonblocking observation lease; shipping
sources and previously captured source bytes remain unchanged. `stage_resources`
verifies the exact original `Common/seq/anim.c` hash, preserves every byte and
appends only an include of `source_resource_quiescence.inc`. Access to original
private counters/queues is therefore in their original translation unit. Full
original source and twenty relevant function bodies are pinned by
`resource-quiescence-source-pins.json`, independently checked by
`check_resource_quiescence.py`. These are original-source policy checks plus
sanitized guard controls, not an actual Win32/capture acceptance receipt.

| Original source path | Exact relevant behavior |
| --- | --- |
| `MapServer/src/svr/svr_init.c` | Initializes the background loader earlier; sets FolderCache callbacks disabled and manual mode before trick/library load; normal map startup calls `groupLoadMap`, `dbSetupMap`, then the new private owner callback, then `dbReadyForPlayers`. FolderCache callbacks are enabled later. |
| `Common/group/group.c:groupModelFind` | SERVER uses `LOAD_HEADER` with `GEO_DONT_INIT_FOR_DRAWING`, so header-only NOT_LOADED is legitimate and must not be forced into a loaded geometry claim. |
| `Common/seq/anim.c:geoLoad` | LOAD_HEADER returns headers without requesting background payload work; other paths can queue work or wait, so the hook cannot assume all models used only this path. |
| `Common/seq/anim.c:heyThreadLoadAGeo` | Holds `heyThreadLoadAGeo_CriticalSection` around `geoLoadData` and ready-list publication. |
| `Common/seq/anim.c:heyThreadLODAModel` | Holds `heyThreadLODAModel_CriticalSection` around queued LOD work; CLIENT code is excluded in the SERVER variant, but the guard checks its count and lock as well. |
| `Common/seq/anim.c:geoRequestBackgroundLoad/geoRequestForegroundLoad` | Main-side requests maintain the outstanding count; a zero count is not guessed from a loadstate bit. |
| `Common/seq/anim.c:geoCheckThreadLoader` | Main-side finalization drains ready data, changes loadstates and decrements counts. The observer never calls it. |
| `Common/seq/anim.c:forceGeoLoaderToComplete` | Drains/finalizes and sleeps until queues empty. Deliberately not used: this observer must not mutate runtime loading policy. |
| `libs/UtilitiesLib/src/utils/FolderCache.c` | Update returns immediately while callbacks are disabled; normal updates reject a different FolderCache owner thread. Manual mode defers callback dispatch. |
| `Common/seq/tricks.c:reloadTrickProcessor/checkTrickReload/reloadTrick` | File callback queues names; actual trick mutations occur in `checkTrickReload` on the normal tick path, not in the directory monitor thread. |
| `MapServer/src/svr/svr_tick.c` | Geometry finalization, FolderCache callback dispatch and trick reload are tick work, after this startup callback returns. |
| `Common/group/groupfilelib.c` | Startup library loading and lookup are pinned. The observer uses only the existing lookup; no load/reload call or engine yield occurs inside the lease. |

Before acquiring a lease the sink **checks**, without changing, the original
`folder_cache_update_enable==0` and `folder_cache_manual_callback_check!=0`.
The new begin function then requires initialized loader critical sections and
rejects the original background worker thread. It uses `TryEnterCriticalSection`
on the original GEO lock, then the original LOD lock, and refuses immediately on
contention. While holding both, it requires both original outstanding counts and
the ready-for-finalization list to be zero. A pending queued APC, active worker,
or unfinalized GEO is a concrete refusal; no sleep, retry, forced completion,
resource load, queue drain, loader cancellation or asset mutation occurs.

Success holds both locks continuously across catalog, roots and resource
observation. The pinned private normal-startup call site is the main source owner;
no new request/finalization/reload callback is invoked by the source producers or
byte-copy sink. The guard checks only 'not loader worker' at runtime; its API must
not be repurposed as a generic cross-thread observer. Library/trick mutation is
excluded by the exact startup/manual-disabled callback scope; geometry/LOD worker
mutation is excluded by held original locks and zero queued work. This is a narrow
source observation lease, not global engine quiescence or a live session lock.

The same owner releases LOD then GEO locks after all observations, before file
flush/rename; every error cleanup also releases an acquired lease. Only new
private diagnostic lease/owner variables and lock ownership change. A mismatched
owner cannot release another thread's lock. Neither original counters, queues,
model state nor FolderCache configuration is changed. Source initialization and
lease acquisition are separate from shader/material/LOD resource completeness.

The sink emits `source_quiescence_status=1 source_quiescence_held=1
source_quiescence_released=1` only when the actual lease succeeded and ended.
Absent original callback scope or failed lease causes sink status 9 and owned-file
cleanup. Capture parser and final binding require those exact outcomes and the
new pinned guard policy. Until a reviewed new Win32 build executes these paths
and exports its new source/run/cleanup receipts, runtime quiescence is **pending**.
No old successful capture is relabeled with this new proof.

`check_resource_quiescence.py --output receipt.json --sanitize` tests actual guard
source with WinAPI fixtures in release/ASan/UBSan: uninitialized state, worker
caller, each busy lock, each outstanding work source, recursive admission,
wrong-owner release and successful balanced lifetime. Source counters/list bytes
remain unchanged. `check_resources_stage.py` additionally exercises release of the
lease at every source/file failure and refuses enabled/nonmanual FolderCache.
Actual Windows API execution remains a separate gate.

Original `initBackgroundLoader` writes its initialized flag before initializing
its critical sections. Therefore the flag test is **not** a generic concurrent
initialization barrier. The pinned startup call must have returned completely on
the same source owner before this later private map hook. The stage contract
explicitly retains that requirement. F independently reviewed the original
queue/counter/lock transitions and this scope restriction; no blocking issue was
found. The source guard remains unavailable as a general-purpose engine API.
