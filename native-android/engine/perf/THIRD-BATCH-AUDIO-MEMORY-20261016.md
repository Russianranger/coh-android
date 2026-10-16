# Third batch F: recovered audio evidence and process-memory observation

Common pinned start: `58caf1d4ab3b39757190f194100ccbc697d57857`.
Implementation source revision: `af68933ffc` (full revision in the qualification
receipt). Exclusive edits are inside `native-android/engine/perf/`. Existing
audio, renderer, support application, workflows, server, session, accepted APKs,
and the primary agent's unpublished work were read-only. Worker A alone owns
application integration. No new gate is accepted by this module.

## Recovered work; no duplicate mixer or observer

The earlier mixer, AAudio lifecycle owner, music/ambient streaming, fixed-storage
performance observer, exact skin cache, moving-camera listener and actual support
counter bindings already exist. This batch verifies their exact source hashes
against the retained receipts before running the new qualification. It does not
repeat those implementations or replace their receipts.

| Existing evidence | Accepted scope retained |
| --- | --- |
| `engine/audio/lifecycle-host-proof.json` | 32-voice mixer; 120.001 **simulated** seconds; 434,784 configured allocation bytes; zero callback allocator calls; three authentic simultaneous clip voices; source gain/pan comparisons; 19 matched synthetic backend opens/closes and fault recovery |
| `engine/audio/android-integration/host-proof.json` | Bounded original Vorbis streaming; source Atlas Plaza music, steam ambience and headset clip; independent decode comparisons; 120 simulated seconds/291 loops/45 pause cycles with constant 461,146 tracked bytes and zero mock stream underruns |
| `engine/perf/evidence/bindings-qualification.json` | Actual camera listener source conventions; owner-generation counter deltas; explicit unknown versus measured zero; 53,090 checks and ARM64 library build |
| Recovered Support Client 0.2.0 code 200 artifact | 13 actual Android emulator scenarios; offline native UI, animation, keyboard, Home/resume, AAudio playback and Surface recreation. These are the earlier artifact's results, not execution of this new module. |

The recovered support artifact is source-bound to
`c14a831b55163dbcf2b3e63b4c52805785fceafa`. Its emulator summary SHA256 is
`1a1622212d9346e530ea3ea4ac74322435092df2f106d1975d141c0d86def6b9`;
final report SHA256 is
`40bc8868dfb7e08c76f021594029eefd9c1dde5cc18e157ae46a7641a3de60e1`.
The final report contains actual draw/upload/collision/cache/skinning counters;
RSS and PSS were explicitly unknown. Its final audio snapshot was running with
`diagnostics_valid=0`: cached stopped-backend values are not current callback
statistics. The zero recorded underruns therefore do not prove continuous
physical playback. Physical route changes, audibility, latency and endurance
still require the Thor test.

No new audio asset is required by the memory observer. Original audio lineage
remains Ouroboros `61bcde64ece0c45a1e3ba1c39f038b15dc6efd7d`; retained audio
receipts carry exact source bodies, codec pins and authentic asset identities.
No synthetic effect sound is represented as an authentic power sound. Worker D's
typed combat cues keep an unavailable original sound mapping explicit.

## New reusable observer

`coh_process_memory.{h,c}` closes the missing process-memory measurement path:

- A fixed `/proc/self/smaps_rollup` read supplies RSS and PSS when available.
- If rollup is denied, absent, oversized or malformed, `/proc/self/status`
  `VmRSS` may supply RSS only. This is the kernel's approximate resident count;
  it is labeled with its separate source. It never substitutes RSS for PSS.
- Known measured zero differs from unavailable. Each field exports its source,
  status and errno. Parser failures cannot publish partial or stale valid data.
- Reads are capped at 16,384 content bytes plus one overflow-detection byte,
  32 attempts per file including EINTR, and at most two fixed self-process files.
  Missing/denied files are not searched through other process paths. No full
  `smaps` scan, shell command, subprocess or heap-owned sample is introduced.
- All successful opens close exactly once, including failure paths. Linux close
  is never retried after EINTR, which avoids accidentally closing a reused fd.
- The caller receives an 80-byte copied snapshot with no pointers or hidden
  global state. The adapter has one 16,385-byte stack read buffer and calls no
  allocator directly. Formatting uses a bounded caller buffer on the export
  thread; 1,024 bytes safely covers the tested maximum report of 420 bytes.

The explicit byte/call limits do not bound kernel syscall wall time. Rollup can
scan mapping accounting inside the kernel. Sampling belongs on a low-frequency
control/export worker, never the audio callback, GL-frame or physics hot path.
Capture a monotonic sample time/age at that owner; do not imply a sample obtained
earlier is a fresh live value. Samples from different proc files are not atomic.
Android policy may prevent PSS collection; that is a truthful unavailable value,
not a reason to return guessed memory or fail rendering/audio.

