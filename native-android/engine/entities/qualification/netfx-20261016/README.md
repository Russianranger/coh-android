# NetFX continuation — host qualification

Parent implementation: `e5bb08d493c68f5faf80caf397aa25691d084502`.
Original import: `0b75ade0c801735e10c5798f641948a45cc50488`.
Exact code/oracle/fixture hashes are bound by `host.json`.

The complete bounded original `entReceiveNetFx` grammar is implemented as
transactional unresolved event metadata and reused inside supported entity
records. This includes zero count, one-shot/maintained/destroy commands,
optional flags/tints/scalars, trigger FX, entity/position origins and targets,
bone index and target entity. All floats must be finite; count <= 32, entity
indices <= 10239, bone <= 255 and timer <= INT32_MAX.

The oracle executes unchanged original `entSendNetFx` and `entReceiveNetFx` and
compares all 17 integer fields and 8 floats per event. Fixtures cover forced
versus incremental filtering, never-send NEW commands, source packet delay,
triggered delay suppression, zero counts and both addressing modes. Complete
supported record fixtures combine original components in audited outer field
order, including nonempty FX plus basic character statistics. They are not a
complete original `sendEntity` or authentic server packet capture.

Release, ASan and UBSan each passed 550,302 checks, 46,261 every-bit truncations,
and 20,000 randomized bodies. Malformed zero commands/IDs, excessive counts,
unknown types, excessive indices/bones, NaN/infinite floats and rollback passed.
All earlier entity/list/stat tests passed. The independent worker review found
no blocking parser mismatch and reinforced the event-delivery boundary below.

Memory stays bounded: 3,600-byte slot; 922,624-byte list workspace; 3,824-byte
record including FX. No heap allocation and no borrowed packet pointer. The
list inspection API discards per-record FX and trigger lists; it is **not event
delivery**. A future complete transaction must retain events, resolve resources,
and validate all remaining tails before rendering or acknowledging anything.
Client timer metadata stores the original wire integer; original NetFx stores
its value as float at runtime.

ARM64 build, Android emulator execution, physical Thor acceptance and actual
full server interoperability remain pending. The existing exact combined APK
is unchanged. `full_update_accepted` and `render_spawn` remain false.
