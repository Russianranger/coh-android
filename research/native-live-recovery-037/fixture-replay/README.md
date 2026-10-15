# Recovered dormant fixture replay

This replay reconstructs an isolated installed source layout from the exact
operation stage and overlays the four files preserved in the later fixture stage.
The original stage bytes and historical test modules remain unchanged. Active
Android paths, runtime launchers, databases, characters, assets and binaries are
not edited. No native C, Game, probe or APK compilation is performed.

Run from a checkout containing both recovered source stages, using the extracted
original CI artifact and a fresh scratch path:

```sh
python3 research/native-live-recovery-037/fixture-replay/replay.py \
  --artifact-root /path/to/extracted/11878700818 \
  --layout /path/to/fresh/qualification-layout \
  --output /path/to/fresh/replay-evidence
```

Both destination paths must be absent and disjoint: neither may contain the
other. Existing paths, including dangling destination symlinks, are refused
before authentication, directory creation or copying. The runner never deletes
or replaces an existing output tree.

The runner authenticates both source manifests and every staged file before
copying source, then verifies every source and artifact named by the original CI
receipt. All twelve original command logs must match their recorded digests and
zero exit codes. Host JNI compilation and `-Xcheck:jni` execution are explicitly
required. The original CI receipt is pinned at SHA-256
`9d28449756c06b539d906cf1cc1729233eebe6a63901e9eca80615c57845270f`;
the retained 35,664-byte host helper is
`cec249a49fa8758b4caf2f074c133fb687f5d53e1c580ab1aa8031b822d653a8`.
This is the original CI host helper, distinct from the separately recorded local
historical helper whose digest starts `b264121c`.

The original job **remains failed** with `JNI dependency boundary changed`, from
the later Bionic dependency audit. Its unchanged raw report is preserved as
`evidence/original-ci-qualification.failed.json`. A separately named derived
host-only receipt records only the authenticated host source, compilation and
28-control execution scope. The derivation grants no Android, Bionic runtime,
Game, shipping or performance admission. The unchanged generic JNI test performs
its own source-recipe and complete helper authentication using this host receipt.

The replay runs these previously defined controls without adding their counts to
historical totals:

| Module | Cases | Scope |
| --- | ---: | --- |
| Fixture owner | 75 | Release-8 JVM, packet parsing, actual host FileChannel reads and descriptor cleanup; Process/JNI/fstat/NT custody uses typed mocks or synthetic packets |
| Guest loader | 36 | Host private-file and inherited-environment controls; external current proof is controlled |
| Operation JNI | 5 | Actual host JNI, current kernel files, TCP and controlled activation |

The five JNI cases cover current fields/order/geometry and held identity, bound
absolute links, owned relative links, safe initial refusal and terminal late
retargeting. The source pins are checked again after replay. Full per-suite logs,
source pins and a scoped replay receipt are under `evidence/`.

Actual packaged Android custody, Wine/FEX/PRoot namespace integration, native NT
and Game consumers, runtime admission and physical Thor startup/zoning remain
unqualified by these controls.

## Runner hardening after the recorded replay

The unchanged original `evidence/replay-qualification.json` pins the exact runner
that executed the 75/36/5 controls. That runner is archived byte-for-byte as
`evidence/executed-replay.py` (SHA-256
`e97bfa22d80052f1d5e49f691c78991eeaae1c783182bdb1bc5c4e5dadbeeca2`).
The archived file is provenance, not the current entry point.

The current `replay.py` subsequently added explicit fresh output selection and
destination preflight. Those changes affect destination safety only. Authentication
and test execution remain unchanged; the historical fixture results are not
relabeled as executions of the hardened runner. Ten focused refusal controls
exercise existing output/layout preservation, overlap and symlink refusal,
required output selection, tampered receipt, tampered recovered source and
tampered retained helper rejection. Their separate source pins and result are
recorded in `evidence/runner-hardening-qualification.json`. The negative source
and helper tests use a minimal controlled receipt with a test-only raw receipt
pin override to reach the original source/helper checks; no synthetic receipt
is admitted or used to load native code.

```sh
python3 -B -W error::ResourceWarning \
  research/native-live-recovery-037/fixture-replay/test_replay_safety.py -v
```
