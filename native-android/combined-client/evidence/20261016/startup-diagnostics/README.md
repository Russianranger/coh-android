# Read-only startup continuation, 2026-10-16

Worker F began at `cda93d96f8696e6a0f2ec6940a0c96e5b852f281` in its own
worktree. Changes are confined to offline tools and this evidence directory.
No guest helper, server, database, profile, cache, workflow, accepted APK or
other-agent module changes. This work creates no new device-test requirement.

## Accepted observations, with complete session attribution

`thor-017-resources.json` reuses the existing bounded ZIP parser and exact
current/historical session matching. The input is the already accepted final
0.1.7 export, not a new execution. Current and historical reports stay separate.

| Attempt | Readiness | DB boundary | Atlas boundary | Preparation classification |
| --- | ---: | ---: | ---: | --- |
| Current 0.1.7, code 8 | 387,340 ms | 70,678 ms | 271,736 ms | Warm schema restore observed |
| Historical 0.1.6, code 7 | 392,192 ms | 69,787 ms | 280,303 ms | Warm schema restore observed |
| Historical 0.1.4, code 5 | 800,298 ms | 550,903 ms | 205,644 ms | Cold mirror observed |

The final 0.1.7 export supplies the matching **historical** 0.1.6 guest receipt,
which was absent from its earlier live export. It now supports that historical
warm classification; it does not retroactively turn the earlier incomplete
export into proof. These different versions/attempts are observational, not a
matched speed experiment. The 4,852 ms readiness difference is not attributed
to a code optimization.

DB plus Atlas boundaries occupy 342,414 ms, **88.4014%** of current readiness.
They include preparation and readiness waits; they are not native CPU profiles.
Current internal preparation includes cache checkout 5.551716 s, schema restore
0.183016 s, definition cache handling 2.178455 s, animation handling 3.199829 s,
and beacon handling 24.258214 s. These internal phases are nested within startup;
never add them again to the top-level boundary total.

Current required-geometry evidence explicitly records verified reuse of 406
files, no worker invocation, and 1.310 s elapsed before PostgreSQL/Wine. The
`warm_schema_restore` branch in original `prepare_atlas_data` is executed only
following successful `ServerDataCache.checkout`. This proves the warm data-tree
branch; the export does not carry its individual validation counts/refusal
history. It also does **not** carry `prepared_server_caches` or
`atlas_beacon_graph` results. Therefore neither the 2.178455 s nor the 24.258214 s
phase establishes definition-cache consumption, beacon reuse, archive decoding
or fallback. All missing statuses and counters remain unknown/null.

## Existing cache behavior and missing visibility

The exact audited donor sources match the source tree at the worker checkpoint.
Hashes are in `qualification.json`; the recovered donor copies were also
byte-compared. Important already-implemented behavior:

- `character_server_data_cache.ServerDataCache.checkout` admits only a closed,
  owner-free matching generation, validates immutable directory identity and
  anchors plus private-file bounds, then changes ownership before renaming.
  Refused generations are preserved. Up to 16 cache generations are bounded.
- `verify` already uses one current no-follow metadata query per directory.
  Changed-parent validation is bounded and verifies exact child layout.
  Repeating this optimization or creating another cache is unwarranted.
- `atlas_beacon_package.install` already has `reused_verified_graph`: a bounded
  single input inventory/fingerprint walk, original receipt/manifest/profile,
  graph fingerprints and exact MapServer identity. This path decodes no archive
  and hashes no input payload bytes. The cold path fully checks source inputs
  and payload hashes; source-qualified shared input proofs may reduce repeats.
- `server_cache_package.install` preserves existing private native caches and
  installs only missing exact donor entries. A successfully prepared cache is
  not proof that the native loader consumed it. Fallback keeps normal loading.
- `server_runtime.main` copies geometry, phase durations and readiness into the
  final report, but omits the detailed creation-report cache records. It is this
  export boundary, rather than missing cache implementations, that blocks
  diagnosis of the remaining 24-second beacon phase.

`projected_caches` is a pure candidate projection of the **existing original
creation-report** field names. It allowlists numeric counters and enum statuses,
normalizes selected fixed refusal reasons, and drops paths, identities and raw
exceptions. This does not install a producer or pretend omitted fields exist.
A coordinator-owned, separately qualified runtime addition could invoke it (or
an equivalent pinned implementation) at the existing report boundary. That
change must preserve current receipt/session ownership and avoid any added
inventory/hash pass. This continuation does not change that boundary.

## Memory and resources

The accepted current attempt has **466** valid samples, zero invalid samples,
zero pressure samples and no pressure-stop request. Minimum observed system
headroom is 7,997,022,208 bytes; minimum Java headroom is 213,160,432 bytes.
These are sampled observations, not a guarantee against transient pressure.

All 36 final process captures are closed with zero overflow. Their recorded
output totals **63,501 bytes**, largest 36,503 bytes. Final retained bytes are
not a whole-process memory measurement or a simultaneous output high-water
measurement. The source's 512 records × 2 MiB per-child theoretical bound is
still not an observed allocation. No deployed output-retention change is
justified by this export.

