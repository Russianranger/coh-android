# Complete command13 inventory envelopes during WAIT_PLAYERS

The genuine received-header witness from run39094808506 adds
`DBGAMESERVER_ACCOUNTSERVER_INVENTORY` after UNAVAILABLE/CHARCOUNT/CHARCOUNT,
all in WAIT_PLAYERS. Its header-only diagnostic establishes no body fields,
account inventory authority or first-unsupported attribution. This source change
is developed independently; the frozen6115 initial receiver and pending68954
preflight proposal remain unchanged until the coordinator authorizes integration.

The original direct `accountInventoryRelayToClient` prefix writes authoritative
and free-transfer-only one-bit values and Auto transfer tokens.
`accountInventoryRelayHelper` writes a NUL shard name and Auto item count, then
each item's SKU via Auto2 (low U32, high U32) and granted/claimed/expiration via
three Autos. It writes LOYALTY_BITS=128 via BitsArray and seven Auto tail values:
unspent/earned loyalty, currency, last-email time/count, account-status flags and
bonus slots. The Queue passthrough and complete Game receive function agree.
The BitsArray operation ALWAYS aligns to a byte, including packed scalar mode.
Its ignored padding need not be zero. Strings continue at their existing bit
offset. There is no zipped sub-body or additional premium block.

The complete native parser reuses the existing bounded scalar/Auto/string
readers in the same translation unit. The original8/14 parser and helper
function bodies remain identical to their C99 qualification. Every item field,
padding bit, loyalty bit and tail scalar must fit the declared logical packet;
any tail, truncation, overlimit or invalid flag/profile refuses atomically.
Items are bounded at1024, strings at16384 bytes including NUL and declared
standalone packets at65536 bytes. These are native refusal domains, not source
server limits. The ordinary session's copied message limit remains16384 bytes;
a standalone valid test packet need not fit the runtime copied path.

The 8-byte parser output contains only item count and the decoded authoritative
wire flag. That flag is not proof of trusted inventory. SKU values, grants,
claims, expiration, shard name, transfer state, loyalty bits, currency, status
flags and bonus slots never escape. There is no catalog/entitlement join, item
sorting or inventory application. Release source catalog-validation macros are
inactive outside FULLDEBUG; debug assertions do not become invented wire
constraints. Duplicate/order/count relationships and numeric masks are not
introduced. The original Game UI can ignore a cached message after seeing an
authoritative one; this validator still requires a complete body and applies no
UI state, so it does not claim that cache-precedence transition.

Only WAIT_PLAYERS handles command13. After full validation and overflow checks,
the session updates a separate lifetime message counter and last item count.
It does not advance phase, reset its deadline, change UID/list/slots, send an
application command or publish inventory/catalog/loyalty state. Failures use the
existing stop/forget path while preserving earlier completed diagnostic facts.
Unknown commands and the opaque Auth-to-DB owner's strict unsupported==0,
exactly-one-matching-empty-list/noqueue/nochoice/nohandoff gate remain unchanged.

The new focused native entrypoint covers only inventory boundary/refusal cases
and new mixed14→8→8→13→players composition. It includes historical setup helpers
with their old main renamed and never called; no old8822 suite is replayed.
The original account-control fixture producer is reused only to supply the
three source-layout setup messages. All login/UDP data in the native tests are
synthetic. The new pinned inventory oracle uses whole source sender/relay/client
functions on bounded trusted data, with catalog/UI/network effects stubbed.
Original unsafe packet code runs only as the trusted O0 oracle, not under the
native sanitizer claim. Exact source/function pins, execution scope, host sizes
and stack rows are recorded in the new receipt.

After committing all new inputs, run only:

```
python native-android/engine/dbclient/check_account_inventory.py --source-root . --sanitize --output /absolute/new/inventory.json
```

No live Auth/DB, sockets, captures, Windows/Android runtime, actor publication,
application ACK, current generation or global memory admission follows.
