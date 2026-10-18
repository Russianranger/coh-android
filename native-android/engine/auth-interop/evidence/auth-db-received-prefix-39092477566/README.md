# Actual received DB command headers — 39092477566

The actual fresh development transaction failed at the strict owner policy:
`OWNER_SERVICE / FAILED / DB / UNSUPPORTED`. Its fixed observed DB phase was
`WAIT_PLAYERS`; one DB login was queued, three unsupported counts were recorded,
and no complete list, queue update, choice or handoff was accepted. Fresh Auth
reached AUTHORIZED in four frames.

The newly observed, context-verified and retired received-header prefix contains
exactly these three entries, in order:

1. `DBGAMESERVER_ACCOUNTSERVER_UNAVAILABLE`
2. `DBGAMESERVER_ACCOUNTSERVER_CHARCOUNT`
3. `DBGAMESERVER_ACCOUNTSERVER_CHARCOUNT`

All three headers decoded in WAIT_PLAYERS, with legacy=false and compressed=false.
The prefix is not truncated (one session, five service calls, total_seen=3).
No SEND_PLAYERS header occurs in these three copied messages. This does not say
what the server may have queued or sent after the owner stopped. Raw bodies are
not exported or accepted by this observation. Its recorded first-unsupported and
body-acceptance flags remain false.

The exact source supports a specific explanation without a body inference:
ordinary `application_message` recognizes only SEND_PLAYERS, MSG, MAP_CONNECT
and QUEUE_POSITION. Each of the three observed header kinds instead enters its
independent-service default branch, increments `unsupported`, and returns OK.
The ordinary service loop can drain all three in one call and retains
WAIT_PLAYERS. The development owner's subsequent `db_service` check rejects a
nonzero unsupported count and returns UNSUPPORTED. This is a source-derived
explanation of the strict owner refusal, not an observed inner parser failure or
an upgrade of the prefix's first-unsupported/body flags. Four whole-function
byte spans (decoder, application dispatcher, service loop, owner DB service) are
independently rehashed by the verifier. A future typed handler must validate the
complete original bodies; this evidence authorizes no generic unknown skipping.

`artifact.zip` is the single root-downloaded artifact 12123094046 (17,000 bytes,
SHA256 dfa3341369b6659e9be3451d8b99cd6adc2d3fa7d1d1ebacd2f051894c448b8e).
Its sole `receipt.json` is preserved byte-for-byte including CRLF (73,968 bytes,
SHA256 44c6eeb9eaa391c550e3534e925d0dcc05eb2954e9bdd186bb7c5526e5604ef0).
`api.json` is the root-provided fixed API projection (3,485 bytes, SHA256
7945c30037835cf92c8d102c9be7ccfb2e23f93b4a96f67e5edf1c6e4cefd6ca).
No second network download or private job/console log retrieval was performed.

Run/job origin is b321a3dd883031072f26c63d4f2d9f4866b63d9d /
39092477566 / 117571944787. The source/recovery steps succeeded; the actual
transaction step failed and the sole fixed artifact upload succeeded. The
workflow tree is ff2d168a643b3751965caf6e67d283ceb71c3bad.

`verify.py` reads only these files and Git blobs; it imports no project helper,
performs no test/build/runtime, and fetches nothing. It reconstructs the exact
109-input pre-import gate: 106 runtime/source pins plus the frozen host proof,
independent F review and exact current workflow. It checks their published Git
bytes, matching receipt/proof/review maps and all 34 historical Auth, 20 builder,
and 28 retained-crypto source-reference pins. The recorded 16 project TUs bind
to that combined qualified source closure. The new probe and zlib object records
have counts 16 and 21 with AMD64 machine records; configuration and compilation
succeeded under owned suspended launch/job cleanup. Platform preflight v2 passed
with no UDP socket and no owner. The probe PE is reported as 3,298,304 bytes,
SHA256 8442838e2c8b19a68115e8797b6cefd8e6f784e6649c12a08b0db148989dcfaa.
The private PE was removed by the runtime: this verifier binds the reported
identity and source record, not independently retained PE bytes.

Auth/Db/SQL identities, owned interserver channel, game UDP listener and group
membership agree before and after the probe; the database had 99 tables.
Retained native local-buffer/socket and child-job cleanup flags pass, all build
and service jobs report assigned/suspended/resumed and empty/closed, and the
nonce registry is absent in both views after services stop. Firewall, LocalDB,
private files/build, candidate and source stability gates pass. The fixed
failure observation does not separately serialize the raw main's owner-cleanup
field; process/job teardown is retained independently.

Complete player-list, internal development-skip witness, normal version,
approved reference checksum, character choice, Map/world authority and accepted
runtime replacement remain false. No accepted Auth-only test was repeated.
The new received-header Win64 build/preflight/runtime observation succeeded;
the development transaction itself did not qualify.
