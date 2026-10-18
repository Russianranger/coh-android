# Development DB received-header observation

This nonshipping overlay adds diagnostic evidence for the first provisional
Auth-to-DB development experiment. It changes neither the ordinary session nor
its unknown-command/body refusal policy. It does not admit an unknown body,
raise a budget, retry, select/create a character, or authorize a Map.

Actual run 39090126094 (source ed77036d1b7f7e47588d74408506d738293643a9)
returned the fixed OWNER_SERVICE / DB / UNSUPPORTED observation: Auth AUTHORIZED,
one queued DB login, zero complete lists and three unsupported counts. That
aggregate cannot identify the first unsupported command, whether a SEND_PLAYERS
header arrived, or whether an application body or transport parser refused.
The sole root-owned artifact is 12122124306, 16,275 bytes, SHA256
4b96a2fe31f1612ab90b47a6371584010f3d862be8a456e6537bbd6f6c732ee3.
No new runtime claim follows from these source controls.

`wrapped_db_received_prefix.c` includes the exact ordinary `coh_db_session.c`
with only create/service/destroy and the actual `coh_net_udp_next` call renamed.
It forwards every call, return value, message and drain order unchanged. Only a
successful copied message from that same active session/UDP binding creates a
row. Its header is read by the original static `message_command` decoder;
legacy offset five and compressed 32-bit headers therefore follow that decoder.
The first sixteen copied headers retain fixed source names (normalized enum
2..21), `NONE` for a failed header, or `UNKNOWN` for an unlisted decoded command.
No raw opcode, copied body, string, account, UID, cookie, pointer or generation
is retained in this observation. Total count and truncation are explicit.

The single process permits one successful session lifetime and generation one.
A second lifetime, rebegin/generation change, UDP-binding/transport-version change or service
reentry invalidates context. Destruction removes private pointers before the
ordinary free while retaining only the scalar prefix. The getter operates only
between service calls and refuses output aliases to owned session, current
message and observer storage. Invalid context remains explicitly unverified.

`db_development_received_probe.c` includes the entire unchanged prior probe
main. Its one fixed printf is bounded privately, its v1 schema becomes v2, and
fixed prefix JSON is appended after original cleanup. It returns the original
main's status. The old whole-main hash and old source proof remain admitted;
there is no replacement success predicate or cleanup implementation. The new
project replaces only that main TU and the session TU with these two wrappers
and still has sixteen project TUs plus the same twenty-one static zlib TUs.
Server PEs, profile, crypto, credentials, deadlines and grant ownership stay at
the accepted inputs.

`db_received_prefix.py` requires the exact bounded keysets and types, source
name/decoded-header pairs and cardinalities. Production child admission requires
v2, validates and projects the prefix separately, then uses the unchanged v1
positive admission function for all prior policy/cleanup claims. The returned
policy result is explicitly labeled a projection and records both its actual v2
producer schema and normalized v1 policy schema; it is not a raw native record. A passing list
also needs available, retired, verified context. A failure projection is latched
before child teardown and survives a late cleanup error while preserving the
first error. The public prefix explicitly says
`first_unsupported_attributed=false` and `body_acceptance_observed=false`.
A received-header prefix is not a complete frame inventory or a decoded-body
witness. A lower receive failure adds no row; a later failure must not reuse a
prior packet as its cause.

Focused controls (no old qualifier replay):

```
python -m unittest -v test_db_received_prefix
```

The controls check exact source catalogue and source hashes; unchanged original
positive admission; strict negative/privacy cases; actual additive main output
under optimized and ASan/UBSan synthetic APIs; and same-copy session wrapper
ordering/lifetime/limits/parity through a controlled UDP API with the real
ordinary session, body encoders/parsers and bit protocol. They do not open a
socket, run a server, execute a WinAPI, or establish real packet provenance.
The synthetic 14→8→8 sequence is solely a controlled order case, never an
identification of the actual three unsupported counts.

The frozen new wrapper shell passes 827 checks in 30 synthetic cases in both
optimized and ASan/UBSan builds. Its five linked TUs are the new harness (which
includes the unchanged session), ordinary DB parser, Auth parser, bit protocol
and Blowfish. Only the two unchanged protocol/Blowfish TUs use O0 under the
retained warning policy; sanitizer flags apply to every object. Three new main
overlay cases (success, service refusal, platform preflight) also pass in both
builds. The six focused Python methods pass. No Windows compilation or new
actual live observation has been performed for this overlay.
