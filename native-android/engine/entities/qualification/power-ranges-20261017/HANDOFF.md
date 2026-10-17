# PowerInfoUpdate range-list continuation

Implemented `coh_power_ranges.*` as an additive raw wire boundary. Complete
original `character_SendPowerRanges` / `character_ReceivePowerRanges` grammar:
repeated one-bit event sentinel, original basepower automatic-width CRC, raw
32-bit F32 word, then a zero sentinel. The original producer visits power sets
and powers in reverse order, tests primary then secondary target types, sends
zero for non-location ranges, suppresses unchanged ranges unless force-all, and
skips null power slots. Events preserve original send order without deduplication.

`coh_power_info_no_changes` begins exactly at the PowerInfoUpdate presence flag.
A false flag still contains that entire range list. A true flag returns
`COH_UNSUPPORTED` with unchanged cursor/output: no partial skipping or inferred
later offset. `coh_power_ranges` also supports a separately established start at
the list after the full branch's power-definition list, but does not establish
that offset or parse any of those preceding definitions.

The module uses the existing `COH_CHARACTER_POWERS_MAX` admission bound (1024)
and the same original automatic-width basepower CRC wire grammar as
character-data. That parser does not expose a reusable standalone CRC decoder,
so the small raw scalar grammar is locally staged against the same original
producer/consumer functions, with existing character-data source/header hashes
bound in receipts. It does not invent power IDs or create gameplay powers.
Zero CRC is retained here: original `basepower_Send(NULL)` emits zero, and the
original range consumer still reads F32 before ignoring an unresolved power.
Raw NaN/infinity/signed-zero words are retained as wire events; they are not
finite-range or dictionary authority. All semantic application remains external.

Output and workspace are arena/heap PODs, allocation-free in production, bounded
at 1024 events. Admission charges both PODs, borrowed input, a 4096-byte named
stack reserve and caller-retained bytes. Failure leaves output/reader unchanged;
workspace is scratch. Host production frames total 272 bytes. Tests prove exact
budget boundaries and 1025-event refusal rather than increasing limits.

Reproduce with a new output path:

```
python native-android/engine/entities/check_power_ranges.py --output /tmp/coh-power-ranges-new.json
```

The checker executes complete unchanged original range producer/consumer,
basepower producer/consumer and automatic-width functions, with original
bitstream I/O and synthetic earray/character/power/dictionary shells. It also
executes the exact unchanged original PowerInfoUpdate false-branch prefixes,
not full PowerInfoUpdate functions. Synthetic dictionary lookup is not imported
source dictionary admission. Original-source host oracle remains unsanitized;
native production/tests run independently under ASan and UBSan.

208 generated fixtures cover both scalar profiles, all eight unaligned starting
offsets, outer-false and direct-list entries, empty/unchanged/forced lists,
null holes, secondary override, reverse multi-set order, raw CRC width boundaries,
null/unresolved powers, nonfinite ranges and 1024/1025-event bounds. Native
controls exercise every short-body truncation, bounded large-body samples,
rounded-scalar malformations, input/output/workspace aliases, invalid readers,
aggregate memory edges, exact terminator offsets and flag=true refusal. Host
release/ASan/UBSan pass 85,440 checks each; C++ boundary linking passes.

Optional `--fixtures-output` preserves the exact generated header. Paired
`--ndk` / `--android-output` build the standalone driver for ARM64 and x86_64
API 26 using the same fixture header and strict warnings. Per-ABI receipts
say `executed=false` and bind source/fixture/binary hashes. No NDK, emulator or
physical Thor was available here. Android compilation/execution remain pending.
No shared build/workflow files were changed.

Remaining: full-branch current-build selection, redefine/default-power and
power-definition/boost bodies, active/enabled/usage/recharge arrays,
inspiration/boost changes, dictionary/prior-state application and complete
outer transaction. `INITIAL_UPDATE_CLOSURE.md` retains full-message refusal.
No actor admission, READY, RECEIVED_CHARACTER or full-update ACK was added.
