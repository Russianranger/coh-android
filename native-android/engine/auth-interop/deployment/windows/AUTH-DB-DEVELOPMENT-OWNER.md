# Nonshipping Auth-to-DB development owner

`auth_db_development_owner.{h,c}` owns one fresh native Auth controller and one
native DB controller. It can publish only scalar observations of a complete
matching empty character list. It has no receipt import/export, raw UID/cookie,
DBID, character-name, session, selection, creation or Map API.

This is the separately labeled development experiment proposed by D at
`41964521bbe1c12e61a3384af6757223871909c5`. The original
`DBServer/src/clientcomm.c::handleLogin` may retain the client version skip when
its provider returns `dev:` even with real authentication. The owner requests
that original policy explicitly. It does not observe the server predicate,
admit a normal version or checksum reference, or weaken the normal-version
gate. The configured checksum is the actual probe's independently measured MD5,
not an installed or admitted reference. Real remote policy and fresh process,
channel, credential, fixture and source provenance remain the hosted driver's
responsibility. A prior receipt cannot enter this API.

`begin` consumes the owner before validation or allocation. The private bridge
requires the same controller's current `AUTHORIZED` result, exact protocol191021,
four complete Auth frames with no pending/buffered/credential/error residue, and
the actually selected up shard1 at127.0.0.1:7000. Its nonzero cookie and private
fixture UID900001 are checked against the actual grant, then copied internally
into both ordinary DB login and receipt. The inaccessible receipt's generation1
is only this owner's local lifetime label. The grant is marked consumed before
DB allocation or begin, and every bridge copy is wiped on success or refusal.
The ordinary Auth receipt is frozen state; retaining its controller is not
revocation monitoring and implies no source-enforced cookie TTL.

The DB profile uses the unchanged real-auth `coh_db_session_begin`, original
protocol20110614, a fresh nonzero probe-supplied transport nonce, loopback local
ephemeral bind, encryption required and the unchanged session DH callback.
The provider and its context stay live and immutable through both controllers'
destruction. D's separate Windows UDP wrapper and exact x64 zlib closure are
required before a Windows probe can use this owner. No ordinary Login, DB,
session crypto, network, existing TCP shim or default build file is changed.

The complete list must match the grant UID, have positive base/total slots and
every slot EMPTY, unlocked, nonvisitor and noninvalid. The observed DB generation
must be1, with exactly one login and list, zero selection generation and no
queue updates, unsupported commands, choices or handoffs. The complete original
parser owns string/slot/auth-array/end-of-message validation; this owner checks
its resulting state. The unchanged copied-message path admits at most16KiB,
including decoded data. Original independent inventory traffic can precede the
list; this deliberately conservative owner refuses it. No continuation or
ignored-command allowance is inferred from synthetic controls.

All calls use one owner thread. Cancel is polled before Auth-to-DB bridging and
before success. Callback reentry into begin/service/timeout/cancel/close/destroy
or diagnostics refuses before mutation; busy destroy preserves the caller's
pointer. Known owner/provider-object aliases are rejected. The existing callback
interfaces do not declare context sizes: their disjoint immutable lifetime is an
explicit precondition. The fixed total30s deadline and explicit timeout close
before any successful publication. First terminal status, cause and actual
ordinary-controller phases survive later rejected operations.

After the one complete list and final cancellation check, Auth closes and DB
intentionally cancel-closes; both are destroyed before COMPLETE and counts become
public. Observed AUTHORIZED/CHARACTERS phases remain separate from final
CLOSED/CANCELLED phases. No graceful peer-disconnect acknowledgement is claimed.
Driver cleanup must independently verify Windows handles and WSA teardown;
ordinary UDP's closure counters cannot prove a failed `closesocket` was released.

The host controls use explicit synthetic Login/DB/session-callback doubles and
track all three allocation sites, zero-before-free, every cancellation poll,
callback reentry, one-shot failures, aliases and list/counter mutations. Simulated
malformed/truncated parser returns test propagation, not another wire parser
qualification. A separate compile/link check resolves all13 actual unchanged
native production translation units without executing them. Release, ASan and
UBSan source-bound receipts are produced only by this new focused helper:

```sh
python3 native-android/engine/auth-interop/deployment/qualify_auth_db_development_owner.py \
  --source-root . --output /tmp/fresh-auth-db-owner --sanitize
```

The new opaque owner is232B on the qualified x64 host (including its40B config
and152B scalar diagnostics). Its complete temporary player list is41772B.
Existing Auth/DB/UDP/Net/zlib/crypto owners and their stacks remain additional;
there is no global budget or whole-callstack admission. Wipe claims cover this
owner's explicit buffers and retained controllers, not every transient stack
copy inside the unchanged parsers. No real socket, cryptography, account login,
development server predicate, character selection, Map/world, actor or ACK
authority is established by these synthetic controls.
