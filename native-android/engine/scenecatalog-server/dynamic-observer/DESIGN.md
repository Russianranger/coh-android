This is a source-backed design for a new isolated observer. No implementation,
build, capture, runtime admission or change to the accepted GROUPS sink/PE is
included. The exact source/native capture already in progress remains intact.

The missing value is the ordered mapping from `dyn_groups[index].tracker` to a
real world occurrence. `Common/group/groupdyn.c::findBreakable` appends the
actual `DefTracker`, not its `GroupDef`. Its traversal uses
`grouputil.c::groupProcessDefTrackerHelper`: process, then `trackerOpen`, then
ascending actual `tracker->entries[0..count)`, starting at ascending root slots.
`grouptrack.c::trackerOpen` returns immediately when entries already exist;
otherwise it may invoke lazy loading before creating children. Definition DAG
preorder and the number of reconstructed runtime instances do not establish
this incidence or its order.

The current COHGTX01 body set contains no tracker parent/entries/count/dyn_group
or `dyn_groups` array. COHRTS01 records roots and definition closure; its named
breakable flags cover external definitions only. COHRBW01 records raw 60-byte
prefixes only for public regular definitions and deliberately keeps their native
flag word opaque. Even recovering every definition flag cannot recover an
already-open tracker tree. Existing data therefore cannot certify the dynamic
index mapping. A wire-declared uncompressed length can bound a diagnostic count,
but does not supply occurrence ownership.

The smallest complete witness should observe the actual array used by the
actual full `groupDynSend`, without replaying `findBreakable` or rebuilding its
list. A separate observer stage should patch only an isolated source checkout
and add new files in this directory. It should include the accepted observer
sources unchanged and emit a separate private sidecar; COHGTX01's existing
format, parser, sink and accepted PE remain unchanged.

The proposed producer has four narrow source seams:

1. At the real `groupDynBuildBreakableList` entry/normal completion, maintain a
   nonshipping monotonic build sequence and an in-progress/refused state.
   Record the existing server `groupDefVersion` too. These are observed process
   counters, never caller-provided generation authority. The hook must see all
   ordinary startup/reset/direct rebuild calls, not install after the first
   build has already completed.
2. In the new GROUPS wrapper, remember the actual successful full GROUPS owner,
   local observation ID and source packet association. Retain no exported
   pointer addresses. Further observation is eligible only for that same
   original link/client/entity/world and completed source build sequence.
3. Immediately around the real full `groupDynSend(pak, full_update)` call in
   `MapServer/src/entity/entsend.c::entSendUpdate`, observe the exact dynamic
   bit-span start/end and complete source array/status values. This is after
   the selected owner and full-update command have been established. Synchronous
   output callbacks only copy/write; no engine callback, load, tracker open,
   rebuild, yielding or mutation is permitted. Recheck array/count/build/owner
   and the rows before/after the original producer call.
4. Complete the packet observation in `entFinishUpdate`, immediately before its
   actual `pktSend(&e->entityPacket, client->link)`, after the terminating zero
   command. `entSendUpdate` alone is too early: it assigns `entityPacket`, and
   later source code may append byte-aligned commands before final send. Copy
   the exact final logical packet and its bit/alignment/compression metadata.
   Require the same owned packet and selected source owner; a replaced packet,
   failed source traversal, closed link, owner/build change or reentrancy aborts
   only the new provisional sidecar. No existing GROUPS witness is revoked.

The sidecar must contain the complete actual array, including an explicit
zero-count case. No selected first N rows or successful-only subset qualifies.
For every zero-based dynamic index, record:

| Data | Source-backed purpose |
|---|---|
| index and `tracker->dyn_group` | Witness exact array order; require one-based tracker value `index+1` |
| root slot and actual child-index path, with the real child count/presence and definition identity at every path step | Distinguish repeated instances and preserve already-open child incidence independently of definition DAG edges |
| canonical regular file/slot or admitted external identity and name | Join the same GROUPS catalog/runtime snapshot without interpreting pointers as IDs |
| named `breakable` / `child_breakable`, def and tracker modification values | Preserve actual source decisions and reject stale/unbound state |
| exact tracker world matrix | Bind the occurrence transform; counts or names alone are insufficient |
| raw source status byte plus named HP/repair | Bind the dynamic wire status to that exact ordered occurrence |

