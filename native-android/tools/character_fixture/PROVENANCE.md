# Phase 8 real Wretch character fixture

This fixture contains every present highest-resolution geometry part selected
by the original Arachnos_Wretch NPC costume: ten source GEO files, eleven draws,
2,626 vertices and 2,986 triangles. The two boots are separate authored models.
The source glove GEO contains only the left arm. The client explicitly allows
missing Larm geometry, so the missing right glove remains None. Nothing is
mirrored or invented. The small right shoulder/stump model is the genuine
GEO_Spadr_Wretch, with its own seven-bone palette.

`pins.json` identifies exact source members in `coh-assets-v1.0.0` Base and
Reference release archives. The acquisition tool reuses the accepted bounded
HTTP reader, demands exact HTTP 206 ranges and stable ETags, and independently
checks member size, CRC32 and SHA-256. The complete source visual manifest and
Reference index had previously been acquired and hash verified. Full outer
archive checksums are published provenance, not a claim that a subset reader
hashed the complete archive. Optional `--use-verified-local` only reuses an
existing file after exact size, CRC and SHA checks and lists such files in the
new receipt. Fresh CI acquisition starts from an empty directory.

The source inventory includes 10 Wretch GEOs, the original MALE_BONES_SCALE_L/S
GEOs, 30 original texture wrappers and the unchanged huge/skel_ready and
huge/run animations. Only the 17 textures actually required by the selected
fallback are decoded into the scene, including the actual stock white texture
resolved by `texFind("white")`. Additional source layers are provenance for the future MULTI/bump
material gate and are not substituted for the selected costume overrides.

`geo.py` parses little-endian x86 disk offsets bytewise, admitting only the
required source versions 0, 2 and 3. The head uses the original fixed 216-byte
version 2 model record; its PackBlock begins at byte132. Other selected character
parts use version 3. Morphology scale-model geometry uses version0 records.
The delta decoder and original GPU V flip are imported from the accepted Phase
6 converter without changing that tool. One-bone palettes and endpoint weights
are preserved. The existing COHMESH1 mesh format is used for all parts.

`original_delta_check.py` runs the retained original source uncompressDeltas
function on every pinned, bounded source channel. It compares 66 channels and
40,470 scalar elements byte for byte, including GPU-upload UVs, exact weight
division/complement and encoded matrix-row index division. It does not cast
disk records to host structures or claim execution of the complete old client.

`morph.py` packages original binary32 fat/skinny `model.scale` triples and the
authored appearance values in COHMOR01. The Android runtime must compute the
appearance and its hierarchy/socket palettes. `prepare.py` retains unmodified
compressed base/motion files in COHRIG01. The original actor source oracle and
the independent hierarchy reference generator produce comparison assets;
those goldens are not a replacement for the native runtime sampler.

`scene.py` packages eleven canonical meshes and seventeen unique mip0 RGBA
textures in COHCHAR8. Base and generic aliases come from the source material
resolver. Colors use the original float(byte) * (1.f / 255.f) expression. Hair
and Neck preserve Collar2x double-sided rendering; Hair retains its real alpha
mask and source-alpha blending. Other selected dual layers are opaque. The
scene uses explicit CW-front, back-face culling and a fixed eleven-part
diagnostic order for a bounded camera. Original transparency sorting,
advanced material quality and original runtime pixel capture remain unqualified.

The selected quality profile disables MULTITEX and BUMPMAPS and uses the
source automatic COLORBLEND_DUAL fallback. `materials.json` retains the actual
six costume composite identities and all omitted high-quality layer names.
The independent scalar material reference evaluates six cases for every draw,
including real texture pairs, source costume tints, strict alpha, fog, blending
and an explicitly controlled alpha swatch. Nearest mip0/clamp sampling and
controlled lighting are diagnostic inputs, not an original GPU capture.

Reproduction in a full checkout:

```bash
python native-android/tools/character_fixture/acquire.py --output corpus
python native-android/tools/character_fixture/prepare.py \
  --corpus corpus --output assets --evidence-output evidence
```

The Android assets are `character.bin`, `rig.bin`, `morph.bin`,
`character-reference.bin`, `material-reference.bin` and `character-fixture.json`.
Generated raw or derived game assets are not committed to the repository.
