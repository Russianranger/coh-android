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

## Result of patch 0048

Run [40011219458](https://github.com/Russianranger/coh-android/actions/runs/40011219458),
head `ff50ae2db53a440667fe2cfa7b262f00ee0c6a74`, failed `server-run`.
Artifact `12531072842` SHA-256:
`8a4776f953dd53cb82e3244646e4a49527989cd0362213dfc9713aeae8478d6d`.

- `armport_stdio.txt` reaches `allents.done`, `allents.wait.done`,
  `geometry.wait`, then `textures.wait` at tick 3647932. It never reaches
  `textures.done`. Those markers bracket `texLoadQueueFinish()`.
- `login-driver.json` contains 49 equal stdio sizes (2,425,773 bytes),
  `world_rendered: false`, and the final guest reports disconnected.
- Both GDB samples attached and exited zero, but did not unwind to game
  frames. The debugger's “corrupt stack?” text is not proof of corruption.
  The main thread's Linux wait channel is `anon_pipe_read`.
- No specific failing wait or texture is established yet. Patch 0049 adds
  opt-in markers around the APC callback, queue critical section, foreground
  drain, uploads and load-screen update. It preserves the original wait,
  texture handling and success criteria. No synchronization fix is claimed.

## Recovered replay inputs

The original `COH-NativeCombined-1792606619522.zip` report was recovered.
`sha256sum` of the archive:
`623800b22640bb0f35a27bbf89bae04253c5acf9e1db10b0365084b0dd7def82`.
The following command output matches the identities in HANDOFF section 5:

```
37994 initial-replay.bin
cc949b01f5db6ff108efcf6afcbfe9567c432b4aa15f3a02c8f193e380cc7b39
74416 post-ready-replay.bin
f134c3c083e571b679ed6976bec36c672028854f4a48879cc0f2d47423db96a9
```

Missing files are no longer a blocker. Claude agreed to the original
receive-code method in PR #6 review 5635319013; see M3-REPLAY-PLAN.md.

Patch 0049 local validation: llvm-mingw 20250910 with the repository
Release toolchain, `ninja -j2 Game/CMakeFiles/Game.dir/src/render/tex.c.obj`
completed with exit 0 (eight existing warnings). `file` reports an Aarch64
COFF object; `git diff --numstat -- upstream` is empty. Runtime result is
pending the next CI run.

## Review follow-up (2026-10-23)

A search of the full 40011219458 client-output.txt finds only the caught
startup RPC_S_SERVER_UNAVAILABLE (0x6ba) exception; no subsequent access
violation or logged loader exception appears at the texture stall. This
does not prove an exception was impossible or supply a missing stack.

Run 40032719161 failed earlier in group loading, with Wine PC
0x6fffffdb7518 reading address 0x50 in thread 0x128. Its final marker is
groupfile.begin for office01/trays/halls/halls.txt; no texture-stall
conclusion can be drawn from that run. Evidence artifact 12539025345
SHA-256 d5cd00b8f6c175a6452527606efd5e4118125c14c38b250dba177a379912e177
was checked before inspection. Patch 0051 adds thread IDs to existing zone
markers; the bounded debugger now prints PC/LR and eight frame-chain levels.

Run 40040798938 libraries passed the host diagnostic suite and ARM64 worker
controls. `ci_results.py --run 40040798938 --job libraries --no-wait --grep
"ARM64 worker"` returns original dispatched=0, patched dispatched=1, and
4096 commands/replies in both notices. Rendering and receiver replay remain
unproved.
