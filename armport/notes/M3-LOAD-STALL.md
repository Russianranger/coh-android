# M3 zone-load investigation

2026-10-23. M3 remains incomplete; this is a diagnostic change, not a fix or
a claim that Atlas renders.

## Observed failure

Run [39973792458](https://github.com/Russianranger/coh-android/actions/runs/39973792458),
commit `748504dcbcc004f60925a33f0895da83bc29f1e1`, `server-run`:

- `ci_results.py --run 39973792458 --job server-run --grep verdict "guest result"`
  reports failure: `ARM64 client did not stay connected on Atlas`.
- The guest record shows map 1 connected at `2026-10-23T15:59:48Z`, then
  `still_connected: false`. The exported screen is still the white loading
  screen. It is not the required Atlas screenshot.
- Unlike the previous environment, the GitHub connector can retrieve job
  logs and artifacts here. Artifact `12515109319` (`armport-m3-evidence`)
  was downloaded and verified against its API digest:
  `5977e8ddce2be82ce2e78a6d7ac5e277642ab279708e8fa8ba10fdc983bf9046`.
- Its `armport_stdio.txt` is 1,990,994 bytes. After the MapServer connection
  line it contains missing geometry, group renaming and autogroup output.
  That does not establish which call is stalled or whether it is still
  making progress. The last partial line is `Cant find ro`.

## Diagnostic change

Patch 0048 is exported by `patchwork.py`. With `ARMPORT_STDIO_LOG` set on
ARM64/mingw it logs timestamps around the original scene/entity receive
calls, group-file loading, map finalization and texture/collision work. It
does not change any packet contents, timeout, loading or success behavior.

The host records log growth during the existing wait. At most two stack
samples (after 120 and 600 seconds) target only a same-user process with an
exact mapping of this run's `CityOfHeroes.exe`. Each debugger invocation
has a 15-second timeout and a five-second kill grace. The debugger pauses
the client briefly; samples are diagnostic, not a performance benchmark.
No server process or network-isolation setting is changed.

A separate workflow step exports the complete loading result and bounded
trace/stack summaries. The original report truncated the status JSON at
1,500 characters, before the loading fields, and exhausted its annotation
budget before some server logs. Full traces remain in the evidence artifact.

## Local validation before push

- `python3 armport/tests/test_m3_diagnostics.py`: 3 tests passed (exact
  executable selection, result retention despite socket/asset noise,
  missing evidence stays unknown).
- `python3 -m py_compile` on the four changed Python modules: passed.
- llvm-mingw 20250910, Release compile with the repository toolchain and
  `ninja -j2`: `clientcomm.c`, `groupnetrecv.c` and `groupfileload.c` passed.
  `file` identifies all three outputs as Aarch64 COFF objects. This is a
  compile check; runtime qualification must come from the new CI run.
- `git diff --numstat -- upstream`: empty.

Next: inspect the new run's zone stages, log-growth samples and symbolized
stacks before changing loader behavior. The saved packet replay remains
blocked on its two exact `.bin` inputs and reviewer agreement on the method
(HANDOFF section 5). No M3 pass, APK, release or merge is authorized by this
diagnostic result alone.
