# Compact catalog ownership and unresolved-name diagnostics

This module recovers the unpublished Worker B compact implementation from the
prior six-worker environment. All 21 hashes in its preserved standalone receipt
matched the surviving original files. The prior standalone and integrated
receipts remain unchanged under `evidence/compact-recovered-*`; the new source
and tests have separate qualification receipts. Accepted APKs remain untouched.

`coh_sg_compact_build` makes two complete catalog walks, builds bounded file/slot
and case-insensitive basename indexes, and copies child matrices into one compact
pool. It preserves every allocated definition, tombstone, null slot and original
file/definition order. Raw definition wire/name views borrow the independently
verified immutable catalog. Cycles, excessive depth, ambiguous names, unknown
references, malformed input, exhausted budgets and cancellation all refuse the
candidate without changing the old graph or caller output. No root or asset
readiness is inferred from catalog name checksums.

The complete authentic capture still fails strict graph admission on seven names.
The separate `coh_sg_compact_audit` walks every record and child without returning
any graph. It counts every unresolved reference and copies at most 16 exact
file/slot/child identities. Truncation is explicit. It changes its output only
when both complete walks validate, then returns either complete-name-closure
`COH_OK` or diagnostic `COH_NOT_FOUND`. Missing closure does not certify cycles,
depth, root reachability, or permission to publish a scene.

| File | Definition slot | Child | Unresolved original name |
| --- | --- | --- | --- |
| 110 | 61 | 1 | `_cot_warpgate_base` |
| 110 | 61 | 2 | `_cot_warpgate_glow` |
| 376 | 32 | 1 | `_mmayhem_curtain_8_01c` |
| 376 | 33 | 1 | `_mmayhem_curtain_8_02c` |
| 376 | 34 | 1 | `_mmayhem_curtain_8_03c` |
| 376 | 35 | 1 | `_mmayhem_curtain_16_01c` |
| 376 | 36 | 1 | `_mmayhem_curtain_16_02c` |

File 110 is `object_library/Villain_Lairs/cot/elements/magicrunes/magicrunes.txt`;
file 376 is
`object_library/Villain_Lairs/unique/mother_mayhem/mmayhem_details/mmayhem_details.txt`.
The parent definitions are `cot_enemy_gate_01` and the five correspondingly named
`mmayhem_curtain_*` definitions. Worker A's separate pinned source audit identifies
empty original RootMod declarations and the `groupDefFuture` fallback into
`group_info.pre_alloc`, outside the regular-file exporter. That audit explains a
source-level mechanism; only corresponding runtime root/definition data can
establish actual reachability and required closure. B does not manufacture these
definitions, guess an alias, suppress a reachable edge, or rerun MapServer.

## Exact capture and measured memory

Catalog: 12,179,670 bytes, SHA256
`61c9408b02e366fa487acc857ffb89cde5d431e7dfcc2b2e01ecd0446bea3763`.
Its 508 files, 40,225 allocated slots and 130,314 child links are all inspected.
The independent catalog walker recomputes definition CRC 3173822562. Reference
CRC 3649375123 and 33 active roots remain recorded source metadata: no actual
root transforms occur in this catalog, so B cannot recompute that CRC or bind
any roots. A CRC match would not authenticate assets or the physical Thor epoch.

| Named reservation | Bytes |
| --- | ---: |
| Borrowed catalog input | 12,179,670 |
| Compact candidate pool | 9,360,555 |
| Maximum one-record decoder scratch | 1,654,842 |
| Observed strict-refusal heap peak, including input | 23,195,067 |
| Compact and walker stack reservations | 98,304 |
| Copied audit output | 12,616 |
| Complete diagnostic aggregate reservation | 23,305,987 |

The strict build exits on the first missing edge and releases its complete pool.
The diagnostic independently validates both complete walks before releasing its
pool. These are named payload/reservation measurements, not process RSS or GPU,
allocator, server or driver memory. Both original caps remain: 32 MiB candidate
ownership and 96 MiB aggregate transaction. Old pool/input, new pool/input,
record scratch, stack and every caller-retained owner/asset must fit together.
A reused input is deliberately counted again during old/new replacement.

A's immutable catalog owner can supply the borrowed span. Acquire/retain the
owner before preparation and release it only after every compact borrower has
retired. Count the owner's object/index plus input allocation slack in compact
`retained_bytes`; compact already charges its borrowed input length. Include
other retained catalog/graph/asset generations and external callback scratch.
Publication remains caller-serialized and returns the prior snapshot without
freeing it. No atomic mailbox or implicit resource pin is supplied.

## Qualification and remaining work

`check_compact.py --sanitize --capture-directory <retained capture>` verifies
source-produced fixtures, exact original record parity, injected allocation
failures throughout both passes, cancellation, malformed input, bounded missing
report truncation, source/generation changes, stale publication and real capture
refusal. The audit also runs through existing scenegraph host/Android fixtures.
`--ndk`, `--android-output` and `--fixtures-output` retain both standalone ABIs,
exact source/fixture/binary hashes and unexecuted build receipts for coordinator
Android 13 admission. No catalog is linked into an APK or fixture header.

Production-O2 host emitted frames measured 12,768 bytes for audit, 592 for build
and 80 per recursive visit. At 129 frames this is 23,680 bytes before small
bounded helpers, below the separate 32 KiB compact reserve. A compile-time
structure-growth guard uses a conservative 128 bytes per recursion level and
1,024 bytes of non-report overhead. Compiler evidence remains platform-specific;
the test harness itself has larger frames outside the production memory claim.

Next: recover a matching complete original GROUPS transaction, retain its exact
file/root/definition generation, resolve reachable closure under source rules,
recompute reference CRC from those roots, and admit actual model/GEO/material
identities. Only then can transforms/spatial ownership yield a complete immutable
world snapshot. Full character transaction and renderer publication remain
independent prerequisites. No live-ready flag, READY/ACK, APK release, physical
acceptance or server-authoritative rendered world is claimed here.
