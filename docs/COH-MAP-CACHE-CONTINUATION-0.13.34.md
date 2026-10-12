# Map cache continuation — conservative metadata reduction

The successor candidate retains the published .33 native binaries and Assets
1.0.0. It removes one redundant metadata query from each immutable-directory
row during a validated warm server-data checkout. One fresh `lstat` supplies the
same real-directory type, device/inode, owner and mtime checks previously read
in two consecutive calls. No prior invocation's metadata is accepted instead of
the current observation. All recorded directories, source roots, anchor byte
hashes, private entries, generation/owner/cleanup checks, changed-parent layout
proofs and ordinary fallback remain mandatory. Cold mirrors and native BIN
freshness decisions are unchanged.

The successful cache summary now records
`immutable_directory_metadata_queries` and
`immutable_directory_metadata_policy`. These count only the primary immutable
directory loop; root, anchor ancestry, changed-parent and private inventory
metadata queries remain additional work.

## Host evidence and limits

The two added regressions exercise actual filesystem metadata calls for 255
immutable directories outside the independently checked anchor ancestry, and
refuse a replaced directory while preserving the closed donor and a persistent
database sentinel. The candidate issued **255** calls for those directories;
the former source issued two calls per row, or **510** for the same scope. This
is a syscall-count reduction, not a paired latency benchmark. All complete
worktree and beacon/runtime profile tests passed locally: **48 cases**, no
skips. The cache-reuse suite initially could not begin because the historical
authenticated .31 parser-test donor was absent at its inherited default path.
The recovered exact APK and original animation pack were then provided through
the existing test environment variables; all **5** cache-reuse cases passed,
without changing or rebuilding either artifact. Namespace/observer/stream tests
also executed freshly against the continuation source: **40 passed**, no skips
(6 namespace, 9 observer, 25 stream). These remain host-only scopes. The initial
fixture error is resolved; it was not converted into a pass or a skip. The
shipping lane must stage those exact historical fixtures and execute its full
applicable gate.

The retained 4,002-leaf host staging fixture measured cold **0.650554 s** and warm
**0.003730 s** in this execution. It compares existing cold mirror work with
existing validated warm reuse; it does **not** isolate the new metadata change
or predict AYN Thor performance. Device latency benefit is unknown. No native
ready, usable-world, FPS, temperature, RSS/PSS or RAM savings were measured.
Removing the repeated metadata call adds no retained cache payload or buffer;
the existing bounded directory/anchor/private inventories still determine
memory use. The physical measurement must begin with THORHERO saved in Kings
Row and distinguish launcher preparation, warm cache checkout, native readiness
and actual world entry.

## Rank 2 authority audit

The isolated BIN observer and namespace audit remain nonshipping prerequisites.
The observer preserves extracted stock decision/IO behavior across 14 cases,
caps observations at 256 rows and retains the binary decoder. Its diagnostic
token is not a provider or content proof. Ordinary UtilitiesLib compilation does
not receive MapServer's private `SERVER` definition, so the staged observer is
not activated in the shipped native consumer.

The owned directory receipt proves safe directory reuse, not every source leaf,
effective native provider, included dependency, matching parser scan set, optional
prefix absence or opened BIN. A file can change in place without changing parent
mtime. Private native BINs deliberately retain precedence. No freshness bypass
or broad production-mode switch is enabled.

The next independent native stage must bind actual ordered roots/Pigs, native
case-folded provider selection and loose overrides to a closed immutable
generation; bind each opened BIN, schema/defines/ABI, full dependency/scan and
optional-absence set; and qualify mutation invalidation/race-safe consumption.
Start with FX or sequencers. Unknown/private/changed BINs retain the full ordinary
loader and decoder. Source-specific observer activation requires genuine Win32
compile, emitted Wine rows, stock/candidate Atlas and Kings equivalence and
measured observer overhead before claiming it supplies native observations.
Do not move a whole-tree rehash onto every map and label the cost eliminated.

## Rank 4 authority audit

The bounded owned stream remains isolated from production PhysX callers.
Its 25 host cases cover C++03 ownership/bounds, actual vendor NxStream headers,
paired allocation accounting and ASAN/UBSAN. LeakSanitizer remains disabled on
this managed host with that limitation explicit. These tests do not execute
SDK cooking/mesh creation or qualify collision parity.

Before integration, audit every real triangle/convex cook/load/export caller,
cooking lifetime and error cleanup; reject stream failures before and after SDK
calls and release rejected nonnull meshes. Bind exact loaded SDK/cooking/loader
bytes and ABI, effective geometry bytes/descriptors/transforms/materials, actual
cooking parameters and cooked output bytes. Authenticate bounded cache input
before entering the legacy SDK, publish privately/atomically, and preserve owned
stock-cooking fallback. A per-stream cap can transiently hold old plus replacement
buffers, up to twice that cap, and does not bound total RSS. Aggregate budgets
need actual mesh measurements. Genuine Wine/native producer/consumer evidence
and Atlas/Kings ground, stairs, walls, doors, movement/combat, monorail, save/reopen
parity are mandatory before any stream/cache change ships.

Rank 2 and Rank 4 remain future independently qualified native changes. Neither
the host prerequisites nor this metadata change establishes physical startup
improvement or the under-30-second target.
