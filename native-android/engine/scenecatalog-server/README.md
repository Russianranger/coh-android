# Optional NONSHIPPING MapServer scene-catalog export

This isolated source overlay makes the source catalog producer callable at one
normal-map startup boundary: after `groupLoadMap` and `dbSetupMap`, before
`dbReadyForPlayers`. The source exporter and sink are appended as includes after
the unchanged original `groupnetsend.c`, in the same translation unit as static
`sendDef`. No source-network, session, persistence or update hook is added.

It is **not in the shipping runtime or standard build flow**. It does not change
an APK, import assets, run or deploy MapServer, exit the server, or promote a
scene to an authenticated/live world. The optional Windows compilation workflow
can establish compilation separately; local tests establish only the stated
host shim and staging behavior.

## Stage and verify

First use the existing `tools/prepare_map_startup_source.py` to create a private
MapServer source staging tree. This exporter refuses an original source tree,
aliases, links, hardlinked input files, repeated staging and existing overlays.
It requires the exact reconstructed `map_startup_certified_animation`
prerequisite receipt and inherited source/overlay hashes. The original
`groupnetsend.c` LF hash is pinned; startup anchors must occur exactly once.
The staging tree must also be private, exclusively owned and free of concurrent
mutation. Link/identity checks are preflights under that ownership contract,
not a defense for an attacker-writable staging tree.

```sh
python native-android/engine/scenecatalog-server/stage_export.py \
  --source-root . --already-staged /private/mapserver-source
python native-android/engine/scenecatalog-server/stage_export.py \
  --source-root . --already-staged /private/mapserver-source --verify
```

Windows staging paths work identically. The receipt is
`native-scene-catalog-server-build-input.json`, build role
`nonshipping_startup_native_scene_catalog_export`, target `MapServer` only.
`verify_staged(source_root, staged_root)` reconstructs and checks this receipt
after a compile, including original/inherited bytes, patched sources, both
includes, stager identity and the complete prerequisite receipt. Ship neither
this executable nor the exporter overlay through a normal release package.

## Explicit operator contract

The staged Win32 sink is silent and disabled unless
`COH_NATIVE_SCENE_CATALOG_OUTPUT` is set to an admitted drive-absolute output
filename and `COH_NATIVE_SCENE_CATALOG_GENERATION` is a nonzero unsigned 32-bit
decimal value. The generation is caller-owned asset identity, not proof of an
asset set or Map ID. No directories are created.

The operator must provide a **private, exclusively owned parent directory** and
exclusive, stable GroupInfo and property serialization for the complete call.
The startup boundary provides the intended owner context. Path checks reject
relative/device/UNC/ADS paths, DOS device names, dot aliases, overlong paths,
unavailable parents and observed directory reparse points. These checks do not
make an attacker-writable parent safe against filesystem races; establishing
private ownership is an explicit precondition.

The sink creates `<output>.partial` with `CREATE_NEW` and no sharing, caps emitted
output at **32 MiB**, then flushes and closes before rename without replacement.
An existing final or partial file is never overwritten or deleted. On failure,
it attempts to close its handle and delete only its own newly created partial;
OS cleanup failure is retained in numeric diagnostics. A destination created
during export prevents publication. The original trusted Packet allocator may
grow transiently before producer record admission. **The output cap is not a
hard heap/process peak-memory cap.**

Diagnostics use one fixed numeric line, with sink `status`:

| Status | Meaning |
| --- | --- |
| 1 | Published |
| 2 | Missing/invalid generation or overlong environment output |
| 3 | Unsafe path, unavailable/reparse parent or existing destination |
| 4 | Create-new partial refused |
| 5 | Producer, callback, byte limit or completion mismatch |
| 6 | Flush failed |
| 7 | Close failed |
| 8 | Rename without replacement failed |

Producer status, failure file/slot, counts and byte totals remain numeric. No
path, account, name, source record, packet data or OS error string is printed.
The producer API is `coh_source_catalog_export(output, context, generation,
report)`: zero succeeds, and each callback must consume/copy its span and return
exactly one. The sink keeps all bytes unpublished until complete success.

## Host qualification

```sh
python native-android/engine/scenecatalog-server/check.py \
  --source-root . --output out/scenecatalog-server-host.json --sanitize
```

The actual sink include runs against a local C WinAPI shim and mock producer in
strict C89 release, AddressSanitizer and UndefinedBehaviorSanitizer modes.
Cases cover default disablement, bad generations, path/parent refusals, exact
U32 generation, success, bounded output, producer/write/flush/close/rename and
cleanup failures, preexisting output/partial preservation and a destination
race. Stager tests cover source conservation, exact owner placement, prerequisite
binding, hash drift, linked/hardlinked/alias inputs, repeat refusal, preflight
side effects and post-build verification mutations. A separate non-Windows
compile/run verifies the sink's no-op branch. LeakSanitizer is not claimed.

These tests do not execute a real MapServer, Win32/Wine filesystem or live game
assets. Native catalog decoder/source-producer qualification remains separate.

## External deployment and delivery

The [disposable deployment and external delivery contract](DEPLOYMENT.md) reuses the exact compile-qualified PE and defines independently pinned catalog transport admission. Storage admission does not establish native record validity or authentic world authority. No shipping runtime or accepted APK changes.
