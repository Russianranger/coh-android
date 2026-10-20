# Native Android roadmap

Updated 2026-10-20. Physical 0.1.16 is recorded; signed 0.1.17 passes focused CI.

Combined 0.1.14 passed stage 41. Physical 0.1.16 carries bodytype 4, Huge,
28 costume parts, 112 strings and 58 colors. The body ends at bit 11648 and
appearance at 11672. Host replay now consumes all 343 power customizations,
recording 343 unresolved CRCs through the original NULL path, then character,
globals and original commands through the exact 301656-bit packet terminator.
Release, ASan and UBSan pass. The independently pinned CLIENT shared count is
26. The earlier 303112-bit packet is distinct. No further framing table is
missing for this saved packet. Android observer replay also passes; original
ACK/READY and release/cancellation tests pass. Actual Thor traffic is pending.

Two physical captures show textured pavement and the box at
[131.453125, 0.25, -114.953125]. The new host source-scene capture is 640 by
360 with a viewable PNG, full-screen controls and a corner return button.
This is host evidence; a new Thor export remains necessary. The real Huge
costume resolves to 14 visible records in 11 GEO files; it is not rendered.
Eight GEO files are package-pinned. Three have no checked manifest entry:
huge_emblem.geo, huge_uarmr.geo and huge_waist.geo. Their presence on Thor
is untested. Actual matching texture and rig loading still need integration;
the box remains the fallback.

Wine accounts for about 2.42 GB PSS. One omitted detail row contributes
1.83 GB without an executable label; MapServer attribution is unproved.
Map and DB startup took about 279 and 67 seconds, without a world or collision
allocation breakdown. PostgreSQL stays unchanged. Recorded physical peaks are
4021653504 RSS bytes and 2925635584 PSS bytes, separate from source charges.

1. Install 0.1.17 and record Thor ACK/READY traffic, positions and full-screen capture.
2. Draw the decoded Huge costume with its actual rig, GEO and textures.
3. Verify imported archive streaming at a different pose without rebuilding.

These three steps remain before the requested real character and live world
are demonstrated. Android replay charges peak at 7533495 bytes under 8 MiB; scene cap
remains 96 MiB. Gates 25–27 stay open. Keep the rolling status and pinned raw
outputs only. All 70 bundles are inventoried there; four unreferenced ones were
removed, while the 66 receipt or documentation references remain.
