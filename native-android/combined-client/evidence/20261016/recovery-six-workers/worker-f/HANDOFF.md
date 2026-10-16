# Worker F: exact operation attribution and memory coverage

Recovered published baseline: `66146bbee161304ba4e4e14cbb53cba6958fb03b`.
The preceding F startup tools and prior worktree were inspected read-only.
This tranche changes only offline diagnostic tools, their tests and this
directory. Accepted server helpers, APKs, profiles, assets and gameplay sources
are unchanged. No server capture or new physical test was performed.

## Implemented and qualified

`analyze_startup_resources.py` now separates inventory/fingerprint walks, input
payload hashing, shared full-byte proof reuse, archive decoding, graph-payload
writes and the source-implied marker write. It preserves null for missing
observations. Fixed original shared-proof refusal enums and selected fixed
definition-cache refusal messages are allowlisted; private text remains omitted.
Contradictory successful-cache receipts fail closed. The existing receipt reader
also reports these operations for standalone map receipts and conventional guest
reports. This does not recover fields that Combined 0.1.7 never exported.

An independently counted seven-case fixture executes these unchanged original
functions from the exact hash-pinned source: `install`, `canonical`,
`VerifiedCollisionInputs`, `proof_owner_identity`, `eligible_shared_provider`,
`mint_shared_inputs`, and `reusable_shared_inputs`. Files, manifests, compatibility
admission adapters and clocks are disposable fixture inputs, **not real assets**.
The full production asset-admission pipeline and native loader are not executed.

| Original branch exercised | Input payload hashed | Graph writes | Archive opens | Marker writes |
| --- | ---: | ---: | ---: | ---: |
| Missing graph | 29 bytes | 2 | 1 | 1 |
| Valid warm marker | 0 | 0 | 0 | 0 |
| Existing graphs, missing marker | 29 bytes | 0 | 1 | 1 |
| Same-generation complete shared proof | 0 | 0 | 1 | 1 |
| Changed generation | 29 bytes | 0 | 1 | 1 |
| Missing generation contract | 29 bytes | 0 | 1 | 1 |
| One changed provider | 18 bytes | 0 | 1 | 1 |

This source comparison resolves an important attribution ambiguity: zero graph
files written does **not** prove a warm cache hit or no archive decoding. A
matching shared input proof also does not skip the cold-path archive decode.
Its fixed policy can describe a partially reusable set; the file/byte counters
determine how much was reused. Actual archive reads, input hash calls and writes
are counted separately from returned source counters.

The new resource analysis pairs only adjacent known entered/leaving records.
An unknown/missing/mismatched boundary breaks a pair; reversed clocks and more
than 32 retained records are rejected. It reports signed coordinator VmRSS deltas
and existing self/reaped-child high waters separately, without adding them.
The unchanged original `guest_resource_sample` function is separately executed
with distinct controlled self/children values to qualify that interpretation.
The Android timestamp conversion is source-audited, not newly emulator-executed.

## Reanalysis of the already accepted Thor report

Exact original input: 37,864-byte `COH-NativeCombined-1792163012982.zip`, SHA256
`e802501bce9738d538d8438cdcdbdb304810a9d7854d45a0dbb47a7188542b73`.
All four original member CRCs are read by the existing ZIP reader; original
input SHA256 is checked before and after. Only allowlisted sanitized output is
committed. Existing physical acceptance and historical-attempt separation remain.

Ready remains **387,340 ms**. Existing stage-entry boundaries remain DB
**70,678 ms** and Atlas **271,736 ms**. Their sum is **88.4014%** of readiness.
The separately paired resource-boundary timestamps below are slightly different
because each resource event is received separately; they do not replace the
accepted stage-entry timings.

| Resource observation | DB preparation/startup | Atlas startup |
| --- | ---: | ---: |
| Entered/leaving received interval | 70,671 ms | 271,718 ms |
| Coordinator VmRSS at entry | 49,520 KiB | 114,976 KiB |
| Coordinator VmRSS at exit | 114,976 KiB | 114,232 KiB |
| Endpoint VmRSS delta | +65,456 KiB | −744 KiB |
| Self high-water at exit | 305,192 KiB | 305,192 KiB |
| Reaped-child high-water at exit, separately | 305,192 KiB | 305,192 KiB |

