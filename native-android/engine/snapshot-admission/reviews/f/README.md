# Independent F snapshot-admission review

Scope: pinned `3e8b5c9f5b794b58a66c6d8c62a593b926a10873` plus A's new isolated
Python admission module. No production source, previous profiling work, accepted
APK, server capture, workflow, or remote branch was changed by F.

The review identified two admission hardening gaps before qualification:

- BZIP2/LZMA member methods could invoke codecs whose decoder working storage is
  outside the named retained-payload budget. A now accepts only STORE/DEFLATE.
- Unix FIFO, socket, block-device and character-device ZIP metadata passed the
  earlier symlink-only guard. No extraction occurred, so this caused no device
  operation. A now accepts regular or unspecified file modes only.

`test_independent.py` exercises exact authentic admission and frozen scope flags,
metadata repacking, duplicates/missing/extra names, six hostile path forms,
payload and length corruption, symlink/special modes, BZIP2/LZMA refusal,
archive-size and truncation controls, duplicate/nonfinite JSON and retained
cleanup receipts. It independently verifies all 19 diagnostic lengths/digests
and both retained catalog/snapshot identities. `qualification.json` binds exact
validator/trust/archive hashes and rejects source drift during execution.
`source-drift-attempt.json` preserves one rejected attempt: all 17 tests passed,
but A added corrupt-stream exception normalization during the run. It is not a
qualification receipt. `first-review.json` is a preliminary 16-test receipt,
superseded by the complete source-stable receipt.

Run from any checkout with:

```sh
python native-android/engine/snapshot-admission/reviews/f/test_independent.py \
  --admit native-android/engine/snapshot-admission/admit.py \
  --capture-zip /absolute/path/evidence.zip --receipt /absolute/path/review.json
```

`capture-review.json` records the independent retained-artifact inspection:
2,024,961 compressed bytes, 34 members and 12,324,476 uncompressed member bytes;
12,179,670 is the largest member. The known trusted manifest and exact member
seal prevent archive-supplied hashes from granting trust. Exact-member digests
also protect source/generation/run receipts before semantic admission.

The capture receipt consistently reports owned process groups absent, private
Wine kill/wait exit zero, unchanged runtime source, successful cleanup and no
failed output publication. This verifies retained receipt consistency, not an
independent observation of historical process teardown. No server was restarted.

The 16 MiB aggregate payload bound is not a whole-process memory cap: Python ZIP
metadata, per-codec workspaces, input buffers and JSON objects add overhead.
Likewise original capture logs were polled and the source process had no hard
memory cap. No process RSS or physical-device memory measurement was performed.
All admitted results remain source-snapshot/offline-analysis only; live GROUPS,
physical generation, authoritative graph/actor/renderer publication and world
acceptance remain false. ASan/UBSan and Android execution are not claimed for
these Python archive tests.
