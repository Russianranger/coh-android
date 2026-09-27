# Sustained character session validation

Status: implemented and ready for hosted validation; no sustained-session pass yet.
The accepted [short resume run 36282414135](https://github.com/Russianranger/coh-android/actions/runs/36282414135)
proved creation, a live currency change, protocol logout/save, same-database
restart and an exact-name scene probe. The next gate keeps the resumed client
connected and requires a second protocol logout/save.

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
