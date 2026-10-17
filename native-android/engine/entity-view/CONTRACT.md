# Source-defined final sky and slave camera fields

`coh_world_view_read` reads the original sky-interest bit, conditional finite
weight and packed2 sky IDs, then slave-present bit and optional three finite
camera PYR words. Absent sky uses the original consumer defaults sky0/sky1 and
weight0. This source-defined default is retained alongside the explicit presence
bit. Sky IDs remain raw, without file/resource dictionary authority. Slave
camera PYR is not a character transform, actor identity or selected DBID.

All reader/input/output/workspace spans must be pairwise disjoint. Caller-owned
POD storage has no allocations or retained input. Input, output, workspace,
4096-byte stack reserve and caller-retained bytes fit the8MiB aggregate limit.
Output and reader commit together after the complete view subtransaction. Late
slave truncation/invalid float rolls back the already parsed sky values. Bytes
following this body remain unread; the original server may append a byte-aligned
meta-command and further entity packet data. This is no packet-end claim.

F's sky oracle executes the whole unchanged sendSkyFade/receiveSkyFade and
original bitstream code with explicit sky callback projection and demo disabled.
The local slave oracle executes exact original conditional producer and consumer
blocks and original bitstream functions. Outer master/slave/control-client
selection and camera ownership conditions are not executed or authorized by
those fixtures. Source hashes and exact block hashes are recorded separately.

The native suite joins200 sky source fixtures with both slave-presence variants
at matching absolute bit cursors. It compares exact raw/consumer-default fields,
cursors and trailing unread data, tests every truncation bit and single-bit
mutation of each joined fixture, and verifies invalid floats, budget/alias and
atomic late rollback. Release/ASan/UBSan run the same suite. C++ linkage and
emitted conservative reachable stack sum are checked. Original source oracles
are unsanitized. No Android app, live server, complete initial update, dictionary,
authoritative actor or acknowledgment qualification follows.
