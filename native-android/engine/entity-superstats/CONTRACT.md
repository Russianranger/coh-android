# Raw original supergroup statistics

`coh_superstats_read` reads the whole original `sgroup_sendList` producer wire
body, including financial-only and complete-update branches. Complete updates
include up to150 raw member records, group strings and colors, seven rank names
and four permission bytes each, entry permission, bounded member-rank rows, ten
conditional allies and final alliance talk rank. Byte arrays round the absolute
cursor to the next byte boundary exactly as original `bsWriteBitsArray`, even
when ordinary scalar fields are not byte-aligned. Permission bytes remain raw;
no native permission, member identity, class, origin or rank authority follows.

Output/workspace are fixed caller-owned POD storage; allocate on heap or arena.
All reader/input/output/workspace spans must be disjoint with overflow-checked
bounds. Count and member-rank rows are limited to150 before writes. This is a
local admission limit for member-rank arrays and the source supergroup maximum
for statistics. Every string must terminate within its explicit source storage
bound; names/classes/origins32, member zones256, group name/emblem64, motto and
message256, description512, rank/alliance names64. Refuse oversized data without
truncation. Missing conditional fields remain zeroed, with their presence flags
retained. Unknown IDs and numeric words are retained in original wire order.

Input, output, workspace,4096-byte conservative stack reserve and caller-retained
bytes must fit8MiB. There are no allocations, dictionary lookups or gameplay
changes. Reader/output commit only after the complete producer body validates.
Workspace is scratch. Subsequent bytes remain unread; this is no packet-end or
whole initial update claim.

The qualification provider executes the whole unchanged original producer and
compares all fields against an independently bounded model. It does not execute
the original `receiveSuperStats` consumer. That executable original consumer
qualification remains outstanding and is recorded as false in native receipts.
The source original bitstream/type definitions, rank/permission layout and
producer are pinned. Release/ASan/UBSan native tests compare180 exact producer
fixtures across both alignments, update/financial branches and150 members.
Selected large fixture truncations are sampled every13 bits plus last-bit cuts
for every fixture; byte mutations are sampled every31 bytes. Budget, alias,
malformed count and random-input rollback are checked. C++ linkage and emitted
reachable stack reserves are checked separately. Original source oracle itself
runs unsanitized with explicit fixture storage callbacks.

This source-qualified raw stager has no enclosing ALLENTS acceptance, selected
character identity, dictionary admission, Android execution, authoritative actor
publication, initial-update acknowledgment or live server qualification.
