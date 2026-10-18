# Complete account controls during the DB character-list wait

The genuine same-copy received-header witness from run 39092477566 contains
`DBGAMESERVER_ACCOUNTSERVER_UNAVAILABLE`, then two
`DBGAMESERVER_ACCOUNTSERVER_CHARCOUNT` envelopes, all during WAIT_PLAYERS. It
establishes the headers and order, not body values, subtype/error text, body
acceptance, or which unsupported increment belongs to which header. The retained
D evidence remains the runtime witness. This change is new source qualification.

`accountservercomm.c`'s `account_clientAccountServerUnavailable` emits only the
command. The original Game `receiveAccountServerUnavailable` consumes no body
and calls `accountCatalogDone`; the Queue passthrough consumes/writes no body.
The independent `ACCOUNT_SVR_RELAY_CMD` direct path also emits this command with
a string at line 966, although the client ignores it. That form is refused:
only the complete command-only sender/relay form is supported.

CHARCOUNT uses `pktGetBitsAuto` for a shard count. Zero is followed by one NUL
error string. A positive count is followed by that many NUL shard names, each
with five Auto integers: unlocked, total, account slots, server slots and VIP-only
status. `handleSendCharacterCounts` updates transfer UI/test state, not the
character list; its count loop uses signed int. The Queue relay forwards the
same fields. `account_clientCountFailure` sends zero plus `AccountClientNoServer`.
The source login path requests catalog, registration and loyalty authentication
before its eventual character list; absent AccountServer behavior is compatible
with the observed headers, but actual body values or eventual SEND_PLAYERS are
not inferred. All original source/function pins are in the new test manifest.

The complete parser has no heap or string copies. Its 12-byte output contains
only normalized command, shard count and zero-count/error branch. Bounds are
65536 declared packet bytes (existing DB parser domain), 256 shard rows and
16384 bytes including NUL per string. These are native refusal domains, not
source server limits. The existing session copied-packet cap remains 16384
bytes, so a standalone parser input within its domain need not fit that path.
All five row values retain source U32 decoding; there are no invented numeric
relationships or Boolean VIP-status constraints. Aligned Auto-bin reserved bits,
unknown commands, missing fields/NUL, overlimits and every logical tail refuse.
Physical backing bytes outside the declared logical bit length are not payload.
All parser errors preserve output, including aliases/invalid profiles.

The only session change is a WAIT_PLAYERS application branch. Complete valid
controls update separate lifetime diagnostic counters and the last CHARCOUNT
branch. Overflow refuses before any counter/last-field mutation. It changes no
phase, UID, player list, request deadline or sends. Errors follow the existing
session stop/forget path; previously completed controls remain diagnostic facts.
Cancellation before the service transaction and the unchanged request deadline
still stop the owner. Other commands retain their existing branches; unknown
commands still increment unsupported. The Auth-to-DB development owner remains
byte-identical and still requires unsupported==0, exactly one complete matching
empty/unlocked list, no queue/choice/handoff, then cancel-close/destroy before
COMPLETE. Account controls themselves cannot satisfy that success condition.

The new focused test uses the real session/parser/protocol with fake UDP and
explicitly synthetic login fixtures; it neither creates actual grants nor runs
Auth/DB/services. Four legacy/alignment profiles cover synthetic complete
14→8→8 progression, real unchanged SEND_PLAYERS parsing afterwards, malformed
controls, overflow, invalid phases, unsupported commands, cancellation and
unchanged deadline. Direct tests cover complete and truncated source fixtures,
string/row/window boundaries, tails, signed count refusal, aligned reserved bins,
output aliases and invalid lengths. The trusted O0 oracle executes both complete
original failure senders, original bit/string/Auto functions, complete original
Game consumers and Queue passthroughs. Positive row bodies are fixture-written
with original bit writers; the complete AccountServer dispatcher is not run.
Unsafe original readers see only trusted padded complete data. Original UI,
network and account services are replaced by bounded test observers.

Run only this new qualifier, after committing its exact inputs:

```
python native-android/engine/dbclient/check_account_controls.py --source-root . --sanitize --output /absolute/new/account-controls.json
```

It admits compiler-derived project/header dependencies, helper and original
source bytes against HEAD before frozen helper imports, rechecks them through
all modes, and records source hashes. Protocol/Blowfish retain the existing O0
host compiler policy; other native code is optimized. ASan/UBSan cover native
code. The new production parser is additionally compiled as strict C99 in every
mode, matching the existing DB client target; the test harness uses C11.
Sanitizers do not cover the trusted original x86 writer oracle. Historical suites, actual
servers, captures, Windows/Android ABI, current generation, world authority and
global memory admission are outside this proof. New session/diagnostics scalar
storage is 24 bytes; exact measured host sizes and function stack rows are in
the qualification receipt. The parser adds no retained owner or provider lease.
