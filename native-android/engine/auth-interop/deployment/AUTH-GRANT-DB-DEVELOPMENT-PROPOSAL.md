# Proposed provisional Auth-to-DB character-list owner

This proposal changes no existing DB/session module, server profile or binary.
Implementation and actual execution require the coordinator's separate scope
review. Normal-version/reference admission in `DB-FIRST-LOGIN-NEXT-SCOPE.md`
remains blocked. This development experiment cannot close that gate.

## Original development policy, with real account authentication

The retained policy matrix SHA256
`c17afbf163cccb5c924138efffe25e3d788c4f851cbc64b2a7988ccb42fd0503`
already qualifies the exact first `handleLogin` block. With `UseFakeAuth=0`, a
`dev:` provider result and client `no_version_check=1`, the original block keeps
`dont_check_version=1`. A missing/mismatched checksum still makes the corrected
verifier report failure, but the original development skip suppresses the outer
version comparison. The subsequent `authValidLogin` still requires the actual
current Auth UID/cookie/account entry. No source patch is proposed for this
exception, and the old matrix need not be rerun.

A distinct new scope could therefore establish actual encrypted Auth login,
real shard selection and consumption of that current grant by original real-auth
Db login, stopping at a complete matching `SEND_PLAYERS`. It must explicitly
report development skip requested/used, checksum enforcement false for this
login, and normal version/reference/Map/full character authority false. It must
not claim that successful development login admitted the missing reference.

The wire checksum should be the measured MD5 of the actually executing new
probe PE, independently checked by its driver. It is not installed as a server
reference, claimed to match a reference, or copied from an arbitrary digest. A
fixed client development label remains an explicitly skipped client declaration,
never a claimed genuine normal provider value.

## New unprotected API and ownership boundary

Proposed files under this deployment directory only:

- `windows/auth_db_development_owner.{h,c}`: a new opaque single-transaction
  owner using unchanged `CohLogin` and `CohDbSession` APIs.
- `windows/db_udp_winsock_compat.{h,c}` and `windows/wrapped_db_udp.c`: a narrow
  Windows UDP port of the unchanged `coh_net_udp.c` translation unit.
- A new probe main, hosted driver and focused tests. Existing selected-only
  probe, TCP compatibility bytes, ordinary DB/session sources and defaults stay
  unchanged.

The owner begins with a numeric explicitly authorized Auth endpoint and private
credentials, and owns both opaque controllers. It exposes no grant setter,
UID/cookie argument, `CohDbAuthReceipt` output or borrowed external DB session.
Only its actual current `COH_LOGIN_AUTHORIZED` controller may produce the private
bridge. Require the actual up shard 1 at loopback port 7000, matching selected
fields, nonzero cookie and exact expected private fixture UID. Construct the DB
login and receipt internally from that same authorization; their fresh local
generation is an owner lifetime label, not an authentication grant. Call only
`coh_db_session_begin`, never `begin_local`, and wipe bridge copies immediately
after serialization. Preserve the original protocol 20110614 and fresh DH
provider. The zero client test-auth-data array is ignored by real-auth Db login;
the complete Auth/game data still comes from its current interserver cache.

Use a fresh owner once, with monotonic bounded service and no retry or reuse
after failure, close, cancellation or suspend. Keep the Auth owner until DB
acceptance/refusal, then close and wipe both. A complete parsed `SEND_PLAYERS`
must match the grant UID. Export only fixed phases/counts/Booleans; wipe the
temporary whole player list, names, Auth data and all grant/receipt/login buffers.
The first actual scope should require an empty list with available slots and
stop there. No character selection, DBID, creation or Map socket belongs to it.

New host controls should exercise success, wrong Auth state, wrong selected
endpoint/UID, absent/noncurrent grant, DB UID mismatch, malformed/truncated list,
duplicate use, cancellation at each transfer and every failure/cleanup boundary.
Test doubles remain synthetic and must not be compiled into the actual probe.

## Windows inputs and source-created registry cleanup

The existing retained Windows TCP shim deliberately refuses UDP and is pinned by
the crypto/core admission. Do not extend or replace it. The new UDP shim must
preserve pointer-sized SOCKET identity through bounded table tokens; implement
only native UDP's socket/fcntl/bind/getsockname/sendto/recvmsg/close subset.
Datagrams stay atomic, independently of Auth's capped TCP sends. Translate
WSAEMSGSIZE into the existing truncation indication and retain exact peer/length
checks. Validate would-block, truncation, short-send refusal, wrong/stale handles,
bind/getname/receive failures and balanced WSA/socket cleanup.

Reuse unchanged `coh_session_key_exchange` and admitted x64 OpenSSL. DB framing
also requires x64 zlib. The exact repository dependency recipe points to
Chromium zlib commit `cf333892c34ab6dbaed37c38a1d5aa6da7b2f99d` and its committed
CMake patch; full dependency source is not locally vendored. Recover and admit
an exact source/artifact before linking only the new probe. Do not select an
unidentified system DLL, rebuild servers or replay old Auth-only suites.

The original installation getter uses `RegCreateKeyExA` even when no value
exists. A first development DB login can thus create the random `ClientProject`
key without an explicit profile write. The new driver must preflight that exact
nonce key absent in the candidate's actual Win32 registry view, then after
service termination delete and verify absence of only that owned key. It must
set no installation/version values and touch no other project key. This cleanup
does not belong to the current selected-only scope, which never calls the
version provider.

The coordinator must retain current PE/generation/channel/UDP/schema/private
credential and cleanup guards in a distinct explicit development scope. Any
future common hook needs separate review; no current registration/selected
scope guard is broadened by this proposal.

## Later ordinary creation and Map handoff

The current paid fixture maps to original VIP status and 12 base slots; no new
entitlement is needed. After an actual character list, a separately qualified
additive creation operation may use only an internal parsed unlocked empty slot,
a bounded name and source-defined creation location. It reuses original
`CHOOSE_PLAYER`; the server validates/reserves the name and allocates the DBID.
The original current session's existing-character choice remains unchanged.

A genuine owned Launcher/MapServer and matching map inputs must exist before
Map transfer. The original server may delete a newly created container when
`setNewMap` fails, and only an actual MapServer response supplies its cookie.
Neither SQL seeding nor a caller-provided DBID/cookie is a substitute.
