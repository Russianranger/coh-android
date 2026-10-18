# Fixed verifier refusal diagnostics

This directory now preserves a SUPERSEDED common-checker draft and its original
one-run proof. Before workflow generation or CI, read-only reconciliation found
that the retained Map255 source map and receiver preflight also freeze the
original checker6285. The draft was not published or executed on a server.
The production checker has therefore been restored byte-for-byte to18c6285.
Its draft775b,13-method test and data-only normalization script are retained as
`.source` files here and in their original Git history. Their old path/hash
bindings describe their recorded qualification revision, not the current path.

A separate new status adapter will delegate the original complete acceptance
function and intercept only the exact native child failure. Its projection
helpers can reuse the qualified draft's exact AST; new adapter controls and
source review are still required. This avoids changing either retained source
gate or rebuilding the unchanged PE/receiver. The details below describe the
historical draft/proof, not completed qualification of that new adapter.

Actual run39101070665 completed the original runtime capture and independently
received the exact GROUPS packet. Its next step refused in the first direct
`check_source_snapshot_verifier.py` invocation, before snapshot admission or
payload retention. The historical checker collapsed every exception and child
refusal to `verification_refused`; its cleaned private payload cannot establish
the inner cause. The canonical actual receipt and independent review remain in
their original evidence directories. No inner cause is inferred here.

The superseded checker draft emits only a fixed phase and, for an exact native failure JSON
with return2 and empty stderr, native stage0..7/status1..7. Malformed, duplicate,
extra, contradictory, oversized, timeout and exception results retain no native
pair. Paths, hashes, identifiers, counts, child stderr and exception text never
enter this public failure projection. Native success output remains private.
The inherited1MiB output check occurs after child capture; it is not a live pipe
allocation bound or a measured process-memory limit.

The read-only source comparison passed once: all nine existing helpers and
constants are unchanged; the normalized `inspect` acceptance/private receipt
AST is identical; all fifteen native validator source files are byte-exact to
actual published18c. It imports no project module and runs only read-only Git.

The new mock-only tests passed once at coordinator source d2a6929dd: thirteen
methods,245 subtest callbacks,294 public-projection checks and184 mocked native
invocations. They import the new checker definitions but launch no native
verifier, compiler, loader, capture, server or old qualification entrypoint.
Source bytes were checked against committed Git before and unchanged after.
The112-byte stderr is the routine unittest result and is retained verbatim.

This source/mock qualification does not admit a scene generation, player,
actor, source provenance, SLEEPING branch, received initial packet, READY or
application ACK. A successor actual capture is required only to obtain the
previously missing failure-stage witness; it must reuse the unchanged admitted
Map PE, receiver and fixture rather than rebuild or requalify them.
