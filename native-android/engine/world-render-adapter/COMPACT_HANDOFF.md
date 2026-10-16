# Compact graph and actor handoff — integration remains closed

Recovery base: `66146bbee161304ba4e4e14cbb53cba6958fb03b`.

The accepted adapter's snapshot, mailbox, surface binding and deferred retirement
interfaces remain intact. This tranche replaces repeated per-draw geometry copies
with bounded per-snapshot indexing and exact identity conflict rejection. It adds
constant-time CPU ownership/capacity metrics. Production graph, entity, renderer,
JNI, Combined build files and accepted APKs are unchanged.

## Required coordinator inputs

| Owner | Available interface | Required before `coh_wr_prepare` |
|---|---|---|
| Catalog A | Independently authenticated immutable COHCAT01 bytes and streaming validation | Catalog/source generation matches the real GROUPS transaction; independent source receipt retained |
| Graph B | Compact ordered file/definition/child views, borrowing catalog allocation | Complete name closure, root matrices from matching GROUPS, both recomputed source CRCs, exact source asset/material semantic resolution |
| Character C | Bounded parsed character/entity/control/global staging records | Entire required update transaction validated before ACK, selected DBID/self slot/pose/appearance and dictionary resolution committed together |
| Asset owner | Accepted `CohRenderGeometry`/`CohRenderMaterial` and logical texture IDs | Supported exact GEO/model/material/texture generation; no missing ID or unsupported render semantic replaced with defaults |
| Renderer E | Immutable receipt/actor/draw snapshot and Surface bindings | All nine independently verified prerequisites; source remains fixture, local development-auth or encrypted-auth as applicable |

A compact graph's `roots_bound=0` or `assets_bound=0` is not eligible. Definition
CRC and catalog SHA do not substitute for runtime root/reference CRC identity.
A successful diagnostic audit returning unresolved references is not a publishable
graph. Staged `CohEntSlot` is not an actor certificate. The runtime cannot currently
supply the required complete graph/character prerequisites. No Combined activation
patch can safely mint the receipt yet; do not use a synthetic complete receipt in
application code. Unit tests containing such a receipt test API mechanics only.

## Ownership and minimal eventual integration sequence

1. A simulation/asset task pins the exact immutable catalog backing allocation
   while B's compact graph and its borrowed definition/name/wire views are in use.
   Complete source resolution and model/material/appearance preparation there.
   Charge old/new catalog, graph, mesh, renderer queue and scratch ownership once
   in a coordinator inventory, then reserve the external portion in E's budget.
   B's separate 96 MiB check is not another free 96 MiB allowance.
2. Build the draw list in original render order. Each mesh ID/generation denotes
   immutable exact bytes. CPU-skinned IDs include pose generation. Instances can
   differ in transform, material and textures while sharing an identical mesh.
   `coh_wr_prepare` validates and deep-copies meshes once per ID/generation and
   every descriptor. It does not retain graph/input pointers. Any error leaves
   the old snapshot and output pointer intact. Release source graph/catalog/mesh
   pins only when every borrower is finished, then reduce the external reservation.
3. Publish complete world/actor generation through the existing mailbox. Keep
   acquired snapshot/binding leases through all queued renderer spans and flushes.
   Retain decoded/uploaded GPU owner storage separately; numeric texture IDs do
   not acquire a GPU lifetime. Prepare bindings before render acquisition and
   resolve exact already-uploaded handles for the actual Surface generation.
4. Preflight scene batches against renderer queue and per-draw limits. The accepted
   queue defaults to 512 draws; adapter capacity is 4,096. A new batching policy
   needs independent order/material tests, especially for translucent draws.
   Submission still scans every vertex/index per instance. New metrics describe
   that work explicitly; storage deduplication is not GPU instancing or culling.
5. On loss/Return/Stop, abandon queued draws before binding/GPU retirement, clear
   mailbox, stop/join concurrent users, release snapshots, and collect on the
   control thread. Final budget destruction must find no owned objects.
6. Qualify the exact integrated standalone/source binaries on both Android ABIs
   and Android 13, then create one Combined successor only when real scene/player
   publication is meaningful. Physical Thor world-entry and actual encrypted
   AuthServer acceptance remain separate requirements.

The current graph reports approximately 9.36 MB topology ownership and 23.20 MB
catalog/graph/record peak, before stack reserves and other retained resources.
Those are Worker B measurements, not adapter ownership or a qualified full world.
Seven catalog edges need original RootMod object-library definitions; real root
reachability and matching generation remain unproven. No fallback geometry is
introduced to close them.

## Qualification level and rollback

The shared-geometry tranche requires new source/host/ASan/UBSan and Android
standalone qualification. Historical Android adapter evidence remains valid for
its unchanged historical bytes only. `check.py` already generates exact source,
fixture and binary receipts for ARM64/x86_64; coordinator CI owns execution.
There is no local NDK in this recovered worker environment. No GPU execution,
physical acceptance, FPS change or authoritative world entry is claimed.

Rollback omits this isolated module or reverts its new preparation/metrics commit;
there are no accepted runtime, server-profile, credential, character or APK writes.
