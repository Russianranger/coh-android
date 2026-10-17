# Complete small original costume input bodies

Implemented: complete bounded Parse6 envelope/body decode for original
ParseBodyPartBegin/ParseBodyPart and ParseColorPalette/ParseColor. Exact recovered
CLIENT-generated BodyParts.bin and supergroupColors.bin produce28ordered body
parts and160ordered float RGB records. No dense costume stash list is produced.
The full costume.bin decoder, original stash construction and matching live
server generation remain separate prerequisites.

Inputs come from run36707839624 artifact11092897979. The committed exact subset
ZIP350c7ad531209a7e3959cb2f4ae044d8551820cc03e9d40ce17c3aae2a5e3241
is verified before extraction, and each raw member is verified against the
independently preserved manifest SHA/size. Actual body bytes are consumed by
UNCHANGED original ParserReadBinaryTable, primitive string/int/U8/float handlers,
nonarray/fixedarray/earray/struct handlers and the actual source tables. Original
ParserWriteBinaryTable and unchanged writers reproduce the complete authentic
files, including retained exact source envelope prefix, byte for byte. Original
writers also generate deliberately changed finite scalar/string fixtures; the
unchanged original consumer redecodes those and supplies complete field-by-field
native expectations. Source oracle runs valid data only. It does not claim
original consumer malformed-input safety.

The oracle's host ParseTable/layout macro bindings, TokenStore field/allocation
adapters, handler registry dispatch and bounded SimpleBufResize backing are
explicit shells. Actual binary-handler and table logic is original. Original
SimpleBufRead/Write/Seek/Tell and Pascal string logic execute unchanged, with
source little-endian scalar inline functions. Exact token/storage/registry files
are pinned. It is not the whole original engine or Win32 ABI execution. Original
runtime memory layout is not inferred from these host structs. Original
ParseTableCRC is NOT recomputed; native compares the actual captured schema CRCs
cf27aba3 (body parts), f0095ef2 (palette), source qualified by pinned table/reader
execution and exact donor identity.

The native module copies all strings and raw U32/float words, retains table/slot
order and exact serialized fields. Duplicate BoneCount entries are retained as
first and last rather than dropping the first original write; the original
TokenStore consumer's final field value is the later one. DontClear retains its
full serialized word; source application narrows to U8. Bone numbers and
bodyPartIndex are RAW values stored in the cache, not postload callback results.
Dependencies, timestamp words, CRC and digest remain in the result. Pascal
padding is skipped as original reader does; bytes remain covered by the entire
input SHA. Embedded NUL and strings>=260 are refused as a narrower diagnostic
profile, rather than claiming the original consumer has these exact bounds.
All color float words must be finite; no RGBA conversion, clamping, rounding,
palette insertion or geometry interpretation occurs here.

Bounds:64KiB entire file,16dependency records,29body-part rows,256colors,259bytes
per copied string. These are explicit diagnostic admission bounds, not raised
original capacities. Full original costume.bin is refused under this module's
size/schema scope. Root/child record byte totals, all counts and complete input
end are checked. A malformed child cannot publish earlier rows. No allocation,
retained input pointer or callback during parsing. Only after complete syntax is
whole-input SHA checked with the caller's independently qualified provider;
output commits atomically. Workspace is caller-owned/off-stack and may change
on refusal. Input/expected hash/provider/context/output/workspace ranges must be
pairwise disjoint (including overflow); immutable inputs persist through the
call. Named budget<=1MiB includes complete spans,16KiB native stack reservation,
declared callback scratch/context and caller retained memory. Callback external
stack/sanitizer closure and LeakSanitizer qualification remain false; existing
container restrictions apply. Results own only inline copied values.

Remaining exact source callback gate: bpReadBodyPartFiles uses ParseBoneNames,
which rejects count>=MAX_BODYPARTS=30, assigns ordered indices and resolves
name_geo or name_geo+R/L through bone_IdFromName. That function calls
StaticDefineIntGetInt(BoneIdEnum,...). The generated AutoGen/bones_h_ast.c table
is not present in the inspected original source tree. This tranche does not
fabricate that generated dictionary, execute ParseBoneNames, or relabel cached
raw bone words as its results. Palette addPaletteToTables/getRGBAFromVec3 and
costume preprocess/fillExtraData/order/hash/resize require their own complete
source qualification before any authentic runtime stash-generation claim.

original_callbacks_applied, authentic_stash_slots and actor_authority remain0.
No original server, world capture, workflow, Android build/execution or physical
Thor test occurs. The existing importer/exporter and protected appearance paths
are unchanged by this module.
