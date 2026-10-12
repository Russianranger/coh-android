# AYN Thor 0.13.34 startup evidence — 12 October 2026

THORHERO directly reopened in Kings Row (map 5, UDP 7003), and the ordinary logout committed the character in Kings Row. Only map 5's native world process was started. The complete outer ZIP and its nested guest report are readable, even though the operation ended with an owned-process cleanup failure. These are separate results: character save and diagnostic export succeeded; overall Character Check did not pass.

The two original uploaded archives were read without modification. Exact archive hashes, current-session identity, stage timestamps, cache evidence, save events and cleanup findings are in `android-evidence/coh-physical-startup-0.13.34-analysis.json`. Source APK is 0.13.34, code 49; this analysis does not claim any successor improvement.

## Measured critical path

Android operation start to client input readiness was **1,398.724 seconds (23:18.7)**. The user observed approximately 24 minutes before login. Guest start to input readiness was 1,394.864 seconds; the difference is launcher/guest admission. User login time is excluded from those figures. Native character connection was later, at 22:29:29 UTC; time spent waiting for the user and entering credentials must not be counted as native startup.

| Phase | Seconds | What the evidence establishes |
| --- | ---: | --- |
| PostgreSQL startup | 0.496 | Persistent cluster startup itself was quick. |
| Local DbServer stage | 362.308 | Includes 331.595 preparation and 29.947 native dispatch readiness. |
| Atlas data mirror within DbServer preparation | 283.768 | Cold construction of a separate private data tree. |
| Atlas graph validation within DbServer preparation | 36.019 | No Atlas world MapServer was launched. |
| Kings Row stage | 507.917 | Includes 269.820 preparation and 236.365 sampled native readiness. |
| Kings data mirror within its preparation | 221.761 | Another cold private data tree. |
| Kings graph validation within its preparation | 39.695 | Reused 489,916,442 bytes of current authenticated Atlas collision input proof; hashed 10,831,264 additional bytes. |
| Client visual assets | 54.737 | All 10,401 files already existed; full output verification and archive reread occurred. |
| Client animation pack | 14.316 | Existing exact pack reused; loose-input verification still ran. |
| All-zone client assets | 86.735 | All files already existed; fingerprint reuse was false. |
| All-zone audio | 8.539 | All files already existed; fingerprint reuse was false. |
| Texture header inventory | 38.198 | Reused the pack but walked the complete inventory; only 1.044 seconds overlapped other work. |
| GPU prerequisite Wine probe | 56.319 | Fresh isolated prefix plus current WGL checks. |
| Native client launch to input readiness | 213.596 | Actual client process initialization, separate from subsequent login/world entry. |

Rows overlap where explicitly described; they must not be summed as independent phases. The whole Local DbServer label is not a PostgreSQL measurement. The user-observed 5:53 and 8:29 UI times remain approximate independent observations.

The two cold mirrors alone consumed **505.529 seconds (8:25.5)**. Both cache receipts refused reuse with the combined reason “Atlas cache identity differs or prior owner did not prove cleanup.” That combined message does not reveal which prior condition failed. This session independently failed cleanup, so simply expecting a faster warm reopen would be unjustified.

## Native Kings Row costs

The native console reports **232.543 seconds** to server ready; the later owned protocol/tick observation reports 236.365 seconds. Console intervals are useful boundaries, not an exclusive CPU profile:

- Sequencer BIN parsing to the next named phase: 99.481 seconds.
- Story arcs: 26.91 seconds; FX: 23.003 seconds; map load: 19.17 seconds; group library loading: 17.123 seconds.
- Beacon load: 3.68 seconds; triangle unpack: 2.32 seconds; PhysX initialization: 6.40 seconds.
- Animation certificate counter: 5,120 certified opens, zero fallback/crypto failures; 1.097 seconds cumulative raw-byte hashing. The long sequencer interval cannot be attributed to certificate hashing alone.

These observations put duplicate staging, native sequencer/provider work, and repeated client validation ahead of cooked PhysX cache work for this run. The client also needs optimization: its startup exceeds three minutes before login. Removing only one server phase cannot establish an under-five-minute total.

## Persistence, export, cleanup and controls

The native connection and committed-save events identify the same session, THORHERO container 1, COHLOCAL, map 5. Saved coordinates remain `(-1613.0712, -10, 677.3567)`; identity, 7 selected power rows and 13 costume rows were preserved. Login count changed normally from 4 to 5. No `/stuck`, relocation or orchestration SQL game mutation occurred. Enhancement rows were not exported in this report, and movement/combat are not newly certified by the diagnostic fields. No zoning transfer was attempted.

Wine prefix shutdown succeeded, but a still-running owned worker's `/proc` environment returned EACCES three times. Cleanup correctly remained unproved; cache return was withheld. The final outer ZIP preserved the current report, console logs, snapshots and saved event despite this failure. Unknown processes must not be signalled to make that check pass.

The legacy connected-session timer set movement admission to 16 minutes, save admission to 17 minutes, and session completion to 20 minutes after entry. Android recorded suppressed input. The ordinary save still committed before its cutoff. The user's request replaces these user-facing test/session gates with explicit start/stop capture controls.

There were 1,409 automatic PixelCopy captures, using 140.267 seconds of PNG encoding CPU during the interaction interval. This is diagnostic overhead, not a native FPS measurement. Input transport recorded 150 sent events and zero transport failures, but it did not prove that Send Text/L3 reached the login fields; the user's report that an external keyboard was required is authoritative.

The separate runtime update lasted 486.693 seconds. Its setup guard recorded 384.852 seconds of cooperative I/O pacing, no memory-pressure pauses, and at least 8.586 GB available memory. This update is separate from the measured reopen and should not be added to its 24-minute total.

## Next acceptance

THORHERO is still saved in Kings Row. Preserve the profile, runtime imports and Assets 1.0.0. The next physical comparison must begin there, measure operation-to-input and native phases separately, use manual capture controls, test Send Text/L3, save normally and export the outer ZIP. No under-five-minute, memory, FPS or thermal improvement is established until measured on the AYN Thor.
