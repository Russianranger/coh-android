# Exact category cache and compact raw category owner

Historical powercats.bin (239,304 bytes) SHA256
67b46915b9bf4440de8f5cf8bf7dd4a9047daee7dc5cb96f2c2be3999f8fc5e7
comes from the exact retained 27,071,659-byte donor ZIP. Whole original category
binary schemas/readers/writers roundtrip it; original ParseTableCRC 0x59248ecb
matches. The 186 categories preserve 6,527 ordered set-name references and zero
persisted pointer-index rows. Source pointer-array serialization is explicitly
bound to donor 32-bit packed indices, never interpreted as host pointers.

The original powerdict_CreateDictHashes and category GetByName functions execute
with genuine parsed category rows, original constructor/find/add/hash/resize and
source category insertion order. Loading only ParsePowerCatDictionary genuinely
leaves dictionary-level sets and powers empty: those branches are structurally
present but no set/power objects or CRCs are fabricated. Their absent callbacks
assert if invoked. This is only category-branch qualification. Original hash is
host-unsanitized with 32-bit ub4 binding, not a full original Win32 runtime.

The native owner copies all category fields, every set reference and raw packed
index, preserving source order. Duplicate category names refuse the complete
import, matching original dictionary constructor refusal. Unknown unique names
and unresolved set-name references remain raw; no references are removed. The
qualified name profile requires nonempty ASCII keys and original case-insensitive
lookup. Empty/non-ASCII keys refuse conservatively. Exact SHA/schema does not
establish current cache/server generation or complete power dictionary ownership.

Input/output/workspace/expected SHA/provider context/scratch/retained bytes are
charged before callback under 1 MiB with an 8 KiB native reserve. No allocations or
partial output commit; source input may retire after successful copied import.
Native release/ASan/UBSan and C++ tests compare every copied field/reference/index
against independent decoding and source lookup ordinals, with truncation,
mutation, valid-digest cap, exact budget, provider cancellation and alias controls.
Source helpers are admitted/source-compiled before execution with stale-PYC and
changed-source controls. No 62 MB power cache, runtime actor, READY or ACK.

The owner occupies 374,856 bytes; its workspace occupies the same amount and
may retire after import. The authentic 239,304-byte input fits with both owners,
digest context and reserved native stack under the 1 MiB aggregate cap.
