# Independent pre-character source review

Reviewed exact Worker C commit `18b84506ec4a0ae02c7617ac8116b3a77e41e9fa`
(integrated coordinator revision `5d76c0bc0`). An isolated detached review worktree
was created; C's changing worktree and source were not modified. No correctness
defect was found in this bounded staging parser. This review does not qualify
the omitted character body or promote staging to an authoritative actor.

Source comparison, not fixture counts:

- `MapServer/src/entity/entserver.c:sendCharacterToClient` first writes five
  packed words in widths 1,1,1,2,1. C preserves raw 32-bit results; the original
  statements impose no boolean restriction, including on `RaidIsRunning()`.
- `Common/auth/auth.h` defines `AUTH_BYTES=128` and
  `AUTH_DWORDS=AUTH_BYTES/sizeof(U32)`. `Common/entity/entPlayer.h` declares
  `U32 auth_user_data[AUTH_DWORDS]`. Both producer and consumer pass
  `8*sizeof(e->pl->auth_user_data)`, hence exactly 1024 bits/128 bytes.
- `BitStream.c:bsWriteBitsArray` and `bsReadBitsArray` align unconditionally,
  independently of `byteAlignedMode`. An unaligned cursor skips to the next
  byte before direct `memcpy`. The native `pad=(8-(cursor&7))&7` plus
  `cursor+=pad` and 128-byte copy matches this. Padding is not constrained by
  the original consumer, so nonzero padding must remain accepted. The generic
  `bsAlignByte` helper is extracted into the oracle but the original array
  functions perform their own equivalent byte advance; no helper call is
  assumed by the parser.
- Four following producer/consumer scalar widths are exactly 1,2,3,1. In
  byte-aligned scalar mode original bitstream operations consume rounded
  bytes. The native reader does the same and additionally refuses values
  exceeding those declared widths. This is explicit fail-closed handling of
  malformed rounded bytes, not a claim the original client refuses them.
- Oracle extraction ends before `character_Send` and before client skin/UI
  changes. Full original bitstream functions execute, but surrounding entities,
  account data, server state and enum counts are synthetic. The oracle is
  unsanitized. Its success establishes only these extracted statement blocks;
  no actual DBID, entitlements, power dictionaries or live packet are supplied.

Transactional and alias reasoning:

`q=*r` snapshots the reader; zero-width `coh_rep_read` validates its bounds and
alignment before further arithmetic. All packed/scalar reads, padding and auth
copy affect only local `q` and zeroed local output `v`. Both `q.bits-q.cursor`
subtractions follow validated cursor bounds. The copy cannot occur without at
least 128 complete bytes remaining, and the final scalars still must validate.
Only after complete success does `*out=v; *r=q` publish staging. There is no
allocation, callback, global mutation, ACK or actor publication. Reader/output
and either with the entire input byte owner are refused before writes; the
range helper also refuses integer-wrapping spans. The API requires valid caller
objects and disjoint storage and does not purport to validate arbitrary pointers.

Independent controls use a separate tiny bit writer rather than the source
oracle. They construct all eight initial bit offsets, nonzero alignment padding,
128 known auth bytes and maximum valid following scalar values. Every truncated
prefix refuses without changing reader/output. Aligned partial aliases across
reader storage and the whole byte owner, including unused bytes beyond declared
bits, refuse without writes; invalid cursor and byte-mode misalignment refuse.
The harness uses aligned storage and aligned partial alias addresses.

Fresh execution:

- Existing original-source oracle: 280 cases / 646,561 checks in each of release,
  ASan and UBSan, plus original producer/consumer cursor equality and C++ linkage.
- New independent controls: 17,328 checks in each of release, ASan and UBSan.
- ASan leak detection remains disabled; the tested parser allocates nothing.
- Android/Thor, whole-character acceptance and ACK authority remain unqualified.

Reproduce independent controls against any checkout with the pinned file hashes:

```
python native-android/engine/snapshot-admission/reviews/recovery-20261017/prefix-review.py --source-root CHECKOUT --output NEW_RECEIPT.json
```

`prefix-review.json` retains both fresh results and original source/production
pins; the independent driver checks source identity before and after execution.
