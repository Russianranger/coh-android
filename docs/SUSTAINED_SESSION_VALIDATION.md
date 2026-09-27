# Sustained character session validation

Status: **passed** in [run 36295176484](https://github.com/Russianranger/coh-android/actions/runs/36295176484)
at `4e8058c3ffe20acda61b55023202d409ed1d0df1`, completed 2026-09-27
05:08:11 UTC. All 12 phases passed with no failures. This establishes the
exercised sustained connection and second save; combat, movement, rendering,
transfers and Android execution remain unvalidated.
The accepted [short resume run 36282414135](https://github.com/Russianranger/coh-android/actions/runs/36282414135)
proved creation, a live currency change, protocol logout/save, same-database
restart and an exact-name scene probe. This follow-on gate kept the resumed
client connected and completed a second protocol logout/save.

## Diagnostic client and provenance

The stock `-justlogin -character NAME` command disables creation but also exits
after the scene exchange. A small opt-in `-resumeonly` patch is applied to a
verified temporary source copy. The immutable `upstream` trees remain untouched.
Without this option, the TestClient retains its existing behavior.

The separate `resume-testclient-win32` artifact identifies the source, PostgreSQL
patch/overlay, diagnostic patch, build commit and TestClient bytes. The sustained
workflow builds it at the same repository commit as the harness. Package
verification checks this identity, x86 PE imports and compatibility with the
accepted runtime dependencies before using it in the owned disposable runtime.
The accepted DbServer, MapServer, schema, template and prior map-readiness hashes
remain required. This experiment does not replace or relabel the accepted stock
reference package.

The character-list packet supplies the selected name and slot, but does not
populate `db_info.players[slot].db_id`. Selection is therefore checked by exact
name/slot. The later processed MapServer player update supplies the real positive
ID, which the harness must match to the original SQL and stock-query identity.
The diagnostic search uses the allocated slot count, so an empty earlier slot
cannot hide a later exact-name character.

## Accepted hosted validation: 36295176484

The corrected diagnostic resumed `TEST-37762`, container ID 1, from account
`CohP62b581371c`. The processed MapServer player update supplied the same ID and
exact name as independent SQL and the stock character query. A missing-name
request for `CohAbsent1474e746a27a` exited naturally with code 3 before any
creation or scene exchange; the whole character inventory remained one row,
and the selected SQL snapshot and login count were unchanged.

Ten connected Atlas Park samples spanned **66.953 seconds**; the largest gap
was 7.625 seconds. Every sample had current network/statistics heartbeats and
connected MapId 1 status. Fresh live replies showed influence 12,345 before and
after observation, then 23,456 after the second command. The second protocol
logout committed before forced residual-client cleanup, as did the first save.

| Committed snapshot | LoginCount | Influence |
| --- | ---: | ---: |
| First protocol logout | 1 | 12,345 |
| Same-cluster/service restart | 1 | 12,345 |
| Missing-name refusal | 1 | 12,345 |
| Second protocol logout | 2 | 23,456 |

Identity and all selected parent/child fields remained identical except for the
explicit second influence value: one `ents`, one `ents2`, seven powers and
16 costume parts. Attribute mappings stayed unchanged and no extra character
was created. All three console observers captured their final snapshot and
exited successfully before residual-client cleanup.

The [complete artifact](postgresql-evidence/character-session-36295176484.zip),
[raw report](postgresql-evidence/character-session-36295176484.json) and
[acceptance/provenance record](postgresql-evidence/accepted-character-session-36295176484.json)
are preserved. Artifact `10924041414` is 12,505 bytes, SHA-256
`410e79e8815ef829a387dc5812f8e4b9b5bc050a3dee855262847366e899dbdc`.
The separately built diagnostic is identified by its unchanged
[build manifest](postgresql-evidence/resume-testclient-build-36295176484.json) and
[source receipt](postgresql-evidence/resume-testclient-source-36295176484.json).
Its executable SHA-256 is
`b09a82d8aaffac18dc74828753ccee466d71a37f913dddc05934cb84957e6f7e`;
the accepted stock TestClient, DbServer and MapServer hashes were retained.

Windows passed all 103 tooling checks; Linux passed 98 with five Windows-only
skips. The same-commit [stock regression 36295176352](https://github.com/Russianranger/coh-android/actions/runs/36295176352)
passed its eight phases, and all four
[PostgreSQL regression jobs 36295176473](https://github.com/Russianranger/coh-android/actions/runs/36295176473)
passed. The stock regression's [report](postgresql-evidence/character-persistence-36295176352.json)
and [complete artifact](postgresql-evidence/character-persistence-36295176352.zip)
are also preserved.

## First hosted attempt: 36293644180

[Run 36293644180](https://github.com/Russianranger/coh-android/actions/runs/36293644180)
at `9358211586902951b05e495ac4b7648d0df0f036` passed all 102 Windows tooling
checks and 97 Linux checks (five Windows-only skips), then built the diagnostic
TestClient successfully. Its runtime passed eight phases: stock creation and
live influence 12,345, committed protocol logout, same-cluster/service restart,
and missing-name refusal with an unchanged character inventory and selected SQL.

The positive resume found `TEST34470` in slot 0, then the diagnostic's premature
ID check returned exit 4 (`COH_RESUME_ONLY_INVALID_SELECTION`) before map entry.
The harness correctly rejected the disconnected pipe. Source inspection confirmed
that the list's zero-initialized `db_id` is never received from that packet; the
ID must instead be checked on the later received MapServer entity. No sustained
connection, second currency change or second save was accepted in this attempt.

The [complete failed artifact](postgresql-evidence/character-session-36293644180.zip)
and [report](postgresql-evidence/character-session-36293644180.json) are preserved:
artifact `10922619086`, 10,005 bytes, SHA-256
`491214ced33579d31c4bec4ef3bd07cd05b6bdd34aca1f6b859e3e227175364e`.
The separate [build manifest](postgresql-evidence/resume-testclient-build-36293644180.json)
and [source receipt](postgresql-evidence/resume-testclient-source-36293644180.json)
identify the initial diagnostic binary, not a successful runtime acceptance.

The same-commit [stock short-resume regression 36293644040](https://github.com/Russianranger/coh-android/actions/runs/36293644040)
passed all eight phases with unchanged influence 12,345 and selected rows, and
`LoginCount` 1 → 1 → 2. Its [report](postgresql-evidence/character-persistence-36293644040.json)
and [full artifact](postgresql-evidence/character-persistence-36293644040.zip)
are preserved. All four same-commit
[PostgreSQL regression jobs](https://github.com/Russianranger/coh-android/actions/runs/36293644041)
also passed.

## Acceptance

1. Use a fresh disposable fake-auth account and database. Create a character,
   observe live influence 12,345, request protocol logout and independently
   confirm committed SQL before forced process cleanup.
2. Restart PostgreSQL and the game services against the same cluster without
   reseeding/import. Require unchanged identity, selected rows, attribute maps
   and `LoginCount` 1.
3. Request a known-absent character name with `-resumeonly`. Require the exact
   refusal diagnostic and natural nonzero exit before any map entry or creation.
   Independent SQL must still contain exactly the original character, with
   unchanged selected rows and login count.
4. Resume the original exact name. Require the client-reported server character
   ID to match the original SQL/stock-query ID, the resume branch, pipe identity,
   connected Atlas Park status, a processed steady `SERVER_UPDATE` identifying
   the same player, and a live server response showing influence 12,345. The
   steady update follows server processing of `CLIENT_READY`; the earlier
   scene/`SERVER_ALLENTS` exchange or `Status: Running` alone is insufficient.
5. Observe the connected session for 60 seconds by default, with repeated
   character status and current map heartbeats. Require a fresh live currency
   response at the end of this observation.
6. Change influence to 23,456 through the normal game command protocol, verify
   it live, request a second protocol logout, and require committed SQL before
   forced client cleanup. Selected identity and parent/child fields must remain
   unchanged except for the explicit currency change; require `LoginCount` 2,
   unchanged attribute maps and no additional character.

The first session uses the accepted stock TestClient. The separately identified
diagnostic client is staged beside it as `TestClientResume.exe` and used for
missing-name refusal and the sustained resume.
The console observer finalizes after each accepted logout/save and before
residual-client cleanup; naturally exiting probes retain their console until
the final snapshot is captured.

## Execution and scope

Use the `Sustained character session` workflow. It reuses accepted schema run
`36088012666`, reference run `36088012664`, template/map run `36176806895` and
reviewed asset `588984151`. Pull requests run tooling checks; the continuation
branch runs the build and runtime experiment. The runtime emits bounded phase
progress and uploads selected evidence even on failure.

A passing result establishes the exercised connected fake-auth session and two
protocol saves. Combat, transfers, graphical/custom-client compatibility,
auxiliary services, graceful whole-server shutdown and Android execution remain
separate gates. No Android APK or performance result is claimed.
