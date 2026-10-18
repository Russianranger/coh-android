# Initial-update send witness: source-only report

The original source permits the first full ALLENTS before CLIENT_READY,
CLIENTINP_RECEIVED_CHARACTER or CLIENTINP_ACK_FULL_UPDATE. No such input should
be enabled to diagnose the current timeout. The actual run's local request count
proves successful queue admission only; it does not prove a datagram or a server
callback. No timeout cause is established by this source review.

This report is read-only with respect to every repository. No source import,
compiler, native test, server or network operation ran. The companion
`initial-send-source-audit.json` binds 20 exact files and 27 complete function
spans to the immutable scene source revision
`18c9c4e1acee319e5bebc4fdc206f429ab6156cc`. Function spans include one final LF.
Its 11,900 bytes hash to
`1b187f909032148f1fedbd8d0f7b51e5d94666bfe14a56b7445baf7e4f6f94cd`.
C905/c684/6b7 and D's new wire harness remain unchanged.

| Stage | Exact original source boundary | Required behavior |
| --- | --- | --- |
| Initial connection | svr_tick.c:153 svrHandleClientConnect | Add the real entity to PLAYER_ENTS_ACTIVE and clear sent_self; this happens during CLIENT_CONNECT, before READY. |
| Request receive | net_link.c:1113 netMessageScan → svr_tick.c:183 svrHandleClientMsg, CLIENT_REQALLENTS at357 | Original normalized command dispatch. Missing entity removes the link; otherwise ready=REQALLENTS(1), sent_self=0, reset entNetLink. There is no READY or full-update-ACK check here. |
| Scheduled tick | svrTickTop → svrTickUpdateNetSend; svrTick → svrTickCheckNetSend → svrTickDoNetSend | Default period is30/4 time units (four updates/second under ordinary timestep); world modification also forces a send tick. This is scheduling, not a per-request wall-clock guarantee. NMMonitor runs only after global frame10. |
| Per-client selection | svrTickDoNetSend:1625–1667 | Actual client entity must exist; backpressure/disconnect and dbCheckMapXfer run first. IN_GAME, RE_REQALLENTS, or nonzero ready with !sent_self selects entSendUpdate. REQALLENTS therefore selects full_update=true. The viewed entity is client->slave if present, else the real client entity. |
| Full packet construction | entsend.c:3824 entSendUpdate, full header4051; character4503 | Writes SERVER_ALLENTS and increments the full-update ID. UnACKed ID sets ordered; it does not defer sending. Full updates send the complete character producer. Self is force-sent even outside normal visible selection, and sent_self becomes1 at4462. |
| Final packet | entFinishUpdate:1656, final send1814–1834 | Both preparation/cleanup explicitly handle sleeping PLAYER entities. Iterate ACTIVE players, resolve actual clientFromEnt, append terminator and call original pktSend. A prior pending entityPacket can be appended/replaced at4606–4641, so entSendUpdate's provisional packet alone is insufficient. |

`Game/clientcomm/clientcomm.c::commReqScene` independently confirms the order:
request GROUPS, request ALLENTS and wait for it, load relevant assets, then send
CLIENT_READY. The original ALLENTS dispatcher sends its ACK before consuming
the body; that is a client behavior after receipt, not a prerequisite of the
first server send. `clientReceivedCharacter` later marks entity.ready1 and
unfreezes it. None of these later behaviors is authorized in the diagnostic.

Three distinctions matter. `svrTickCheckDisconnect` can return before the sender
or, for local_server backpressure, wait while monitoring the link. Application
full-update ACK and ordinary transport reliability ACKs are different. Finally,
`pktSendDbg` enqueues/compresses/fragments; its normal fragmented path returns0
even after adding every fragment. A zero return cannot be labeled send failure,
and invocation cannot be labeled socket transmission or native receipt.

