# Gates 19–21: authored ground, source WALK and directional locomotion

This batch continues the physically accepted gates 16–18 at
`8e83f2343f29c7b4baee7876268c5ccb1e8b01b4`. It extends the same
Session Client source, version `0.2.0-gates19-21`, code 2. This debug package uses
`org.coh.sessionclient.walk` and the launcher label **CoH Native Session Client
0.2.0**. It installs alongside the accepted 0.1.0 client because that hosted
package used an unavailable ephemeral signing key. Existing app data and reports
are retained. A pinned public test signer supports subsequent debug updates;
the Java/JNI namespace remains `org.coh.sessionclient`. The conventional client
and release signing are unchanged.
The original character, rig, morphology, Atlas benchmark and comparison inputs
are recovered byte-for-byte from the exact accepted APK. They are not rebuilt
or reacquired. Existing receipts, failed attempts and the accepted APK remain
unchanged and available for rollback.

| Gate | New integrated behavior | Bounded scope |
| --- | --- | --- |
| 19 | Real Atlas trainstation floor and a second authored bench, original group transforms and mesh delta decoding, source collision grid offsets and CTri flags. Four new render parts, six genuine textures, 276 collision triangles. | The immutable 202,880-byte added world is a selected authored branch, not full Atlas. One floor detail asset is absent; the unchanged original client binding routine selects its genuine grey-texture fallback. Detailed floor appearance remains incomplete. |
| 20 | Active original WALK velocity/surface routines, CTri radius/cylinder queries, feet/head grounding and three-pass wall sliding at 30 Hz. Real wall contacts and safety-bound events are reported separately. | Static geometry, neutral source surface modifiers and the selected source walking profile. Jumping/powers, entity collision, full tracker streaming, server authority and prediction remain outside this subset. At an incomplete fixture edge an explicit scene guard restores the last supported position; it is not authored collision. |
| 21 | Authored RunPre/RunCycle/RunPost, inherited male early-stop walk/idle fallback, backward/left/right Pres and Cycles, source priorities/interruption groups, phase retention, MoveScale and recursive interpolation on the Huge hierarchy. | A bounded ground graph with original encoded keys. Random idle variants, airborne/swim/combat/weapon/FX and authoritative sequencing remain pending. Pushing into a wall retains desired movement and the source minimum animation rate .25; release follows its authored stop. |

The new ground and obstacle render positions and collision records share exact
binary32 world coordinates. The old benchmark's private startup transform/depth
witness remains intact and cannot move the actual WALK actor or camera. New
geometry receives separate CPU/GPU transform-feedback and actual visible-pixel
checks. Floor base textures retain source repeat sampling and ScaleST0 8/14;
accepted actor/benchmark samplers retain their prior qualified policy.

One immutable collision cache is built at session creation; no full GEO/model
loader or per-frame asset decoding is used. Input changes are retained in a
bounded 32-edge Android adapter and consumed at source physics ticks; opposing
and released controls still flow through the accepted source control kernel.
Focus loss clears queued input and velocity, while Surface recreation retains
logical WALK, camera and animation state. Reset is explicit. Detailed per-move
counters and cumulative contact/ground/slide/bound counters support qualification.

## Source and host evidence

- Source WALK: 12,736 independent active-source velocity cases and 144 supplied
  wall-contact transcripts match exactly. The real authored scene passes
  grounding, a stationary bench contact plateau, short tangent sliding,
  reversal, clear/reset and distinct support-boundary tests under ASan/UBSan.
  This is not whole-client or original tracker execution.
- Directional graph: 4,470 ticks and 31,290 comparisons match the selected
  original graph exactly. Original per-bone codecs, retarget, recursive blending
  and matrix composition compare 1,165 poses × 60 bones; hierarchy error is
  below 1e-6. The old COHLOCO1 behavior is retained and rechecked because the
  native view/state ABI grew; its original receipts are not rewritten.
- New GEO delta channels execute original source decoding. Indexed render and
  collision vertices compare byte-for-byte. Complete source trick lookup must
  pass in the full CI checkout; sparse local preparation explicitly retains
  that audit as pending. The genuine grey fallback is qualified from the
  unchanged lookup function and actual legacy binding statement.
- Native report serialization tests the exact Session declaration and shipped
  serializer, including all twelve animation counters and sixteen depth
  diagnostics, escaped strings and 64-bit counters. Its worst-case report is
  8,441 bytes within a 16,384-byte bound. This host test does not execute JNI,
  Android or graphics.

Source/tool details live in [walk](walk/README.md),
[world preparation](tools/walkable_fixture/README.md),
[locomotion](locomotion/README.md) and
[directional checks](tools/directional_fixture/CHECKS.md).
The updated session workflow builds/lints ARM64 and a separate x86_64 package,
verifies exact assets/signature/ELF, then drives actual Android input and
checks new scene rendering, directional transitions, bench blocking/sliding,
Home/Recreate/Reset and real document export. No automatic movement script or
synthetic JNI input substitutes for the Android input tests.

**Implementation and local source/host checks are complete. Android build and
emulator qualification are pending until their final receipts are recorded.**
**Physical gates 19–21 remain pending.** Accepted gates 13–18 are unchanged.
No full Atlas, live server login/replication, full sequencer, GPU palette
skinning or sustained performance acceptance is claimed.

See the [combined new Thor procedure](session-client/THOR-TEST.md).