Build the pointer-to-index lookup internally from the complete actual array,
then enumerate the existing rooted tracker tree using real root slots and
existing child arrays only. Comparing array pointers to those known rooted
occurrences avoids dereferencing an unvalidated arbitrary array target. Keep a
bounded path stack, detect cycles/aliased roots/duplicate array targets, require
parent incidence and complete array coverage, and reject ambiguous or unreachable
targets. Do not call `trackerPack` with name allocation, `trackerOpen`,
`groupLoadIfPreload`, or `groupDynBuildBreakableList` from this observer. No
pointer/address is serialized. A sparse ordered row stream plus bounded internal
membership workspace is enough; the entire unrelated tracker tree need not be
exported.

Path steps may share a compact parent-ordinal ledger rather than repeat all
ancestors in every dynamic row. They must still represent actual tracker child
counts and identities, not claim those are the corresponding definition-entry
counts/order. Every referenced definition must resolve to the same coherent
retained regular/external catalog or refuse. A native consumer must not replace
these actual paths with definition preorder or apply statuses to its runtime
graph unless that distinct occurrence association is independently verified.

Use the current native limits as refusal ceilings: at most 65,536 dynamic rows,
100 path edges (matching original TrackerHandle capacity), explicit aggregate
visited-node/path-work limits and a bounded sidecar/file total. Traversal and
internal membership storage must be charged before output. These are observer
budgets, not whole-process RSS claims. Choose concrete visited/work/byte limits
only when implementing against the actual corpus; do not truncate on excess.

The actual Win32 build must qualify `sizeof(DynGroupStatus)==1`, seven HP bits,
one repair bit and their raw-byte packing with compiled probes. `groupDynSend`
passes `dyn_group_count*sizeof(DynGroupStatus)` raw bytes to `pktSendZipped`.
The native consumer should compare its exact expanded dynamic span to all
observed raw status bytes, with exact zlib end/input/output and the full array
count. This proves the packet's statuses use the captured order; a count match
alone does not. The ordinary whole-initial parser can then consume the exact
source count diagnostically while ownership admission remains a separate step.

The new private sidecar should have fixed versioned framing, complete row and
path counts, source build/reset observations, the old GROUPS observation/owner
association, the actual dynamic span, the final original ALLENTS packet and a
commit-last footer. Flush/close/rename exclusively after source rechecks; bound
all partial output, preserve existing files, and independently attempt rollback.
Its source/PE/run bytes and all data hashes must be externally admitted. Compare
the final original ALLENTS logical bytes/bits/profile to the actual same-owner
native `initial-update.bin`; compare the prior original/native GROUPS witness
through the existing source admission. Never associate captures only by equal
count, name CRC, matrix checksum or a caller-supplied map/generation label.

This witnesses the complete array actually used by the sender. It does not claim
that replaying the build algorithm from a definition DAG would produce that
array, or that the array remains valid after source release. If an implementation
instead chooses a verified rebuild contract, it must separately prove the real
lazy-load and existing-tracker state at every build decision; it cannot infer
those facts from the current envelope.

A later sidecar from another process/run must not be attached to the existing
raw initial packet as historical ownership. If this missing observer requires
a future source build/capture, it is a new missing-input transaction, not an
export retry or repetition of successful catalog milestones. Existing GROUPS
source generation keeps its immutable point-in-time scope. New sidecar parsing
alone leaves source generation, current tracker lifetime, dynamic world
application, actor publication, READY/received-character/full-update ACK and
world authority false. Raw generic outputs stay private; any fresh-fixture-only
export requires separate explicit review.

Required focused controls for implementation are repeated definitions at
different paths, already-open child order differing from definition order,
lazy/preload refusal without invoking loaders, zero/count-cap cases, root holes,
duplicate/unreachable/cyclic targets, inconsistent parent/dyn_group/modification
values, wrong matrix/definition identity, source array/status changes between
producer hooks, replaced final entity packet, exact final packet/native pairing,
and short-write/flush/close/rename rollback. No actual run is authorized by this
design.
