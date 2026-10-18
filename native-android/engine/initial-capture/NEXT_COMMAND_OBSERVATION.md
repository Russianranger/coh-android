# Contract after the next genuine command-name witness

Read-only source review and design. No source hook, parser, command skip, request,
ACK, build, runtime capture or existing qualification was changed or rerun.
The command in actual run39081284657 remains unobserved: its status2 is not an
opcode, and the controlled peer's SERVER_GAME_CMDS case is not live evidence.
Exact file/function pins are in
`qualification/next-command-observation-source-review-20261018.json`.

## What the current diagnostic distinguishes

Root stdoutv2 uses the C-owned first-refusal `refused_command_valid` and fixed
`refused_command_kind`. The classification is of the **outer normalized command
in the refused current owned message**, not a nested command or a source caller.

| Observation | Established fact | Still unknown |
| --- | --- | --- |
| `status=2` | COH_UNSUPPORTED | The command, packet body and producer path |
| true / SERVER_UPDATE | Original normalized outer command2 (legacy wire7) was decoded | Why the source used a delta update and whether any later ALLENTS exists |
| true / another known source name | That normalized outer enum was decoded | Its nested commands, body fields, side effects and source send call site |
| true / UNKNOWN | A normalized outer value was decoded outside the231-name whitelist | Which unknown value; different unknown values intentionally collapse |
| false / NONE | No valid decoded command was attached to the first refusal | Decode failure versus another no-current-message cause; use paired failure/phase fields |

Successful raw ALLENTS capture also retains false/NONE because no command was
refused; `initial_packet_observed` and the independent failure/status fields
distinguish that result. The API cannot reveal an inner opcode behind a
SERVER_GAME_CMDS envelope, a second command, a header scalar offset or any packet
string. It also does not expose a raw numeric opcode. No field identifies a live
dictionary/cache generation, selected actor, dynamic tracker or world owner.

Under the qualified current receiver, a valid SERVER_ALLENTS passes the command
comparison. A later refusal is OWNER, HEADER, OBSERVER, RELEASE or cancellation;
a paired COMMAND/SERVER_ALLENTS result would need source/result association
review before changing parsing. A HEADER/SERVER_ALLENTS result alone still does
not reveal which field failed.

The classifier is cleared before every owned-message fetch and command decode.
A failed next fetch after an accepted CONNECT_MSG therefore does not inherit
that command; an encoded command peek in a decoder receipt is not substituted
for a successfully decoded loan. The current proof explicitly covers that case.

## Original source boundaries that must remain distinct

`MapServer/src/entity/entsend.c::entSendUpdate` writes SERVER_ALLENTS plus a packed
full-update ID only when its `full_update` argument is true. Otherwise it writes
SERVER_UPDATE without that ID. Both have entity/control/delete data, but the
full branch later sends the whole character while the ordinary branch sends
stats against existing player state. Reclassifying UPDATE as ALLENTS would
shift framing and invent the missing complete initial character.

`Game/src/clientcomm/clientcomm.c::commHandleMessage` dispatches the outer enum.
Its ALLENTS branch reads the full-update ID and sends CLIENTINP_ACK_FULL_UPDATE
**before** calling `entReceiveUpdate`; the capture must not execute this original
dispatcher as a way to learn grammar. The native isolated capture has no such
ACK path. `entReceiveUpdate` itself resets entities/player on the full branch,
reads entity/control/deletes, then receives the full character or ordinary stats.
These simulation mutations are not a diagnostic parser contract.

`Game/src/entity/entrecv.c::entNetUpdate` is a later timing/history/interpolation
and simulation pass. It is not the transport dispatcher or initial wire parser.
Its transforms do not turn raw initial records or fixture identity into an
immutable current actor pose. Full semantic ownership still precedes renderer
publication.

REQSCENE calls `worldSendUpdate` and leaves the original client NOT_READY.
REQALLENTS later sets REQALLENTS and clears sent_self. `svrTickDoNetSend` selects
the full update for a non-IN_GAME ready client that has not received itself.
Meanwhile START_PACKET can create a SERVER_GAME_CMDS envelope in entityPacket,
and `entFinishUpdate` flushes an existing entityPacket for a client regardless of
that ready test. Thus GROUPS followed immediately by ALLENTS is not a promised
application-packet ordering. Dynamic definition sends in `sendWorldChanges` are
separately gated IN_GAME; they must not be presumed to be this pre-READY refusal.

