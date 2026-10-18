# Actual account-control progress and Inventory header — 39094808506

This fresh actual development transaction failed at OWNER_SERVICE / FAILED /
DB / UNSUPPORTED after Auth AUTHORIZED (four frames) and one queued DB login.
The fixed DB phase was WAIT_PLAYERS, unsupported=1, player_lists=0, and queue,
choice and handoff counts were zero. It did not qualify a complete player list.

The bound, retired and untruncated same-copy received-header prefix now has four
entries, all decoded in modern/uncompressed WAIT_PLAYERS:

1. DBGAMESERVER_ACCOUNTSERVER_UNAVAILABLE
2. DBGAMESERVER_ACCOUNTSERVER_CHARCOUNT
3. DBGAMESERVER_ACCOUNTSERVER_CHARCOUNT
4. DBGAMESERVER_ACCOUNTSERVER_INVENTORY

There was one session and six service calls. No SEND_PLAYERS header occurs in
these four copied messages; this is not an assertion about other queued or
future server traffic. Raw bodies, credentials, UID and cookie were not exported.
The prefix's first-unsupported-attributed and body-acceptance flags remain false.

The exact current source supports a specific explanation. The new complete
bounded 14/8 handlers must return OK before the ordinary loop reaches the later
Inventory fetch. This supports their completion by source-derived control flow,
without revealing their body values or upgrading the header observer's scope.
Command 13 is still outside the current recognized branches: it enters the
independent-service default, increments unsupported once, and returns OK without
parsing its body. The unchanged development owner then rejects unsupported=1.
WAIT_PLAYERS and the complete four-header prefix agree with this trace; the
failure is not an observed Inventory body-parser refusal. A future Inventory
handler needs complete original-body validation, not a generic unknown skip.

The root-downloaded artifact 12124625207 is preserved once as `artifact.zip`:
18,245 bytes, SHA256
8d8b2518f5420a129d097b705c50406f5cbf323d1dd697c5941bb7dfa01bd4bd.
Its sole CRLF `receipt.json` is byte-exact: 77,676 bytes, SHA256
868fbad511f087d7cee898201054b3270499c94cac5328d37a1a6f570b332080.
The root's fixed `api.json` is 3,478 bytes, SHA256
b84645297bba4e8ba2c6c06666ef8120c287ab1b91ccf6216fe6d9dc20777c03.
No duplicate download or private job/console log retrieval was performed.

The run/job origin is 39094808506 / 117578922139, source
6e96fe22a567a3e252449feb37483cfea1566d8a, tree
8d1fb5f8e37cfa6b277ddd9f49d903fbfc703ad6. Source and recovery steps passed,
the fresh transaction step failed, and its fixed receipt upload passed.

`verify.py` fetches nothing and executes no project helper, test, compiler or
runtime. It pins the exact artifact/member/API and reconstructs the 137-source
pre-import gate from published Git bytes: 128 runtime inputs, two common CMake
inputs, six frozen proof/review files, and the exact workflow. The current
128-map, independent F review, two common integration pins and current C99
36-input proof are bound separately. Old 126/106 proofs remain immutable
historical records, not current whole-source admission claims. The verifier also
checks 34 historical Auth, 20 builder and 28 crypto-reference source pins and
four exact current whole-function byte spans for the source-derived trace.

The actual new build has 17 project objects and 21 zlib objects with AMD64 records;
project source hashes bind to the admitted closure. Its reported private PE is
3,299,840 bytes, SHA256
1978acc1b3de864b2e658857fbdef4e427b1b58d44f2a05d269905595ea2e317.
The new platform preflight passed with no UDP socket/owner. This verifier binds
reported PE identity and source/object records; private PE bytes were removed
by the runtime and are not independently retained here.

Auth/Db/SQL generations, owned channel, game listener and normal group membership
are unchanged across the probe; the database had 99 tables. The native socket
was created and closed once, with zero active handles or cleanup errors.
Retained sensitive-buffer/socket/child-job flags pass; suspended assignment,
verified resume, empty/closed build and service jobs, registry absence in both
views after stopped services, firewall/LocalDB/private-file teardown and final
source/candidate stability all pass. The fixed failure observation does not
separately serialize the raw main's owner-cleanup flag; process/job teardown is
retained independently.

Complete list, normal version, approved reference checksum, internal development
skip witness, character choice, Map/world authority and accepted runtime
replacement remain false. No old Auth-only or source/native suite was replayed.
The source-qualified 14/8 handler composition advanced to a new actual Inventory
header; it did not complete the original development player-list transaction.
