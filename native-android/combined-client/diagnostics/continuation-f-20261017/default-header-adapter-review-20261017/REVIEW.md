# Independent fixed-seven staging adapter review

F found no remaining concrete blocker in B source
`a0ef67a7a7731c1ea77b67c5d7e66b928617a57c`. Its exact proof SHA-256 is
`70c2880a646baa2e172ae68936b02de9a2148ba9567511c4e64684ca3f98966e`.
All 17 recorded source hashes match the worktree and exact committed blobs.
F reviewed source, original helper isolation, native bridge, tests and scope;
F did not rerun the qualifier.

Requested fixes are included: independent cleanup attempts preserve the primary
error, only fixed secondary-code/count notes leave the CLI, execution sources
are rechecked before compile and execute, and ELF bytes are frozen around
execution. Fifteen owner-reported controlled methods and release/ASan/UBSan
cases cover these paths. Unlink refusals can leave owned leftovers; cleanup
continues and success is not reported.

The exact cold worktree and seven full source-body hashes remain mandatory.
Retention is fixed and independent of parser support. Existing outputs are
preserved; only seven public-source files plus a sanitized manifest can be
retained. The full import proof is reused from its pinned receipt, rather than
independently rehashing every imported leaf.

All tests use explicitly controlled staging/body pins. No authentic default
body or real staging run is established. Whole namespace/default identity,
current provider generation, material/GPU/world authority, Android ABI, RSS and
global parent-budget fit remain false. Python archive/compiler/runtime storage
is diagnostic external memory, separate from the short-lived native header
owner's named reservation.
