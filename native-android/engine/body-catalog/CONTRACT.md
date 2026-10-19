# Body-catalog bone enum prerequisite

This milestone qualifies the generated enum provider required by the original
`ParseBoneNames` postprocessor. It does not admit a runtime body catalog or
advance the initial ALLENTS parser past `FIRST_BODY_CATALOG_REQUIRED`.

The source body-type table/count was already qualified by costume-import work.
The missing executable prerequisite here is `BoneIdEnum`: original `bones.h`
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

Qualification stops before executing ParseBoneNames, loading body-part files,
the costume parser/importer or a MapServer transaction. The original callback,
selected body-part parser/cache inputs, initialization order and complete
source/build/profile/run association still require evidence. Existing authentic
CLIENT cache bytes and their row count cannot substitute for current server
postprocessing or source-owned runtime catalog provenance.

The generated enum is an executable source prerequisite, not a costume
dictionary generation or an authenticated runtime dictionary. No packet, Map,
session or build counter becomes such a generation. Body/default catalog
admission, complete character, selected ownership, source generation, actor
publication, application ACK and world authority remain false. Existing
dictionary-index stops, cleanup and resource limits are unchanged.

Run only `check_bone_enum_provider.py --sanitize --output NEW.json`, optionally
with `--evidence-directory NEW_DIRECTORY`. Full evidence belongs in the focused
workflow artifact; the repository retains its compact receipt. No accepted
generator/compiler, renderer, transport, JNI or Android13 suites are replayed.
