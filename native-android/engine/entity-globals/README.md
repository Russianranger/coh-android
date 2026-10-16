# Standalone power-mode global update

This additive module decodes the complete, unchanged-source-defined
`entity_SendPowerModeUpdate` / `entity_ReceivePowerModeUpdate` grammar from
`Common/entity/PowerInfo.c`. It is a bounded staging component, with no enclosing
ALLENTS integration, renderer connection, dictionary lookup or acknowledgment.

The source sends one presence bit. An absent update preserves the previous list;
a present update sends a pack3 count followed by that many pack3 mode IDs and
replaces the entire list. A present empty list clears it. The decoder preserves
32-bit source integer bit patterns, order and duplicates. IDs remain unresolved
metadata. A local cap of 1,024 entries bounds work and memory; this is an explicit
admission policy, not an original server capacity assertion.

`coh_global_power_modes` consumes exactly this body at the current reader cursor
and leaves following fields unread. Reader, state and event are transactional:
all three remain byte-for-byte unchanged on invalid input, truncation, overflow,
excess count or overlapping memory. An accepted present replacement zeros unused
slots. An absent update preserves even unused prior state bytes. There is no
allocation or retained input. Callers must serialize access to the mutable inputs.

`CohPowerModes` occupies 4,100 bytes. Parsing uses one local 4,100-byte candidate
plus a reader copy and scalar locals. A caller preserving old state while parsing
into a separately staged candidate must reserve 12,300 bytes for these three
mode-state copies, plus reader/event/input and enclosing transaction memory.
The borrowed replication reader keeps its existing 16 KiB ordinary body limit,
or its explicitly initialized bounded limit up to 4 MiB. This parser does not
allocate, copy or retain that body. Source producer/consumer shells are test-only.

## Source and qualification

`source-pins.json` binds LF-normalized original source files. `check.py` extracts
and executes both complete power-mode functions unchanged, along with original
BitStream readers/writers. Non-debug packet wrappers and a fixed owner/earray
shell supply test storage. The shell is not the original earray allocator, and
no power dictionary or eligibility rules are exercised. The original host oracle
runs at O0 on trusted padded fixtures without sanitizers. The new native parser
is independently run in release, ASan and UBSan modes.

The 110 producer fixtures cover normal bit positions 0–7 and source byte-aligned
positions 0 and 8; no update; empty replacement; pack3 boundaries; full raw 32-bit
IDs; duplicates; and the 1,024 admission limit plus one. One hundred supported
fixtures are compared with the unchanged original consumer's complete output and
final bit cursor. Ten over-limit source fixtures are rejected without invoking
the original consumer. The original producer's dirty-flag clearing is checked.
Small fixtures have every truncation tested; large fixtures test the first/final
96 bits and every 97th intermediate bit. The suite adds 25,000 deterministic
random inputs, malformed pack overflow, strict byte-aligned booleans, disjoint
memory refusals and byte-exact rollback. A real C++ executable links the C99 API.

Run from this checkout:

```sh
python native-android/engine/entity-globals/check.py \
  --source-root . --sanitize --output /tmp/entity-globals-host.json \
  --fixtures-output /tmp/entity-globals-fixtures.h
```

Optional `--ndk /path/to/ndk --android-output /tmp/entity-globals-android`
builds both ARM64 and x86_64 standalone executables and records their hashes.
Those receipts say `executed: false`; a build is not an Android execution result.
The root coordinator owns shared workflow admission and emulator execution.
Source revision/tree, clean-state flags, native input byte hashes and generated
fixture identity are retained separately. Qualification is specific to this
subgrammar; it is not real server interoperability or physical Thor acceptance.

## Enclosing transaction and next grammar audit

Pinned `MapServer/src/entity/entsend.c::entSendUpdate` and
`Game/src/entity/entrecv.c::entReceiveUpdate` place the independent
`PowerInfoUpdate` before power modes, followed by badge update and, for a full
update, badge monitor information. Inventory, invention, workshop, team,
supergroup, league, optional attribute description, dynamic group, sky and
optional slave orientation tails follow. This module cannot skip the preceding
PowerInfo grammar or establish where this body begins from arbitrary ALLENTS.

The badge audit found a distinct complete grammar: debug mode; terminated player
badge records with owned/visible/known/progress and optional source filename;
optional recent history; and an optional separately terminated supergroup list.
The source consumer also performs dictionary lookups and UI state mutations.
Recent history has an eight-bit wire count and only 50 destination slots; a new
bounded consumer must reject excess counts before application. Supergroup owned
records assume a dictionary entry before accessing it. The badge monitor sends
ten optional packed IDs and then runs dictionary/state-dependent validation and
sorting. None of these three badge functions is implemented or claimed by this
checkpoint. They require their own whole-grammar and side-effect boundary review.

No packet ID, DBID, selected-player identity or generation is encoded in this
power-mode body. The enclosing transaction owner must verify those, stage this
state alongside every required field, and discard stale or invalid transactions
without publishing partial state. Worker C owns record/full-update composition;
Worker F owns the initial character envelope. Complete global tails, immutable
authoritative actor publication and full-update acknowledgments remain closed.
Removing the standalone target and source references rolls this module back;
accepted APKs, shared interfaces and server runtime are unchanged.
