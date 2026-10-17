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

## Closed source selection and lifetime review

The follow-up review closes the finite source alternatives, subject to the same
owned, fresh fixture execution model used by the retained capture:

| Alternative | Concrete source closure |
| --- | --- |
| Different root or patch PIGG | Whole original source reference search: gameDataDirOverride is initialized null and assigned only by addAppropriateDataDirs. Actual auto-discovery failure excludes that branch. piggDir is static ./piggs with no setter/reassignment. PigSetAddPatchDir is called only by the Game client -patchdir path. fileSetDataDirHack is used only by the Game costume comparison tool. Neither caller belongs to MapServer startup. |
| Later global folder insertion | MapServer's other FolderCacheAddFolder calls operate on separate character-transfer/settings caches, not global folder_cache. Server has no extra fileAddSearchPath caller. The actual relative GEO names do not enter the absolute-path bypass. |
| Different mode chooses a hidden GEO | Original FolderCacheChooseMode chooses DEVELOPMENT_DYNAMIC because the sole root animation PIGG excludes texts.pigg. Dynamic lookup and filesystem-only fallback resolve existing relative names against the same finite roots. Neither ./piggs nor its animation inventory contains any GEO path. Thus there is a single case-unambiguous ./data body candidate regardless of fallback between those modes. |
| Previous process or serialized GLD header cache | glds_ht has a zero initializer. geoFindPreload only looks there. The initial entry is created only after fileOpen(name, rb) and successful geoLoadStubs, which reads and inflates the file header. The only other source insertion is modelReload, whose replacement comes from geoLoad(...LOAD_RELOAD), using that same read path. No persistent serialized GLD/header supplier is present. Shared memory is explicitly disabled and actual startup reports no shared heap. |
| File-change reload races | The source hook is after groupLoadMap/dbSetupMap and before dbReadyForPlayers. FolderCache callbacks are disabled before loading and enabled only after that normal startup block. Manual callback mode is enabled. modelInitReload registers callbacks but does not supply a separate header generation. The snapshot guard additionally holds the qualified original GEO/LOD loader locks during observation. |
| Startup command writes | map_batch_cmds is initialized null and set only by the absent batch flag. cmdCfgLoad reads server/db/commands.cfg to adjust access levels; it does not execute those commands. The normal capture hook precedes player admission and normal gameplay loop dispatch. No editor/unpack/create-bins flag is supplied. |
| Geometry loader or sibling writer changes bodies | anim.c has only the two rb fileOpen calls (header and later mesh data). modelReload only reloads via that path; its write is the separate fixed GetVrml lock file. AutoLOD writes lods/...txt, not the source GEO. Group conversion/save paths produce group text/rootnames/geobin/temporary map data, not the object-library binary bodies. The server-side .geo reference in checkoutDefFileByName is a library lookup; checkoutMapFile immediately returns and performs no checkout/copy/write. |
| Fixture orchestrator changes copied bodies | Capture copies every leaf before replacement, then replaces only MapServer.exe; PostgreSQL/ODBC and DB edits are in a separate runtime/prefix. Source runtime is re-inventoried unchanged after capture. No second asset writer or external client is launched in the owned disposable fixture. |

The inspected original bytes are pinned to actual exporter source revision
`a45c657fcc6b3bd8f3a70c59e9aa85ee19455f3f` in
`evidence/prepared-geo-source-route-files.json`, including their Git blob IDs and
SHA256 values. The private source overlay changes the observer, startup hook and
GEO/LOD quiescence guard; its retained compile/stage identities are separately
bound by the successful capture verifier. These are reviewed source conclusions,
not assertions automatically established by searching for a filename suffix.

This closes the source route under the retained owned-startup scope: an observed
library header must originate from its uniquely prepared body, and prior GLD
cache reuse must originate from an earlier read of that same immutable body in
the same process. A direct opened-leaf digest is therefore not the only possible
proof route. Read-only file modes alone would not have established this result;
the absence of another applicable body writer and the startup timing matter.

Two exact values were not retained as direct observations: the physical leaf
string returned by FolderCacheGetRealPath for each open, and the SHA256 of that
runtime-copy leaf at the instant of its open. They are derivable through the
closed preparation/selection chain above rather than directly logged. A consumer
must label this distinction and retain the source and execution identities. It
must not relabel the aggregate runtime inventory as a per-leaf observation.

`check_prepared_geo_provenance.py` replays the actual fixture/source/run/capture
pins, original Git source bodies, exact donor helper pins, complete 406-file
required geometry commitment and all 391 separately acquired body hashes. It
emits an immutable review witness containing every body and its source ordinals.
Its source-route conclusions require independent review; the witness itself is
not a native admission permit. Existing native resource-index inputs and their
false material/live/world authority flags remain unchanged until an explicit,
reviewed admission contract consumes the full proof chain.

CLIENT effective materials, texture swaps, lighting, LOD state, per-model
post-load bounds and the matching live GROUPS generation remain separate
prerequisites. The completed disposable-source body provenance is not a claim
about physical Thor files or any independently running server generation.
