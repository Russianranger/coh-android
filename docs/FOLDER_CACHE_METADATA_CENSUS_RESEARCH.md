# Full FolderCache metadata census: source-only next stage

This is an implementation plan, not runtime authority or a performance result. No
Game, MapServer, Wine build or native execution was performed for this research.
The frozen 0.13.37 client adapters remain unchanged. The existing native sorting
qualification remains a separate historical result; it did not establish a host
startup gain or a Thor improvement.

The smallest useful stage replaces repeated Wine directory enumeration and
first-lookup metadata calls for five completely proved immutable branches:
`texture_library`, `object_library`, `fx`, `scripts`, and exact `scripts.loc`. It replays the ordinary
FolderCache constructor and preserves its complete nodes, children, tail pointers,
hash table, provider choice and scan callbacks. THI1 texture headers alone cannot
provide this namespace, especially for nontextures, directories and excluded
entries.

## Native boundaries

There is no literal `globalSingleGDD` symbol in the inspected source. The proposed
predicate means `fc == folder_cache`, exactly one authenticated
`FolderCache_GetNumGDDs(fc)`, and the matching `fc->gamedatadirs[0]` provider.

| Native location | Existing behavior | Smallest proposed change |
| --- | --- | --- |
| `file.c:fileLoadDataDirs` | Registers loose roots in reverse order, assigns virtual priorities, then adds PIGs | Bind the actual ordered roots/PIG inventory to the census; do not reorder or change the mode |
| `FolderCache.c:FolderCacheAddFolderToNode` before `fwFindFirstFile` | Enumerates one directory, calls `FolderNodeAdd`, assigns attributes/counters/callbacks, then recursively visits directories | Obtain authenticated rows for that exact directory and feed the literal existing per-entry helper; retain the recursive walk and hash-building calls |
| `FolderCache.c:FolderCacheRequestTree` | Dynamic mode materializes requested trees, across each GDD; records requested paths | Keep the function and its membership bookkeeping; its ordinary constructor can consume the census |
| `FolderCache.c:FolderCacheFileSystemOverride` before `_AltStat` | Searches roots from highest priority; creates/updates an override node from readable loose metadata | An immutable-only tri-state accessor may provide exact present metadata or proved complete-branch absence; unknown cases call the original `_AltStat` path |
| `fileutil.c:fileScanAllDataDirs` | Requests a tree and walks actual FolderNodes to create `_finddata32_t` scan callbacks | Leave this path intact. Never substitute a texture-header callback or omit nontexture nodes |

Game selects `FOLDER_CACHE_MODE_DEVELOPMENT_DYNAMIC` for its loose-data setup and
disables callbacks while loading. It enables callbacks again after loading.
Changing the mode, declaring `all_data` early, or deferring the original metadata
construction until character entry would invalidate this optimization.

## What a complete census must preserve

The stock constructor consumes `cFileName`, `nFileSizeLow`,
`ftLastWriteTime` converted with `_FileTimeToUnixTime(..., FALSE)`, and the
`DIRECTORY`, `READONLY`, `HIDDEN`, and `SYSTEM` attribute bits. It deliberately
uses the low 32 size bits. A candidate must preserve that behavior rather than
silently repairing it.

Retain the *defined* native find-data fields for provenance: the attribute word,
all three FILETIMEs, size high/low, exact long and alternate filename bytes, plus
the provider, parent directory and enumeration ordinal. Do not serialize the raw
320-byte stack structure. The pinned Wine `FindFirstFileExA` and `FindNextFileA`
copy the defined fields but do **not** initialize/copy `dwReserved0/1`; trailing
name bytes and struct padding are also not authoritative. Normalize those
unconsumed bytes in the decoder and qualify parity of the actual FolderCache
consumed fields.

Access time can change during ordinary reads. A historical complete defined-field
snapshot is provenance, not proof that all fields are still current. A claim of
full-current-WFD equality additionally needs fresh access/creation-time mapping.
The first adapter should claim exact FolderCache consumed-field parity, not a
general replacement for the Win32 enumeration API.

`_AltStat` opens with `GENERIC_READ`, reads by-handle information and converts the
write FILETIME to UTC. `_FileTimesToUnixTimes` has the literal
`if (1 || _IsUTCVolume(name))`, so this source also takes the nonlocal conversion.
However, enumeration can expose an entry that the by-handle open cannot read.
Record or independently qualify the readable override projection and error
state. A WFD entry alone cannot authorize a successful `_AltStat` result.

The exact Wine source also establishes why an APK filename/hash list is
insufficient:

- `get_file_info` observes a link and then follows its target; directory links
  and mount boundaries affect the reparse bit.
- Writable mode bits control `READONLY`; `user.DOSATTRIB` can affect hidden/system
  attributes, with a dot-name hidden fallback.
