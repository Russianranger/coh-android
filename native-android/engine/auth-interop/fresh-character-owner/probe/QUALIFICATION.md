# Fresh allocation probe: private policy and CLI controls

The new `fresh_probe_policy.c` and `fresh_character_probe.c` implement the next
source boundary after the already qualified fresh-character owner. The old
`.proposed` files remain historical. The qualification below predates the new
Windows backend source and its separately scoped
[host API controls](windows/QUALIFICATION.md). Actual Windows compilation and
execution of that backend remain separate obligations; there is no shipping
build target for this new CLI. Neither the ordinary owner/session sources nor
the original writers, services, profiles, accepted APKs or workflow are changed.

`fresh_probe_decode_policy` consumes the proposed exact96-byte LE record into
private caller-owned storage, with no allocation or file/process access. It
checks the fixed format, bounded Auth port, Atlas1/loopback7001 tuple, nonzero
process generation/hash/nonce and zero reserved bytes. Misaligned or overlapping
output refuses, and failed output is unchanged. These are syntactic checks:
they establish no live process, executable identity, entropy, authentication or
Map readiness. The future backend must measure/admit those actual facts through
retained regular nonreparse file/process handles before consuming this record.

The CLI accepts only `--platform-preflight` or `--allocate-offer PRIVATE_POLICY_FILE`.
Runtime reads account1..14, password1..16 and authored name1..63 printable ASCII
bytes as three LF-terminated lines plus exact EOF, refusing stdio read errors.
These private values never
enter argv or receipt output. It begins once, wipes its three local buffers and
configuration immediately after begin, bounds service time, and destroys the
owner before finalizing its borrowed platform/provider lease. Fixed diagnostics
must meet every one-shot, generation, cleanup, source-policy and authority
barrier before success. A late cleanup failure cannot erase the first fixed
owner error or its persistent-allocation-possible observation.

If an unexpected consuming owner destroy refuses and leaves the owner live,
the dependent platform/provider lease is retained until process exit. Cleanup
remains incomplete and the CLI fails; it must not release a borrowed provider
beneath live controllers. Independent platform finalizers are otherwise all
attempted even after an owner close/diagnostics failure or platform failure.
No native cancellation, wiping, retirement or handle closure claims SQL rollback.

The final focused run is `worker-c-probe-final-03`, using release, AddressSanitizer
and UndefinedBehaviorSanitizer independently. Each mode passed668 private-record
parser checks and104 CLI controls. The parser checks fixed fields/bit mutations,
all short lengths, excess/null input, alias/alignment, port boundaries, empty
generation/hash/nonce and each possible sole nonzero hash/nonce position. The
CLI controls cover private-input bounds, exact invocations, all admission flags,
generation/phase/policy/authority barriers, each fallible component and cleanup
step, timeout/clock regression, first-error retention and dependent lease lifetime.
One new host stream returns EIO after three complete valid synthetic lines,
proving it is refused before platform initialization rather than mistaken for EOF.

These CLI controls link the actual new CLI to explicitly labelled public-owner
and platform doubles. They execute no original owner, Login/DB controller,
socket, Windows API, private policy file, original service or SQL transaction.
The existing owner127-scenario and encrypted-wire qualifiers were not replayed.
No production fresh allocation, persistent character, Map handoff, READY,
application ACK, Android/Thor execution, global96MiB fit or RSS/GPU measurement
is admitted. LeakSanitizer alone is disabled for this executor; no leak claim is
made from the doubles or their static storage.

`qualification/controls-20261018/worker-c-probe-final-03.json.gz` binds17 exact
compiler/source inputs before/after, all compiler commands, six host executable
hashes and315 result records. Its companion trace archive preserves exact child
stdout/stderr and dependency output; host executables stay in the external run
directory. The source was not committed during this development qualification;
primary integration must compare all17 raw pins to committed source. No remote,
Windows PE, Android ELF or original-service provenance follows from those hashes.

Three earlier successful local stages are retained separately. `dev-03` tested
the first CLI, `final-01` preserved actual cleanup error codes, and `final-02`
corrected the dependent-provider failure path. `final-03` adds the EOF-versus-EIO
refusal. Exact `final-01` and `final-02` predecessors of the last narrow source
changes are retained and checked against their receipts.
The initial dependency query failed because the new checker omitted the native
include directory, before compilation; that first stderr remains in the tool
transcript rather than a separately retained file. A second new run compiled
and exposed an incorrect test enum expectation (DB failure6, not list failure7);
its exact child output is retained. No original production owner was changed
to satisfy either development error.

For a changed source boundary, use a fresh external destination:

```sh
python native-android/engine/auth-interop/fresh-character-owner/probe/check_fresh_probe_controls.py --source-root . --output NEW_EXTERNAL_DIRECTORY --sanitize
```

## Next actual original-server transaction

The next executable deployment step is still the fresh Windows profile/service
readiness qualification, together with actual Windows admission of the new
backend source for this API. The
accepted compiler/model helper artifact is insufficient to launch and hold the
original Map process. The backend/driver must not accept a policy nonce or an
open UDP endpoint as a substitute for independently observed same-realm readiness.

The original source identifies the required chain. `dbRegister` registers the
Map with the current DbServer; `dbReadyForPlayers` sends the current map ID in
`DBCLIENT_READY_FOR_PLAYERS`, whose ordinary DB dispatcher calls
`dbClientReadyForPlayers`. A separate actual observer must bind that event to the
retained admitted original Map process, generation and the exact fresh Auth/DB/SQL
realm. A sleeping diagnostic Map or compiled PE alone cannot satisfy it.

After that proof, the private driver creates the fixed policy and launches the
admitted new probe with a fresh authorized account/password/name through stdin.
The real owner must consume the same Auth grant into encrypted DB, require the
complete matching empty list, derive the slot and queue the unchanged ordinary
choose writer. Original `handleChoosePlayer` validates and temporarily reserves
the name, selects the start map, enforces real capacity and asynchronously
allocates the new container. The original `setNewMap`/Map receipt path must
produce a genuine parser-observed creation offer for the independently owned
Atlas Map1 endpoint. The native owner retires only that offer; it does not
connect to Map or initialize the character. If queueing occurred, allocation
remains possible on every subsequent failure or cancellation.

The driver must stop all owned original services and Map before retiring the
whole fresh SQL database and isolated profile, preserving before/after evidence
without publishing private identity/records/packets. It must leave normal client
version/reference-checksum acceptance false under this explicitly provisional
development policy. A future full-character writer and resumable Map owner are
separate work: this terminal offer is deliberately not resumable. Gates25–27
remain open.
