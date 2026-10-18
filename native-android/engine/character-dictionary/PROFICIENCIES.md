# Complete historical Proficiency dictionary owner

`coh_proficiencies_read` imports the complete retained `Proficiencies.bin` and
`ProficiencyIds.bin` Parse6 records. It copies the five strings and two signed
words of each definition and every signed ID/name row, preserving input order.
The historical schema CRC words match the original ParseTableCRC traversal,
including both complete static define lists. The focused source oracle executes
that traversal with the established zlib/Crypto++ digest-byte adapter.

`load_ProficiencyDictionary` loads the ID dictionary before definitions.
`attribfiledict_FinalProcess` visits ID rows forward: nonpositive IDs do not
enter either map; first case-insensitive name wins; maximum positive ID includes
rows whose duplicate insertion fails. `genericinvdict_CreateHashes` visits
all definitions forward. The first case-insensitive name enters its name map;
a later duplicate definition receives no ID. A new name uses the first ID-map
match or increments from maximum ID plus one. Every active definition then
writes its reverse slot, so different names sharing an ID leave the last
source definition in that slot. This owner preserves those distinct name and
reverse-index results. The two finalizer functions execute in the focused
oracle with bounded host earray and default ASCII case-insensitive map storage
adapters; the engine stash hash/allocation implementation is pinned and read,
not executed. Both shared and nonshared source branches have identical logical
slot assignment; only the nonshared branch executes here.

`id_find` and `id_name` expose the historical ID-map first-name and
first-numeric-ID rows separately; these may name removed definitions.
`find` returns the first definition name winner. `by_id` validates an actual retained
active definition at that ID; absent definitions are not reconstructed from
an ID-map name. `join` requires both lookups to identify the same row and
therefore refuses a different-name ID collision. Zero and hole IDs return
NOT_FOUND. The original Proficiency getter dereferences a slot after its
range check; this owner refuses holes safely. Empty/non-ASCII names are an
explicit unsupported domain rather than a claim about null stash keys or the
original CRT locale. A file with no positive ID row refuses because the
original ID finalizer returns false. Origins and rarities remain opaque signed
persisted words, without enum or gameplay validation.

Limits are native policy: 64 KiB per full file, 512 definitions and ID rows,
4096 reverse slots, 64 KiB aggregate copied text, each field shorter than260
bytes, 16 MiB read/comparison/poll work, and 512 KiB charged aggregate memory.
The aggregate includes both inputs, expected hashes, provider/control structs,
declared callback contexts/scratch, output and full candidate workspace,
retained memory and8 KiB native stack reserve. No allocation or borrowed input
pointer is retained. These bounds are not an RSS/Android fit claim. All known
spans are checked for disjointness before any callback; source/provider leases
are immutable through final cancellation and single output commit. The copied
owner alone must remain live for later lookups.

The focused checker requires the exact retained27071659-byte ZIP and both
exact members, authentic Git source closure before importing helpers, original
whole binary record readers/writers, and the whole two finalizers/getters. It
compares both authentic file roundtrips and synthetic duplicate/fallback/hole
projections, malformed/truncated/digest/cancel/alias/budget refusals. Source
TokenStore/earray/map allocation/layout adapters are explicit. Original engine
stash execution, original shared-memory loader/reload/server selection and
32-bit ABI are outside this host proof. ASan memory checks and UBSan run; LeakSanitizer is disabled because the host
restricts its process inspection. No previous dictionary qualifier runs.

Run only the new qualifier:

```
python3 native-android/engine/character-dictionary/check_proficiencies.py \
  --actual-caches-zip /path/to/client-caches.zip --sanitize --output /new/proficiencies.json.gz
```

This closes one typed reward dictionary dependency of the complete initial
character transaction. It does not establish current cache generation, full
power/boost ownership, other reward type dictionaries, current costume/world
joins, complete initial packet acceptance, actor publication or ACK authority.
