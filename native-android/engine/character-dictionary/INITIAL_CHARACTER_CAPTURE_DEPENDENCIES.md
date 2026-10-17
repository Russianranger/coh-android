# Receive-only initial character capture dependencies

The original protocol has a bounded, pre-READY evidence opportunity. The current
`capture_local_scene.c` and opaque Local/Map APIs do not expose it. Changing only
the receiver tool while keeping those APIs unchanged cannot request or capture
ALLENTS. No common controller, parser, tool or source file was edited by this
review. No runtime transaction was launched or repeated.

Exact 23-file source pins are retained in
`qualification/initial-character-capture-source-review-20261017.json`, SHA256
`9047efe94530f231b2b66f58c0c02544170f2b1bb8b1c786a4c772612bc3f42b`.
The native/common/original bytes matched main revision
`777e33c4318f50eefe622d513009092af8c34bc8` at review. This is a source review,
not evidence that an actual initial packet was received.

## Original send eligibility before READY

| Source | Required phase/effect |
| --- | --- |
| Game/src/clientcomm/clientcomm.c::commReqScene | Original client receives GROUPS, sends CLIENT_REQALLENTS, waits for SERVER_ALLENTS, loads relevant resources, then sends CLIENT_READY. |
| MapServer/src/svr/svr_tick.c::svrHandleClientMsg, CLIENT_REQALLENTS case | Requires an existing entity; sets ready=CLIENTSTATE_REQALLENTS, sent_self=0 and clears the per-client entity-link table. It does not read READY's cookie/password fields. |
| svr_tick.c::svrTickDoNetSend | A nonzero ready state with sent_self=0 triggers entSendUpdate. The argument full_update=(ready!=CLIENTSTATE_IN_GAME) is true for REQALLENTS. |
| MapServer/src/entity/entsend.c::entSendUpdate | Emits SERVER_ALLENTS and full-update ID, always includes the player entity, and calls sendCharacterToClient whenever full_update is true. No additional READY-state gate surrounds that call. |
| MapServer/src/entity/entserver.c::sendCharacterToClient | Sends auth/player-type prefix, complete character_Send powers/inspiration/boost/inventory body and the enclosing self-character fields. The character is embedded inside ALLENTS, not a separate initial-character network command. |
| Game/src/clientcomm/clientcomm.c SERVER_ALLENTS handler | Original client sends CLIENTINP_ACK_FULL_UPDATE after receiving ALLENTS. This is a client response, not a prerequisite for the first ALLENTS. |
| MapServer/src/player/parseClientInput.c | ACK_FULL_UPDATE advances ackedFullUpdateID; RECEIVED_CHARACTER invokes later character/login behavior. Neither handler gates the initial full-update producer above. |

Thus READY, RECEIVED_CHARACTER and full-update ACK need not be sent to obtain the
first requested full packet. With no REQALLENTS at all, CLIENT_REQSCENE leaves
ready=NOT_READY, so the same unmodified transaction does not request that update.
REQALLENTS is an actual source request with server effects and is not passive
observation. Any future use belongs to an explicitly authorized nonshipping
local diagnostic policy; the ordinary controller's documented refusal remains.
Transport reliability acknowledgments are separate from these application
commands and continue to obey the existing transport implementation.

## Exact current code barriers

* `combined-client/tools/capture_local_scene.c::main` breaks on the first scene
  observer call and requires SCENE_INCOMPLETE/UNSUPPORTED as its terminal result.
  Its synchronous observer can borrow only GROUPS via scene_lease. Closing and
  writing capture.json follows that observation; there is no later receive.
* `engine/mapclient/coh_mapclient.c::inspect` only queues REQSHORTCUTS after an
  accepted CONNECT and REQSCENE after SHORTCUTS. GROUPS is completely structurally
  inspected, then its observer runs and inspect deliberately returns UNSUPPORTED.
  No REQALLENTS is queued. The public header promises no REQALLENTS/READY/ACK.