- Creation time depends on the actual compiled stat/birthtime configuration; the
  fallback is write time. Names and short names depend on native conversion and
  short-name generation.
- Directory enumeration starts with directory membership, but reads each entry's
  current metadata before returning it.

Bind the actual Wine/FEX/native binaries, Wine build/config recipe, PRoot mount
and UID mapping, prefix drive mapping, timezone/codepage policy, source functions
and filesystem behavior. Read-only source analysis does not qualify that mapping
on Android.

Directory rows include empty directories, nontexture files and special excluded
states. Policies must be exact:

- Constructor dot-first names are skipped. A skipped `.name` must not become
  false absence for a direct override lookup. Dot/dotdot are explicit special
  entries, not safe relative file paths.
- `FOLDER_CACHE_EXCLUDE_FOLDER` compares directory basenames at every recursion
  depth. `ONLY_FOLDER` restricts root entries only.
- Ignore-prefix filtering happens in queries/scans, not in the constructor. Do
  not drop those nodes when replaying.
- Development/production mode, override bans, `ban_all_overrides`, ordered ignore
  prefixes, and exclusion mode/name belong to the recipe.
- Case-insensitive collisions require the ordinary fallback. Preserve original
  case. The importer establishes text-directory case first and reuses it for
  asset directories; it allows paths longer than the native `MAX_PATH`, which
  requires refusal rather than truncation in this adapter.

## Authority available today, and its gap

`AtlasAssetImporter` checks every extracted byte against authenticated inventories
and publishes a generation atomically. Its subsequent `inspect` only checks the
pointer, completed receipt and data directory. The guest `import_identity` also
checks the receipt/count/bytes; it does not rescan every current leaf.

Cold `prepare_worktree` already visits every source leaf, normalizes timestamps and
read-only permissions, creates links, and copies writable cache/DB-ID files. Warm
reuse validates native/prerequisite files and receipt compatibility, not every
immutable input. `ServerDataCache` proves directory ownership/identity/mtime,
private-entry safety and at most 64 immutable anchors. Its directory fingerprints
and anchors do not detect all in-place leaf changes. A mode of `0444` alone is
not a read-only filesystem guarantee; the owner can change it.

Consequently no current receipt can authorize persistent census reuse. THI1,
directory mtimes, the 64 anchors, a passing boolean, an earlier native producer,
or a BIN schema CRC must not open the new gate.

## First feasible source/provider proof

1. During an existing cold mirror/normalization operation, collect a complete
   canonical vector without a second content traversal. For each immutable leaf,
   bind original authenticated import/supplement content identity, exact logical
   path/case, alias/link text and link fingerprint, resolved real target and its
   `dev, ino, mode, uid, gid, nlink, size, mtime_ns, ctime_ns`. Bind relevant DOS
   xattr state or the exact qualified absence/error policy. For every parent,
   bind identity, permissions and exact child membership, including empty dirs.
   Collect after normalization, and recheck the generation before publishing.
2. Capture native find-data and readable override projections under the exact
   qualified runtime/provider. The stock enumeration can donate this census
   during a normal first load; the new code should not require a second Wine
   traversal. Capture remains untrusted research until the full current
   generation, mapping and byte authorities agree.
3. For a warm launch, validate that entire metadata vector once. Do not rehash
   the 3 GB of content when the original authenticated content and every exact
   immutable leaf fingerprint still agree. Use a native ARM64/Android-side batch
   outside Wine/FEX, preferably fused with existing required validation; bind its
   physical-to-guest path/UID mapping. A PRoot Python pass may be the first
   correctness prototype, but cannot be presumed cheap.
4. Hold the existing operation/ownership lease through validation and native
   startup. Bind the actual native consumer/source/ABI, import generation,
   worktree root, overlay/supplement recipe, ordered PIG identities, prefix and
   per-launch nonce. A pack hash is not a source-generation proof. Any changed,
   unavailable, unknown or raced input withdraws the whole affected branch and
   uses the ordinary native path; preserve all player/database state.
5. Keep mutable BINs, `.dbidmap`, logs and unproved supplemental/private files on
   the stock path. A later actor that writes an admitted branch must revoke its
   authority synchronously before mutation. Unexpected callbacks, directory
   monitor overruns, a PIG update, a new root, a mode/prefix policy change or
   unknown owner also withdraw admission.

This warm metadata pass is new work. Its total cost must be measured alongside
the removed Wine calls. If it merely relocates the same delay to launcher
preparation, do not ship it as a speed improvement. A true zero-walk persistent
proof needs a separately designed managed writer epoch or a qualified immutable
backing mechanism; neither is established in this repository today.