`entFinishUpdate` adds the final zero terminator immediately before pktSend.
The earlier entSendUpdate tail can append an older entityPacket behind a
byte-alignment marker before assigning the new packet. Any future source witness
uses A's one SAME-final-Entity/Packet/Client/link association after the terminator,
with exact final source/native payload bytes and logical bits, GROUPS/run and
actual owned selected handoff. An earlier bracket or matching labels alone is
insufficient. No duplicate final-packet hook or source packet copy is proposed.

## Shortest conditional next step

First retain the genuine stdoutv2 name/valid pair with its exact source/build/run,
paired first-failure fields and cleanup receipt. A version1 historical record
has an unavailable enum; it must not be upgraded by matching the synthetic case.
The current capture releases an unsupported message and retains no raw body, so
the name alone cannot retroactively supply missing bytes or nested fields.

| Genuine next witness | Minimum next evidence, before any body-parser change |
| --- | --- |
| false/NONE | Resolve the recorded failure stage and actual loan/decode lifecycle. Do not select a body parser without a decoded source name. |
| true/UNKNOWN | Resolve source/enum/profile provenance with the producing source process. No fallback dispatcher or guessed normalization is safe. |
| SERVER_UPDATE | Associate the SAME source final packet with the actual entSendUpdate full_update argument, ready/sent_self state and viewed-entity owner. Keep refusing it as the initial character transaction. |
| SERVER_GAME_CMDS | Only after this genuine outer witness, the smallest receiver-only extension is a **single first-inner-command observation** on the same bounded loan, following original handleGameCmd's first Pack1 read. Close before that body's bytes; no scan, marker loop, body skip or continuation. |
| SERVER_ALLENTS with HEADER refusal | Qualify its exact source byte-alignment/header/schema profile. The current enum does not identify the failed scalar; do not change odd-send/debug/schema checks from status alone. |
| Raw ALLENTS observed successfully | Reuse the existing whole-initial/attribute diagnostic on the exact immutable bytes/bits and matching required input owners. Do not add another packet parser or mark the raw header as a complete character. |
| Any other known enum | Find its complete original producer and consumer, required history/dictionaries and bounded whole body/end contract. An outer name alone does not justify ignoring that packet. |

The proposed single-inner observation, if the corresponding genuine witness
arrives, would reuse the existing immutable loan, current claimed handoff and
fixed name whitelist. Original handleGameCmd starts with Pack1 when called with
-1; SERVER_GAME_CMDS is body-free, but subsequent commands need their own bodies.
Those inner Pack1 values use the original source enum; do not repeat the outer
legacy wire-ID remapping inside the envelope.
Observe only that first inner value (or explicit zero terminator), retain a
source-fixed classification and refuse before its body. Do not silently advance
over additional markers. The zero/end case would still need an exact-end proof
and separately approved continuation policy before treating a packet as empty.
Zero is a grammar terminator observation, not an opcode name; do not disguise it
as the outer classifier's UNKNOWN or infer an empty packet from the name alone.
This contract authorizes no implementation now and no ACK/READY/received-character
response. It explains the smallest evidence-producing change after a specific
real name establishes its source grammar.

Every future extension must keep one REQALLENTS, current loopback/handoff/message
generation checks, encoded16KiB/decoded4MiB caps, exact synchronous loan lifetime,
disjointness, cancellation/deadline cleanup, first-refusal preservation and prior
valid GROUPS evidence. No raw packet text, unwhitelisted string or numeric opcode
is added to public status. Unknown bodies always refuse as complete transactions.

## Whole-initial prerequisites remain unchanged

The retained complete costume slots and existing importer/taskforce parser do
not establish the actual server table epoch for this packet. The source-derived
26/52 shared-list profiles do not establish the actual unsent wire omission
count or global dictionary pointer family. The proposed per-build local-value
ledger addresses only its framing fact once source/native packet association
exists. A's actual ordered dynamic tracker witness is still separate from the
definition occurrence graph/count. Complete Boost objects, typed reward and
evaluation owners, full source-ordered power sequence and CreatePartTwo remain
semantic prerequisites. See character-dictionary/WHOLE_INITIAL_INPUTS.md and
POWER_SEQUENCE_DEPENDENCIES.md. No retained proof is relabeled as current, and
all actor/current-generation/world/ACK flags remain false.
