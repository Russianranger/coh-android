# Standalone original title update

`coh_ent_titles` decodes the full original `entReceiveTitles` substructure,
starting at its presence flag. This closes one very-rare source branch as a
standalone staging interface. The entity-record parser still refuses very-rare
records; no record/full-character admission, acknowledgment, title localization,
selected-player identity or rendering is enabled.

The exact source order is presence, name, packed title selection, optional
article/common/origin strings, two automatic color integers, badge word,
optional special title, glowie flag, gender/name gender, article flag, respec
tokens, turnstile event/mission and automatic helper status. Original endgame
raid producer behavior writes zero event/mission values. All 32-bit words retain
their wire bits, including values that the original stores in signed `int`.
Title, badge, color and helper values are metadata, not resolved resources or
validated gameplay privileges.

Original capacities including NUL are 128/10/32/32/128 bytes for
name/article/common/origin/special strings. Native code rejects oversized input
rather than reproducing legacy truncation. It rejects malformed scalar high
bits in byte-aligned mode, missing terminators and every truncated field.

The API borrows the packet only during the call and allocates nothing. A
388-byte candidate is parsed locally before reader/state commit. Source absence
retains prior state; source presence clears absent optional strings. A packet
older than the prior title packet is fully validated and consumed without
changing state. Equal packet IDs apply, matching the original titles-specific
`IS_OOP(x) (pak->id < x)`. Nonzero packet IDs are required, and unsigned comparisons
do not guess wraparound. On every parsing failure both reader and prior state
are unchanged. Failure receipts contain only stage/status/bit offset.

The owning entity transaction must reset this POD for a new entity/session
generation, validate selected DBID and unique owner, and publish it only with
all other complete actor data. The name is descriptive and cannot replace DBID
identity. API arguments must not alias one another. Store the candidate alongside
the existing transaction rather than duplicating large appearance events in all
entity slots. Discarding the candidate provides rollback; accepted clients and
APKs are untouched.

## Qualification distinction

The pinned producer has no standalone title function. The oracle extracts its
**unchanged title statement block** from `sendEntity` and places it in a small
function with source-shaped entity/player storage. This is independently
executed original source code, but is not execution of full `sendEntity`, its
outer rare-bit decisions, a full record or `entSendUpdate`. The complete original
`entReceiveTitles` function executes unchanged. `titles_oracle_shim.h` supplies
deterministic array storage, bounded trusted string/copy adapters and a raid
configuration flag. The original BitStream readers/writers and automatic integer
functions execute unchanged. Source block/function SHA256 values appear in the
host receipt, alongside all original file pins and oracle/native source hashes.

Fifty-four source-produced fixtures cover absence, empty fields, populated
metadata, source-capacity strings, mixed optional fields, all automatic integer
widths, signed integer bit patterns, raid zeroing, both alignment modes and all
ordinary starting bit offsets. Each is compared with the original consumer for
older/equal/newer packet IDs (162 comparisons). Native tests exercise every
truncated bit for all three freshness cases, sequential clear/retain behavior,
explicit reset, trailing transaction boundaries, byte mutations and 20,000
deterministic random malformed inputs. Separate manually assembled malformed
fixtures use original scalar writers and deliberate byte-width values; they are
not counted as complete original title producer output.

Release, ASan and UBSan qualify the new native code; original historical writers
run separately at `-O0` on trusted padded buffers. No authentic server title
capture or complete source initial-update oracle is claimed. Android build and
execution belong to the coordinator's consolidated qualification; this host
checkpoint does not by itself establish Android or physical acceptance.
