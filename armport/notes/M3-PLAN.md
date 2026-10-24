# M3 plan: into Atlas Park

Exit test (PORT-PLAN.md): scripted login against the CI server to Atlas Park
in CI; saved native-android packets replay through the original receive code;
screenshot check.

## Route

- **Server:** reuse the stack `android-game.yml` already qualifies on
  `ubuntu-24.04-arm`: original DbServer and MapServer under the app's ARM64
  Wine (FEX for the x86 servers), loopback only, the reviewed game data and
  schema, Atlas Park saves (`tools/android/game/host_game_smoke.py`). It runs
  without an AuthServer; its TestClient talks to DbServer directly.
- **Client login without AuthServer:** the original client does the same when
  given `-db <ip>` (`clientcomm/authclient.c`: a set `cs_address` skips
  `authConnect` and uses DbServer's game-client port). So the ARM64 client
  runs with `-db 127.0.0.1` against that stack.
- **Scripted input:** drive the login screen with xdotool on Xvfb (account,
  password, Log In, character select, Enter World), answering the Ultra Mode
  prompt first. Each step is checked against the client's stdio log and
  window state; screenshots at each step.

## Steps

1. Stand the server stack up in `armport-build.yml` (a job after
   `client-run`), reusing the accepted donor packages and data rather than
   rebuilding them. Evidence: DbServer and MapServer listening on loopback.
2. Run the ARM64 client with `-db 127.0.0.1`, script the login, reach
   character select. First 64-bit check: the network library keeps `SOCKET`
   values in `int` (`notes/64BIT-AUDIT.md`, known issues); qualify or fix.
3. Enter Atlas Park with a saved character; screenshot check (the client's
   own map name and a non-loading frame).
4. Replay the saved native-android packets (three initial packets; the
   0.1.19 post-READY snapshot and 115 UPDATEs) through the original receive
   code in the ARM64 client and compare with the 32-bit reference decode.

## Risks

- The stack's runtime cost on the ARM64 runner (x86 servers under FEX next to
  the ARM64 client under Wine); keep to 2 compiler processes and one game
  stack per job.
- Account/character fixtures: use the stack's existing disposable save data;
  no real accounts or secrets.
