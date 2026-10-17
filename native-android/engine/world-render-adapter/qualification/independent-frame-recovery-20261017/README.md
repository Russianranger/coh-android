# Independent recovered frame qualification

Recovered baseline `4f6fe92107a10323a90123c6856de578943300e2` executes unchanged
adapter frame bytes: 32,284 assertions in each Release/ASan/UBSan mode.
The original source matrix header was materialized from the same Git commit
by expanding this isolated worktree's sparse checkout; its pinned digest passed.

Test commit `d4952a414354f4d8c0b26680df9af640a2847b4a` adds all seven cancellation
boundaries during a disjoint selection rebind at the **same Surface generation**.
Each refusal retains old selection masks and borrowed texture names, and rejects
newly selected draws without modifying the output. This closes a regression gap
where Surface-generation rejection alone could hide partial scratch publication.
Production adapter and renderer implementation bytes are unchanged.

The clean committed test tree independently passes 32,320 assertions in Release,
ASan and UBSan, including the original 512 matrix comparisons, 5,000 mutations,
2,000 publications with three readers, 1,025 draws in ordered 512/512/1 batches,
and zero measured render allocations or frees. Six frame Android admission
Python tests pass. LSan remains unavailable; exact accounting controls execute.

Receipts retain exact revision, tree, all source hashes and identical mode results.
No local NDK exists. Android ABI builds/emulator execution remain delegated to
coordinator CI; no GLES, APK, physical Thor or live-world result is claimed.

Source graph shortest-path review is read-only and bound to exact reviewed bytes.
It validates deterministic topology witness mechanics, not semantic assets or
live transaction authority. Complete GEO/material/resource and actor/transaction
producers are still missing; current prerequisites cannot mint a production
renderer receipt. No synthetic receipt or Combined activation was introduced.