## Application contract agreed with A

For the continuation APK, A uses a zero-handle JNI `processMemory()` call on its
dedicated Java report worker at roughly 1 Hz. That function samples and returns
JSON without touching a renderer/session/audio pointer. The immutable string and
timestamp cross to the report owner; the latest snapshot is exported separately
from existing observer gauges. This avoids adding a native owner lock or a race
with destruction, Surface recreation or the callback.

`coh_process_memory_apply(snapshot, bridge)` is provided for future native owner
integrations. Call only after copying to the serialized bridge owner. It applies
known fields only and validates all fields before mutating any gauge. A failed
sample leaves previous high-water/history gauges intact; export the latest
snapshot alongside them to expose missing or stale current measurements. A may
leave bridge RSS/PSS gauges unknown when its separate report observer measured
them; that states the two measurement paths accurately.

Only A changes support build sources, JNI/report export and scenario assertions.
Add `engine/perf/coh_process_memory.c` once and include its header. The standalone
perf CMake target already includes it. This does not change common/root build
files or any live protocol/session interface. GPU timing and real allocation
interception remain unknown; no query, readback, fence, `glFinish`, thermal guess
or synchronous GPU operation was added.

## New qualification

Run without changing old receipts:

```sh
python3 native-android/engine/perf/check_process_memory.py \
  --ndk /path/to/android-ndk \
  --output /tmp/process-memory-qualification.json
```

Committed receipt: `evidence/process-memory-qualification.json`.

| Stage | Result |
| --- | --- |
| Implemented | Pure bounded parser, fixed self-process reader, copied snapshot, explicit unknown/source/errno JSON, optional owner-serialized gauge application |
| Host/source qualified | 114,112 C checks; 4,096 parser property cases; 2,048 independent Python arbitrary-precision shuffled-key/parser/JSON cases; current Linux self-process sample |
| Negative/boundary tests | Duplicate/missing fields, NUL, signed/fractional/invalid-unit/overflow values, exact-limit/oversized files, short reads, interrupted/open/read/close failures, denied proc files, rejected partial snapshot, unknown versus measured zero, bounded JSON, historical gauge preservation |
| Host endurance | 10,000 synthetic mixed success/permission/IO/fallback cycles; every opened descriptor closed; no directly linked allocator calls; not wall-clock game endurance |
| ASan/UBSan | Passed; LeakSanitizer cannot inspect `/proc/PID/task` in this host, recorded explicitly. Allocator guard remains active. |
| Android built | ARM64 and x86_64 API26 shared libraries, strict warnings and no unresolved symbols; exact hashes and compiler recorded |
| Emulator | New integrated continuation APK qualification belongs to A/coordinator; not claimed here |
| Physical Thor | Pending actual returned report; no gate 43–45, 30 FPS, full-game RAM, battery/thermal or physical audio acceptance |

This observer is new OS telemetry, not a reconstructed game algorithm. Original
game comparison is therefore not applicable to the proc parser. Existing source
audio/perf behavior is protected by verifying unchanged module hashes against its
original-source receipts. The actual host sample is not an Android memory number
and must not be used as a game RAM budget.

## Consolidated physical checks and remaining work

Fold these into the coordinator's one support-APK test, preserving Session Client
0.3.0 and Combined Client packages/data:

1. Run the offline scene, rotate the camera around the spatial emitter, trigger
   available mock actions and verify music/ambience remain audible. Export one
   report once assets/audio have settled; RSS/PSS must be known with a source or
   carry an explicit unavailable status. Record sample age and never infer zero
   memory from a missing field.
2. Use Home/resume three times, recreate the Surface and test an available actual
   output-route change plus focus interruption. Confirm playback recovery without
   duplicate music or stuck mute. Capture a paused export so AAudio's joined
   callback/xrun/underrun data are valid, then resume and export again.
3. Exercise the bounded scene for 15 minutes with animation, movement, Near/Far
   changes and audio. Export start/end/paused diagnostics. Compare module bytes,
   RSS/PSS, cache counts, frame histogram and audio diagnostics within that
   explicitly bounded scene. Log audible glitches or rising memory. This is not
   full Atlas/Kings Row, representative live gameplay or thermal acceptance.

Remaining work includes real device audio routes/focus/latency, longer physical
render/audio endurance, broader original SFX mappings, actual allocation events,
supported nonblocking GPU timing, thermal measurements and larger representative
world/actor workloads. Existing exact skin-cache comparison evidence is retained;
it does not establish a Thor speedup. Do not add speculative timing waits or
replace unavailable values to make a report look complete.

## Rollback

First revert A's optional JNI/report/build references to this observer, then
revert this additive perf source/evidence commit set. Keep accepted APKs and all
old receipts. No game data, server process, history reset or branch rewrite is
involved. Safe promotion still requires the coordinator's fresh remote-head,
path-overlap and workflow-concurrency checks.