The optional query accessor has three results: `PRESENT`, `PROVED_ABSENT`, and
`UNKNOWN`. Absence is allowed only inside a branch whose complete *current*
membership is proved. Excluded or skipped rows cannot supply absence. Absolute
paths, traversal, case aliases, unreadable entries, unknown providers or runtime
policy changes always return `UNKNOWN` and execute the existing fallback.

A known animation PIG can coexist only after its exact ordered index/member
inventory proves no overlap with the five admitted branches. Merely checking its
archive filename is insufficient. Otherwise retain native provider merging and
stock enumeration/stat; do not invent loose/PIG precedence. Equal timestamp and
the permitted one-hour difference can select a PIG; root/PIG order is material.

## RAM and bounded representation

The implemented controlled FCEN1 representation deliberately uses canonical
320-byte WFD records plus 8 bytes of directory/arrival ordinals per row. For
173,011 files, file rows alone require 56,747,608 bytes (54.12 MiB); directories,
directory-table names and the ordinary FolderNodes are additional. The actual
five-branch file count on the Thor has not been measured. This is a RAM tradeoff,
not free reuse. A compact consumed-field codec remains a separately qualified
future stage; do not substitute it silently for the agreed decoder.

The current matching producer/decoder caps are 200,000 total rows, 16,384
directories, 259-byte relative paths and a 64 MiB total blob. The decoder borrows
immutable bytes and a caller-owned directory index capped at 64 KiB. The guest
producer spools rows after 1 MiB, then creates one final bounded packet; it does
not retain a second complete Python row list. A full 212,393-file/10,637-dir host
provider can exceed these limits, so only completely admitted branch subtrees
belong in the packet. Its root anchor is explicitly partial and must never be
replayed as a complete native root enumeration. Unknown or over-limit branches
fall back before node or callback mutation.

Map one immutable blob or perform one bounded read; decode one stack WFD at a
time. Avoid a second entire mutable node tree and avoid realloc growth overlap.
The normal Win32 FolderNode is nominally 40 bytes before pool/name/hash overhead;
those ordinary nodes still exist. The census is additional memory, not a
replacement for that tree. Preserve nodes through world entry, and release only
the replay blob when every admitted branch is materialized and no future query
depends on it. Never clear the tree and postpone rebuilding to login/zoning.
Native RSS/PSS and allocation peaks, including allocator/string/hash pools, must
be measured; arithmetic caps are not observed device RAM.

## Required gates before implementation/promotion

The isolated source/C prototype remains disabled. First require literal-body,
FolderNodeAdd and tree/hash/callback parity with the stock source. Exercise full
mixed directory membership; empty dirs; nontextures; dot and ignored entries;
all exclusion modes; callback presence/reentrancy; populated children; foreign
cache; modes and per-thread mode overrides; case aliases; long paths; attributes;
time boundaries/one-hour provider rules; high file sizes; root/PIG reorder;
known nonoverlapping and overlapping PIGs; readable/unreadable projections; and
ordinary mutation/overrun handling. Compare exact nodes, provider/file_index,
seen/hash flags, parent/child/tail links, callback results and scan order.

Decoder tests must reject bad format/version/source/consumer/recipe, overflowed
counts/offsets, truncation, overlapping sections, bad names, duplicates, provider
aliases, invalid directory parents/cycles, checksum tamper and all allocation
failures before changing any FolderCache node. A partially validated replay must
not leave half a tree before fallback. Canonical records exclude uninitialized
native bytes.

Guest authority tests must cover changed-in-place content with restored mtime,
ctime/inode/mode/UID/link/xattr changes, addition/removal/renaming with unchanged
claimed receipts, ancestor replacement, altered case, changed imports/overlays,
interruption, stale captures, ownership mismatch and each validation/publication
race. Unknown input must preserve the original worktree/character and produce
usable evidence, without deleting/recreating data.

Then perform an independently authenticated native Win32/Wine stock/candidate
pair on the same complete provider. Record enumeration/stat counts by branch,
constructor/readable-override projections, full FolderNode namespace/scans,
ordinary BIN freshness/IDs/loader decisions, renderer/readiness/owned cleanup,
and all phase/memory counters. Run cold and validated warm cases, plus real world
entry/movement/zoning qualification where available. Inspect calls after
`all_data` and after world entry to catch delayed work. Include ARM64 authority
validation time in whole-operation comparison, not only Game time. Keep parser
signature/CRC/body bounds and ordinary saves unchanged.

Only successful source/native/authority gates can justify a separately reviewed
activation. The existing six native sorting cases, the dormant migration tests,
and a host C decoder are not qualification of this new census. The next physical
run must still read THORHERO's authoritative saved location, export reliable
reports, and demonstrate actual client/zoning timings on the AYN Thor.

## Isolated fresh producer checkpoint

