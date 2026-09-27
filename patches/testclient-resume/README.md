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
name comparison is case sensitive, including when earlier character slots are
empty. Without `-resumeonly`, stock defaults and packet handling are preserved.

Diagnostic lines and outcomes:

- `COH_RESUME_ONLY_SELECTED id=N slot=N name=NAME` records the positive ID and
  zero-based slot supplied by DbServer's character list.
- `COH_RESUME_ONLY_MISSING name=NAME` disconnects from DbServer and returns exit
  code 3 before choosing, creating, or entering a map.
- `COH_RESUME_ONLY_SERVER_UPDATE id=N name=NAME` records a processed steady
  `SERVER_UPDATE` after scene loading. It verifies the received entity's ID and
  exact name against the selected identity. The marker is emitted once.
- Invalid arguments return 2. Invalid selected identity or received entity
  identity mismatch returns 4. These paths do not fall back to creation.

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
