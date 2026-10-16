# Existing startup receipt reader — offline follow-up

This follow-up adds `tools/read_startup_receipts.py` and
`tools/test_startup_receipts.py`. It reads existing evidence and changes no
runtime, launcher, private report writer, cache, profile, database or APK.

## Exact retained evidence and the Combined visibility blocker

The source audited at `cda93d96f8696e6a0f2ec6940a0c96e5b852f281` has these
existing paths/fields. Paths below describe original producer locations, not
files this tool creates on a device.

| Existing source | Retained file / field | What it proves, when matched |
| --- | --- | --- |
| `LocalCharacterServer.persist_startup_observation` | `<state>/map-startup-observation.json`, format 1 `maps` | Reported installed MapServer pin, beacon validation status/counters, preparation timestamps and sampled ready upper bound |
| Same original function | `<state>/latest-report.json`, `map_startup_observation` | Same observations in the conventional guest context; may contain other private context, which this reader drops |
| `LocalCharacterServer.collect` | `<capture>/map-startup-observation.json` | Final ordinary conventional collection of those map observations |
| `client_startup_diagnostic.persist_report` | `<state>/report.zip` → `latest-report.json` and `client-evidence/map-startup-observation.json` | Bounded conventional report and captured file packaging |
| Conventional `latest-report.json` | `character_creation` or `character_reopen` → `private_map_data.server_data_cache`, `prepared_server_caches`, `atlas_beacon_graph` | Existing data-checkout outcome/refusal and definition preparation/graph outcome; native cache consumption still needs separate proof |
| `diagnostic.Context` | `stages[].started_utc/finished_utc`; stdout JSON-line `type=stage`, `time_utc`, `status=running/passed` | Explicit observed UTC pairs only; unbound logs are never joined to a different session |
| `ServerDataCache` | `<owner-root>/character-server-data-<key>[-<session>]/cache.json` | Closed/checked-out ownership and validation inventory, **not** evidence of a later checkout hit or native BIN consumption; private marker is not consumed here |
| `atlas_beacon_package` | `<private-runtime>/data/server/atlas-beacon-installed.json` | Existing manifest/profile/input/graph fingerprint receipt; marker presence alone is not a current run's reuse outcome |
| `atlas_beacon_package` | `<worktree>/atlas-required-geometry-installed.json` | Required-geometry generation receipt; actual current reuse needs the session outcome |
| `server_cache_package` | Imported `server-caches.zip` / `server-cache-manifest.json` | Donor provenance/compatibility; installation or loader consumption is not established by archive presence |
| `game_map_progress` / `LocalCharacterServer` | `<private-runtime>/character-atlas-progress.bin` | Opt-in sequence/tick/stage publication; its raw 128-byte record has no elapsed clock and cannot alone reconstruct native phase durations |

**Combined deliberately disables the conventional observation writer:** its
`Server.persist_startup_observation()` override in
`native-android/combined-client/runtime/server_runtime.py` is a no-op, with a
comment explaining that private context must not be serialized. Its final
report retains curated geometry, phase durations, stage history and readiness,
but not the original detailed creation-report cache observations. Therefore
there is no hidden accepted-Combined `map-startup-observation.json` in the
provided export to recover. The privacy boundary remains intact.

A future coordinator-owned change could select bounded numeric/enumerated
fields at the existing curated boundary after independent qualification. This
work neither installs that change nor recommends re-enabling full private
context serialization. No new cache is indicated.

## What the reader does

- Accepts an existing JSON file, or explicitly selected ZIP member (up to one
  nested ZIP). It never extracts files or scans arbitrary device directories.
- Recognizes the existing standalone map receipt, conventional creation/reopen
  guest report, conventional `guest` wrapper and Combined final guest report.
  Nested character receipts must match the enclosing guest session. Raw session
  IDs, accounts, names, PIDs, private paths and exception text are not emitted.
- Distinguishes explicit data/graph `hit`, explicit refusal/fallback,
  definition `preserved`/`installed_missing`, graph `installed`, and `unknown`.
  Durations and marker presence never manufacture a hit.
- Preserves content SHA256/byte provenance at every selected archive level.
  Preserved MapServer pins are reported observations, not independently
  revalidated installed binaries. Wrapper presence does not confer Android or
  physical acceptance.
- Computes stage intervals only when both explicit UTC timestamps exist. UTC
  points are rounded individually to milliseconds, so differences can vary by
  1 ms from a separately rounded higher-precision elapsed value. Wall intervals
  are subject to wall-clock adjustment and are not native CPU profiler timings.
- Marks ready elapsed values from the original map observation as **sampled
  upper bounds with unbounded observer delay**, never exact readiness timings.
