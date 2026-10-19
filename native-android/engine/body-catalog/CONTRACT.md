# Body-catalog bounded callback qualification

This milestone executes the unchanged original `ParseBoneNames` callback in a
bounded source profile using the accepted generated enum provider. It does not
admit a runtime body catalog or advance the initial ALLENTS parser past
`FIRST_BODY_CATALOG_REQUIRED`.

The source body-type table/count was already qualified by costume-import work.
The accepted enum prerequisite is `BoneIdEnum`: original `bones.h`
marks `BoneId` with AUTO_ENUM, and the original `bone_IdFromName` uses that
generated table through the original StaticDefine lookup functions.

The provider builds the repository's StructParser target from pinned source,
runs it over an isolated exact copy of the original header, and consumes its
actual emitted table. No lookup rows are handwritten. Original enum values,
row order, prefix handling and aliases remain source-derived. The generator's
source closure and output bytes, executed compiler/tool identities and the
standalone lookup source are retained as qualification evidence.

The standalone lookup uses the complete source StaticDefine/StaticDefineInt
layout, including intptr_t and the display field. Original lookup functions
remain unchanged. Platform adapters and excluded dynamic-list/debug profiles
are explicit. Host layout and optimized aliasing assumptions are qualified
only for this source-provider profile; they do not establish the original Map
executable's ABI or the Android device's ABI.

COUNT is a source sentinel outside the valid bone-index range. INVALID and
unknown names return -1. DEFAULT is the source alias for index0/HIPS and must
not acquire an invented refusal. This bone alias supplies no costume default
part count. A successful source lookup does not resolve a rig/asset or apply
actor, character or world state.

The qualification input profile allows ASCII queries up to259 bytes, at most
256 rows and4,096 queries, a2MiB fixture and a4KiB numeric result. Embedded NUL,
non-ASCII, excess lengths and overlapping output refuse without changing caller
storage. These are qualification bounds, not new original lookup grammar.
The generated table file is checked against64KiB. None of these limits changes
the existing packet, report, dictionary or cleanup limits.

The current callback input is the exact retained authentic CLIENT BodyParts.bin:
2,584 bytes, SHA256 b0955c46731ed0cb54ad01d96015b301e583bd0224f8d872f50cfefeb08f6beb,
from the committed deterministic subset archive whose origin/recovery was
previously verified. This qualifier verifies that exact archive/blob and member
again; it does not regenerate or substitute caches. Each native mode uses the
unchanged qualified native decoder and compares every raw field of all28 rows
against an independent projection of these trusted bytes. Derived expectations
come from the independent source enum, not cached bone/index values.

`parse_bone_names_provider.py` emits complete original BodyPart/BodyPartList
declarations and unchanged whole ParseBoneNames/GetBodyPartCount. Its input
adapter passes callback-relevant geometry, bone count and raw derived fields;
unused full-struct fields are neutral fixture data. The name field aliases the
owned geometry for an unreachable fatal-message path. This does not qualify a
full-record roundtrip, original earray allocator or Win32/Android object ABI.

Complete preflight precedes every original mutation. The fixed qualification
profile allows at most29 rows; original MAX_BODYPARTS aliases MAX_COSTUME_PARTS60.
The existing import1..29/native limits are unchanged conservative policy, not
that original fatal threshold. num_parts must be1 or2. ASCII names exclude
embedded NUL and allow259 bytes for single bones,126 for pairs:126+R/L+NUL fits
the original128-byte temporary buffer. All caller row/name/output/receipt spans
must be disjoint as specified by the API. Source global/argument list consistency
is constructed by the owned fixed adapter; an association flag is a profile
condition, never authentication or selected-character ownership evidence.

Unknown names remain-1; COUNT and DEFAULT keep their raw source values. Original
bone-validity fatal checks are commented out, so the wrapper adds no validity
filter. Single-part rows preserve their second raw bone. The callback sets each
row index and resolves one or two names. Its return1 means callback completion
only. The original getter's observed count comes from adapter-owned callback
rows; it is not a genuine MapServer count or costume default. Outputs commit
only after completion; preflight refusal leaves caller storage unchanged.

The adapter runs in an isolated single-thread source profile, uses fixed owned
rows/pointers/names, clears global metadata, and uses volatile byte writes to
wipe temporary storage. The inherited enum/platform adapters remain explicit.
Exact source pins, compiler identities, stable inputs and bounded native frames
are recorded. External libc/crypto sanitizer/stack closure and global/device RSS
are not established by those frame measurements.

Qualification still stops before original Parse6/ParserLoadFilesShared loading,
full initialization, the costume importer or a MapServer transaction. CLIENT
callback results cannot substitute for current server postprocessing or complete
loaded-input/source/build/profile/run association. A runtime catalog/default,
dictionary generation and application acceptance remain unavailable.

The generated enum is an executable source prerequisite, not a costume
dictionary generation or an authenticated runtime dictionary. No packet, Map,
session or build counter becomes such a generation. Body/default catalog
admission, complete character, selected ownership, source generation, actor
publication, application ACK and world authority remain false. Existing
dictionary-index stops, cleanup and resource limits are unchanged.

Run only `check_parse_bone_names.py --sanitize --output NEW.json`, optionally
with `--evidence-directory NEW_DIRECTORY`. Full evidence belongs in the focused
workflow artifact; the repository retains its compact receipt. Accepted enum
generation is reused as a dependency; its old checker/native suite is not replayed.
No general compiler, renderer, transport, JNI or Android13 suite is replayed.
