# Saved-character startup repair after 0.13.12

**0.13.13 / code 28 is published**, source
`be955678b4b82f889b31c4071b3b979b0aef6771`.
[Download APK](https://github.com/Russianranger/coh-android/releases/download/coh-atlas-gameplay-v0.13.13/COH-Atlas-Gameplay-0.13.13.apk).
[Production CI](https://github.com/Russianranger/coh-android/actions/runs/37324515114)
passed fresh Win32 compilation, the production formatter fixture under MSVC
Win32, 985 scenarios in 64 suites with no skips, all seven real PostgreSQL
fixtures and the retained-signer SDK checks. The
[independent public-byte receipt](android-evidence/reopen-startup-repair-0.13.13-publication.json)
verifies all 72 payloads: 67 retained and five native/verification replacements.
Physical Thor reopen/training/UI/timing validation remains pending.

The [October 5 device receipt](android-evidence/reopen-startup-repair-0.13.12-device-result.json)
records `coh-atlas-gameplay-20261005-135502.zip`. It identifies 0.13.12,
THORHERO character ID 1 and the published DbServer hash. The reopen attempt
ended after 94.328 seconds, before MapServer or the game client started.
Android remained running. Runtime setup had completed separately in 99.460
seconds. These are not Atlas or actual client startup measurements.

DbServer connected to PostgreSQL, then asserted in `quick_sprintf.c:101`:
`(size_t)(tail-buf+1) <= buf_size`. Its assertion reporter opened TCP 52015.
The existing listener guard correctly rejected that extra listener with
`Unexpected or duplicate game listener evidence`. The guard remains unchanged;
its new regression replays the partial normal listener sequence followed by
the assertion listener. Owned cleanup stopped PostgreSQL and Wine and reaped
remaining workers.

`x_beginthreadex` formats the caller's source filename and line into a fixed
128-byte thread-name buffer. The hosted 0.13.12 build embeds a 123-byte
`TaskThread` header path. Adding `(110)` requires 128 bytes plus the terminating
NUL. Starting the SQL FIFO workers therefore overflows the diagnostic buffer.
The repair allocates the complete diagnostic name and releases it after the
synchronous thread-naming call. Thread creation, assertions, SQL FIFO behavior,
transaction rollback and commit-before-ACK remain unchanged. Production-source
regressions must cover the exact boundary and longer paths, not just a shortened
build directory.

The 0.13.13 derivative retains the published 0.13.12 UI/client payloads and
builds a fresh DbServer with both this thread-name repair and the existing
PostgreSQL empty-child-row witness/order fix. No database reset, asset import,
Game rebuild, listener exception or ignored SQL error is part of the repair.
The original publication and failed device evidence remain historical records.

Use [the focused 0.13.13 test](COH-Atlas-Gameplay-0.13.13-testing.txt): first
establish reopen reaches character selection and
Atlas, then inspect UI, train at Ms Liberty, complete a power purchase, save and
reopen. Stop and export once if startup fails. Physical training, UI restoration
and actual client startup savings remain pending; this report reached none of
those phases.
