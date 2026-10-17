# Independent recovery qualification and owned-memory diagnostic

Pinned recovery source `4f6fe92107a10323a90123c6856de578943300e2`.
Only this directory changes. Accepted APKs, server/profile state, production
runtime, shared build files and original worktrees remain unchanged.

## Verified existing capture, without recapture

`capture-review.json` independently reruns the existing exact retained-artifact
verifier over both immutable archives. Every ZIP member CRC is checked, along
with archive digests, compiled PE, source/run binding, source blob hashes,
catalog/snapshot hashes, cleanup assertions and identical release/ASan/UBSan
diagnostic results. Its 16 existing malformed/provenance/authority controls pass.
There is no new server execution or native decoder rerun.

The authentic observations remain 33 root matrices, seven distinct external
`pre_alloc` futures and exactly one root-reachable future,
`_mmayhem_curtain_8_01c`. Both CRCs match. A captured source snapshot does not
admit a live GROUPS transaction, resources, actor or renderer world.

## Concrete next startup diagnostics

`startup-projection-gap.json` pins the exact source files and identifies the
existing cache counters lost at the Combined final report boundary.
`LocalCharacterServer.prepare_atlas_data` already preserves beacon, definition
and data-cache receipts in `creation_report`. `server_runtime.main` exports
only `server_preparation_phase_seconds` from that structure. The safest next
coordinator-owned change is an allowlisted scalar projection under the original
receipt root names in that same final-report owner block. Existing offline
readers can consume it without another decode, hash, inventory walk or runtime
startup change. Do not export the entire creation report: it includes private
paths and unrelated state. Fixed-status allowlists and scalar interpretation
already exist in `tools/analyze_startup_resources.py:projected_caches`.

This can distinguish actual warm hits from cold archive validation with zero
graph writes, and count reused versus rehashed bytes. Current producer receipts
still lack separate inventory/hash/decode/write timings and explicit beacon
warm-marker refusal codes. Those require separately reviewed instrumentation;
phase duration alone cannot supply them. Atlas remains the largest accepted
startup interval; schema restore at 0.183 seconds remains a low priority.

## New opt-in memory measurement primitive

`sample_owned_memory.py` adds a one-shot read-only `/proc` observation for an
explicit PID/start-ticks pair. It scans at most 8,192 PIDs, follows at most 64
descendants, checks same real/effective/saved/filesystem UID and rechecks each
selected PID/start-time/parent identity before and after memory reads. Reuse,
reparent, missing RSS and oversized files refuse the sample. It does not launch
or signal processes, run a timer or read command lines/accounts/environment.
The CLI emits a fixed refusal instead of raw path-bearing OS errors.

RSS sums can count shared pages repeatedly. PSS is returned only when available
for every enumerated selected process. Sequential `/proc` observations can miss
short-lived children and concurrent membership changes: neither RSS nor PSS is
an atomic tree peak, whole Android memory measurement or established overlap.
This diagnostic needs explicit integration into a future justified measurement
run; it is not wired into startup and establishes no performance improvement.

Fourteen fixture controls pass, covering ownership/reuse/reparent, unavailable
and duplicate PSS, missing RSS, file/process bounds, read-only behavior and
private-field omission. A controlled self-owned host child was sampled and
reaped, recorded in `owned-memory-host-probe.json`; no game server/device was
used. This environment supplies RSS but no PSS for that probe, correctly leaving
the PSS aggregate null. The host number is not evidence about Thor memory.

Run the one-shot tool only with a previously observed owned root identity:

```sh
python3 sample_owned_memory.py --pid OWNED_PID --start-ticks OBSERVED_START_TICKS
```

## Independent A/B reviews

`independent-ab-review.json` binds exact source hashes. A's single-read frozen
preparation at `8492b1d43b5910a8ca77b2940d0489c64c850c26` retains the same
admitted bytes, cannot reopen a changed archive, keeps detached map identity and
does not grant publication. Its three preparation tests pass independently.

B's witness API at `fe31a2a4e7566edf5625769122618b3265377354` has bounded BFS,
one-time visitation, disjoint workspace fields, depth-limited output arrays,
transactional outputs and no allocation. Native modes reuse B's qualification;
F performed source review only. At F's request B explicitly documented the
additional 12-bytes-per-node scratch and stack/output reservation separately
from the build-only graph memory report in `88785554293e462300d942065dab3a42b70d5257`.

## Environment and reproduction

`environment.json` records Python/GCC/Java availability. Clang, CMake, Ninja,
adb and emulator are unavailable on PATH. A bounded same-UID `/proc` inventory
observed no compiler, server or emulator processes; visibility into other chats
is not established and no process was interrupted. `ps` itself fails in this
environment, so the inventory used read-only `/proc` instead.

```sh
python3 -m unittest discover -s native-android/combined-client/diagnostics/recovery-20261017-primary-f -p 'test_*.py' -v
python3 -m unittest discover -s native-android/combined-client/diagnostics/recovery-20261017 -p 'test_*.py' -v
python3 native-android/combined-client/diagnostics/recovery-20261017/verify_capture.py native-android/corpus/server-catalog/runtime-snapshot-38977202310 .
```

Qualification: offline host Python and independent source review. No new native
code, sanitizer rerun, Android build/emulator/device execution, encrypted login,
physical startup improvement or live world acceptance is claimed.
