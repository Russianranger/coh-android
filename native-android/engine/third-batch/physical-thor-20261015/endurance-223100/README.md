# Thor code 201 — ten-minute endurance follow-up

**The bounded offline application's ten-minute physical endurance and audible-playback checks pass.** The report records **15 minutes 43.997 seconds** of foreground execution and a single completed render context lasting **10 minutes 41.862 seconds**. The user confirms: “Audio and music is heard and no apparent defect from what I hear.”

This is the same session and exact released ARM64 APK as the earlier report: `org.coh.nativesupport`, code 201, SHA256 `ed280805188d82ffbb911e9799f43c42a5a0382fb8346ff97ffc794d85cc9ddc`. Both asset manifests remain identical. Runtime source is `e89f20c56619cbab87728bd49eff8f835b3b3c98`; device remains AYN Thor, Android 13, Adreno 740.

| Observation | Result |
| --- | --- |
| Rendered frames / active time | 56,495 / 943.997 s; **59.85 frames/s** |
| Frame observer | Mean 15.566 ms; p95 upper 18 ms; p99 upper 21 ms; maximum 43.159 ms |
| Slow samples | 18 above 33.33 ms among 56,494; zero at least 100 ms |
| Lifecycle | Two pause/resume pairs; 18 contexts started / 17 completed; all 17 returned contexts released objects |
| Errors | Zero unexpected graphics, cleanup, transform or support errors |
| Process RSS | 180.65 → **177.26 MiB** across the two reports |
| Process PSS | 72.65 → **68.42 MiB** across the two reports |
| Audio recovery | Five opens, four closes, two native route reopens; running without a reported device error |
| Retained closed-backend audio observations | 92,839 callbacks, maximum 7.152 ms; retained mixer checkpoint has zero stream-underrun frames |
| Male preview | 877 frames / 7,016 draws / two uploads; zero failures |

One expected `EGL_BAD_SURFACE` cancellation occurred during explicit Wretch recreation and recovered. Two abandoned frame-observer intervals are lifecycle accounting, not measured Android compositor drops. The frame mean excludes the outer sleep; FPS uses rendered frames divided by active foreground duration.

The process-memory endpoints are lower, with measured world cache, skin cache and partial module budgets unchanged. This supports the bounded endurance result; two endpoints do not establish leak freedom or a continuous memory trend. Java-used and native-heap endpoints rose by about 9.17 MiB and 0.44 MiB respectively, so the lower RSS/PSS must not be read as every memory measure decreasing. GPU duration, thermal state and full-game performance are unmeasured.

Audio counters now contain real retained data from closed/joined backends. `diagnostics_valid=0` correctly indicates that the fifth backend is currently running, so its ongoing callbacks are absent from this checkpoint. Zero retained stream-underrun frames is not a platform-xrun, latency or complete-session guarantee. The user's listening report supplies the physical audibility evidence. Route callbacks/reopens are demonstrated; output-device identity and per-route listening are not recorded. `focus_changes=0` leaves focus interruption open.

Pause/resume recovery is established, although the report cannot identify the exact Android UI action that caused each pause. The two pauses last about 1.4 seconds each; the consolidated procedure still calls for three Home cycles and two explicit Recreate actions, whereas this report records two pauses and one explicit Recreate. Male resources were re-uploaded after a Wretch context recreation; this does not yet prove recreation while Male is active. Three local character selections and 456 bounded blocking ticks are new observations. Nonempty chat, explicit animation selection, wall/sliding geometry, Male-active recreation/portrait, full panel coverage, audio-focus interruption and full source/model/world parity remain open. Existing screenshots are the earlier landscape evidence; no new screenshots accompanied this follow-up.

No full numbered gate closes. This evidence does not cover live networking, complete zones or authoritative gameplay. The accepted Session/Combined apps and primary agent paths are unchanged. **Use the existing APK; no rebuild is needed.**

`assessment.json` contains identities, formulas, counters, limits and source-semantic checks. The original report is preserved byte-for-byte in `COH-NativeSupport-20261015-223100.json.gz`, raw SHA256 `f1ab649c65241079e942ed01dd7bdace7bb92956d45a4817914783a6a5f24460`. The prior report and its assessment remain unchanged.
