# Zone preparation research for 0.13.27

Research ran from 2026-10-11 01:04:33Z to 01:34:48Z: 30.25 wall-clock minutes, with parallel source review and controlled host experiments. The requested 30-minute window is complete; exact timing is in the companion JSON. This is source and host evidence, not device qualification. The initial audited continuation head was `2518f5df4b3b1907a70c0d72b7ac4a07be8a24c4`; .26 publication/runtime source remains `64a1833bc0d2dc1035c11188c6ae8c7fdb58244b`, with the accepted Game compiled at `c512e912a004b66886a7667640aa1a967e95de64`. No native or graphics change was made by this research.

## What the available evidence establishes

- The user accepted .25 as a much better physical FPS baseline and reported two successful .26 transfers. Sustained 30 FPS, all controls, destination Save and reopen, and .27 preparation/recovery remain distinct qualification questions.
- The original complete .26 gameplay export is unavailable. The retained reopen export never launched Game and contains no renderer/FPS or second-map preparation trace. Therefore neither preparation CPU contention nor memory or storage contention has been measured from that physical run.
- A reported low-memory exit is a relevant risk signal, but the available archive cannot place it specifically at the earlier live preparation or Finish/background event.
- The second destination is a new MapServer process. It reuses the same staged runtime, imported assets, derived caches and Wine prefix. It does not repeat `prepare_runtime`, import, mirror, native compilation or APK setup. Warm return reuses the retained peer; that is separate from automatic cold preparation.

## Source findings that change the optimization choice

| Finding | Implication and limit |
| --- | --- |
| Native `setLoadPriority` already selects BELOW_NORMAL in production and IDLE in development; runtime priority returns to NORMAL/BELOW_NORMAL. | Another Windows priority call would repeat existing intent. In pinned Wine, the Unix setter sends priority metadata to wineserver and the server assigns its metadata field; it does not call Linux `setpriority` or a Linux scheduler API. |
| The installed runtime is ARM64 Wine WoW64 with the pinned FEX Windows module, inside glibc PRoot. | Generic standalone FEXLoader/FEXServer advice is not automatically applicable. The module creates a process-local FEX context. The pinned `CodeCache::LoadData` and `SaveData` bodies are TODO placeholders; `SaveData` returning true is not an implemented persistent cache. |
| `-nosharedmemory` disables both shared memory and the shared heap. | Parsed server definitions and process-local JIT state can be duplicated in the second MapServer even when common file pages are cached. Removing this flag needs native shared-memory/address-space, CRC, namespace, failure and persistence qualification; it is not a harmless launcher tweak. |
| Native empty MapServers keep entering `svrTick` and the 30 Hz pacing path. | A retained empty origin can continue CPU and memory cost after transfer. `SIGSTOP` would also stop DB/network heartbeats and progress. Proper empty-instance quiescence or retirement requires a protocol/state design; changing world simulation flags is not equivalent. |
| TSR modes load global definitions and remain in a synchronization/sleep loop. | A TSR is not a reusable destination process factory. In the current disabled-sharing mode it adds a resident process without demonstrating amortized definition/JIT work. |
| The existing progress producer exposes STARTUP, MAP_LOAD, DB_SETUP, readiness and main-loop stages, UTC samples, monotonic freshness and native PID/TID. | A bounded observation history can be added without a native rebuild. A sampled stage is not an exact phase-duration or CPU/GPU timer. Early parsing, file work and translation remain combined under STARTUP. |

Pinned sources:

