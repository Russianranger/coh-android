# Selected-record original outer order fixture

This additive host fixture executes the entire unchanged original `sendEntity`
control function from pinned `entsend.c`. It is a prepared, full-update, self
entity fixture; visibility/preparation, generic cached sends and the whole engine
are not executed. Explicit macros provide the prepared fixture state. Source
inline field statements, full-create promotion and conditional call ordering run
unchanged, using the existing whole original packet/bit writers plus original
`pktSendIfSetBits` and `pktSendIfSetString`.

Every child serializer is an explicit adapter that injects a separately supplied
bit span. **The adapter does not execute those original child functions.** The
retained marker corpus proves outer order, inline control layout and exact stage
positions only. Marker bytes are not valid selected-record grammar, appearance,
character stats or actor fixtures. Native composition must replace every relevant
span with independently qualified exact child output and compare every projected
field. It must not relabel this whole control function as whole engine/child
producer or original receiver execution.

`order_oracle.generate(texts)` accepts a mapping containing
`MapServer/src/entity/entsend.c`, verifies its complete LF SHA256, and returns the
C fixture suffix plus source identity. `build(root, work)` constructs a host
shared object using the frozen existing DB bit-writer provider. Its APIs are:

- `record_clear_children()` clears borrowed child descriptors.
- `record_set_child(id, bytes, bits, required_mod8)` sets one borrowed span.
  Child IDs1..23 are listed in `order_oracle.CHILDREN`. Bits start at bit0 of the
  supplied span, little endian within bytes. At most65,536 bits per child are
  supported. Keep its backing buffer alive and immutable until the call ends.
- `record_outer(scenario, aligned, prefix, output, bits, begin, boundaries,
  events, event_count)` runs one record. Output storage must be65,536 bytes,
  boundaries28 U32s, events72 U32s. Scenarios0..15 vary taskforce, status,
  translucency, name/flashback/ignore-combat flags and raid/in-phase selection.
  The full self fixture always has player and character storage. Prefix0..7 is
  allowed in unaligned mode; the aligned fixture requires prefix0.

Each event is `[child_id, before_bit, after_bit]`. The first26 boundary words are
the13 stage begin/end pairs in `coh_selected_record.h` order, with record begin
and end repeated in the final2 words. These are actual cursor observations;
the taskforce/rare boundary is recorded by the fixture `ENTINFO` accessor before
the original send-on-odd expression writes its first bit. No source statement is
inserted or removed. Record begin is immediately after the actual original list
delta index, which remains in the output.

`required_mod8` must equal the child producer's exact start offset modulo8.
Value255 is permitted only for a separately proven relocation-safe provider.
Explicit internal byte-array alignment can make raw child relocation invalid;
regenerate such children at the real offset. Aligned child spans must have byte
aligned start and length. Unsupported injected profiles assert in this trusted
fixture, not a production parser. Total packet capacity is the existing bounded
64KiB source-writer fixture. No public native import, allocation or authority is
created. All stores/callbacks are serialized host fixture ownership.

The small qualification runs144 cases with relocation-safe16-bit markers and
8,208 ordering/boundary/bit-copy controls. The original x86 host writer is
unsanitized; no original child receiver, server, Win32 ABI, Android, selected
entity transaction, dictionary generation, actor, world or ACK is qualified.

```sh
python3 check_order.py --source-root /path/to/pinned/source --output fresh.json
```
