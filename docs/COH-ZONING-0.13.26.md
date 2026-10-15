# 0.13.26: controlled Atlas instance zoning

## Accepted physical baseline

The user accepts 0.13.25 as the new serviceable testing baseline and requests
zoning next. The actual `coh-atlas-gameplay-20261010-183224.zip` is 0.13.25,
runtime `d6c7a89ef4f73b563a188d9f4562411f1e917dbe`, native Game producer
`c512e912a004b66886a7667640aa1a967e95de64`, with the actual renderer
`zink (Turnip Adreno (TM) 740)`. Archive SHA-256 is
`5aae571b698eaed74f67436a54effb0867cb9b1a8d5bbc8099061a85d9de9e5b`.

Eight pure gameplay windows at observed cap 30 cover 1,866 frames and average
42.959 ms / 23.278 Hz. The histogram p95 upper bound is 83 ms and the maximum
interval is 323.732 ms. The separate .24 report remains 194.165 ms / 5.150 Hz;
different routes and conditions prevent attributing an exact causal speedup.
Sustained 30 FPS is still open. SQL and native-position save verification passed,
THORHERO identity, powers, costume, XP and influence were preserved, and cleanup
passed. Generic gameplay/input/controller flags remain false; submitted inputs
do not qualify every control.

Sparse setup/sort/draw observations average 9.863 / 0.163 / 3.753 ms across 60
samples. No full-ring waits were observed. Scene, submission and queue windows
overlap; renderer wall remains different from GPU duration. Detailed evidence is
in `android-evidence/render-queue-0.13.25-thor-20261010.json`. Do not request this
baseline test again or retune graphics as part of zoning.

## First zoning scope

The finite first target is genuine native travel between Atlas Park map 1 and
its defined instance 101. These are two MapServer processes with separate
numeric map identities and UDP endpoints, using the same reviewed Atlas world.
This implements the transfer and persistence foundation; it does not claim a
different city or mission map has been qualified. Existing hosted native
round-trip evidence is documented in `MAP_TRANSFER_VALIDATION.md`.

Kings Row (map 5) and Galaxy City (map 29) require a separate dependency and
collision/visual coverage pass. Direct map references reveal geometry absent
from the currently inspected inventories; transitive and event-layer coverage
is not established. Reusing Atlas assets for these cities would be insufficient.

The accepted .25 Game, render-worker optimization, GPU driver/probes, native
servers, DLLs, graphics profile, assets, setup repair and character database are
retained. This pass adds Android controls and an explicit guest zoning profile.
Normal non-zoning behavior retains its original Atlas-only proof contracts.

## Preparation, transfer and recovery

The session reads the saved supported destination from the existing character
database and starts that map first. It does not reset a saved MapId or position.
The sidebar offers destination preparation and, after verified readiness, an
explicit travel action. Preparation starts only the other supported MapServer;
empty unrelated zones consume no process slots. The two supported maps stay
alive for the bounded session, allowing a warm return. Cold map preparation and
observed transfer time are recorded separately. Transfer observations include
status-query and log-delivery latency, so they are not pure native loading time.
Neither is a device speed claim;
the future target of zoning in under 30 seconds remains unverified.

Each session permits at most four transfers and retains its existing movement,
neutral-wait and save deadlines. Initial map-1 safe-ground recovery remains
available before the first preparation. Using it requires saving and reopening
before zoning; preparing a destination disables recovery for that session.

Travel uses the stock `/mapmove` command, bound to the current session, Game
process, character and monotonically increasing request epoch. A submitted
command is not arrival. Destination process ticks, exact numeric DbServer map
status, a fresh native CLIENT_READY/ResumeCharacter observation after the
request, same character identity and an absence of `InMapXfer` establish native
arrival. Fresh Android views then establish presentation evidence.

The retained immediate native character event producer is scoped to Atlas map
1. Instance 101 uses a separate explicit stock native log route bound to the
owned map instance and current transfer epoch, plus independent read-only
status/SQL checks. Unlabelled shared map logs and stale initial readiness cannot
satisfy that proof. Ordinary save requires fresh native position, logout and
disconnection observations plus committed map/position and preserved selected
character rows. LoginCount may increase once per reopened session, never once
per transfer. A saved or interrupted map 101 session can reopen there without
synthetic SQL repair and can travel back to map 1.

## Validation and pending device evidence

**0.13.26 / code 41 is published** from
`64a1833bc0d2dc1035c11188c6ae8c7fdb58244b`.
[APK](https://github.com/Russianranger/coh-android/releases/download/coh-atlas-gameplay-v0.13.26/COH-Atlas-Gameplay-0.13.26.apk)
SHA-256: `b14bfd307fc2c51bd628670efbed1e03fc2283408ee73546aa8b6fe8bbbf3c60`.

All four jobs in [workflow 38077801231](https://github.com/Russianranger/coh-android/actions/runs/38077801231)
passed, including the separate actual public-download audit. Qualification ran
1,749 tests across 122 suites with zero skips, seven real PostgreSQL fixtures
and 9,770 source pins. The 117 retained suites and authenticated original native
proof remain in the gate. SDK/signature/package/payload checks passed; 71 of 77
donor runtime payloads are identical, six helpers/manifests changed and one
zoning helper was added. The exact .25 Game, servers, graphics and world assets
were reused. Independent source/receipt review passed without repeating native
builds or the large public APK download. Full publication evidence is in
`android-evidence/zoning-0.13.26-publication.json`.

The October 10 Chicago / October 11 UTC follow-up physically confirms **two
successful transfers, according to the user**, followed by an interruption around
Finish/report export and switching to another app. This is an accepted physical
zoning result; do not request another round trip merely to replace missing logs.

The supplied `coh-atlas-gameplay-20261011-003909.zip` is a valid 14-member export
of a later 1.684-second failed reopen. Its .26 manifest content exactly matches
the published build; requested Turnip/Performance are present, but Game never
started in this captured attempt. The leftover private display socket blocked
launch. There is no guest report, zoning trace, actual renderer sample or saved
event. The prior session's exact destinations, save outcome and timings cannot
be derived from this ZIP. Archive identity and bounded observations are appended
under `device_followups` in `android-evidence/zoning-0.13.26-publication.json`;
the original publication receipt flags remain historical host claims.

A historical Android reason-3 exit for the .26 setup PID supports low-memory
termination as a possibility. It is not tied to the user's Finish/background
transition. Reason-10 records on Android 13 can also describe package/component
changes and are not proof of force-stop. Reference:
[Android ApplicationExitInfo](https://developer.android.com/reference/android/app/ApplicationExitInfo).

Source review identifies the next bounded reliability work: preserve previous
guest evidence before retries, retain access to older completed reports, durably
checkpoint live session evidence, recover only demonstrably dead owned display
sockets, and put external report copying under foreground-service ownership.
The existing accepted Finish path already retains the foreground service until
its internal report is complete; no specific Finish exception is demonstrated.
No code or APK changed for this feedback record.

Complete native arrival traces, map-101 save/reopen, individual controls,
memory/temperature behavior and transfer duration remain unverified. The .25
physical FPS baseline is retained. After the interruption/export issue is
addressed, any further test should target those remaining gaps rather than
repeat the accepted .25 benchmark or the already successful two transfers.