- Accepts original JSON-line stage events with `--json-lines`. Human console
  text, missing timestamp pairs and alleged textual cache hits remain unknown.
  Every new running event resets the candidate pair; failure/cancellation/result
  events clear it. Source running events may also be progress heartbeats, so
  these are explicitly **latest-running-to-passed segments**, never complete
  stage durations. Log events lack source session binding and are never merged
  with a receipt.

Bounds: outer ZIP 64 MiB (hashed in 1 MiB chunks), nested selected ZIP 32 MiB,
final JSON/log 2 MiB, 256 ZIP entries, 256 MiB aggregate declared uncompressed
content, two selected levels, 128 receipt stages, maps 1/5 only, 8,192 log lines,
16 KiB per line and 256 recognized events. ZIP paths, duplicates, links,
encryption, compression modes, selected sizes and CRCs are checked. Before
constructing `ZipFile`, an EOCD/central-header preflight caps central metadata
at 256 KiB and counts at most 256 actual headers, checks declared/actual
counts and exact directory bounds, and refuses ZIP64, multidisk archives,
embedded-NUL filenames and unsupported directory forms. A forged small EOCD
count cannot trigger allocation of an unbounded ZipInfo inventory. Input
identity/size/timestamps must remain stable while read. JSON duplicate keys,
nonfinite literals and structural bounds reuse the existing qualified parser;
numeric projections independently enforce finite bounded values.
Inputs outside these limits are refused rather than truncated or extracted.

## Available actual evidence

`combined-017-existing-receipt.json` comes from the already accepted archive
SHA256 `e802501bce9738d538d8438cdcdbdb304810a9d7854d45a0dbb47a7188542b73`,
selecting only `combined-server-latest-report.json`.

Its recorded guest UTC pairs give DB **70,563 ms** and Atlas **271,714 ms**.
These are distinct from the application-received boundary intervals of
**70,678 ms** and **271,736 ms** in the earlier analysis. They are not a new
startup measurement, code speedup or native substage breakdown.

All detailed cache-receipt outcomes remain `unknown` because those fields were
not exported. The independent phase field still explicitly reports
`warm_schema_restore`; the prior source audit supports the data-tree warm branch
from that phase. This reader intentionally keeps the stricter question of an
actually retained checkout/refusal receipt separate. No raw conventional
physical startup receipt was available for this follow-up; conventional reader
qualification uses the source-produced synthetic files described below.

## Source qualification and usage

Twenty-three tests passed after independent review corrections. Five exact unchanged producer methods were extracted from
SHA256-pinned source and executed in isolation:

- `LocalCharacterServer.record_startup_preparation`
- `LocalCharacterServer.persist_startup_observation`
- `Context.stage`
- `Context.passed`
- `Context.event`

The file fixture supplies deliberately fake nonexecutable MapServer bytes,
caller-provided graph status and a deterministic clock. It writes only to a
disposable temporary directory through the original persistence method. Thus
`original-producer-fixtures.json` qualifies source field/file handling and
redaction; **it is not an authentic cache hit or server execution**. Definition
hit/refusal cases are explicitly schema fixtures. Negative tests cover stale
sessions, missing/negative clocks, absent Combined details, malformed maps/JSON,
unsafe ZIP members, duplicates, symlinks, nested bounds and private-value leaks.
Review regression controls execute original stage-retry methods, reject pairing
across failed attempts, label repeated-running/heartbeat segments, exercise
interleaved stages, and prove ZIP64/multidisk/forged-count/directory-size/NUL
refusal occurs before the ZipFile constructor. In particular, running at 0 s,
failed at 5 s, retry at 10 s and passed at 15 s now produces only the 5 s retry
segment; it cannot report 15 s as the second attempt duration.

```sh
python3 -m unittest discover -s native-android/combined-client/tools -p 'test_startup_receipts.py' -v
python3 native-android/combined-client/tools/read_startup_receipts.py /path/to/Combined-export.zip --member combined-server-latest-report.json
python3 native-android/combined-client/tools/read_startup_receipts.py /path/to/report.zip --member client-evidence/map-startup-observation.json
python3 native-android/combined-client/tools/read_startup_receipts.py /path/to/report.zip --member latest-report.json
python3 native-android/combined-client/tools/read_startup_receipts.py /path/to/outer.zip --member report.zip --member latest-report.json
python3 native-android/combined-client/tools/read_startup_receipts.py /path/to/guest-stage.log --json-lines
```

The nested-member example requires those exact members actually to exist; the
tool does not guess outer export names. Native sanitizers/Android builds are
inapplicable to these offline Python additions. No new APK, physical acceptance,
real authentication, live world entry or device speedup is claimed. Rollback
removes the two new tools and this evidence directory.
