# Proposed source observation for the shared wire layout

Design only. No observer, source overlay, default build, accepted PE, source
global or capture was changed. This proposal is separate from A's actual dynamic
tracker witness. Current source generation, complete character, actor and ACK
authority remain false.

The smallest new source observation that closes a required initial wire
parameter is the **actual computed omission index for each transmitted build**.
It does not require guessing whether the process started empty or reloaded, or
assuming that one global read remained unchanged throughout serialization.
Costume is a separate, possibly earlier parser prerequisite; its complete source
exporter already exists and needs an actual coherent runtime observation.

## Exact original dependency

`Common/entity/character_net.c::character_SendPowers` computes player/multiple
build mode, writes its flag and build-level profile, and starts builds1..7 at actual
`g_numSharedPowersets` while still transmitting each build's total set count.
The corresponding receiver copies build0 pointers and uses the same unsent
global count to decide which wire set bodies exist. The count is not inferable
from packet fields alone. The native `CohCharacterWireProfile` explicitly keeps
its externally supplied identity/count separate from dictionary authority.

`powerdict_FindSharedPowersets` appends references without clearing the list.
`load_PowerDictionary` calls it after either shared-memory hit or parse fallback.
`load_AllDefsReload` loads a separate `NewPowerDictionary` then calls
`ReloadPowers`; old and new list pointers cannot be assumed to belong to the
same immutable family. Thus observing26 or52 is not proof of startup history.
The smallest framing witness instead observes the producer's actual computed
`iFirstPowerset` and `iSets` locals for every build. The producer does not
dereference `g_SharedPowersets` inside this function. Current ordered global-list
identity is a separate semantic prerequisite, not a condition for observing
these actual per-build wire control values.

Reviewed source at C baseline `9f3dcfb17e99a7d35608d4a389583a1997057b90`:

| Original function | First source line | Whole LF body SHA256 |
| --- | ---: | --- |
| `Common/entity/character_net.c:character_SendPowers` | 614 | `09180c33c2458de745e770fe71c6f8aee09ffcbb76bd304eed0b7f4361297585` |
| `Common/entity/powers_load.c:powerdict_FindSharedPowersets` | 1580 | `c189107add6f5772292f35b166e9c69c714be22709f8e60e4e01c0796f8abad6` |
| `Common/entity/powers_load.c:load_PowerDictionary` | 2696 | `d40438d23f16e14a4da30ad6277603e049e3ab37117820981c21897e669080a8` |
| `Common/entity/powers_load.c:ReloadPowers` | 2766 | `a225bd5bf3e5c1eb160407c4fdedfbb00577788c13d0da646ea4543ced2efc15` |
| `Common/entity/load_def.c:load_AllDefsReload` | 1516 | `a5429b2e4bf56dea05c3728473451feda73fa1bb71240db5c8639e84655ee22e` |
| `MapServer/src/entity/entsend.c:entFinishUpdate` | 1656 | `043259c9a6cfd91b4e89f80dfe08ab607433c84d14d3bf4ea080acfd212e0c98` |

Each exact source file was compared to the baseline Git blob before hashing;
whole-function extraction is the existing source review helper, not execution.
`qualification/shared-wire-observation-design-pins-20261018.json` additionally
binds the exact headers/profile/exporter inputs and A's unchanged
`cc056230c1628ed5a82da1df05d91b3a3792c888` dynamic observer design. Both original
`character_base.h` and `entPlayer.h` define MAX_BUILD_NUM as8.

## Small complete observer proposal

Use new isolated nonshipping stage/observer files only, subject to separate
source/build qualification. Do not alter accepted source or the old scene sink.
There are two observation stages:

1. Bracket the original `character_SendPowers` call. Read the actual source locals
   for player/multiple-build mode, MAX_BUILD_NUM and active build after they are
   computed. For each actual build, observe `iBuild`, `iFirstPowerset` and `iSets`
   **after** the original assignments and immediately before the original set
   count is written; record that build's begin/end logical bit offsets. Do not
   replace or recompute these locals. Do not call SelectBuild, a loader, hash
   constructor, sort, grant function or any mutation to inspect this state.
   The existing producer still performs every original build switch, loop and
   write. The observer only reads the values that actually control those writes.
2. Commit only when the SAME pending packet is the final initial ALLENTS packet
   in `entFinishUpdate`, after its end marker and immediately before `pktSend`.
   Check the same character/packet/link association; bind the witness to the
   complete final source payload/exact bit length and the corresponding native
   decoded raw packet. Later append-only commands on that same packet are
   expected; every recorded subspan must remain inside the final packet.
   Replacement/rebasing or unknown association refuses rather than guessing
   offsets. `entSendUpdate` alone is too early: more commands can be appended.

