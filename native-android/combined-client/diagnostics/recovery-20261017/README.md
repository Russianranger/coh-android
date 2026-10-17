# Independent retained capture audit

This evidence-only tool verifies the exact two artifacts from run 38977202310.
It reads all 46 ZIP members and their CRCs, binds the retained PE and 11 compiled
members to the source identity, checks 33 original source files directly from
Git revision `3e8b5c9f`, verifies 19 diagnostic log hashes, and compares capture,
cleanup, generation, source/run identity and all 3 native diagnostic receipts.
It never extracts or executes the PE and starts no service or emulator.

The captured result still has 33 verified roots, 7 authentic external objects,
15,352 reachable regular definitions and 1 reachable external object. Only
`_mmayhem_curtain_8_01c` is reachable. All 7 have no model, library path or
successful bounds lookup. This is not resource admission or live GROUPS authority.
All diagnostic modes retain false world/actor/assets/publication flags.

Archive admission is exact historical SHA256 and size, followed by declared
member-count/expanded-size bounds, path/duplicate rejection and reading every
member. All member hashes that have retained receipts are rechecked. The outer
SHA binds remaining members. The tool retains expanded bytes in host memory;
this is independent offline evidence inspection, not the native import's budget.
It does not reexecute native diagnostics or infer cleanup from source alone:
cleanup is the exact already captured receipt, tied to exact archive bytes.

Run from the repository root after recovering the retained corpus:

```sh
python3 native-android/combined-client/diagnostics/recovery-20261017/verify_capture.py native-android/corpus/server-catalog/runtime-snapshot-38977202310 .
python3 -m unittest discover -s native-android/combined-client/diagnostics/recovery-20261017 -v
```

For an external read-only retained corpus, set `COH_CAPTURE_CORPUS` for tests.
The checked-in `capture-audit.json` was generated against the surviving original
worker-f corpus without modifying that directory. 16 controls pass, including
payload and PE corruption, archive byte/size mismatch, cleanup/live-authority
claims, source-map changes, generation/identity mismatch, diagnostic-log changes
and disagreement between release/ASan/UBSan receipts. An initial test harness
repository-parent typo was corrected before qualification; no production file
was changed.

Native allocation accounting remains 16,791,741 named bytes, with 16,298,797 measured
native allocation peak. Neither number is process RSS, Android memory or GPU
memory. There is no new physical qualification or performance improvement.

## Startup priorities preserved from recovered evidence

The accepted warm readiness remains 387,340 ms: DB 70,678 ms, Atlas 271,736 ms.
These two stages represent 88.4014% of readiness. The 24.258214 s beacon phase
has no exported cache receipt. Existing source fixtures prove zero graph writes
cannot distinguish warm cache reuse from a cold archive decode, and shared proof
reuse can still open/decode the archive. No new capture is justified to guess.

1. At the next meaningful Combined successor, export already available bounded
   cache operation counters under the session report owner. No new hash/scan pass.
2. Measure native Atlas substage times and owned-process RSS/PSS with exact
   binary/cache identities, keeping existing readiness and cleanup policy.
3. Establish DB preparation and process overlap before attributing the historical
   coordinator +65,456 KiB endpoint change or 305,192 KiB self high-water.
4. Optimize only a demonstrated cache refusal/repeated operation. Warm schema
   restore 0.183016 s is not the priority target.

These are measured priorities and missing-observation dependencies. No shipping
startup, gameplay, server profile or accepted APK changes are included.
