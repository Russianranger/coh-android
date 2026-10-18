# Specific initial request transport witness

This optional nonshipping role observes the existing REQALLENTS transaction.
Build `coh_request_tx_map.c`, `coh_request_tx_net.c`, and `coh_request_tx_udp.c`
instead of `coh_initial_map.c`, `network/coh_net.c`, and `network/coh_net_udp.c`;
add `coh_request_tx.c`. Keep `coh_initial_local.c` and all other source choices,
protocol/Blowfish per-source O0 settings, deadlines and protocol policies.

The replacement translation units contain the frozen original bodies plus
marked scalar hooks and relative include wiring. The focused checker reverses
those insertions and compares every original byte. No hook controls a protocol
return, queue decision, send call, retry, ACK removal or timeout.

The existing initial Map owner checks the actual claimed handoff, generations
and whole GROUPS consumption before its single REQALLENTS call. A bracket at
that call binds the current capture identity to its actual Map UDP instance.
The UDP hook binds that instance to its actual NetLink; a hook after Tx payload
assignment records only the one committed reliable, uncompressed, unfragmented
request Tx ID. The ID and all pointer keys remain private. Reservation/next-ID
guesses and the next arbitrary socket callback are never used for attribution.

The pump snapshots that exact selected Tx ID and prior sent flag immediately
before its existing callback. It records the actual callback result before the
original early return. A synchronous UDP I/O failure can close/clear the Tx from
inside that callback; the bounded in-flight snapshot survives long enough to
record that same callback's failure. COH_NOT_FOUND is a deferred callback;
other valid nonzero CohStatus values are failures. The original UDP adapter maps
only a full successful sendto to COH_OK. Retry successes remain the same Tx.

A transport ACK is observed only inside the existing used+sent+matching-ID
retirement branch, after frame decoding. In the production path the unchanged
UDP peer filter runs before NetLink receipt. This ACK ledger precedes subsequent
application-payload validation, so it proves no server request dispatch or
application/full-update acceptance. Other queue clearing is labelled separately,
never inferred as an ACK. The first retirement reason remains latched.

Create the optional witness after capture begin succeeds, on the same owner
thread. Use its service/close/cancel/timeout wrappers for the corresponding
existing operations. Every wrapper delegates once with the same arguments and
result, even if the witness is absent or refuses observation. After a terminal
operation, retire the witness before destroying its capture, then snapshot and
destroy it. Calls after retirement should use the ordinary terminal operations.
Do not access, retire, destroy or reenter the witness from an observer callback
or concurrently. Thread-local borrowed scope is cleared at every wrapper exit.
The witness allocates at most256 bytes and copies no packet, credentials,
endpoint, account, DBID or generation. It is additional diagnostic storage,
not a proof of global aggregate or RSS fit.

Public output consists only of bounded counters, typed refusal/retirement codes,
flags and existing owner-service clock offsets. No server receipt, source
generation, complete initial character, actor, application ACK or world authority
is granted. The actual complete initial-character/actor progression remains an
independent unfinished task.

Focused host tests use explicit doubles for the outer capture operation and
request bracket. The real queue, UDP-to-Net mapping, frame codec, pump, retry,
matching ACK branch and loopback sockets execute. They include an actual sendto
EBADF causing synchronous source close before COH_IO, deferred and other-status
callbacks, an earlier unrelated Tx, unsent/wrong/corrupt ACKs, matching ACK,
queue limits, cancellation, close, timeout, observer limits and invalid owner/
clock controls. This is controlled peer evidence, not an original server session.
Production replacement roles are compiled and linked, not executed by this test.