* Local and Map are opaque. The only public Map pointer reaches the Local scene
  observer, whose contract forbids reentry except scene_lease. The observer
  cannot queue another command or borrow a later packet. Constructing another
  UDP socket would not preserve this actual DB/Map/connection owner.
* Even if an ALLENTS were present, Map inspect and replication::session_message
  both reject non-GROUPS bodies above 16,384 B. For smaller ALLENTS, they parse only
  its update prefix, increment entity_prefixes, and return UNSUPPORTED without
  an observation callback. Merely continuing the current tool's loop is not a
  complete packet capture seam and does not remove either size guard.
* `coh_initial_update_diagnostic` already composes bounded source-order raw
  header/list/control/delete/character/global-suffix and exact trailing command
  syntax. It is not called by Map inspect and it always retains authority
  refusal. It additionally needs actual profile/schema/selection/generation,
  costume and loan-provider context. Unknown supported-domain boundaries,
  attributes, invention, game commands or dictionaries can still refuse a live
  packet. None is permission to scan, skip or ACK it.

## Smallest legitimate future nonshipping extension

A separate diagnostic owner/policy can reuse the actual opaque DB handoff and
Map transport while retaining the ordinary controller behavior. It needs an
explicit one-shot REQALLENTS request after successful complete normal GROUPS
inspection, outside observer reentry, and a synchronous ALLENTS loan before the
ordinary prefix-only refusal. Local must forward that loan without exposing a
raw socket or accepting caller-provided DBID/cookie/session labels. A separate
nonshipping owner built from the existing DB handoff/UDP modules is another
option; the current public Local/Map APIs alone cannot implement either seam.

The raw observation must bind the exact current Map client, event address,
message/lease generation, selected DBID/selection generation and still-live
claimed DB handoff, actual connection/message IDs, ordered ID, transport version,
byte-alignment profile and full reader representation. It copies synchronously
or streams to a fresh private O_EXCL file, hashes the exact bytes and records
original payload bits/cursor. Pointers expire on callback return and the opaque
message is released exactly once. Existing cancellation, authorization,
loopback, timeout, transport/framing/crypto/ordering checks and cleanup still
apply. Callback return cannot authorize protocol progress or semantic acceptance.

A dedicated raw-capture observation may borrow the complete decoded message
without pretending its unparsed body passed the application parser. It must say
raw_message_captured, not complete_character/initial_update/actor/ACK permitted.
Do not widen ordinary Map/replication acceptance to 4 MiB merely to observe this
message. The existing transport already bounds encoded reassembly to 16 KiB and
owned decoded output to 4 MiB. Those caps remain hard refusals if the actual first
ALLENTS exceeds them; capture is not a reason to enlarge them speculatively.
An output/aggregate budget must include the live decoder/message, private
retention and any provider/parse workspace. A file stream avoids another 4 MiB
in-memory payload copy. Bound requests, observations, elapsed time and written
bytes. Preserve the first failed parser checkpoint; no draining past an unknown
or failed parse to search for ALLENTS. An actual earlier unsupported command is
new input to close, not a skippable prefix.

Logical bit length is available from the existing actual owned message. For
uncompressed packets it is the exact reassembled wire payload_bits. Compressed
source uses byteAlignedMode: bsWriteBits rounds widths, BitsPack writes 32 bits,
and original bsCompress asserts bitLength is byte-multiple; its header retains
raw byte count. The owned decoder validates that raw size and records exactly
decoded_bytes*8. Preserve that profile and bit length, not guessed byte padding
or an inferred shorter end. The original server appends a Pack1 zero terminator
in entFinishUpdate; successful future full parsing must consume its actual end,
including any source-aligned nested commands, rather than trim bytes to fit.

On the first eligible full ALLENTS, the nonshipping receiver can retain the raw
message then close without READY, RECEIVED_CHARACTER or full-update ACK. That
provides authentic branch bytes for the whole power-sequence design. A raw loan
or a complete syntactic diagnostic does not supply runtime dictionary/shared
loader generation or the required power/reward/evaluator/world semantic owners.
Current actor, complete initial transaction and application ACK remain refused.
