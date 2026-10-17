# Independent power-range staging source review

Reviewed Worker C candidate `aeb74ba71` in a separate detached review worktree.
No C source or C working-tree files were modified. No correctness defect was
found within the standalone range-list / false PowerInfoUpdate staging scope.

Exact original-source semantics:

- Full `PowerInfo.c:character_SendPowerRanges` visits power sets and powers in
  reverse array order, skips null `Power *`, computes location/teleport/position
  ranges, and lets a matching secondary target override the primary range. It
  emits only changed ranges unless `bSendAll` is set. Each event is one sentinel,
  `basepower_Send(ppowOriginal)` and `pktSendF32`; the list ends with zero.
- Full `character_ReceivePowerRanges` always reads a base-power identifier and
  F32 for each sentinel before attempting dictionary/owned-power application.
  Null and unresolved dictionary entries do not omit the F32. Thus the native
  parser correctly stages every wire event in arrival order, including duplicate,
  zero and unknown CRCs. It does not claim those identifiers are owned powers.
- Complete `character_net.c:basepower_Send` sends CRC or zero through
  `pktSendBitsAuto`. Complete `basepower_Receive` decodes that identifier and
  attempts dictionary resolution; the real client may report an unknown CRC.
  Those reporting/application effects are deliberately outside native staging.
- Full original `pktSendBitsAuto` / `pktGetBitsAuto` select one of widths
  2,10,24,32 using a two-bit selector. Native staging duplicates these scalar
  widths and retains a noncanonical wide zero that the original reader accepts.
  Byte-aligned transport rounds individual scalars; native staging additionally
  rejects out-of-width rounded values as documented malformed-input policy.
- `bsWriteF32` and `bsReadF32` reinterpret and transmit 32-bit representations.
  Native staging reads uint32 words without floating-point arithmetic, retaining
  signed zero, infinity and NaN payloads without finite-range/application claims.
- Exact original `entity_SendPowerInfoUpdate` and receive no-change prefixes
  both call the range-list function even when the update flag is false. Native
  `coh_power_info_no_changes` includes this complete list. True flag returns
  UNSUPPORTED without committing the caller reader or output; it never scans
  through the unsupported definition/status body to find a plausible range list.

Oracle structure review:

The checker extracts the complete two range functions and both complete
basepower functions, plus complete original scalar/auto/F32 bitstream functions.
Only the false outer-update prefixes are extracted, ending before the first
true-branch statement. These boundaries are pinned and no whole true branch is
claimed. Synthetic shells provide arrays, dictionaries, range computations and
owned-power lookups; their observation captures each decoded CRC/F32 event even
when dictionary resolution fails. The shell suppresses original missing-power
reporting and is not real dictionary/application qualification. Original oracle
is unsanitized; native release/ASan/UBSan tests are distinct. Original producer
reverse iteration is preserved by native staging retaining observed wire order.

Memory and transactions:

Output and caller workspace stay disjoint from one another, reader and complete
input byte span. All values accumulate in workspace with a local reader; only
validated terminator commits reader/output. Workspace is intentionally unspecified
on failure. Budget subtraction is guarded before adding input and retained bytes;
SIZE_MAX retained bytes refuse. The cap is a named preparation budget and local
record admission capacity, not a protocol maximum or process-memory measurement.
No allocation, dictionary lookup, callbacks, actor publication or ACK is added.

Fresh tests:

- Replayed pinned original-source checker: 208 fixtures / 85,440 checks in each
  release/ASan/UBSan mode, including capacity, malformed selectors/scalars,
  truncation, alias, exact budget and unsupported branch controls.
- Independent integer-only writer, separate from original-source oracle: 20,113
  checks per release/ASan/UBSan mode. It covers both scalar modes and all valid
  start offsets; zero/noncanonical wide zero, unknown and duplicate CRCs; exact
  raw +/-zero, infinities, quiet/signaling NaN payloads, negative and subnormal
  words; every truncated message; untouched trailing suffix; retained-budget
  overflow refusal; and unsupported true flags followed by tempting valid tails.
- No Android execution, real dictionary application, complete PowerInfoUpdate or
  authoritative actor acceptance is claimed. ASan leak detection is disabled;
  the parser allocates nothing and independent caller allocations are freed.

Reproduce the separate writer checks against a checkout matching recorded pins:

```
python native-android/engine/snapshot-admission/reviews/recovery-20261017/ranges-review.py --source-root CHECKOUT --output NEW_RECEIPT.json
```

The review receipt combines the fresh original-source replay with independent
results. The independent driver verifies all native source/header dependencies
and its harness hash before and after execution.
