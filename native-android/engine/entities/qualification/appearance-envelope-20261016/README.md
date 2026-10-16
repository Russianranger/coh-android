# Complete appearance wire envelope — host qualification

Parent implementation: `8475ce3e5d641b393904dfdce61f4b486eca4a0e`.
Original import: `0b75ade0c801735e10c5798f641948a45cc50488`.
`host.json` binds exact implementation, source pins, oracle adapters and fixture
hashes. Earlier raw-body receipts remain unchanged.

The standalone parser covers the complete original non-debug appearance wire
envelope: own-player reward lists, deferred intent, current/additional slots,
single and multiple costumes, supergroup costume/mode/emblem, special FX, NPC
fallthrough with custom colors, owned costume, sequence name and optional world
group. It does not compose persistent entity state or resolve rendering assets.
The existing `coh_ent_appearance`/`coh_ent_record` full/owned/custom variants
remain closed pending complete transaction composition and generation ownership.

The oracle now executes unchanged original `entSendCostume`, `entReceiveCostume`,
`ent_SendCostumeRewards`, `ent_ReceiveCostumeRewards` and their original raw body,
indexed/cache and packet primitives. Deterministic adapters provide engine
storage and menu/render side effects. A call-through observer records only body
destinations and ending cursors around the unchanged raw receiver. Expected
decoded body fields and reward names come from the original consumers; source
input metadata supplies presence and filtered-list positions those consumers
do not retain. Original runtime rendering, FX normalization, deferred scheduling
and real dictionary/resource lookup are not qualified by those adapters.

Twenty envelope fixtures cover ten scenarios in both alignment modes; eight
previous raw-body fixtures remain. Cases include self single/multiple/deferred,
supergroup/FX/NPC-custom fallthrough, other-player deferred, owned, custom NPC,
sequence, no appearance, ten stored costumes and a new character with zero
additional slots. The source `num_costume_slots` value is **additional slots**;
`costume_get_num_slots` adds one and product entitlements. It must not bound stored
costume count directly. Fixtures explicitly cover ten stored bodies with two
additional slots. Manual original-writer fixtures also cover 256 filtered reward
entries per group, byte-value 255 additional slots and malformed cases.

Release, ASan and UBSan each passed **1,083,422 checks**, **211,896 every-bit
truncations** and **25,000 randomized bodies**, including 1,000 bodies also sent
through the envelope parser. Every incomplete source envelope rolls back reader
and complete output, including failures after multiple valid costume bodies.
Unknown types, self-ownership mismatch, dictionary generation mismatch, missing
reward indices, null reward strings, excessive reward counts, invalid current
and stored indices, invalid custom flag and long sequence/FX strings fail closed.
All earlier entity/list/stat/FX/raw-costume tests also pass. Sanitizers cover new
native code/tests; trusted original functions run at `-O0` outside sanitizers.
LeakSanitizer is disabled under the existing sandbox process-map limitation.

Envelope output is 692,064 bytes and separate workspace 772,984 bytes. There is
no parser heap allocation. The bound admits ten stored bodies plus one
supergroup body, two reward lists of at most 256 source entries each, one custom
NPC color body, and fixed string fields. Do not put these envelopes in every
entity table slot: the future transaction owner must bound aggregate retained
appearance events and old/candidate generations. See `COSTUME_IMPORT_CONTRACT.md`.

Native parsing preserves raw deferred intent and special-FX names. A future
semantic owner must apply packet order and source optional-field retain/clear
rules. The historical owned-costume consumer skips its body on stale packets;
native parsing always validates the entire body before future stale-event
discard. No claim of source parity for that historical cursor bug is made.

No authentic costume dictionary is captured. No complete selected-self entity,
initial character/global tail, authoritative actor or network acknowledgment is
enabled. Android ARM64 build, emulator execution, physical Thor and genuine
server interoperability require separate evidence. Accepted APKs, profiles,
assets and saved data are unchanged.
