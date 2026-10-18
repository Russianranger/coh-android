# Fixed selected-probe failure observation

Both cases in run `39083677928` reached DbServer Ready and the native probe,
then returned `selected_private_probe_failed`. The old branch checks either a
nonzero child return or oversized stdout before parsing. Its receipts retain
neither input, so they establish no more precise native cause. All service,
firewall, SQL, private-file and source/candidate cleanup gates passed.

The additive diagnostic changes only the Python selected driver. Native probe,
login core, server PEs, profiles, crypto, protocol and timeouts are unchanged.
It is not a protocol repair or a successful selected-grant claim.

An optional driver-owned empty dictionary receives a projection from the actual
Popen child and its private TemporaryFile before exceptions or Job teardown.
Only exit-zero/exit-one completed children can provide JSON evidence. Running,
unexpected-exit, malformed, duplicate-field, nonfinite, extra-field, invalid
type and oversized outputs yield fixed refusal/unavailable categories. The
entire original fixed native key set is required, including false DB/Map,
normal-version, checksum-relaxation and independent-provenance claims.

The public failure object contains only fixed child/JSON categories, the
source-defined `CohLoginState` name, protocol class ZERO/EXPECTED/OTHER, bounded
counts and Booleans. It exports no raw protocol value, packet, grant, account,
UID, cookie, path, exception text, output body or body hash. Stdout length
saturates at 8193 to represent the existing 8192-byte limit. A VALID observation
means this diagnostic shape was admitted, never that the grant was admitted.
The owned probe cleanup Boolean and fixed outcome are filled even if late Job
cleanup raises. A native/parse/timeout exception retains its exact identity/code
when Job stop or fallback handle close also throws; cleanup failure remains
explicit and cannot qualify success.

After every attempted probe outcome, the same original service/SQL generation,
channel, UDP-owner, Auth-listener and shard-state observer runs in `finally`.
An observer refusal has only the fixed public enum
`OWNED_RUNTIME_OBSERVER_REFUSED`. A prior probe exception retains precedence;
a later observer error cannot replace that first cause or discard the safe
projection. Success still requires the unchanged positive probe admission and
the post-probe ownership check, followed by original full outer teardown.

Six new source-only methods in `test_selected_probe_failure.py` cover exact
state-enum binding, every projection/privacy refusal class, actual-shaped child
failure and late cleanup ordering, unchanged positive validation, and post-probe
observation on success/refusal/timeout with first-failure preservation. No C
compiler, network, SQL or service executes in these tests. The old Auth-only,
native and composition suites are not replayed for this diagnostic addition.

Only a coordinator-reviewed fresh cap1024 diagnostic case is needed next.
The capped case can return after the normal case supplies concrete protocol
input or an actual grant. Continue to upload only the sanitized receipt.