There are 28 retained resource observations and 13 complete known stage pairs.
The longest adjacent gap is **271,718 ms**. These measurements describe the
Python coordinator, not MapServer or a concurrent server process tree. Self
high water is known, but its allocating operation is not. The DB interval
contains preparation phases and server wait; the larger self high-water value
cannot be attributed specifically to beacon decoding from these records.
The near-flat coordinator Atlas endpoint RSS cannot establish flat MapServer
memory. Process records contain durations, not a shared process start/end
timeline; they cannot recover process overlap. Cgroup/PSS and whole Android plus
server overlap remain unmeasured.

The existing 466 system/Java observations still show zero pressure samples.
Warm data checkout and 406-file geometry reuse remain accepted. Beacon and
definition-cache receipts remain absent; the 24.258214-second beacon phase does
not reveal a hit, refusal, hashing fraction, archive decode or write count.
Historical low-memory exits remain unattributed. No leak, allocation-failure
cause, whole-process peak, speedup or kill prevention is claimed.

## Benchmark, bounds and reproducibility

`startup_bench_resources.py` measures bounded offline archive read, parsing,
analysis and JSON encoding only. Five repeats of ten analyses of this exact
input, with `tracemalloc` enabled, produced median **18.736 ms** per analysis
and maximum **16,809,154 traced Python bytes**. Timing includes tracing overhead;
it is not device startup timing or whole-process RSS. The existing reader's
16 MiB bounded read accounts for its temporary input allowance even for a small
ZIP. No production memory optimization follows from this host benchmark.
Every repetition checks identical input provenance and deterministic output.
Repeats are capped at nine and iterations at 100. Full measurements are retained
in `analyzer-benchmark.json`; the previous console experiment remains unchanged.

From the repository root:

```sh
python3 -m unittest discover -s native-android/combined-client/diagnostics/continuation-20261016 -p 'test_*.py' -v
python3 -m unittest discover -s native-android/combined-client/tools -p 'test_startup_resources.py' -v
python3 -m unittest discover -s native-android/combined-client/tools -p 'test_startup_receipts.py' -v
python3 native-android/combined-client/tools/analyze_startup_resources.py /path/to/accepted-export.zip
python3 native-android/combined-client/tools/startup_bench_resources.py /path/to/accepted-export.zip
```

The unchanged historical source object `cda93d96f8696e6a0f2ec6940a0c96e5b852f281`
must be available for original-function tests, as required by the previously
qualified receipt-reader tests. Its audited source bytes still match baseline
66146bbee. Source-function hashes and fixture results are retained in
`original-operation-oracles.json`.

## Ranked remaining optimization work

1. At the **next justified Combined successor**, export existing bounded cache
   counters and fixed statuses at the coordinator-owned final report boundary.
   Preserve session ownership, output bounds and redaction; do no new scan or
   hash pass. This is the lowest-risk prerequisite for diagnosing the current
   24.258214-second beacon phase. It yields visibility, not direct savings.
2. Add bounded native Atlas stage/progress timing in a disposable measurement
   run while retaining exact binary/cache identities and protocol readiness.
   Atlas remains the largest observed interval. Distinguish loader, cache
   acceptance and world preparation; expected savings are unknown.
3. Correlate the DB interval with existing nested preparation checkpoints and
   a verified owned-process RSS/PSS timeline. This is where coordinator RSS
   changes in the accepted trace. Preserve SQL, cache, profile and cleanup gates;
   do not infer memory cause from two endpoints or add child/self high waters.
4. Only after the new cache receipt identifies a real repeated cold path,
   investigate why its marker/generation/provider proof was refused. Preserve
   all exact source checks. The source fixture proves that retained graph files
   alone cannot answer this. Decode or hashing savings remain unmeasured.
5. Preserve the prior console memo prototype as a lower-priority experiment;
   its existing host result cannot explain minutes of startup. The current
   warm schema restore is only 0.183016 seconds and is not a priority target.

Qualification level: implemented and host/source tested offline diagnostics.
28 resource tests, 23 receipt-reader tests and 26 original analyzer tests pass.
No new native code requires ASan/UBSan or an ABI rebuild. There is no new Android
binary, emulator run, physical acceptance, runtime optimization or authenticated
world-entry result. Rollback reverts only this tranche's diagnostic files and
evidence. Missing cache producer receipts and complete owned-process memory
coverage are explicit remaining dependencies.
