# Native Android roadmap

Updated 2026-10-20 America/Chicago. Physical Thor 0.1.18 is now recorded.
The accepted 0.1.14 stage-41 passage and real-pose box remain established.

The complete 303,112-bit initial packet reaches its original zero terminator,
including 12 application-tail commands. Diagnostic partial-tail fallback was unused.
All 343 unresolved power CRCs were consumed through the original tolerated path.
ACK and READY were each sent once: 5 and 26 payload bytes, 20 and 44 wire bytes.
The complete 30-second observation received 115 messages, totaling 61,014 bytes:
one ALLENTS and 114 UPDATE messages. No retry, timeout or server disconnect occurred.
All 115 position observations were unsupported; movement or stationarity is unknown.
The final suspended/cancelled native owner closed both sockets; the server stayed alive.

The host draws 13 Huge meshes with the original rig, authored scales and textures.
On Thor, asset resolution reports Face_V_Helmet_Robotic_01 and keeps the box.
This does not prove the named asset is absent from the imported archives.
The exported 640x360 PNG is byte-identical to the retained 0.1.17 pavement/box image.
Its source version is 18; the current app is version 19. No fresh 0.1.18 capture is exported.
Runtime archive inputs attached, but a different server-sent pose remains unverified.

Next 3 steps: resolve the reported costume asset lookup while retaining box fallback;
refresh capture for the current session; decode post-READY position observations.
Visible Huge still requires successful asset resolution/upload and a fresh physical
world capture. Gates 25–27 remain open; packet completion adds no world authority.

All 91 same-UID processes are counted despite 59 omitted detail rows.
Peak PSS is 2,977,093,632 bytes. MapServer PSS is 1,879,005,184 bytes;
DbServer PSS is 440,761,344 bytes. These do not separate world/collision allocations.
No new low-memory exit is shown. The older exit cause remains unresolved.
Caps remain 4 MiB decoded, 16 KiB ordinary, 8 MiB initial, 96 MiB scene, 7168 B report.
Initial source aggregate peak is 7,534,269 bytes, separate from actual process PSS.

The rolling diagnostic status retains hashes, send timing and physical evidence.
This update changes documentation only; no APK, database, runtime or cleanup action.
