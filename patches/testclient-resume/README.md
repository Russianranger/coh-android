# Resume-only diagnostic TestClient overlay

`0001-resume-only-diagnostic.patch` changes only
`Utilities/TestClient/src/main.c` in a fresh PostgreSQL source staging tree.
`upstream/ouroboros` and the accepted stock runtime remain unchanged. Build this
with `tools/prepare_resume_client_source.py` and the `resume-client.yml` workflow;
the artifact carries a distinct source receipt and Win32 executable hash.

The opt-in invocation is `-resumeonly -character NAME`. Argument validation runs
before the legacy parser, requires one bounded name, and rejects interactive
selection. After all arguments, it sets exactly `TEST_LOGIN | TEST_RESUME_CHAR |
TEST_STAY_CONNECTED`, with all secondary automatic test groups disabled. The
name comparison is case sensitive. Opt-in search scans all `max_slots` entries
so occupied slots after empty slots are included (`player_count` only counts
occupied entries). Without `-resumeonly`, stock defaults and packet handling are preserved.

Diagnostic lines and outcomes:

- `COH_RESUME_ONLY_SELECTED slot=N name=NAME` records the exact name and
  zero-based slot supplied by DbServer's character list. That packet does not
  transmit the character database ID; its unused client field remains zero.
- `COH_RESUME_ONLY_MISSING name=NAME` disconnects from DbServer and returns exit
  code 3 before choosing, creating, or entering a map.
- `COH_RESUME_ONLY_SERVER_UPDATE id=N name=NAME` records a processed steady
  `SERVER_UPDATE` after scene loading. It requires a positive received entity ID and
  exact selected name. The independent harness must bind this ID to the original
  SQL/find identity. The marker is emitted once.
- Invalid arguments return 2. Invalid selected identity or received entity
  identity mismatch returns 4. These paths do not fall back to creation.

The character-list contract is `DBServer/src/clientcomm.c:sqlGetPlayersCallback`
and `Game/src/clientcomm/dbclient.c:receivePlayersCommon`; IDs stay in the
server-side slot table. The actual player entity ID is decoded and stored in
`Game/src/entity/entrecv.c`, then reported after a successful steady update.

The update marker relies on pinned source behavior: `commReqScene` in
`Game/src/clientcomm/clientcomm.c` receives `SERVER_ALLENTS` before sending
`CLIENT_READY`; `MapServer/src/svr/svr_tick.c` passes a non-full update only for
`CLIENTSTATE_IN_GAME`; `MapServer/src/entity/entsend.c` emits `SERVER_UPDATE` for
that non-full path. The diagnostic requires `commCheck(SERVER_UPDATE) == 1`,
retains the ordinary `commCheck(0)` drain, then checks the current entity.
A callback error (`-1`) never counts as a successful update.

This proves the narrow diagnostic path only when the hosted harness also
verifies live identity/currency, a bounded connected interval and another normal
logout/save. It does not by itself validate combat, rendering, Android or an APK.
