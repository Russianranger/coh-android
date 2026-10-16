# Offline Atlas / Kings Row preparation and streaming

This additive module prepares original **offline source hierarchy metadata** and
provides a bounded asset-selection adapter. It does not change or connect to
networking, authentication, live scene packets, the accepted Session Client,
Combined Client, or a server. All pre-existing world, asset, renderer and WALK
modules remain read-only dependencies.

The important distinction is **placed source RootMods versus admitted draws**.
A RootMod may be an editor marker, sound emitter, invisible collision/volume
object, LOD element or a wall panel. The large expansion counts are not a claim
that these many objects have been rendered. Both maps have exactly one actual
geometry-layer top-level `Ref`; preparation does not treat every `Def` as a root.
Atlas includes 262,144 authored neighborhood-wall panel occurrences: the original
`neighborhood_walls.txt` recursively assembles 512 panels in each wall section.
The existing four two-wide benches, six four-wide benches and one station floor
are preserved exactly as a separately checked regression subset.

## Current scope

- `tools/prepare_zones.py` reads only blobs from an explicit pinned Git commit,
  reuses `tools/map_fixture/prepare.py`'s group parser, traverses actual map
  references, expands reachable object-library definitions and records inherited
  tint and texture-override rows without silently applying unqualified semantics.
- A unique-definition graph calculates dependency occurrence counts without
  repeating hundreds of thousands of tiled wall declarations. A separate bounded
  placement expansion records original matrix values. Text-definition gaps and
  implicit GEO-only roots remain explicit unresolved dependencies.
- `tools/source_math.py` compiles the already pinned original degree/YPR and
  matrix routines and compares the accepted native `engine/world` routines on
  every expanded node. It retains the original matrix output, including signed
  zero. It does not substitute a Python approximation for source matrices.
- External Atlas and zone asset manifests provide exact original payload paths,
  lengths and SHA256 identities. This is manifest provenance, not a claim that
  full external archives or all payloads were downloaded here. The original
  `.geo` model table and each source trick/material/texture chain still require
  admission. Known version-8 GEO endpoints explicitly list the accepted rigid
  bridge's version-8 limitation; unknown versions remain uninspected.
- No new texture fallback, invented collision floor, or placeholder model is
  introduced. The original accepted 11-instance map remains the rendered scope.
- `tools/summarize_zones.py` produces compact compressed dependency reports for
  Git and an external metadata-only pack containing full placements. It does not
  embed large original game assets in an APK or Git history.

See `evidence/source-summary.json` for exact counts, original-source matrix
comparisons, missing source blobs/definitions, resource caps and external pack
identity. **Kings Row placement expansion is capped/incomplete. Neither map has
full-zone GPU or collision/render alignment acceptance.** Other imported map
layers (audio, gameplay volumes, event content, etc.) are listed but not expanded.

## Runtime adapter contract

`coh_offline_world.h` borrows an immutable, validated generation-specific world
packet. The indexed asset loader is reused; no custom decoder/cache is added.
The adapter conservatively selects intersecting cells and instance spheres,
uniquely pins exact-generation raw dependencies and checks the entire byte budget
before acquisition. Missing admitted geometry, cancellation, budget exhaustion,
capacity overflow or stale generation preserves the previous selection and pins.
The exact same source matrix is returned for future render and collision
preparation. This matrix identity alone does not prove geometry alignment.

The raw generated manifests are **not directly loadable runtime pages**. They
contain 300k+ / 600k+ RootMod placements and origin-based diagnostic cells, while
a runtime packet admits at most 65,536 instances, 4,096 cells and 8,192 assets.
Integration must first:

1. Resolve original GEO/model tables, rigs where relevant, material/trick aliases
   and all exact texture dependencies. Admit decoder/material families separately.
2. Calculate conservative geometry bounds (outward-rounded sphere/cell bounds),
   remove only source-qualified non-render semantics, then construct bounded
   spatial pages. Origin-only cells cannot be used for visibility/collision.
3. Assign ascending source IDs within the cell-partitioned immutable packet;
   record original semantic identity separately. Call `coh_offline_validate` on
   the loader owner before publication. Never mutate its borrowed arrays.
4. On the **asset-loader owner thread**, select into a zero-initialized staged
   `CohOfflineSelection`. Acquire/decode may perform source I/O and bounded cache
   allocations; selection must not run on simulation, audio or GL callback threads.
5. Publish the new generation only at a consumer safe point. Keep old immutable
   packets and selected pins alive until renderer/collision consumers acknowledge
   retirement, then release them on the loader owner. Do not copy live selection
   structs or replace a selection while any old raw view remains borrowed.
6. Use `coh_bridge_acquire/prepare/submit` for the independently admitted model
   with the same source matrix as Worker E's off-thread collision preparation.
   Worker E's immutable collision generation requires complete per-neighborhood
   geometry attestation; these partial manifests deliberately provide none.
7. Handle Surface generations through the existing renderer/bridge owner. Do not
   use GL context loss as permission to free source packets still used elsewhere.

The selection cap is 256 instances and 256 unique dependencies. Overflow is an
explicit `COH_LIMIT`, never silent truncation. Cancellation polls at cell boundaries
and at most every 64 scanned instances. The planner itself has no allocation calls;
this is not a zero-allocation claim for the reused loader or an FPS measurement.

## Reproduction

Use the exact source revision in the summary, with the original blobs available
locally in the coordinator checkout. A partial clone reports unavailable blobs;
it does not fetch the entire upstream tree or read another agent's working files.
Obtain only listed blobs through the authorized GitHub connector and verify their
Git blob hashes before adding them to the local object database if needed.

```sh
python native-android/engine/offline-world/tools/prepare_zones.py \
  --repo . --revision 58caf1d4ab3b39757190f194100ccbc697d57857 \
  --asset-manifest /path/to/zones-world-supplement-manifest.json \
  --asset-manifest /path/to/atlas-world-supplement-manifest.json \
  --output /path/to/external-zone-preparation
python native-android/engine/offline-world/check.py \
  --output /path/to/offline-world-qualification.json \
  --ndk /path/to/android-ndk
```

Preparation bounds: 1,000,000 visited placement nodes, depth 128, 65,536 unique
definitions, 8 MiB per source file and 128 MiB source corpus. Capped placements
remain labeled incomplete; the unique-definition graph is recorded separately.
The external pack is metadata only; a future renderer still needs authentic assets.

`check.py` verifies actual loader integration, generation/rollback/cancellation,
malformed source paths, source cycles and traversal bounds, ASan/UBSan, strict
ARM64 compilation, 1,000 cache-switch cycles, the 1,024-instance/256-cell case,
selection overflow and a 1,024-byte unterminated-path witness. Its synthetic cache
and visibility counts do not establish full-world memory, frame pacing or FPS.
LeakSanitizer is not claimed. Independent Worker E reran this suite successfully.

## Qualification and rollback

Implemented and host/source qualified within these scopes; ARM64 object compiled.
This new module has **not** run in the Android emulator or on AYN Thor and is not
integrated into Support Client 0.2.0. Future integration should use one consolidated
support application after bounds/model/material admission, with real GPU and
collision parity evidence. No numbered full-world gate closes from these results.

Rollback is additive: remove this module/subdirectory and any future explicit
build registration only after checking dependents. Keep accepted historical
receipts and app packages. No branch reset, server reset or data deletion is needed.
