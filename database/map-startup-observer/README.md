# Nonshipping BIN freshness observer prerequisite

This isolated overlay advances the rank 2 namespace/BIN work without altering
the published 0.13.32 APK, qualified native binaries, assets, or loader behavior.
No shipping workflow consumes it. It creates neither an effective-provider
generation nor a certificate and does not bypass freshness validation.

`tools/prepare_map_startup_observer_source.py --source-staging /absolute/isolated/tree`
applies to an existing isolated native source staging tree whose parser and six
retained provider/consumer files match the immutable source exactly. It refuses
the repository root, immutable upstream, linked paths, changed source and repeated
application. Its receipt pins the original/patched parser, overlay, retained
provider sources, unchanged binary decoder, and the explicit nonshipping contract.

For SERVER compilation only, `ParserIsPersistNewer` emits at most 256 bounded
`COH_MAP_BIN_FRESHNESS_V1` rows, one per observed call, covering schema/open,
dependency-table read, top-level membership scan, dependency-date checks,
optional-prefix presence/membership, and cleanup/seek. Rows identify an input by a
bounded diagnostic token; that token is not an integrity hash or provider proof.
Production's existing short circuit is labeled `production_assumed`; it must not
be mistaken for successful dependency verification. Timer failure/backward time
sets `clock_valid=0` and zeros every phase. After the cap, timing and logging stop.
The observer adds no filesystem reads or explicit heap allocations. Logging/CRT
may allocate, and logging and clock calls have overhead; the host fixture does not
measure these native costs.

The current CMake `UtilitiesLib` target compiles `textparser.c` without SERVER;
MapServer's private SERVER definition does not propagate into that static
library. A normal native build therefore will not activate these observations.
No build definition is changed here. A future isolated native qualification lane
must review a source-specific SERVER definition/adapter for the parser translation
unit, verify any affected included-header semantics, and prove actual emitted rows.
Do not define SERVER broadly on all UtilitiesLib sources or claim activation from
staging alone.

The extracted actual native C stock and instrumented functions run against the
same bounded IO adapters. The fixture compares returned handles, the exact loader
IO call sequence, scans/date checks, close/seek counts and list mutations across
14 cases: bad open/schema, bad dependency table, changed dates/includes, removed
dependencies, added/deleted matching sources, the stock one-hour date rule,
production, optional prefixes, include-only input and empty dependencies. It also
checks the observation cap, failed/backward clocks, inactive finish and non-SERVER
no-op behavior. Windows QPC is adapted for host execution. This is algorithm/source
qualification, not an actual Win32 build, complete MapServer/Wine execution,
collision parity, native timing or physical Thor validation. The binary decoder
is byte-retained and its decode/fallback costs are outside this observer's scope.

Next gates are actual Win32 compilation, stock/candidate Atlas and Kings startup
and fallback equivalence under Wine with these phase rows, observer overhead and
native lifetime proof, then controlled physical fresh/warm comparisons. Do not
publish this observer as a startup optimization. Build the complete native
ordered-root/Pig/case-folded effective-provider generation, mutation invalidation,
and per-BIN scan/include/optional-absence certificates only after that evidence;
unknown/private/changed BINs must retain the ordinary loader and all decoder checks.
