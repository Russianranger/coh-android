# Focused B/C/F/A8 CI artifact review

Run [39073157441](https://github.com/Russianranger/coh-android/actions/runs/39073157441),
attempt 1, completed successfully at published commit
`91cacafa4451cf7504b5dd105f2790ae1c41739b`, tree
`499e397a7bc3eaf0d01a8b404317b94a2b97384b`. All steps in job 117514794401
succeeded. The workflow reused the exact accepted cache/resource archives once;
it ran only the new B selector, C boost-slot qualifier, F host ABI/overlap
inspection and A's eight public-status controls. This review reuses those results
and runs no qualifier or capture.

The actual artifact 12115756974 was downloaded and retained as `artifact.zip`:
21,884 bytes, SHA256
`54be63d80829412fb83cccf2f587f3bc8edb81d778261cd01bf1c13aa49462dd`.
That matches GitHub artifact metadata and the upload log. ZIP CRCs and all three
regular, unencrypted members pass; each extracted member exactly matches the
retained archive.

| Member | Bytes | SHA256 |
| --- | ---: | --- |
| `trick-model.json` | 14,941 | `7e2f7b3765ddb2b040cb48ad2f1db119281223069f6f0fdcbe6b103c1ade4fca` |
| `power-boost-slots.json.gz` | 10,630 | `51b877c457de94081b9f9eda6020646afe917caa6e96bb8cff9116012fdda6c9` |
| `latest-owner-overlap.json` | 28,565 | `e367e57daf7023f77fba6b1f6549f8e692dfe6ff0996c53a5c32e2060b7ff6df` |

Every proof identifies the published commit. The source audit verifies all B 45,
C 59 and F 48 current source entries against exact published git bytes. Including
the workflow, A8 source, audit script/handoff and preserved receipt blobs gives
149 distinct pins in `source-verification.json`. All eight F historical receipt
hashes and every explicit historical/current source-difference map recompute
exactly. B/C source and result/control cohorts match their retained host proofs;
the new CI receipts remain separate current executions of those narrow scopes.

| Scope | Result |
| --- | --- |
| B, each release/ASan/UBSan mode | 301,210 checks; 28,046 original comparisons; six mutations refused |
| B actual retained root associations, each owner | 3,083 queries; 1,959 matches; 1,124 misses; 528 distinct rows; zero presence/name/file disagreements |
| C, each release/ASan/UBSan mode | 375,012 checks across 11 profiles |
| F | Actual C/C++ host size/alignment agreement, including new optional owner/result types |
| A8 | All eight public-summary unittest methods pass in the retained job log |

B's C++ consumer binds the exact whole/detached C object hashes in the CI
receipt. C reports its actual C/C++ link pass; this review does not reexecute it.
F includes schedules at 16,496 bytes, boost projection at 56 bytes, its separate
65,536-byte workspace and B's 320-byte caller result. Its additional named owners
total 3,824,536 bytes. Added to the preserved old/candidate reference, the named
lower bound exceeds 96 MiB by 3,235,921 bytes before excluded required charges.
This is historical comparison arithmetic, not a measured current application
peak or a current fit/retirement claim. Actor, omitted geometry, material/GPU,
provider and runtime charges remain explicit exclusions.

A8 has no separate artifact member: the exact published test, summary and stage
helper hashes are retained, with its eight successful method names and final
`Ran 8 tests ... OK` bound to `job.log` and the successful job step. These are
public-status/privacy controls, not an original server capture or GROUPS result.

Historical CLIENT/SERVER generation equality, actual current TexBind/material
selection, whole character receive/actor/ACK authority, complete parent aggregate
admission, Android/GLES/Thor acceptance and world authority remain false. No old
LOD/material/other qualifier, 391-GEO download, runtime capture, APK or production
owner preparation is repeated by this review.

The read-only binding check is reproducible from a checkout containing the exact
published commit, using a fresh output path:

```
python native-android/engine/world-render-adapter/qualification/trick-model-selection-39073157441/verify_artifact.py \
  --source-root /path/to/coh-android --output /tmp/FRESH-source-verification.json
```

`source-verification.json` SHA256:
`a33d55e2a7d6d07b6eee0616edef857ac8720606136e8a51ff044f7266eccb95`.
The raw archive, original members, decoded job log with trailing whitespace
normalized, run/job/artifact metadata,
verifier and complete evidence manifest are retained together.
