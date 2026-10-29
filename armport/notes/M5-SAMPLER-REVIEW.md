# Sampler review fixes and launch evidence

Review: [Claude 5692088051](https://github.com/Russianranger/coh-android/pull/8#pullrequestreview-5692088051).
This revision is based on `dd9d755bdfd5914a85bb42144ac3ee4bbaa4852b` and is separate
from build 40805020119, which later failed before MSVC (see M5-WINDOWS-PRODUCER-FIX.md). No native patch or runtime pin changed.

## P2: process discovery must make progress

The original sampler advances scandir before inspecting ownership. If the new
zone PID consumes the last part of a sample window, its inspection fails but the
next sample begins after that PID. Replaying Claude's exact directory order with
the original dd9 source leaves MapServer 9008 absent for five windows. This is a
specific original-code negative reproduction, not an inferred timing problem.

A timed-out discovery PID now retains one retry. It gets the first inspection in
a fresh window, before known processes. A callback with no time left preserves
the pending retry. A PID too expensive even for an entire window cannot hold the
scan indefinitely: its one retry is consumed and directory discovery continues.
The PID is freshly authenticated on each attempt; incomplete rows never enter
CPU-delta history. Missing/partial samples still cannot become zero CPU values.

Deterministic tests cover target-first and Claude's costly-prefix order, timeout
after the second ownership read, an expired intermediate callback, and a single
process exceeding a whole window. Both directory orders find the target within
two usable windows with the fixed code.

## P3: bound observer state preparation

The sampler no longer deep-copies the cleanup receipt, all dead-leader/worker
sets or the complete 4,096-group lineage registry. It uses private scratch
receipts/census sets, scans at most 32 lineage keys per callback through a
resumable iterator, and copies only the exact PID/start-time group's cached proof
with deadline checks between workers. Optional future-cleanup proof collection
is suppressed in this private observer; authoritative cleanup state is unchanged.

Cached groups larger than 128 workers are omitted, not truncated into usable
proof. The omission is reported and fresh UID/token/namespace/start-time checks
can still provide a process total. Denied worker environments cannot be rescued
without their exact previously authenticated lineage. Before/after ownership and
PID/start-time checks remain required. Bounds are cooperative between operations;
this does not turn OS reads into hard realtime operations or measure device cost.

## Prior-zone retirement groundwork

`MapLaunchHistory` records at most five immutable owned-launcher descriptors.
Atlas-to-King's Row-to-Atlas resident travel reuses existing generations. A new
launcher reference gets a different generation even if Linux reuses its PID.
Actual native identity/readiness/save/exit proofs still come from existing
mechanisms; these observations cannot authorize a signal or cache return.

Existing full consoles remain. Additional unique generation files contain at
most 256 KiB of complete, redacted console lines each. Capture rebinding, overflow,
missing bytes, exhausted history and export errors are explicit. Multiline
secrets suppress the optional tail. Optional errors cannot change gameplay,
readiness, save or cleanup. A failed initial Atlas readiness check retains its
launch observation while preserving the original failure and not marking ready.
No retirement, restart API, native progress/control path or signal was added.

## Verification and next gate

`PATH=<javac module launcher>:$PATH ARMPORT_SERVER_BASELINE_ROOT=<pristine c86a579>
python3 -m unittest discover -s armport/tests -p 'test_*.py'`: **415 passed**.
This includes 42 telemetry tests and 14 launch-history tests. Separately, existing
saved-map startup 14, zoning 38 and monorail 9 tests pass; these 61 tests are now
also in the build workflow. Their saved-startup fixture explicitly models an
already admitted uninstrumented package, fixing six missing-fixture errors also
reproduced before the launch-history change. Production admission was not relaxed.

Build 40805020119 finished with a Windows host-import failure. After its host
correction, run the full serialized build (build_server_metrics=true), runtime (all three input IDs
from that build), and APK (m4_run_id from runtime, server_metrics=true) at the exact
revised SHA. Post exact artifacts/digests/provenance before Claude handoff review.
No new APK, Thor result, performance improvement or M5 acceptance is claimed.
