# Opt-in DbServer loopback listener binding

Listener prerequisite for the next Android DbServer diagnostic. Current hosted
qualification and donor status are recorded in [ANDROID_DBSERVER.md](../../docs/ANDROID_DBSERVER.md).
Physical Android execution remains a separate gate.

`COH_WINE_DB_LOOPBACK_ONLY` absent preserves the stock `sockBind` result and local
address. Only the exact value `1` enables the mode. Empty, zero, padded, or other
values fail startup with code 2. Initialization is the first operation in `main`,
before `memCheckInit`, the persistence fixture bypass, and normal startup. An
atomic one-way policy refuses activation after any `sockBind` attempt or a second
activation. Other callers of the staged UtilitiesLib retain the default policy.

The enabled policy changes wildcard IPv4 listener binds to `127.0.0.1`; explicit
addresses must be in IPv4 `127/8`. Every successful bind is checked with
`getsockname`: exact address size/family, exact selected loopback address, nonzero
actual port, and equality with any requested nonzero port. `SO_TYPE` must identify
TCP or UDP. Only then does it emit the flushed stdout record
`COH_WINE_DB_LOOPBACK_ONLY bind verified: protocol=... address=... port=...`. Invalid addresses,
bind failures, and failed endpoint verification close the supplied socket and
exit the process with code 2, because some stock callers ignore bind failures.

The flushed stdout startup acknowledgement confirms policy activation. Verified
endpoint records prove successful binds, not a subsequent `listen` or readiness.
Normal `-exportdump` calls `dbInit(-1)` and binds real endpoints. The existing two
hosted normal exports now require default mode first, then fixed-input and
loopback mode together. The second export must record all 12 synchronous TCP
binds and UDP7000, derived from the immutable source and port constants. TCP6992
crash-map reporting starts in an unchecked `CreateThread`; its zero-or-one
observed bind is preserved separately in the source contract as asynchronous,
and is not required before the export returns. Every observed record must still
match an exact source-derived endpoint. Unknown, duplicate, missing synchronous,
malformed, or nonloopback records fail the gate. The same catalog, schema,
process-exit and cleanup gates remain required, with no extra server launches.
The persistence fixture bypasses normal initialization and does not itself
exercise listeners; its loopback and fixed-input flags are explicitly absent.

The boundary covers explicit IPv4 listener binds through `sockBind`, including
`netInit` TCP/UDP, crash-map reporting and the assertion listener. This is not
network namespace isolation or an outbound-connection restriction. The existing
host network namespace gate remains required. PostgreSQL and the virtual display
already have their separate loopback/no-TCP configuration.

`test_loopback_bind.py` compiles the exact staged policy and startup parser. It
uses real TCP/UDP sockets to check default behavior, ephemeral and requested
ports, explicit loopback addresses, refusal, late/repeated activation, and
close-before-exit for injected observation failures. Linux runs use a small Win32
API shim; `--require-windows` requires native MSVC/Winsock. The source preparation
tests bind the added files and startup ordering to the package receipt while
leaving the immutable upstream snapshot unchanged.

Guest and host validation reject altered mode metadata, source contracts and
endpoint evidence. The hosted qualification workflow runs the native Windows
contract before building both variants. The current qualification record binds
the tested source, package and runtime evidence; adoption by another gate is
recorded separately. No Android listener execution is claimed.
