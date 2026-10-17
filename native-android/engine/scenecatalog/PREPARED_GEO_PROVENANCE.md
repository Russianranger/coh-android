# Prepared authentic GEO bodies and runtime selection proof

This audit separates two concrete propositions. Successful exact preparation
proves that the candidate full bodies were present in the prepared source tree.
It is stronger evidence than matching model metadata. Proving that a particular
runtime Model was read from that body additionally requires the original file
selection and lifetime invariants below. No metadata-equality receipt changes
source-generation, asset, material or renderer authority flags.

## Exact inspected generation

The actual resource capture is run 38994607354, resources SHA256
`8500764939215b576e5ff88056ec85b475785038e09600019846ff5a06eb1cd6`.
Its `control-fixture.json` SHA256 is
`3be317b5cc4b24aad8b19cd93e18762f12270ad4284c31a81e7587e4e35fadc1`.
The fixture builder authenticates public donor APK
`e56df1bcf2210aff131ba80189b1b2dee760f27066e3ee26e09c5fea1654ad80`.
The inspected guest helpers are the donor commit
`74fe247be85173e618f1af2c8af71b1316de4cd8` bytes, individually matched to
`packaged_guest_sources` in that actual receipt, rather than current helpers.
The fixture builder itself matches the recorded SHA256
`dba537cde48a595e20c127b1f22fb83525205dbf6b12568ca4d3c762dbb50383`.

## Positive construction evidence

| Stage | Source-enforced property | Actual retained observation |
| --- | --- | --- |
| Fixture | Fresh output; authenticated APK guest imports; cold protected client tree; unconditionally invokes original atlas supplement install | Prepared success, imported inputs readonly |
| Atlas install | Exact manifest/archive; missing-only installation; full target SHA comparison or verified payload extraction; case-conflicting leaf/directory selection refuses | 388 of the 391 candidate files belong to the pinned atlas manifest |
| Required geometry | Original `atlas_beacon_package.ensure_required_geometry` selects the complete pinned client-visual object-library GEO inventory; verifies existing full bodies or extracts CRC/SHA-verified bodies before server staging | Required-original-geometry phase completed; remaining 3 files belong to that manifest |
| Cold mirror | Checked roots; private real directories; immutable collision requires full SHA equality; otherwise immutable file link to verified source | `cache_reused=false`, cold mirror and receipt seal phases completed |
| Zone filter | Only exact zone-manifest relative names excluded | No overlap between these 391 candidates and the pinned zone manifest |
| Later installers | Map-package leaves are PE32 verified; server cache entries restricted to server/bin/*.bin; beacon derived caches are separate from object-library bodies | Native/cache/beacon preparation phases completed |
| Animation PIGG | Runtime root piggs directory may contain only server-animations.pigg; complete independently checked inventory restricted to player_library/animations/*.anim | Animation installation succeeded, 5878 entries |
| Capture copy | Every source leaf is dereferenced, hashed and copied to a fresh private map-runtime; source is re-inventoried after capture | Ordered inventory unchanged: 176613 files, 4273657217 bytes, commitment f2bd6c0bac0ea8dafbf76cdff40b33089c48318a968d3db6fbb20899e172f99f |

Consequently a successful execution of this pinned, cold preparation chain is
an affirmative source proof of full-body installation and staging, not merely a
lookup candidate label. The 391 separately acquired bodies independently agree
with those same exact manifest leaf SHA256 values. A whole-archive SHA was not
recomputed by the bounded range acquisition and is not claimed by it.

## Runtime opening: what is already constrained

The private capture starts a fresh process and Wine prefix, passes
`-nosharedmemory`, and launches the candidate in its private map-runtime cwd.
Only MapServer.exe is replaced after the source copy; DB configuration is in a
separate db-runtime. The original geoLoadInternal opens its selected library
name with `fileOpen(name, "rb")` before geoLoadStubs; its glds_ht is process local.
The captured GEO paths are relative original object-library names. Captured
NOT_LOADED state describes a loaded header awaiting mesh data; it does not mean
that a truncated header-only disk file was installed.

Original fileLoadDataDirs adds ./piggs and ./data. Presence of ./data suppresses
gamedatadir.txt fallback. The copied fixture drops empty directories, including
the original empty tools directory; retained stderr reports failed automatic
game-data-directory discovery, consistent with that layout. The only permitted
root PIGG has animation-only names, so it cannot shadow an object-library GEO.
The ordinary relative fileOpen route goes through FolderCacheQuery and
FolderCacheGetRealPath, with case-insensitive folder resolution; the pinned
installers reject case-conflicting targets.

## Remaining audit obligations before an opened-body authority gate

The following are concrete source proof obligations, not requests for another
server capture. A direct opened-leaf receipt is one possible proof, not the only
one.

1. Independently close every SERVER startup caller capable of changing the
   search path, PIGG directory, FolderCache mode or gameDataDirOverride. The
   retained command has no data/path/patch override, but absence of flags alone
   does not cover internal setters or configuration consumers.
2. Close all post-copy object-library writers and all cached-header suppliers
   reachable in the exact candidate binary. The copy preserves read-only modes
   and the observed loader opens rb, but source-inventory-unchanged checks the
   original tree, not the separate runtime tree; it cannot by itself certify
   runtime-copy immutability through the observation interval.
3. Bind the verified preparation chain and these selection conclusions to the
   actual source/run/compile digests in a reviewed admission object. The present
   aggregate inventory receipt is not an independently replayable per-leaf
   inventory and should not be relabeled as one.

Once those finite obligations are source-closed, the deterministic prepared
body plus unique original selection route can establish opened-body identity
without adding a digest hook or rerunning the server. CLIENT effective materials,
texture swaps, lighting, LOD state and live GROUPS generation remain distinct
prerequisites even then.
