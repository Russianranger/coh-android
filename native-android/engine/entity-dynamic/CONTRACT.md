# Bounded dynamic-group wire diagnostics

`coh_dynamic_diagnostic_read` stages the whole original `groupDynSend` producer
wire body. A full update has the packed all-ones marker, packed compressed and
raw sizes, mandatory byte alignment and zlib payload. A delta has an ordered
count and index/7-bit health/1-bit repair records. Duplicate delta indices are
preserved in wire order. No prior state or dynamic graph is updated.

The caller's `expected_count` is an explicitly unauthenticated diagnostic bound.
Full raw size must equal it, delta indices must be smaller, and both count and
rows are locally capped65536. `world_ownership_verified` always remains zero.
A numeric count, even nine, never establishes original runtime generation,
root ownership, tracker occurrence order or graph identity. Those require the
separately captured and verified immutable scene graph occurrence binding.
This module cannot publish a dynamic world or authoritative actor.

Compressed input is limited1MiB. zlib must reach exact stream end with exact
compressed input consumption and exact expected output bytes; trailing streams,
extra decompressed bytes, truncation and malformed envelopes fail. A one-byte
output sentinel bounds and detects expansion past the expected byte count.
All zlib allocations use a fixed256KiB aligned workspace arena with bounded
multiplication/alignment checks and no system allocation. Failed decoding leaves
workspace scratch only. Arena bookkeeping resets for every full update; frees
are no-ops within that single-call arena lifetime. The caller retains all arena
storage, so no library allocations leak or escape after inflateEnd.

Reader, input, output and workspace spans must be disjoint and overflow checked.
Allocate the large fixed PODs on heap or arena. Input, both PODs, fixed zlib arena,
4096-byte native wrapper stack reserve and caller-retained bytes count once
within8MiB. This excludes unmeasured external zlib stack and does not qualify a
whole-dependency working-set budget. Reader
and output commit only after the entire subtransaction passes. Subsequent
sky/slave/outer commands remain unread. No packet-end assumption is made.

F's provider executes whole unchanged original groupDynSend, pktSendZipped,
pktSendZippedAlready, bitstream and source bitfield definitions with synthetic
status/tracker arrays. Its independent bounded diagnostic zlib decoder supplies
160exact fixture projections. The original gameplay consumer is not executed.
Native release/ASan/UBSan compare every raw status and delta field, both modes,
full/delta/empty branches and cursors, all selected zero-offset truncation bits,
byte mutations, trailing data, wrong diagnostic counts, aggregate limits, aliases
and rollback. C++ linkage and conservative emitted stack reserves are checked.
Host system zlib and Android platform zlib are separate dependencies; Android
execution is recorded only if actually run. Original source oracle is unsanitized.
The exact linked host zlib library hash/version/flags are recorded. That external
library is not rebuilt with sanitizers and its internal stack is not measured;
the emitted stack check covers native wrapper functions only. Dependency stack
and sanitizer closure therefore remains false, independently of native tests.
No authenticated world count, dictionary, whole initial update, actor, ACK or
real-server acceptance is qualified here.
