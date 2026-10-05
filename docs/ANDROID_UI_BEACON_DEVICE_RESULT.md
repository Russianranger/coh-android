# 0.13.13 physical Thor UI and beacon follow-up

The 2026-10-05 Thor sessions resumed the existing THORHERO, completed the first
training purchase, returned to combat, saved normally, and reopened with the
trained level and Aimed Shot retained. The user reports no crash. This closes the
earlier physical startup/training crash question while leaving UI and Atlas
beacon data as the next work.

Live continuation head inspected: `6098d5e040d9a41654acec60e92c64be2b5aacee`.
The APK identifies itself as **0.13.13** in both reports; its implementation
source is `be955678b4b82f889b31c4071b3b979b0aef6771`. Native identities match the
published repaired DbServer and retained Game/MapServer. Exact report hashes,
read-only SQL outputs, witness paths/line numbers and phase measurements are in
[the evidence receipt](android-evidence/ui-beacon-0.13.13-device-result.json).

## Character and training evidence

Report `coh-atlas-gameplay-20261005-153904.zip` begins with character ID 1,
internal level 0/default, 115 XP, 89 influence and seven powers. The stock entity
log records Ms. Liberty interaction and `BuyPower` for
`Blaster_Ranged.Archery.Aimed_Shot` at 15:34:10. Native power logs then record Aimed
Shot activations/hits in combat. The character receives 25 further XP, 14
influence and a Generic Accuracy enhancement, followed by ordinary logout timer
expiry at 15:37:49. Post-logout SQL reads show internal level 1/display level 2,
140 XP, 103 influence and 15 powers. All seven original positive power UniqueIDs
remain; only their two expected SubId/PowerID positions shift. The eight additions
are the purchased Aimed Shot and seven stock Inherent/Fitness automatic grants.
Costume and `ents2` rows are unchanged.

Report `coh-atlas-gameplay-20261005-155202.zip` starts from those committed rows:
level 2, 140 XP, 103 influence, and Aimed Shot UniqueID **564586690**. It reaches
Atlas and ordinarily logs out again at 15:50:39 with the same level/XP/influence.
Final SQL preserves all 15 power UniqueIDs and all gameplay fields. Its sole
power-row change is `powersetlevelbought` from null/default to 1 on eleven
Inherent/Fitness rows. This exact native normalization requires source proof in
the validator; it does not justify accepting arbitrary power edits.

Both reports have `startup_only_reopen=true`, no required task gate, and no SQL
gameplay mutations by the launcher. Their overall diagnostic flags are **false**
because the retained-row validator rejects `ents` in the training session and
`powers` in the next reopen. Native purchase/logout, final SQL reads embedded in
`latest-report.json` process outputs, and the next session's baseline prove
committed persistence independently. The report files do not contain a separately
named post-snapshot artifact; the evidence receipt identifies each captured SQL
process index. Do not describe these exports as passed qualification or infer a
runtime crash from their exit code. Both exports verify graceful PostgreSQL/Wine
cleanup and owned-process reaping.

## Startup phases

Times below retain existing phase boundaries. Resource preparation and the native
dependency preload are distinct from actual client startup.

| Measured phase | 15:39:04 export | 15:52:02 export |
| --- | ---: | ---: |
| Wine initialization | 65.031 s | 7.761 s |
| DbServer startup stage | 40.606 s | 38.460 s |
| Local Atlas startup stage | 223.649 s | 210.356 s |
| Visual preparation | 61.871 s | 29.733 s |
| Client animation preparation | 14.117 s | 13.537 s |
| Wine/FEX Win32 DLL probe | 1.540 s | 0.945 s |
| Texture preparation | 54.805 s | 21.064 s |
| Texture wait before client | 53.257 s | 20.108 s |
| Native animation dependency preload | 2.864 s | 3.013 s |
| Native Menu dependency preload | 3.670 s | 2.734 s |
| Actual client startup | 198.157 s | 188.310 s |
| Android operation start to observed login | 1501.214 s | 556.889 s |
| Observed login to world-ready event | 84.909 s | 84.519 s |

The second operation-to-login interval is **9:16.889**, consistent with the user's
approximately nine-minute observation. Actual client startup is **3:08.310** in
the captured boundary; the user's stopwatch was approximately **3:03**. Atlas is
**3:30.356**. The first login observation occurs long after native client startup
completed, so its operation-to-login interval includes user interaction delay
and cannot be treated as initialization time.

The second launch reused the verified visual fingerprint: **zero archive reads,
zero decoded files, zero installed files**, retaining all 9,613 prepared leaves.
Wine reused its readiness proof without registration passes. The prior 0.13.11
actual-client measurements were 334.499/324.792 seconds; the new captured client
phase is materially shorter, while warm Atlas remains about 3:30. This comparison
does not isolate one cause or claim equivalent reductions in login/world time.

## Remaining UI and beacon evidence

The attached screenshots show restored inspiration and power icons, and rendered
training ownership/selection controls in the styled screen. Remaining visible
artifacts include white squares in enhancement slots/inventory, tips, and some
nameplate/status areas. The user also reports an empty right pane during power
selection. Native training source must establish what belongs there at display
level 2 before treating an empty third panel as missing artwork.

The console's missing-texture diagnostics are dominated by global costume/trick
validation and do not identify useful missing UI stems. Resolve exact UI
dependencies from native code and original client textures; do not import unrelated
world/costume sets in response to those global diagnostics. Screenshot observations
alone cannot distinguish a missing asset from renderer fallback or intentional
empty native content.

Both owned Atlas consoles explicitly report:

> Beacon file not loaded for map: maps/City_Zones/City_01_01/City_01_01.txt

The gameplay screenshot also displays the native un-beaconized warning. Existing
map-layer beacon objects/geobin are not a generated pathfinding beacon file.
Beaconization must supply and validate native navigation data for the exact Atlas
geometry; hiding the warning does not satisfy the task. Zoning is deferred to the
next pass, as requested.
