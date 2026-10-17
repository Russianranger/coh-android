# Renderer frame recovery

Base: `3e8b5c9f5b794b58a66c6d8c62a593b926a10873`.

Recovered from preserved `/workspace/scratch/142ad4bc669b/worker-e` by content:

- `coh_world_render.c`: SHA256 `48e82a2db95157663e509dbb088d63ce30503f838335bf73e42ac945eae437f1`
- `coh_world_render.h`: SHA256 `a79ffff0fb0743436193bb3371adde449e03ac7c7b06eb06e2fa3576e461c130`

The prior worktree was not reset or edited. Its broken `.git` pointer prevented
recovery of unpublished commit metadata; source comparison establishes exactly
what differs from the pinned remote. Only the two unpublished implementation
files were copied. Existing shared-geometry functionality was already in remote
and was not duplicated. New tests and documentation qualify the recovered API.

This closes the COMPACT_HANDOFF step requiring bounded ordered frame batching.
It adds no authentic world receipt producer and enables no Combined code path.
Graph/root/checksum/resource semantic closure and complete actor/full-update
validation remain upstream prerequisites. A source-only runtime snapshot is not
a matching live GROUPS transaction and cannot itself mint a renderer receipt.

Qualification: `check.py --sanitize`, exact source hashes in
`qualification/frame-recovery-20261017/host.json`. Release, ASan and UBSan execute
the same deterministic corpus. Source matrix oracle executes unchanged original
`mulMat44Inline` for 512 cases. No NDK is supplied in this worker; Android build,
emulator, physical Thor, GLES and real server acceptance remain unqualified for
this tranche. Accepted historical APKs are unchanged.
