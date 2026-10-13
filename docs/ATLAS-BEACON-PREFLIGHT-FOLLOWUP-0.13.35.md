# Separate beacon preflight follow-up

This draft is preserved on `codex/beacon-preflight-historical-fixtures-035`, based on `6136171`. It is separate from the continuation branch and the shipping 0.13.35 APK. It has not been merged, published as an APK, or qualified for native graph generation.

## Recorded failure

At source `33f31586b43399e25f61e13c6c4411e09c6b6d60`, [native beacon run 38325717305](https://github.com/Russianranger/coh-android/actions/runs/38325717305) failed in preflight job `115063786951`: 228 cases ran, with two errors in historical `.13→.14` reconstruction tests. The old packaging validator was given current `.35` helper source and rejected it with `Required geometry must be proved before source fingerprints and cache identity`.

The current generator's `fingerprint`/`os` dependency correction passed. Native generation was skipped; this failed run produced no graph. The `.35` APK retains previously qualified graph/native bytes, with current saved-map, generator and beacon-installation tests in its separate release qualification. The failed historical packaging suite is not a `.35` qualification module.

## Draft repair

- `tools/android/interactive/qualify_atlas_beacon_preflight.py` supplies exact `.14` helper inputs to only the two existing historical reconstruction cases. Their validators and mutation checks are unchanged. All other generator, graph, cache and packaging cases still execute on current sources.
- `tools/android/interactive/test_atlas_beacon_preflight.py` checks fixture integrity, exact byte copying, scoped root restoration, rejected symlinks/mutations and failure/skip propagation.
- `.github/workflows/android-atlas-beacon-generation.yml` authenticates the historical fixtures and calls the runner. It restores the previously excluded publication-workflow case. Native generation, recovery and readback steps remain intact.

The workflow retains its existing continuation-branch execution guard. This preservation branch is not itself an authorized native-generation or publication run.

## Fixture provenance and validation

The original `.14` qualification artifact is `11381713754`, from run `37392793426`, source `25f821da9e782281953412543057054abd8dd320`. Its exact archive is 6,137,683 bytes, SHA-256 `4c42683fe1cad44f6bed1df5f0a649d36b0bc68761f91f2ad26e78d4ecc60c8a`.

That downloaded archive was independently hashed. Both historical helper files were retrieved at the exact original commit without text normalization and matched its qualification source pins:

| File | Bytes | SHA-256 |
| --- | ---: | --- |
| `android/guest/local_character_server.py` | 116895 | `1a36bdfe81784c72a6a9f8a8cd355348fcf7ccb6dacd26f52bf098108528f615` |
| `android/guest/native_training_save.py` | 17455 | `a1bc4641eb96fed662274d742cea8ad51f47ab44fc0a35dec155da8a0e486fdc` |

The draft runner's 10 host tests passed with zero failures, errors or skips. The restored publication-workflow test separately passed. These results cover the draft fixture mechanism, not native graph production or current physical gameplay.

**Outstanding:** the full proposed preflight, including both historical cases against the exact public `.13` APK, has not executed. It must pass with the real donor, followed by the appropriate native recovery/readback qualification, before this follow-up is accepted. No shipping artifact, native result or physical performance claim is derived from this draft.
