# Selected-self architect and taskforce wire events

`coh_ent_taskforce` decodes the two consecutive selected-self very-rare
substructures: `entRecieveTaskforceArchitectInfo` (original spelling) followed
by `entReceiveTaskforceParameters`. It requires the caller to establish this
source boundary and selected-self ownership. The outer rare flags, subsequent
rare entity tail, full character data and global tails remain unsupported.
This API does not publish actor state or send any acknowledgment.

The architect grammar includes update/on-architect flags; automatic flags, ID
and contact index; the original 32-byte contact-name capacity; optional full and
custom NPC contact costumes; and optional arc name, author, description, rating,
region and architect invulnerability metadata. Contact geometry/rig/material
references remain unresolved. A full costume body reuses `coh_ent_costume`
against an already imported immutable dictionary with the matching generation;
custom colors reuse `coh_ent_custom_costume`. No dictionary is required when no
new full body appears. That does not authenticate an absent or cached resource.

The parameter grammar includes packed flashback flag, update flag, a 32-bit
mask and automatic integers for set slots in increasing order. All 32 source
slots, including bit 31, are supported with defined unsigned arithmetic. Slot
indices 1 and 23 hold the producer's **raw relative clock words**, modulo 2^32.
The decoder does not use wall time. A future semantic owner must apply the
transaction's explicit client timebase to those words, matching original
time-limit/start-time conversion. Other slots retain raw integer bits.

## Event application remains separate

The result preserves presence flags rather than inventing persistent state:

- Missing architect update, or present update with `on_architect=0`, sets only
  the source on-architect flag to false. Other zero-filled event fields are not
  instructions to clear existing metadata or resources.
- While on architect, costume `exists=0` clears the corresponding prior contact
  costume; `exists=1/body=0` retains it; `body=1` replaces it. A retained body
  requires the future owner's validated source generation and resource lifetime.
- The producer shares one cached-costume flag for full and custom bodies.
  Sending the full body first sets that flag and can suppress the later custom
  body in the same update. Both presence flags remain explicit.
- Absent review metadata retains prior review/invulnerability values. Absent
  parameter update retains the prior parameter mask/values; flashback is still
  read. Present parameters replace the mask and only its set slots; unset prior
  values remain inactive and are not represented as replacement events.

These original consumers have no independent packet-order checks. The complete
entity/session owner must handle order, duplicate delivery, generation reset,
existing taskforce ownership and atomic rollback. Do not apply the event to a
live actor before every required source transaction field is validated.

## Admission and memory

Contact names allow 31 non-NUL bytes, matching source storage. Review strings
have explicit native admission budgets of 255/127/4,095 non-NUL bytes for
name/author/description. Those are bounded client limits, not claimed original
dynamic-string maxima; larger otherwise valid server metadata fails closed.
Flashback admits only producer boolean values. Malformed scalar high bits,
missing terminators, dictionary holes/mismatches and any truncated nested or
later field fail without changing reader or output.

The pointer-free event is 70,632 bytes on the tested 64-bit host ABI. Its caller
workspace is 151,552 bytes, containing one event candidate plus the existing
costume scratch. Prior event + candidate event + workspace costs 292,816 bytes.
Parsing allocates nothing and retains no input pointer. The dictionary is shared
read-only; its existing 4 MiB limit and generation replacement budget still
apply. The complete session must account for these bytes along with catalog,
graph, other actor events and assets. This is not a complete aggregate session
budget implementation. Use one bounded off-thread transaction buffer; never
embed the contact bodies in every entity-table slot. Arguments must not alias.

## Original-source evidence

The oracle executes unchanged original `entSendTaskforceArchitectInfo`,
`entSendTaskforceParameters`, `entRecieveTaskforceArchitectInfo`,
`entReceiveTaskforceParameters` and `TaskForceIsParameterEnabled`, plus the
already qualified original costume producers/consumers. Source `TaskForce` and
parameter-enum declarations are extracted unchanged from pinned `teamCommon.h`;
fixture owner shells and unused team members do not establish engine ABI parity.
Original sources are read from the checkout or the current Git tree for sparse
files, then checked against exact source pins. No historical Git object or
network retrieval is needed.

Synthetic outer update/flashback flags compose those component producers in
source order. This is not execution of complete `sendEntity` or `entSendUpdate`.
Fixture adapters provide deterministic taskforce/story storage, a fixed clock,
review callbacks and resource destinations. Call-through observers record only
body destinations/end cursors; original body functions still perform all reads.
The test compares consumer-observed fields and converts consumer clock results
back to their wire words; it does not derive the expected payload with the
native decoder. No real taskforce, captured story or authenticated dictionary
is bundled.

Twenty-two source-produced fixtures cover both alignment modes, no update,
on-architect false, no/replaced/cached full and custom bodies, shared cache
suppression, bounded maximum/empty review strings, no/empty/all-slot parameter
updates and relative-time underflow. Tests compare fields excluding C padding,
use byte-exact rollback snapshots, exercise every truncated bit, mutate bytes,
reject malformed/oversized inputs and run 5,000 additional deterministic random
inputs. Old source writers execute only trusted padded fixtures at `-O0`;
release/ASan/UBSan exercise the native parser. Source adapters, raw dictionary
fixtures and runtime UI/resource behavior remain distinct evidence categories.

Integration is additive: link `coh_taskforce.c`, allocate one event/workspace,
borrow an admitted costume dictionary, and stage the result after the preceding
entity fields. Keep the existing rejection barrier until subsequent rare,
character and global branches and all dictionary identities are complete.
Discard staging for rollback. Android compilation/emulator execution belong to
the consolidated coordinator workflow; no accepted APK or profile changes here.