The existing GROUPS observation completes exporters, profile restoration and
commit synchronously before original worldSendUpdate calls pktSend. A confirmed
native GROUPS packet does not establish a source callback still running after
that send. No callback-induced post-send stall follows from the current proof.

## Current native evidence and deadline

At the pinned receiver, coh_initial_map_service pumps UDP first, processes the
GROUPS loan and releases it, then send_command serializes and queues one reliable,
unordered, uncompressed REQALLENTS. It sets reqallents_sent1 and returns. The
new request is transmitted by a later UDP service/pump. The root CLI's total
deadline starts before DB/Map/GROUPS and can expire before that later service.
This is a mechanically possible path, not evidence that it happened in391010.
No deadline extension is proposed.

Raw CLI stdout v2 has20 keys; A's fixed public projection has25. Neither exposes
packet/datagram sent/queued counters, TX-pending state, service-call count or
phase timestamps. Private initial-observation and old capture.json likewise do
not serialize outbound request ID/counters/timestamps. The nested C diagnostics
already contain total map UDP datagrams_sent and NetLink sent/tx_pending, but
those totals are not emitted and cannot identify a particular request anyway.
Whole-process or workflow timings cannot reconstruct GROUPS arrival, queue time,
a post-queue pump, or request transmission. The public25 fields therefore cannot
mechanically prove deadline pressure before GROUPS/request emission.

## Smallest proposed new outbound witness

Proposal only; no new API, wrapper, stage or executable is implemented here.
Keep default Network/Map/Local bytes unchanged. A separately qualified nonshipping
transport TU can include the unchanged implementation, as the current diagnostic
Map/Local TUs do, and expose only a private owner-bound observation seam.

Bind exactly one request to the already owned Map connection/generation and
source serialization call. After the real queue succeeds, bind the unique actual
new TX packet whose immutable payload, logical bits and flags exactly match that
REQALLENTS. Do not predict an ID from a counter or accept a caller ID. Ambiguous,
replaced or retired association makes the witness unavailable. Observe its real
send callback at the actual pump; only a full successful sendto result latches
`request_datagram_emitted`. A would-block/error/retransmission does not fabricate
that state. Keep the original queue/callback return and all control flow intact.
No extra send, receive drain, skip, ACK, READY or deadline change is allowed.

Retain only queue-observed, emitted, post-queue-service-count and relative
monotonic queue/final-service offsets plus a fixed refusal enum. Distinguish
successful local sendto from server receipt. One target, one unfragmented
<=128-byte source request, eight fixed scalar event rows and <=1KiB private
report are sufficient proposed policy caps; no packet/credential/key copy,
new heap, global/RSS or authority claim. Actual lifetime, cancellation, reentry,
known-span disjointness and owner/workspace charge need their own new tests.

The complementary smallest server witness is one same-GROUPS-owner ledger:
actual decoded CLIENT_REQALLENTS entry and post-transition; target visit/selection
at the real send tick (including pre-backpressure marker); full sender entry and
return from actual sendCharacterToClient; same final packet at entFinishUpdate
and original pktSend invocation. Record actual branch visits, not a duplicate
scheduler. Validate the current live callback arguments against internally held
link/client/entity keys; emit no pointers/UID/cookie/account values. Later ready1
must not be checked using the old GROUPS-only NOT_READY predicate. Replaced owner,
viewed/slave mismatch, missing final association or cap exhaustion refuses this
witness without changing source behavior. Reuse A's proposed single final-packet
association for any later dynamic/shared-layout witnesses; no second packet copy.

This server ledger distinguishes absence of a callback from selection/construction
progress. Actual enqueue/fragments/socket transmission needs a separately bound
lnkAddToSendQueue/pktSendRaw witness; pktSend's return is insufficient. Exact
final source bytes/bits matched to the native loan remain necessary for an
ALLENTS producer association. Complete character/current dictionaries, dynamic
world ownership, actor publication and every application ACK remain refused.
