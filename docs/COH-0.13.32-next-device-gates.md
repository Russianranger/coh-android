# Focused .32 Thor gates after publication recovery

Use the published **0.13.32 / version code 47** APK and unchanged four-part
**Assets 1.0.0** installation. The October 12 continuation adds offline
qualification tools; it does not supply a replacement APK or a measured speedup.
The qualified release guide remains unchanged:
[COH-Atlas-Gameplay-0.13.32-testing.txt](COH-Atlas-Gameplay-0.13.32-testing.txt).

## Preserve the baseline

Install the [published APK](https://github.com/Russianranger/coh-android/releases/download/coh-atlas-gameplay-v0.13.32/COH-Atlas-Gameplay-0.13.32.apk)
over the current app. Do not uninstall, clear data, create a replacement THORHERO,
or reimport already verified asset volumes. Run **Set up / update runtime** once
and wait for **Runtime ready**. Keep GPU test, Performance/800x600, the 30 FPS
selection, fan setting, charging state and approximate starting temperature
consistent. The existing world render size is 600x450 inside the 800x600 UI.

## Separate the device tests

1. **Atlas persistence and timing.** Choose **2 · Reopen saved THORHERO**,
   log in with `COHLOCAL / offline`, and select the existing character. Check
   costume, powers, enhancement inventory/slots, movement and combat. Record
   preparation, actual native-ready and usable-world times separately. Release
   controls for the normal 60-second neutral wait, choose **Save character /
   log out**, wait for **Saved character verified**, then **Finish and save
   report**. Export the complete outer ZIP. Reopen again and verify the same
   character and enhancements. The second fresh process measures validated
   cache reuse; it does not prove a cold or warm Android page cache.
2. **First Kings arrival and saved map.** In a separate Atlas reopen session,
   request Kings Row at the actual monorail immediately after connection.
   Keep the app foreground and remain near the station. The cold admission
   reserve is 1,140 seconds of the 1,200-second connected window, so request
   within roughly the first minute. Require actual Map 5 connection, movement
   and a usable world. Check terrain, buildings, NPCs, textures, loading screens,
   camera, Jump, clicks and audio. Save in Kings normally, wait for verified save,
   finish and export. An unavailable return after a lengthy cold start is a
   separate remaining-time refusal, not proof of a transport failure.
3. **Kings reopen and return.** Reopen the character saved in Kings. Confirm
   Map 5, position and enhancements, then promptly use its actual monorail to
   Atlas. Require actual arrival and movement in Atlas, followed by ordinary
   verified save, finish/export and another reopen. If Kings saved reopen or
   return fails, retain that focused failure report. Do not reset the profile.
4. **Reused Kings preparation and round trip.** After the preceding gates,
   request Kings promptly in another Atlas session and distinguish validated
   preparation-cache reuse from an already resident MapServer. Attempt return
   while enough session time remains. At most two MapServers and four transfer
   epochs are supported. A resident return reserves 510 seconds, meaning it
   must begin before approximately 690 seconds of connected play have elapsed.
   Save, finish and reopen if the launcher refuses for insufficient time.

The exact boundary also includes readiness/arrival checks and user interaction.
The existing reserve, timeout, ownership and save guards are retained. A
MapServer ready line alone does not prove transfer, movement or saved reopen.

## Record comparable measurements

| Measurement | Required distinction |
| --- | --- |
| Preparation | First update/fresh destination, validated data reuse, already resident map |
| Native readiness | Actual process launch to native ready; readiness/tick/DB checks separately |
| Usable world | Operation or station selection to connection **and** movement |
| FPS | Visible range/dips and native frame evidence; Android captured frames are not game FPS |
| Temperature | Start, world entry and sustained play; same fan/charging conditions |
| RAM | Available report process RSS/PSS/peak evidence with sampling scope; record missing fields |
| Save | Verified ordinary save plus next-session identity, map, powers and enhancements |
| Cleanup/export | Overall result, owned-process cleanup and complete outer Android report |

The historical physical .31 reference is Atlas native ready **234.094 s**
(creation), **216.496 s** (reopen), Kings preparation **376.161 s** and Kings
native ready **274.187 s**. Kings did not transfer. These are not controlled
.32 A/B results and must not be labeled a .32 performance improvement.

Use **Abort operation** early if stuck, then export the failure report. After
an interruption, recover retained reports before another session. Export from
**Reports / export**, wait for **Report exported**, and attach the complete
outer `coh-atlas-gameplay-YYYYMMDD-HHMMSS.zip`; a screenshot or inner guest ZIP
does not carry full attribution, capture, ownership and cleanup evidence. Export
a storage report as well for import/setup/storage problems. An incomplete
overall report can still contain an observed committed save; record both.

No .32 physical FPS, temperature, RAM, startup improvement, complete monorail
or sub-30-second result has been established by this continuation.
