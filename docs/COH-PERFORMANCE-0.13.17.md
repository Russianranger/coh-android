# 0.13.17 native gameplay cap and repeated texture diagnostics

This pass continues the audited 0.13.16 Game/APK at
`d41aab3dd1a2f169a0ec71ff47d56767a8eb65e5`, after physical AYN Thor testing.
It retains the accepted llvmpipe stack, 800×600 surface, Performance world
render scale, server binaries, assets, beacons, persistence, controls and
Android Java/DEX. Zoning remains deferred.

## Physical evidence and update correction

`android-evidence/performance-0.13.16-thor-20261007.json` binds the complete
support ZIP (SHA-256
`36cb3284014b7963d8f2cb39e0c9f727acc4f82fa9d82a8ab5d0f718cf717471`).
The operation passed character reopen, save verification and owned cleanup.
The user reported fairly stable FPS with hitches and requested a 30 FPS test.

| Measured phase | 0.13.16 update run |
| --- | ---: |
| Reopen to observed login | 691.012 s / 11:31 |
| Login to observed world | 67.676 s / 1:08 |
| Reopen to observed world | 758.688 s / 12:39 |
| Local Atlas startup | 227.043 s / 3:47 |
| Actual client startup | 193.541 s / 3:14 |
| Native map connection to CLIENT_READY | 64.508 s / 1:05 |

The earlier instruction that runtime setup would not be required was wrong.
The runtime generation derives from the complete embedded manifest; changed
native/helper bytes require **Set up runtime once after updating**. The old
UI's “new install only” label is misleading. The export confirms successful
setup taking about 99.431 seconds and retained character state. Reopen later
replaced the detailed installer receipt, so the ZIP does not establish every
installer download/extraction. Keep the current fail-closed ready-generation
checks and preserve runtime/app data/imports/characters. Do not clear data.

This run also revalidated existing visual bytes and refreshed owned Atlas
caches. It is not an unchanged-warm startup measurement; another warm run is
needed before claiming repeated preparation costs or startup savings.

## Why a cap change needs an accompanying optimization

Across 2,203 native gameplay frames, mean cadence was 123.047 ms (8.127 Hz),
main wall work excluding explicit pacing was 104.452 ms, and pacing was
17.752 ms. Submission/backpressure averaged 39.311 ms. Work exceeded 125 ms
on 536 frames and 200 ms on 126 frames; its maximum was 1,455.434 ms and p95
histogram bucket bound was 250 ms. Pure gameplay windows sampled approximately
20.96 ms of main-thread CPU per frame. Wall work includes waits and is not CPU
time. Presentation and llvmpipe worker budgets remain partly unattributed.

The console contained **24,856 CUSTOM TEXTURE ERROR lines**. Nine Electro/
Circuitry messages accounted for 23,832 gameplay repetitions, 2,648 each.
`changeTexture()` emitted these repeatedly after loading/fallback checks.
Bounded scene/frame logging did not cover this path.

The new source layer bounds repeated diagnostic reporting around those two
Errorf calls. Every texture load attempt, fallback texture, assignment and
appearance update remains. The first error for each of 64 retained full identities remains visible.
Null, oversized and further unique identities pass through the original error
path. Bounded suppression records make reduced repeated output explicit. This changes diagnostic overhead, not asset
availability. It does not promise an FPS gain or repair the absent textures.

## 30 FPS experiment

Only the verified new Game producer receives the new controls. Performance
launches request a **30 FPS gameplay cap**; Compatibility launches retain 10.
The native hook applies after argument parsing, so the retained launcher's
10 FPS arguments and saved state cannot undo the requested gameplay cap.
Menu and inactive caps remain 10. Invalid/unset controls retain fallback
behavior; cache generation is excluded. Existing scene/frame diagnostics,
resource freshness and gameplay validations remain enabled.

For a comparison with identical Performance graphics, use the native command
`/maxfps 10` after entering the world, then `/maxfps 30`; this changes the cap
within the running session. `/showfps 1` exposes the native FPS display.
The cap is a maximum, not a sustained-FPS promise. This 0.13.16 workload does
not demonstrate sufficient headroom for stable 30 FPS.

## Qualification and next physical gate

The new release lane appends the gameplay layer to the unchanged scene/frame
source ancestry and rebuilds only Game. It requires real Win32 cap/diagnostic
harnesses plus the retained native scene/frame checks, targeted producer/
guest/migration/package scenarios, all prior gameplay/save/recovery suites,
all seven PostgreSQL fixtures, exact retained Android/server/asset/dependency
payloads, SDK/signer audits and an independent actual-public-APK audit.
Release completion and exact source/hash evidence belong in HANDOFF and the
publication receipt only after those gates pass.

Follow `COH-Atlas-Gameplay-0.13.17-testing.txt`: required setup once, then first
and warm startup, matching 10/30 FPS routes and complete per-run support ZIPs.
Physical 0.13.17 FPS, temperatures, scene times and stability remain unverified.