Self/reaped-child high-water RSS must not be added into a live process-tree
peak. Cgroup counters and guest PSS are unavailable. The existing 466 samples
cannot identify historical Android low-memory allocation causes. No new cause,
leak, concurrent process overlap or kill-prevention claim is made.

## Independent host experiment

`bench_startup_console.py` extracts and executes the exact unchanged original
`OwnedProcess.text` and `map_crash_observation` function ASTs from the pinned
source commit. Six append/UTF-8/crash-marker/overflow cases yield **51 exact
result comparisons** against an experimental unchanged-length memo. The
prototype retains only the bounded final observation, not another decoded
console. It re-runs the original function after every append.

Five repeats of 1,000 unchanged, noncrashing polls produced these medians on
this x86_64 host (`console-experiment.json` retains every measurement):

| Retained output | Original, 1,000 polls | Prototype, 1,000 polls |
| --- | ---: | ---: |
| 36,503 bytes, current largest capture | 146.088 ms | 0.077 ms |
| 65,536 bytes | 255.752 ms | 0.076 ms |
| 2,097,152 bytes, source bound | 7,849.588 ms | 0.078 ms |

This is a synthetic host microbenchmark, not ARM64/Wine/device startup data.
Even 1,000 polls at the observed 36,503-byte size cost about 0.146 s here; it
cannot explain minutes of startup. Production reader-race/lifetime behavior,
non-append resets and Android timings are not qualified. The prototype is not
imported by runtime or ready for deployment. Highest possible output-size
results are not representative of the accepted device capture.

## Ranked next work

Savings below are investigation budgets/ceilings, **not forecasts or measured
improvements**. No candidate bypasses source validation or changes persistence.

| Rank | Candidate | Potential time / evidence | RAM cost | Stability risk / complexity | Required independent gate |
| --- | --- | --- | --- | --- | --- |
| 1 | Export existing numeric cache/progress observations at the current session report boundary | No direct savings; resolves whether part of 271.736 s Atlas / 70.678 s DB is actually fallback | Small bounded counters; no extra scan | Low / small | Session binding, allowlist, report bound and unchanged runtime behavior |
| 2 | Profile native Atlas loader/progress substages, retaining tick and protocol readiness gates | Largest observed stage 271.736 s; savings unknown until native substage evidence exists | Bounded phase counters | Medium / medium | Same installed native binary, progress timestamps and cache-consumer proof; disposable measurement environment |
| 3 | Separate DB native initialization from its nested data/asset preparation | 70.678 s boundary; internal phases sum 36.930 s, not an independently measured remainder | Bounded phase counters | Low for observation, medium for later changes / medium | Measure exact nested intervals and waits; preserve SQL/schema/persistence checks |
| 4 | Audit existing beacon reuse and immutable validation when receipt is visible | 24.258 s phase ceiling; actual reuse/fallback and hash/I/O fraction currently unknown | Reuse existing counters; no new cache | Medium / medium | Report graph status, files checked, payload bytes hashed, archive decoding; only optimize a demonstrated repeat |
| 5 | Audit warm data checkout directory/anchor work | Entire checkout is 5.552 s; current one-stat optimization already exists | Existing bounded inventory | Medium / medium | Numeric changed-parent/private/anchor counts, same identities and before/after integrity tests |
| 6 | Prototype unchanged-console observation memo | Host ~0.146 s per 1,000 polls at current largest output; device savings unknown | One bounded observation | Low-to-medium / small | Concurrent reader/overflow/cancellation parity, then repeatable device evidence; no runtime edit yet |
| 7 | Measure aggregate owned-process RSS/PSS and output retention | No demonstrated startup savings or allocation failure; identifies actual memory overlap | Bounded sampler only | Medium / medium | Verify owned process identity, timestamps, process-exit correlation and access; never export command lines/environments |

Do not spend the next cycle optimizing the already 0.183 s warm schema restore.
Sub-minute readiness requires evidence-driven reductions in native DB/Atlas
stages; shaving current external preparation alone cannot establish that goal.
Do not delete accepted caches to manufacture a cold test. Future normal
consolidated device runs should retain final JSON/ZIP after clean Stop so the
same session's preparation receipts are available.

## Reproduction and qualification

```sh
python3 -m unittest discover -s native-android/combined-client/diagnostics/continuation-20261016 -p 'test_*.py' -v
python3 -m unittest discover -s native-android/combined-client/tools -p 'test_startup_resources.py' -v
python3 native-android/combined-client/tools/analyze_startup_resources.py /path/to/accepted-export.zip
python3 native-android/combined-client/tools/bench_startup_console.py --source-root /path/to/repository
```

26 unchanged baseline tests and 15 addition tests passed. Tests cover stale
sessions, cross-version history, unknown cache receipts, fixed reason mapping,
private-value redaction, malformed elapsed/count values, output bounds,
nonmutating analysis and stage-boundary arithmetic. The existing parser keeps
archive/member/decompression/JSON bounds and CRC/privacy controls.

Qualification status: implemented and host/source qualified **only for this
offline tool scope**. No new Android ARM64 binary, emulator execution, sanitizer
run, physical acceptance or server interoperability is claimed. Python offline
logic does not require a native sanitizer or APK build. All accepted runtime
artifacts remain untouched. Rollback removes only these three new tools and
this evidence directory.
