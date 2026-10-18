# Complete Details cached geometry groups

The existing Salvage/Details and BaseDetail inventory owners retain definition
names and ID identity. They do not expose the six persisted geometry group names
needed by a future base scene resolver. This standalone bounded owner reads every
field of the complete original Details Parse6 BIN body and copies those six
resource names, definition name, surface and mounted/animated flags. It changes
neither accepted owner and does not bind a current character/world generation.

A successful original `ParserLoadFiles` BIN read returns before
`DetailDictPreprocess`. That preprocessor runs when loading text before writing
a cache. Consequently this BIN owner preserves `_f`/`_w`/`_c` roots, leading `*`,
explicit variants, `dim`, empty values and surface=-1 exactly as persisted.
Applying suffix generation or surface inference here would change 33 root names
in the authentic input and would misrepresent the original cache-hit branch.
Native flags preserve original U8 truncation. Original empty indirect-single
strings become NULL; copied empty refs are absent. Every one of the 47 persisted
fields, complete record lengths, file ledger and final end is validated. Arrays
and unrelated fields remain opaque. Text preprocessing, CLIENT unused-field
pruning, post/finalizers, group loading, materials and actor publication do not run.

The copied owner retains complete input SHA256 and caller-admitted provenance.
The caller must independently admit those identities; an arbitrary expected hash
cannot authenticate a resource archive. Row ordinals preserve full Details order
including duplicate names; no name hash, inventory ID or geometry membership is
invented. Getters return borrowed immutable owner slices. Empty fields return
NOT_FOUND. `dim` remains explicit data and is not treated as a group to load.

Native refusal policies are 4096 rows, 512KiB complete input and copied text,
8MiB total read/comparison/poll work, 8192 array elements, source Pascal strings
under 12000 bytes, ASCII definition keys under 128 bytes and resource names under
1024 bytes. The complete 16MiB aggregate charges input/config/provider/control/
contexts/output/workspace, declared callback scratch/stack, 16KiB native stack and
caller-retained old owners before callbacks. No heap allocation occurs. Output
commits only after full parsing, input hash and final cancellation. Valid callback
errors keep their first status; out-of-domain digest errors become COH_INVALID.
Scratch may be partial after refusal. All source/provider leases can retire after
success. These are child policies and caller accounting, not process/RSS/GPU or
global 96MiB fit claims.

Run only the new checker:
`python3 native-android/engine/basedetail-resources/check_resources.py --details-bin DETAILS --output NEW_DIR`.
It admits the exact retained complete original 401216-byte Details body with
SHA256 `11e5104e0210fa5cbbc910932e5df461a34853e9a30d43f890d31510cdf2ce28`.
It compares canonical complete projected rows with the whole original BIN table
reader on explicit bounded host storage. Whole original loader functions and
`basedata_Load` are independently hashed, unexecuted source witnesses for the
cache branch; an ordering guard confirms the early successful-BIN return before
text preprocessing and cache writing. The host string adapter follows original
empty indirect-string policy. Original stash/allocator/ABI/geometry are not
reproduced. Release/ASan/UBSan target only the new module/test and immutable
headers; old qualifier entrypoints do not run. The original comparison is
unsanitized; native leak detection is disabled. Source bytes, fixture and
binaries are bracketed. No Thor/Android/current CLIENT/world acceptance or APK
change follows from host qualification.

Earlier source-algorithm experiments are preserved separately with an explicit
scope correction: their preprocessing comparison passed, but that transformation
is inappropriate for the successful BIN consumption branch and is not admitted
as resource integration.
