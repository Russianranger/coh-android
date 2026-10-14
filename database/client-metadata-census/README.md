# Client metadata census prototype

This stage is not enabled in the launcher or shipped Game. The production source
does not call `cohFolderCensusRegister`. Binary parsing, a matching opaque token,
and a callback supplied by a controlled fixture do not establish provider
authority. No native Game/Wine, Android, world-entry or physical performance
qualification is claimed for this prototype.

The preceding bounded folder-sort candidate passed genuine Wine client startup
compatibility, but demonstrated no useful host timing gain: the retained warm
native witness was 19.236 seconds, versus 19.217/19.482 seconds for the ordered
warm candidates. It reduced insertion comparisons, while retaining every Wine
filesystem enumeration. Physical client startup remained approximately 264
seconds in the supplied 0.13.36 sessions. This independent next stage targets
the Wine enumeration/syscall work rather than comparisons alone.

## Consumer behavior

`coh_folder_census.h` parses FCEN1 with complete preflight before exposing rows.
It uses at most 64 MiB of caller-owned blob storage and 64 KiB of caller-owned
directory offsets, without heap allocations or filesystem access. Directory
lookup uses a case-insensitive binary search. Original per-directory arrival
order remains exact. The complete scoped directory graph includes empty and
named dot directories, nontextures and ignored-prefix files. Named dot entries
remain available in the census even though the stock constructor prunes them.

The canonical Win32 projection retains attributes, all three FILETIMEs, both
size words and long/short names. Reserved words, trailing structure padding and
string padding must be zero. Pinned Wine's ANSI enumeration leaves the reserved
words uninitialized; those bytes cannot authenticate a provider. Capture access
and creation times are provenance, not a claim that those times still equal a
fresh lookup. Current FolderCache parity concerns its consumed name, low size,
last-write time, directory/readonly/hidden/system fields.

UtilitiesLib does not inherit the Game target's CLIENT macro. The dedicated
`COH_CLIENT_METADATA_CENSUS_PROTOTYPE` compile gate is absent from the retained
production build; a future Game-only qualification must explicitly supply it.

The source overlay replays admitted rows through the literal extracted stock
per-entry constructor. It preserves FolderNodeAdd, attributes, counters,
provider precedence, recursive traversal and the existing hash/query routines.
It does not replace texture callbacks or use THI1 as an enumeration authority.

The context requires a future qualified caller to supply an owned cache,
matching generation token and a live current-provider lease. The owning thread
and original context/index addresses are bound; copied contexts and aliased
registration inputs are refused before writes. Decoder output alias misuse
preserves the input/index bytes instead of attempting to clear overlapping
storage. Additional source
guards require the dedicated Game-only build macro, the global cache, exactly one GDD, the admitted PIG count,
dynamic development mode, ALL-folder policy, disabled updates, no create/delete
callbacks, virtual location 0 and initially empty siblings. Only
texture_library/object_library/fx/scripts are eligible. Unknown paths, changed
providers/policies, malformed blobs, absent or revoked leases and populated
PIG/prior-provider branches retain native enumeration. A populated owned branch
revokes the whole registration before recursion can replay an empty child.
Every other failed owned admission or unknown eligible directory also revokes
registration, including a callback that clears itself during stock fallback.

The native filesystem override remains unchanged. This prototype never treats
a skipped entry, missing decoder record or unreadable file as proof of absence.

## Actual portable verification

The extracted stock FolderCache constructor and FolderNodeAdd execute on 707
controlled C cases. They compare complete linked trees, metadata/provider bits,
parent/previous/next/tail links, counters, original arrival sequence and callback
traces in each enabled/compiled-disabled lane, with four additional alias/copy
API guard cases. All fallback scenarios retain stock enumeration counts; admitted
complete fixture branches omit three native enumeration opens. The existing
native hash-table body is source-identical; the fixture compares complete tree
membership with a digest and does not execute the actual StashTable itself.

These are portable controlled tests using Win32 type/enumeration adapters.
They are not genuine current native provider or device timing measurements.

## Gates before any optimization can ship

1. Capture actual native defined WFD fields and complete branch membership under
   the exact retained Wine/FEX/PRoot/native consumer identities.
2. Bind the authenticated import/supplement/overlay recipes to every current
   alias and target identity, mode, ownership, link, size, mtime/ctime, relevant
   DOS xattrs, directory identity and exact children. The repository currently
   has no complete immutable generation proof.
3. Perform one fresh complete warm metadata vector pass outside Wine/FEX,
   preferably fused with existing mandatory client preparation. Directory
   mtimes and 64 anchors cannot safely replace this pass. A readonly chmod is
   not a read-only filesystem or closed writer epoch.
4. Qualify source-derived projections against genuine native observations,
   including read permissions and symlink/xattr/case/short-name behavior. A
   Python/POSIX projection by itself cannot authorize replay or `_AltStat`.
5. Execute native retained/replay/fallback parity for constructor/hash/queries,
   texture binds and winner IDs, catalogs, BINs, shaders and full payload
   behavior; then actual login/world entry and physical AYN Thor gameplay.
6. Measure whole launcher validation plus native readiness. Moving work out of
   Wine only counts as an optimization if total critical-path time improves.

Generation state is scoped to the four admitted immutable branches. Any root
anchor used to connect those branches must be explicitly marked partial and
unreplayable; it cannot claim a complete native root enumeration. All mutable
bins/dbidmaps, unknown supplements/providers and unsupported paths use stock.
No player database or persistent character profile is touched.