Reuse A's proposed final packet association method for the dynamic observer:
one pending Entity/Packet/Client association, final end-marked source payload,
exact logical bit length, same source GROUPS/run and native owned selected
handoff/message receipt. The native decoded ALLENTS bytes and bits must exactly
match. There is no second independent packet association label or source packet
copy. This is coordinated design only, not an implemented shared observer.
The exact final seam is `entsend.c`1814–1834: after
`pktSendBitsPack(e->entityPacket,1,0)` and immediately before
`pktSend(&e->entityPacket,client->link)`, using actual `clientFromEnt(e)`.
The append at4606–4641 can copy an older packet behind a byte-aligned meta-command;
the observed final logical length/profile must come from the final packet.
An earlier provisional packet replaced by a different final owner refuses.

One pending target transaction is sufficient. Keep raw pointers only as internal
synchronous keys; emit no addresses, account names, UID, cookies or credentials.
All durable output is private source evidence; public output needs only fixed
status/count fields. Source/run/build labels come from the admitted capture
chain; they are not independently authenticated merely by writing them here.

Proposed diagnostic domain: exactly one or eight build rows, build indexes0..7
and first/total set counts0..256 (existing character set cap), with monotonically ordered
bit spans inside the same existing4MiB decoded packet domain. Each row requires
only build index, first set, total sets, begin bit and end bit, as five
little-endian U32 words. Eight rows are
160 bytes; a fixed512-byte serialized ledger cap leaves room for the power-call
span, actual player/build profile and versioned framing. This is a design format
cap, not a measured C ABI or owner/budget qualification. The final packet stays
under its existing source/native loan and is not duplicated by this ledger.
Charge pending state, writer context/output/retention and actual callback stack
before implementation; no eager dictionary scan or62MiB graph is necessary.

Require build0 first-set0 and, for the supported player profile, the actual
first-set values of builds1..7 all equal. That common value becomes the observed
wire omission count; no independent recomputation from globals is substituted.
A single non-player build has no shared omission observation; do not infer the
process's global shared-list count from that mode.
Refuse inconsistent build order/profile, unequal omission starts, first>total,
negative/over-cap counts, invalid bit spans, packet mismatch, I/O failure,
cancellation and incomplete finalization. Zero shared count is valid. These are
explicit supported-profile refusals; the observer must not change valid original
serialization to make it fit. No skipped rows, guessed loader history or repeated
application request is allowed.
An unsupported observer must preserve an already valid independent GROUPS scope.

## What it would close

A qualified source/native packet association can establish the exact unsent
shared-count wire parameter for that **diagnostic packet**, using the actual
per-build omission starts. It could remove the need to try guessed26/52 layouts
when running the existing whole initial diagnostic. It does not by itself admit
all BasePower fields, current historical-cache equality, gameplay IDs, Boost
objects/evaluation, a whole character or any existing runtime-generation flag.
The current historical shared owner remains immutable and source-only; a new
observation cannot silently relabel it as current. Even a successful ledger
leaves actual ordered `g_SharedPowersets`/current dictionary pointer identity,
source runtime reload state and every gameplay dictionary join unadmitted.

A later complete shared-list semantic witness could observe the actual ordered
list, repeats and pointer equivalence, matching each entry by pointer incidence
to current allocated dictionary rows and recording exact names under explicit
bounds. It would need a coherent source-owned immutable dictionary epoch;
before/after equality alone cannot prove that no intervening mutation occurred.
That larger witness is not required for this minimum framing ledger and is not
proposed as an extra implementation before genuine packet diagnosis.

If a raw initial packet is captured without this witness, retain it exactly.
The missing source state cannot be recovered retroactively by choosing whichever
count makes the parser reach the end. No new standalone native kernel is needed
before this actual evidence exists.

## Costume witness has no missing builder implementation

`costume-export/stage.py` already prepares a source-qualified startup hook after
`loadCostumes`; `source_costume_export.inc` walks all real initialized ordinary,
extra and palette stash slots through original getters into the existing4MiB
COHCDI1 format. The full historical slots, body inputs, import and taskforce
consumer are already available. Reuse those complete owners rather than adding
another builder or parser.

The missing fact is execution on the actual source process and a coherent
association of those complete tables/body-part identities with the packet's
costume serialization. Startup-only pointer/capacity/count equality is not proof
that contents stayed unchanged. A future source stage must prove an exclusive
unchanged table epoch covering serialization, or observe the complete tables in
that coherent window using the existing exporter. A configured generation number
is a label; exact export contents plus the qualified process/run/packet chain
must establish its association. This proposal does not change protected costume
or Support implementation or authorize another expensive capture.