- [COH runtime lock](https://github.com/Russianranger/coh-android/blob/2518f5df4b3b1907a70c0d72b7ac4a07be8a24c4/android/runtime-lock.json)
- [Wine Unix ProcessPriorityClass path](https://github.com/wine-mirror/wine/blob/b073859675060c9211fcbccfd90e4e87520dc2c2/dlls/ntdll/unix/process.c)
- [Wine server process-priority handler](https://github.com/wine-mirror/wine/blob/b073859675060c9211fcbccfd90e4e87520dc2c2/server/process.c)
- [Exact shipped Wine/FEX build recipe](https://github.com/Russianranger/lsb-android/blob/ba052de14f3e10bffe114d209095ade70d56f529/native/fex/Dockerfile)
- [Pinned FEX Windows WoW64 context](https://github.com/FEX-Emu/FEX/blob/320c5f18475b0c8a7e99c51a5fdc5b5e35b147ab/Source/Windows/WOW64/Module.cpp)
- [Pinned FEX cache placeholders](https://github.com/FEX-Emu/FEX/blob/320c5f18475b0c8a7e99c51a5fdc5b5e35b147ab/FEXCore/Source/Interface/Core/CodeCache.cpp)
- [Native MapServer startup, priority, sharing, TSR and pacing](https://github.com/Russianranger/coh-android/blob/2518f5df4b3b1907a70c0d72b7ac4a07be8a24c4/upstream/ouroboros/MapServer/src/svr/svr_init.c)
- [Native server tick](https://github.com/Russianranger/coh-android/blob/2518f5df4b3b1907a70c0d72b7ac4a07be8a24c4/upstream/ouroboros/MapServer/src/svr/svr_tick.c)
- [Zoning launcher and retained peer](https://github.com/Russianranger/coh-android/blob/2518f5df4b3b1907a70c0d72b7ac4a07be8a24c4/android/guest/character_zoning.py)

## A limited, reversible scheduling experiment

A destination-only temporary Linux nice increase is a plausible preparation mitigation. It reallocates contested CPU time; it does not remove parsing, translation, memory or I/O work, and may extend cold preparation. It needs an actual-device capability probe and exact ownership/readback/restoration before readiness. The active Game, shared wineserver, PostgreSQL and app UI must not be included in its ownership scope.

The general claim that an unprivileged Android app cannot restore a raised nice value is too broad. AOSP Android 13 `init.rc` sets soft and hard `RLIMIT_NICE` to 40. The Linux floor is `20 - rlim_cur`, so 40 permits a decrease down to -20 subject to credentials/security policy. This is a source default, not proof of Thor's inherited limit or permission. Probe in a disposable child, retain actual limits/errors, and use unchanged scheduling when the round trip is not proved. Do not change hard limits or request capabilities.

Linux nice is per thread; fork/exec and new native threads inherit the creator's value. Correct restoration must cover late threads and descendant processes, avoid double demotion of an already weighted child, bind PID/TID start times and both private ownership tokens, and fail closed on ambiguous inheritance or denied restoration. A threaded Python parent must not use `preexec_fn` for scheduling; Python documents its deadlock risk.

Each existing child starts a new session. Under fair-group autogrouping, per-task nice can be less useful between separate sessions. Non-root CPU-cgroup placement can override autogrouping. Record readable `/proc/PID/cgroup` and `/proc/PID/autogroup`, rather than assume either effect. Android task-profile definitions can be overridden by the vendor and bundle CPU, IO and timer-slack actions; do not write private cgroup controls or move the whole app to a background profile.

SCHED_BATCH is a mild waking-task preemption policy, not a nice weight reduction. SCHED_IDLE risks starving preparation. An IO priority change affects supported block schedulers/IO contexts, rather than all file reads or page-cache work. With no explicitly set IO priority, supported schedulers may derive the default from nice, so changing nice must not be described as guaranteeing a strictly CPU-only effect. None is a substitute for measuring the limiting resource.

Primary references:

- [AOSP Android 13 inherited nice limit](https://github.com/aosp-mirror/platform_system_core/blob/android-13.0.0_r1/rootdir/init.rc)
- [AOSP Android 13 thread priority implementation](https://github.com/aosp-mirror/platform_system_core/blob/android-13.0.0_r1/libutils/Threads.cpp)
- [Linux nice permission and inheritance](https://manpages.debian.org/testing/manpages-dev/setpriority.2.en.html)
- [Linux resource-limit semantics](https://manpages.debian.org/testing/manpages-dev/getrlimit.2.en.html)
- [Linux policies, autogroups and CPU cgroups](https://manpages.debian.org/testing/manpages/sched.7.en.html)
- [Kernel nice weight design](https://www.kernel.org/doc/html/latest/scheduler/sched-nice-design.html)
- [Android task profiles and vendor overrides](https://source.android.com/docs/core/perf/cgroups)
- [Python subprocess threading restriction](https://docs.python.org/3.11/library/subprocess.html)
- [Linux IO-priority semantics](https://manpages.debian.org/testing/manpages-dev/ioprio_set.2.en.html)
- [BFQ scheduler priority support](https://docs.kernel.org/block/bfq-iosched.html)

## Host checks, explicitly not physical FPS results

`linux-scheduler-host-smoke-20261011.json` records disposable host-child calls. Host `RLIMIT_NICE` was 0/0: 0→5 succeeded, native-thread and exec-child inheritance was 5, restoration failed with EACCES (13), and the parent stayed at 0. SCHED_BATCH→SCHED_OTHER succeeded in that child. This validates the need for a restore probe; it does not model Android 13's limit of 40.

`linux-fair-share-host-fixture-20261011.json` records six short trials with two CPU workers pinned to one allowed CPU. Equal nice yielded foreground shares 49.96–50.09%; weighting the other worker at +5 yielded 75.19–75.28%. The parent priority was unchanged. Host autogroup metadata was unavailable. These are synthetic scheduler CPU shares, not Game, Wine/FEX, Android, preparation latency, GPU duration or FPS. The parent's separate frame-jitter experiment supplies an additional host mechanism check; it also remains a host result.

## Measurements that select the next change

Keep the existing GPU mode, visual settings, 800×600 selection, fan and charging state. A one-action cold test must include click → prepare → first completed tick → exact native protocol readiness → native transfer → exact arrival → fresh display/input gates. Keep warmed return time separate. Preserve timeout/save/export rules and include failed or interrupted preparation.

| Resource question | Useful bounded observations | Interpretation limit |
| --- | --- | --- |
| CPU load versus scheduling contention | Exact destination PID/TID CPU tick deltas; Game CPU/runqueue-wait deltas if safely readable; `schedstat`; group membership; phase timestamps | CPU seconds differ from wall time. Missing/disabled scheduler stats must be explicit. |
| Storage versus cached file activity | Per-role `io` deltas for `read_bytes` and `rchar`; major/minor faults; readable IO PSI totals | `rchar` is logical traffic, not storage bytes. System iowait alone is unreliable. Page-cache reads may incur CPU/PRoot cost without storage IO. |
| Duplicated memory or reclaim | Sparse target RSS, optional permitted PSS/private dirty, app/PG memory, live peer count, available memory, memory PSI/swap | Summed Wine RSS can double-count shared file pages and excludes app/PG/GPU allocations. PSS sampling can be costly and may be unavailable. |
| Observer overhead | Sampler wall/CPU cost, bounded console growth, native-log read metrics | The existing console/log observers can themselves consume CPU; avoid new full-tree scans. |
| Thermal/presentation versus queue/scene work | Existing native render observations, Show FPS/dips, thermal status and comparable physical conditions | Renderer wall time includes CPU, submission, waits and presentation; it is not pure GPU duration. Thermal headroom is a slow system estimate, not raw GPU temperature. |

Primary metric documentation:

- [Kernel proc counters and PSS](https://www.kernel.org/doc/html/latest/filesystems/proc.html)
- [Scheduler CPU and runqueue counters](https://www.kernel.org/doc/html/latest/scheduler/sched-stats.html)
- [Pressure stall information](https://www.kernel.org/doc/html/latest/accounting/psi.html)
- [Cgroup memory throttling/reclaim limits](https://www.kernel.org/doc/html/latest/admin-guide/cgroup-v2.html)
- [Android low-memory pressure behavior](https://source.android.com/docs/core/perf/lmkd)
- [Android own-process memory information](https://developer.android.com/reference/android/os/Debug.MemoryInfo)
- [Android process-memory sampling limits](https://developer.android.com/reference/android/app/ActivityManager)
- [Android thermal APIs](https://developer.android.com/reference/android/os/PowerManager)

## Cache claim correction and future native work

The native `ParserLoadFiles` message saying it is parsing from a bin is printed before locating and validating that bin. It is not proof that the binary cache was consumed. In development mode `ParserIsPersistNewer` can traverse the source tree and compare file dates; later failure can fall back to text. Production mode avoids those date checks but also refuses text fallback and clears/fails missing or invalid persisted data. Therefore a broad production flag is not a safe performance switch.

The parent measured a .25 FX log interval of 34.753 s, but available log boundaries do not partition cache validation, deserialization, postprocessing or text fallback. `cacheRelevantFolders` currently covers Defs and animations but omits FX. However, `fileScanAllDataDirs` requests that top-level folder tree itself before walking it in the normal dynamic-cache path. Simply adding FX to initial folder caching may move the same work earlier rather than remove it. `FileListFind` also already uses binary search despite its older linear-search comment. Neither a folder-prefetch nor a replacement lookup algorithm has a demonstrated benefit here. First instrument parser/cache phases; any resulting narrow native change requires newly qualified server provenance and is outside .27. The host companion checkout's 61,854 FX files are not a measured device-runtime inventory.

- [Native ParserLoadFiles and persist freshness checks](https://github.com/Russianranger/coh-android/blob/2518f5df4b3b1907a70c0d72b7ac4a07be8a24c4/upstream/ouroboros/libs/UtilitiesLib/src/utils/textparser.c)
- [Native relevant-folder cache setup](https://github.com/Russianranger/coh-android/blob/2518f5df4b3b1907a70c0d72b7ac4a07be8a24c4/upstream/ouroboros/Common/gameComm/initCommon.c)
- [Native directory walker and folder-tree request](https://github.com/Russianranger/coh-android/blob/2518f5df4b3b1907a70c0d72b7ac4a07be8a24c4/upstream/ouroboros/libs/UtilitiesLib/src/utils/fileutil.c)
- [Native existing file-list binary search](https://github.com/Russianranger/coh-android/blob/2518f5df4b3b1907a70c0d72b7ac4a07be8a24c4/upstream/ouroboros/libs/UtilitiesLib/src/utils/structInternals.c)

Future multi-city work should keep a bounded active+pending process budget and qualify origin retirement or true empty-instance quiescence with DB/network liveness. Shared-definition memory may amortize private parsing/memory only after its native correctness constraints are proved. Neither broad prefetching, KSM/THP tuning, TSR warmers nor a purported unimplemented FEX persistent cache is a demonstrated low-risk fix.

## Additional controlled work and selected implementation

A host contention fixture used three CPU workers on one core and a periodic
30 Hz foreground task with 5 ms work. Two trials per policy ran for five seconds
each in normal, nice+5, batch, batch, nice+5, normal order. Normal policy had
9.027/9.037 ms p95 foreground lateness, nice+5 had 4.011/3.653 ms, and batch had
8.793/8.832 ms. Background work counts remained similar. This only demonstrates
a Linux scheduling mechanism; it neither predicts Thor FPS nor establishes a
faster destination load. Host RLIMIT_NICE was zero and only disposable workers
were lowered. Parent affinity was restored.

The appended-console fixture uses the actual 133,648-byte .25 initial MapServer
console over 600 polls: old repeated decoding touches 80,188,800 bytes; the new
scanner touches 171,984 bytes including overlap. Host wall times were about
0.335 s and 0.00132 s. This removes redundant observation work; those values are
not Android timings and do not explain a minutes-long preparation by themselves.

The available .25 initial Atlas startup stage lasted 236.613 s. Its log boundaries
include 34.753 s for FX, about 34.274 s for story, 21.66 s map loading, 2.52 s
beacons and 3.48 s collision. These boundaries can nest and are not an additive
profile. They describe initial .25 startup, not the unavailable .26 preparation
report. Initial server staging/beacon generation is also separate from a second
MapServer using the same staged runtime.

Selected for .27: incremental console scanning; conditional, exactly owned and
restored destination nice+5; bounded native stage/resource observations; and
one-action travel timing from tap through fresh usable arrival. Native binaries,
prepared cache archives, runtime engine and graphical features remain unchanged.
The priority change has no explicit IO-priority setting, but some Linux storage
schedulers derive default IO priority from nice. It may extend preparation;
judge it using both playable FPS and complete loading time.

Later FEX releases document disk-cache and memory work, including
[2609 disk caching](https://fex-emu.com/FEX-2609/) and
[2604 memory changes](https://fex-emu.com/FEX-2604/). These capabilities must not
be assumed present in the pinned Windows module. A runtime upgrade needs its own
qualification and is deferred. No visual reduction, asset reimport, prewarm that
hides loading, broad production-mode switch or native rebuild was selected.

## Shared-service and memory gaps

Game uses its separate client working tree; the two MapServers share a private
server runtime. Mutable bin/geobin files are copied into separate regular files,
so a second server's cache writes cannot be assumed to notify Game through a
shared writable cache. Native directory monitors can still submit work to the
shared wineserver. The pinned [Wine directory change handler](https://github.com/wine-mirror/wine/blob/b073859675060c9211fcbccfd90e4e87520dc2c2/server/change.c)
deduplicates watched inodes and combines filters; a second process does not
automatically double the entire kernel watch tree. Shared-service contention is
a hypothesis, not a measured cause of the user's preparation regression.

The new destination sampler does not measure shared-wineserver, PostgreSQL, app
or GPU cost. Although another diagnostic has a Wine memory sampler, the actual
character-reopen flow and supplied .25 report do not contain that series. A
later trace may need sparse safely owned per-role CPU/IO observations and small
cache metadata snapshots. Avoid continuous full-tree scans, heavy PSS polling
or verbose syscall tracing during the comparable gameplay test.

On heterogeneous Arm devices, CPU capacity, energy-aware scheduling and clamps
also affect placement and frequency. Host nice shares are not promised Thor
allocations. The retained native `-donotautogroup` switch controls COH world
grouping, not Linux autogroups. CPU affinity, frequency/governor, clamps, IO
priority and kernel memory settings are not changed in this pass.

Native directory notifications exclude LAST_ACCESS, so ordinary immutable reads
are not evidence of Game change callbacks. The retained `idleExitTimeout 0`
keeps the peer available for a warm return. Enabling automatic exit would also
require a reviewed map-retirement state machine: the current health guard
correctly treats an unexpected ready-peer exit as failure.
