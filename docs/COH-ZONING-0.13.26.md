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

The publication gate preserves the .25 regression suite and seven real
PostgreSQL fixtures, adds zoning state/receipt/recovery checks, and reuses
authenticated native artifacts. SDK/signature/payload validation and a separate
actual public-APK audit remain required before a release is declared published.
Build and publication results are recorded in the current handoff after success.

Physical .26 arrival, map-101 save/reopen, memory/temperature behavior with two
maps and transfer duration remain pending. The retained renderer has the accepted
.25 physical baseline; host tests do not establish Thor zoning speed. Follow
`COH-Atlas-Gameplay-0.13.26-testing.txt` after publication.
