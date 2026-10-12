# Native namespace / BIN freshness gate

The second recommendation in the October 11 MapServer report remains a precise
next milestone. The `.32` data work does **not** enable a freshness bypass,
global production mode, or speculative extra tree preloads. The audit tool
`tools/map_startup_namespace_certificate.py` emits a source-bound **blocked**
receipt; its name identifies the workstream, not a shipping certificate.

The existing owned server-data generation proves closed process ownership,
directory identities/mtime, bounded immutable anchors and private-file ownership.
It is useful for safe directory reuse. It does not prove every source leaf, the
effective native provider, included dependency or top-level parser scan set.
Changing a source leaf in place need not change its parent's mtime. An arbitrary
existing private BIN is deliberately preserved by the donor installer.

The actual native `FolderNodeAdd` uses case-insensitive names. Later Pigs have
higher priority; loose roots use their native virtual priority. An equal timestamp
(or the native permitted one-hour difference) can select the Pig; a changed loose
timestamp selects the loose provider. Dynamic `FolderCacheQuery` can discover a
loose override. Consequently a manifest's filename/SHA list cannot stand in for
the provider actually selected by Wine/FolderCache.

`ParserIsPersistNewer` first checks signature/current ParseTable CRC. In developer
mode it then reads the BIN's dependency list, scans matching top-level membership,
compares dependency dates and checks optional-prefix presence/absence. Keeping
only the CRC while bypassing this traversal would not preserve those guarantees.
The stock decoder's declared extents and EOF checks must also remain active.

A qualified first certificate must bind:

1. The actual ordered source roots, ordered Pigs, FolderCache mode, ignore/prefix
   policy and complete case-folded effective provider namespace.
2. The exact **opened** BIN and its current native schema/defines/ABI identity,
   every included dependency and generated ID file, and exact matching scan set.
3. A closed immutable generation created during existing verified import/setup,
   with native lifetime/ownership, mutation invalidation and race-safe consumption.
4. A native fixture proving stock/candidate equivalence for ordinary acceptance
   and for changed/removed/added sources, case collisions, loose overrides,
   root/Pig reordering, stale/corrupt/private BINs and absent optional prefixes.

Unknown or modified private BINs, changed inputs and unproved generations must use
the complete ordinary loader. Start with sequencers or FX, rather than changing
all parsers. The fixture added with this audit executes the extracted actual C
provider-selection and stock freshness algorithms with bounded dependency/IO
adapters. It is an algorithm qualification, not a full MapServer/Wine execution
or a measured device gain. Rehashing the complete tree on every map would move
the same cost and must not be reported as eliminated work.
