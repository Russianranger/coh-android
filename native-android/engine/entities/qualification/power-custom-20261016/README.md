# Power customization wire envelope — host qualification

Parent implementation: `fe3cd7b52cde3ab029bec55a698f0d1348b35ed5`.
Original import: `0b75ade0c801735e10c5798f641948a45cc50488`.
`host.json` binds exact native/oracle sources and fixture hashes. Earlier
appearance/body receipts remain unchanged. The fixture headers were regenerated
from the same pinned original functions after qualification and verified against
the qualified receipt hashes; unchanged native suites were not rerun just to
copy artifacts.

The standalone API covers complete non-debug `entReceivePowerCust` grammar,
including self/other/owned envelopes, current/additional slots, single/multiple
lists, list presence, auto-sized counts/CRCs/colors and token strings. It retains
raw wire order and duplicate IDs. It does not import a real power dictionary,
resolve resources, compose entity state or admit a complete character update.

The source oracle executes unchanged original `powerCustList_send`,
`powerCustList_receive`, `comparePowerCustomizations`, `entSendPowerCust`,
`entReceivePowerCust`, `costume_get_num_slots`, packet auto functions and prior
costume/envelope functions. Storage, earrays, StructCopy, account products and
power dictionary data are explicit synthetic adapters. Original consumer values
produce expected colors/tokens. Lookup observers preserve original CRC
arguments, including missing dictionary IDs; list observers record destinations
and ending cursors without decoding fields. The oracle verifies absent lists
retain seeded state, while present-empty lists clear it. Native output records
those event flags but does not apply persistent state.

Sixteen power-customization fixtures cover both alignment modes for self
multiple/single, other-player, owned, absent, empty, no change, duplicate IDs,
unknown dictionary ID and ten slots expanded by product entitlements. The 28
existing costume/appearance fixtures remain, for **44 fixtures** in the combined
costume oracle. This remains synthetic source execution, not server traffic.

Release, ASan and UBSan each passed **1,142,224 checks**, **227,549 every-bit
truncations** and **25,000 randomized bodies**, including 1,000 bodies also parsed
as power customization. Every incomplete original fixture preserves reader and
complete output. Unknown types, self mismatch, current/list index failures,
per-list count overflow, late aggregate overflow and long tokens reject without
partial publication. Manual original-writer boundary fixtures verify exactly
4,096 items across eight full lists and refusal of a ninth full list. Each list
admits at most 512 entries. All earlier entity/stat/FX/costume tests also pass.

Each power envelope/workspace is 1,114,392 bytes on the qualified 64-bit ABI;
parsing allocates no heap and retains no input pointers. Caller-owned objects
must remain off stack, and aggregate retained event/old generation budgets must
be enforced by future full transaction integration. No normal transport size
policy is changed by standalone large-fixture readers.

Sanitizers cover new native code/tests. Original trusted source functions run
at `-O0` outside sanitizers; LeakSanitizer remains disabled under the existing
sandbox process-map limitation. Independent code review and Android ARM64,
emulator, Thor and authentic server execution require separate evidence.
`full_update_accepted` and `render_spawn` remain false. Accepted APKs, gameplay
modules, profiles, assets, accounts and characters are unchanged.

The additive C++ linkage follow-up wraps the public costume header in
`extern "C"` for JNI/C++ callers. `cpp-link.json` records a real C++ executable
linked against separately C-compiled parser/reader objects and invoked through
every public costume/power API. `check_cpp_link.py` verifies that current C
preprocessing is byte-identical to the qualified base parser/header, then tests
C++ linkage. The copied base header is bound by `host.json`; no historical Git
object or full checkout is required to reproduce this comparison. The source
qualification above remains bound to its original exact header bytes, while
the companion receipt binds the guard and C++ smoke test.