Two new files in `foldercensus-producer-037`, based on `1b8da4e`, are frozen
separately from the shipping 0.13.37 sources: `android/guest/folder_cache_census.py`
and `tools/android/interactive/test_folder_cache_census.py`. They have no runtime
caller or native-registration implementation; authority remains `None` and all
activation/shipping booleans remain false.

Each invocation validates the explicit five-branch recipe, hashes the declared
current consumer/runtime/PIG blobs with open/identity checks, and performs two
complete fresh metadata/membership passes after supplements are finalized. It
binds every selected leaf's current type, UID/GID, inode/device, mode, nlink,
size, ctime/mtime, logical alias and direct target, relevant DOS xattrs, complete
selected directory membership, empty/dot directories, and all input ancestors.
The root's other immediate entries are reference-only; their descendant trees
and mutable BIN/DB-ID files are not certified. Runtime/PIG facts are capture
provenance, not a supplied-list replacement for actual native provider/index
observation. Existing warm receipts and 64 anchors do not supply a generation.

Known read-only shared inodes are permitted only with an explicit complete alias
group inside the finite owned source/import/store roots. Both passes verify all
alias paths and ancestors, identical current inode metadata, no write bits, and
`nlink == complete alias count`. Unknown extra aliases, chained/relative links,
directory aliases, source ancestry replacement or unavailable metadata refuse
the packet. This preserves archive/content-store links without copying, breaking
links or reimporting. The current zone package source documents shared input
archive links and single-link installed output; the normal client mirror uses
absolute file symlinks and read-only imported leaves. Actual PRoot legacy l2s
UID mapping remains a separate qualification requirement.

The final fresh host suite passed 23/23 with zero failures/errors/skips and
ResourceWarning treated as error. Source pins were unchanged before/after. Tests
include ctime-detected in-place rewriting with restored mtime, membership and
ancestor changes, link and hardlink closure failures, case/path/type/access/xattr
ambiguity, mutable cache exclusion, exact scripts.loc scope, provider/runtime
changes, size bounds, current fallback reports, and repeated-operation evidence
preservation. The producer never reads a player profile/database, changes input
metadata, launches Wine/Game, or recreates data. Safe CLI failures emit a current
operation report and no native packet; existing operation outputs are preserved.

The independent actual portable C decoder accepted the 4,864-byte controlled
packet, checked all 14 canonical rows/directory lookups and uppercase queries,
and rejected six alias/bounds controls. This proves packet interoperability, not
observed Windows ABI/Wine WFD parity or a current native lease. The controlled
fixture's provider was removed after capture, so it cannot be admitted as a live
provider even if its packet hash is correct.

For a controlled 5,000-leaf host provider, three full captures in fresh case
processes measured 0.663–0.674 seconds for direct readonly files and
1.087–1.098 seconds for 5,000 direct absolute symlinks to readonly import files.
Each included 100 complete shared-inode groups, both fresh walks, all alias
checks, hashing a 9,478,144-byte recovered Game and 245,968-byte runtime-probe
fixture, and final 1,663,920-byte packet encoding. Both cases had 66 directories
and 5,065 rows. The probe is explicitly not a qualified Wine/FEX runtime closure.
Filesystem caches were uncontrolled; no stock Wine enumeration comparator was
run, no device speedup or linear extrapolation is claimed. Process maximum RSS
reached 17,208 KiB (direct) and 17,644 KiB (symlink), including interpreter/setup
baseline; this is a host process peak, not native/device incremental PSS/RSS.

The next gate connects these fresh complete current observations to independently
observed native WFD/readable-override rows and the actual full ordered PIG
projection under exact consumer/ABI/runtime/mapping identities. Bind both packet
bytes and source generation to the native owned operation lease. Reusing native
captures across starts requires exact current generation comparison; a token,
prior receipt or helper assertion alone cannot authorize it. Capture and current
validation cost must be charged to whole-operation timing before enabling Game.

## Pinned primary source

The accompanying `foldercache-metadata-census-source-receipt.json` records exact
inspected repository files and the retrieved Wine sources. Wine is pinned to
`b073859675060c9211fcbccfd90e4e87520dc2c2`:

- [kernelbase/file.c](https://github.com/wine-mirror/wine/blob/b073859675060c9211fcbccfd90e4e87520dc2c2/dlls/kernelbase/file.c)
- [ntdll/unix/file.c](https://github.com/wine-mirror/wine/blob/b073859675060c9211fcbccfd90e4e87520dc2c2/dlls/ntdll/unix/file.c)

The existing `docs/MAP_STARTUP_NAMESPACE_CERTIFICATE.md` describes the provider
authority gap. This plan extends that boundary to a complete FolderCache metadata
census; it does not turn that blocked audit into a shipping certificate.
