# Independent AuthServer receive and readiness review

Pinned integration base: `3e8b5c9f5b794b58a66c6d8c62a593b926a10873`.
Original source subtree: `f634e21e230009fa8edc91d15429cd4da69eee8c`.

This review owns only this directory. The concurrent AuthServer implementation
under `/workspace/scratch/9174d12e2a11/auth-isolated` was read without modification.
No service, Windows runner, workflow, APK, shared source or authentication policy
was changed or executed. Reviewed file identities are in `receipt-review.json`.
The primary recovery handoff and `AUTH-ONLY-LOGIN.md` were read in full.

## Result and actionable readiness finding

The retained failed runs still establish no encrypted account login. The intact
run 38974164017 executed neither probe: the original process remained alive but
failed listener readiness. Its same SQL PID/start identity survived AuthServer job
shutdown, outside that job; process existence does not establish working SQL
connections, and the failed schema DROP remains failed cleanup.

Original `GlobalAuth.cpp` initializes DB before creating `ListenThread`:

1. `DBEnv::Init` can fail; `ShowDBInitError` calls a modal `MessageBoxA` before the
   following `exit(0)`. An unattended modal can therefore retain a live process
   with no listeners after DB failure. This is a source-supported possibility,
   not proof that the historical run showed that dialog.
2. `DBEnv::Init` returns TRUE after its void `AllocSQLPool` call. If its initial
   `Login` succeeds but all later pool connections fail, no statement handles
   reach `m_pFreeSqlPool`. `GlobalAuth` then calls `g_ServerList.Load` and creates
   `CDBConn` before listener startup. The exact `CDBConn` constructor loops
   `Sleep(100)` until a free handle exists, with no deadline. This is another
   source-supported alive/no-listeners branch.
3. DB login and individual pool connections carry 60-second timeouts, so a fixed
   90-second external readiness failure alone cannot identify a precise stage.
   Increasing that bound alone would not repair a modal or empty pool.

`startup-qualification.json` records 15 controls per release and ASan/UBSan mode.
The compiled test extracts the exact original `DBEnv::Init`, `DBEnv::AllocSQLPool`
and `CDBConn::CDBConn`; ODBC, platform, logger and lock calls are bounded fixtures.
It covers environment/attribute/Login refusal, all-pool-connection failure, and a
healthy pool. Empty-pool Init succeeds and the constructor waits three times;
a fixture Sleep interceptor then raises an exception to bound execution. This
proves control flow, not actual ODBC behavior, wall-clock delay or the historical
failure cause. LeakSanitizer was disabled; no Windows or crypto execution occurred.

Recommended next diagnostic changes belong to the concurrent auth owner:

- Record bounded numeric stage outcomes for initial DB login, usable pool count,
  server-list query completion and listener creation. Retain only statuses and
  SQLSTATE/native error numbers after reviewing for credential/row disclosure.
- If monitoring the original unchanged binary, inspect owned-PID modal presence
  and its fixed known dialog classification without exporting arbitrary contents.
- Check the same owned instance and exact x86 driver connection health near the
  failure boundary; a matching SQL process identity is insufficient. Keep these
  new failure-local controls distinct from already accepted SQL-only evidence.
- Preserve failure and cleanup flags independently; successful instance deletion
  must not substitute for the unexecuted/failed schema DROP.

## Receive candidate review

The concurrent source-pinned candidate makes one exact call-site change:
`DecPacket(inBuf+2, ...)` becomes `DecPacket(inBuf+pi, ...)`. The original `pi`
tracks the current body start. It is 2 for the first uninterrupted frame, 0 after
`CIOSocket::Read(ri-pi)` compacts retained body bytes, and advances past earlier
frames when TCP coalesces messages. The hard-coded 2 is therefore also wrong for
later coalesced frames. The candidate cursor matches the original dispatch
`PostObject(pi, ...)` and opcode check `inBuf[pi]`; it preserves compaction,
length policy, encryption function and account policy. This is a coherent narrow
source correction.

The concurrent fixtures already cover split positions, partial and coalesced
frames, invalid lengths/opcodes, failed byte decoder checks, varying body lengths
through 4096, and an ordered mutable decoder-state observer. Their opaque decoder
and mocked IO cannot qualify cryptography, concurrent IOCP dispatch, real Windows
socket behavior or authentication. This review did not duplicate or rerun those
fixtures; it reviewed their exact recorded hashes. It does not approve or claim
qualification of the separate hosted candidate deployment driver or a patched PE.

The original 344-control offset oracle remains relevant historical source
qualification. The actual capped probe received protocol 191021, sent 170 bytes,
then reported a reset-like system error after one received frame. That observation
is consistent with the demonstrated source defect, but deleted private logs
prevent assigning the exact live close cause. The intact probe's successful
compilation establishes no executed login. Normal sends also cannot guarantee
server receive boundaries or remove the need for fragmentation controls.

Even a future isolated fixed-server encrypted account success would still require
wrong-password/missing-account/corrupt-frame refusals, source/binary matching,
complete cleanup and separate AuthServer-to-DB-to-Map qualification. Gate 26,
authoritative actor publication and physical Thor acceptance remain open.

## Reproduce only the new bounded source controls

```sh
python3 native-android/engine/snapshot-admission/reviews/d/qualify_startup_review.py \
  --source-root . --output /tmp/coh-independent-auth-startup.json
```

The receipt hashes the complete original DBConn.cpp and each extracted function,
the fixture, generated translation unit, and executed binaries. The original
subtree is verified before extraction. No protected implementation is written.
