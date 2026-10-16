# Entity character-stat continuation — host qualification

Source baseline: `cda93d96f8696e6a0f2ec6940a0c96e5b852f281`.
Original source import: `0b75ade0c801735e10c5798f641948a45cc50488`.
Exact implementation, oracle, test and source-file hashes: `host.json`.
Retained exact corpus: `fixtures.h`.

Implemented and host/source-qualified:

- Original pet basepower CRC serialization.
- NPC/sequence appearance references, correct retained world-group semantics,
  translucency, per-channel ordering and rollback.
- Complete pinned basic/self absolute statistic schemas with original producer
  **and consumer** parity for all transmitted float/integer values.
- Target/assist/taunt/placate metadata, status mask/strings, inventory sizes.
- Atomic supported entity record integration, including nonempty basic stats.

Host release, ASan and UBSan each passed 471,082 checks, 38,743 every-bit
truncations and 20,000 randomized body cases. List tests retain 50 cases and
9,084 truncations. Fixtures are synthetic; no actual server full update was
captured or accepted. The original complete outer `sendEntity`/`entSendUpdate`
functions were not executed. Status fixtures are manually source-layout-built;
original status functions were audited/pinned, not executed.

Memory: 3,600-byte slots, 922,624-byte caller-owned workspace. A full 256-slot
caller table plus workspace costs 1,844,224 bytes. No parser heap allocations
or retained packet pointers. Full-tail admission and render spawning are false.

Android ARM64 and emulator qualification remain pending coordinator CI; this
worker environment has no discovered Android NDK or `cmake` executable. Direct
host C99 compiler tests with `-Wall -Wextra -Werror -pedantic` succeeded. Previous
receipts in sibling directories remain historical and do not qualify this code.

Rollback: revert this additive engine module continuation; no APK or saved data
changes. See `../../INITIAL_UPDATE_CLOSURE.md` before production integration.
