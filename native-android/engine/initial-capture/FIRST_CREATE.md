# Initial ALLENTS first-create observation

The physical Combined 0.1.9 Thor reports prove initial packet receipt, not a
complete character transaction. The standalone report records INITIAL_OBSERVED;
the ZIP's later CLOSED state preserves the observation and verifies two owned
sockets closed. Their raw packet body was deliberately not retained.

The Combined diagnostic observer now calls `coh_initial_create_probe` during
the exact synchronous ALLENTS loan, using its actual shortcut schema and owned
selected DBID. It reparses the header from the **post-command** cursor, then
decodes the first delta and the complete original `entSendCreate` block using
existing native parsers. No second create grammar or speculative dictionary
generation is introduced. Default production Map/Local/replication sources and
Combined 0.1.9 imports, version, signing, saves and profiles are unchanged.

The numeric `world_handoff.first_create` report retains header/create end bits,
the first failing stage/cursor, entity index/type, self flag and raw self DBID
comparison. No name, DBID, entity ID, packet pointer or packet bytes are retained.
Before observation the report is null. A complete create normally reports
`UNSUPPORTED / FIRST_RECORD_BODY_REQUIRED`. Truncated/malformed input or an
unsupported header/profile reports its own earlier boundary. This syntax result
is separate from successful raw capture and never creates a transport failure.
The next record cannot be located until the current record's body is decoded.
No scan, skip, application ACK or gameplay publication occurs.

## Original protocol evidence

In `upstream/ouroboros/MapServer/src/entity/entsend.c`, `entSendUpdate` initializes
the previous index to -1; `sendEntity` writes the signed delta as U32 and the
create bit before `entSendCreate`. The whole create producer writes its end flag,
entity ID/type, optional self/access/DBID, pet metadata, class/origin indices,
strings, seed and contact metadata. The visible list can precede the fallback
self send: the first entity need not be the selected character. Canonical list
termination is delta0/create1/end1. Byte-aligned booleans must still be 0 or 1.
`Game/src/entity/entrecv.c:entReceiveUpdate` confirms the enclosing source order.

`e->id` is a raw server entity generation, distinct from entity slot, DBID,
packet ID and Map generation. A matching self create is only wire consistency
against the owned local-development handoff; it does not establish whole-list
uniqueness, authenticated server identity or source dictionary ownership.

The existing `initial-update` diagnostic composes list, control, deletes,
character/global suffix and command tail. It requires an actual costume
dictionary/manifest generation before complete records can be admitted. No Map,
message or session counter can substitute for that generation. All character,
source-generation, actor, ACK and world-authority flags remain false.

## Qualification scope

`check_initial_create_probe.py --sanitize --output NEW.json` executes the pinned
original create producer and bit writer on fixture objects, then tests only
this probe in release, ASan and UBSan. Framing joins are explicit synthetic
header/index compositions; neither a whole original ALLENTS transaction nor new
Thor execution is claimed. The affected JNI adapter is checked independently
with explicit controller/JNI doubles, including refusal reporting and cleanup.
No general renderer, compiler, network or Android 13 suite is repeated.

The previously reported unsupported Map count is the ordinary successful GROUPS
inspector's deliberate UNSUPPORTED boundary (command6, exact consumed end), which
the capture wrapper continues past. It is not an unidentified failed message.
Gates 25–27 remain open. No new APK is produced for this prefix-only source step.
