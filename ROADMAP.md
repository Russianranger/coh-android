# Native Android roadmap

Updated 2026-10-20. Physical 0.1.16 reports are recorded; development has resumed.

Combined 0.1.14 passed stage 41. Physical 0.1.16 confirms bodytype 4, Huge,
28 costume parts, 112 strings and 58 colors. The body ends at bit 11648 and
appearance at 11672. Host replay now consumes all 343 power customizations
through bit 39216, recording 343 unresolved CRCs through the original NULL
path. Their names do not affect wire length. Original signed inventory receive
reaches bit 41312 of 301656; remaining original receive integration is active.
The earlier 303112-bit packet is distinct. ACK and READY remain unsent.

Two physical captures show textured source pavement and the yellow box at
[131.453125, 0.25, -114.953125]. They are 192 by 41 pixels. The next diagnostic
adds full-screen controls and bounded 640 by 360 capture after viewport resize.
The actual Huge costume resolves through the existing appearance adapter;
its first required model is huge_PANTS.geo / GEO_HIPS_Tight. Genuine matching
rig, geometry and textures must be present before replacing the box.

Wine accounts for about 2.42 GB of PSS. One omitted detail row contributes
1.83 GB, but its executable identity is not retained, so MapServer attribution
is unproved. No world or collision allocation breakdown was captured.
PostgreSQL stays unchanged. Recorded process peaks are 4021653504 RSS bytes
and 2925635584 PSS bytes; source payload charges remain separate.

1. Finish the saved packet; use original ACK/READY and observe subsequent traffic.
2. Draw the decoded Huge costume using its actual rig, GEO and textures.
3. Stream imported archives at a different pose without rebuilding the APK.

These three bounded steps remain before the requested live world with a real
character is demonstrated. The 8 MiB initial and 96 MiB scene caps remain.
Gates 25–27 stay open. Update the rolling status; commit raw output only when
a checker pins it. Four unreferenced bundles were removed; all 70 are listed
with their pins and hashes in the rolling status. Referenced bundles remain.
