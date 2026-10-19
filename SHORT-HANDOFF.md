# CoH native: FileListRead stage

native-android ONLY; baseline aae99208. Thor 13/ARM64.
Thor 0.1.9 INITIAL_OBSERVED; both sockets closed. ZIP CLOSED means cleanup.
Gates 1–24 preserved; 25–27 open. No broad suites replayed.

ONE: whole original FileListRead + FileListCreate/serialize helpers.
SerializeReadOpen is a dependency; accepted test mains not replayed.
Pinned ParserLoadFiles NULL tuple/caller order audited only; actual callers
and ParseTableCRC unexecuted. CLIENT BodyParts.bin 2584B/b0955c... hashed:
header end20/list end64, BEFORE body size/records. No current Map proof.

NULL skip ignores tag/count/entries: count_observed=0, never verified empty.
Only complete nonnegative skip extents supported. Fresh COLLECT cap16 is
native policy. Source order/duplicates/slashes/raw dates/seen0/NUL prefixes/
padding preserved. Paths>=260 become empty after skip. No FileListInsert,
normalization/date lookup/filesystem validation.

Complete entered-field preflight; original accounting rejects and partial
nodes stay scratch. Fixed owned buffer/calloc/earray/growth, little-endian/
time32 host adapters; atomic output and volatile cleanup. Numeric oversized
Pascal warning observer. Input<=64KiB; existing app limits unchanged.

Release/ASan/UBSan each 4,917 checks/124 fixtures; 16 source inputs and compiler/
Python stable. Measured fixture source/input/build/profile/run bindings only.
Qualifier: engine/body-catalog/check_file_list_read.py.
Receipt: qualification/file-list-read-20261019/host.json.
CI: Native FileListRead dependency stage. No Map/Thor run or APK.

ALLENTS41/43 and dictionary-index stops intact. Catalog/default/generation/
character/ownership/actor/ACK/world false. 4MiB input/192B child/7,168B report,
overflow guard/socket cleanup and Combined0.1.9/imports/signing/profiles/saves
preserved.

Next ONE: bounded original body-read composition. Current Map loaded-input/
source/build/profile/run provenance required before admission. Fetch latest,
read both handoffs and preserve all bans.
