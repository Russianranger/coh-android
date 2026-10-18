Run39085257785 reached the genuine SHARDS_READY state with three received
frames and zero listed shards. The fixed failure projection and independently
checked pre/post service generations, registration channel and cleanup close
the previous observation gap. It did not reach shard selection or AC_PLAY_OK.

The source-owned fixture has one registered shard in group1, but its selected
account SQL omitted `user_server_group`. The original `get_server_groups`
procedure returns only that account's relation rows. `CAccount::Load` fills
unused region entries with -1; the complete LoginUser carries those entries
through registration and lookup. The unchanged native controller sends a
protocol191021 server-list request with zero explicit groups. The original
server then uses the account's groups and includes a shard only when its group
is0 or matches an account group. Group1 therefore has no match in this fixture.
The actual receipt witnesses an empty returned list; it does not directly
observe the private SQL membership table. The missing relation is a
source-inferred causal candidate supported by the exact fixture and filter.

The correction inserts exactly the normal fixture-account-to-group1 relation
inside the selected-only private SQL. It retains the original group1 shard,
server filters, Auth-only account SQL, binaries, encryption, credentials,
timeouts, development/version/checksum policy and shipping profiles.

A new read-only scalar executes the original `cohauth.dbo.get_server_groups`
into a session-only table variable. It requires exactly one matching account
and Auth row, the exact single loopback shard1/group1/port7000, exactly one
matching account-group relation and exactly one returned group1. All database
objects use three-part names, so sqlcmd has no `USE` context-change message.
The existing whole-output numeric scalar parser remains strict; the new gate
also requires exact integer1. It exports only verified Booleans, no returned
group values or account identifiers. The gate runs after seeding, immediately
before the probe and in the always-running post-probe ownership observer.
A failed post-probe check prevents qualification and preserves a primary
native failure if one was already active.

Five new host methods check the same generated SELECT/CASE predicate and
original procedure SELECT using an explicitly scoped SQLite dialect adapter,
including missing, wrong, extra and stale relationships, account/UID/shard
metadata and stale returned groups. They also check malformed scalar types,
pre/post refusal and primary exception preservation. A C++ shell compiles the
complete unmodified original MakeServerListPacket and its PushInt/PushShort
helpers: unassigned group1 is omitted, matching group1 is returned, another
group is omitted, an explicit match is returned once, and the original group0
universal behavior remains unchanged. The fixture never adopts group0.

Run `python -m unittest -v test_selected_group_membership.py` from this
deployment directory on Linux with c++ available. These are new source/host
controls, not SQL Server execution, a repeated Auth-only suite, an actual
service retry or a live grant qualification. Exact whole-function, source and
sanitized actual-receipt pins are preserved with the new proof.
