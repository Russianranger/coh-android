# Historical initial-power boost slots

`coh_schedules_read` implements the complete original `ParseSchedules` and
`ParseSchedule` binary grammar. It copies all seven ordered signed-int arrays,
including duplicates, negative thresholds and unsorted entries. The original
`CountForLevel` counts a prefix after clamping a negative level to zero; sorting
or counting every qualifying entry changes its behavior.

`coh_power_boost_slots_prepare` closes the corresponding arithmetic dependency
in `character_ReceivePowers`: count free slots for character level minus power
purchase level, cap by the selected persisted `BasePower.iMaxBoosts`, and clamp
received slots minus allowed free slots to zero. It reads the entire selected
BasePower record in at most 4 KiB requests, validates every field and nested
record using the existing complete descriptor, and matches both stored and
computed fullname CRC to its borrowed stream dictionary entry. It copies no
power graph. The caller must resolve the selected row with the source-qualified
gameplay IDs; raw category/global power rows are not wire gameplay IDs.

The importer copies schedule data, so its input may retire after success. The
projection borrows its schedules and stream owners and the stream's immutable
provider, context and file lease; all must outlive it. Output is unchanged on
every syntax, identity, I/O, cancellation, alias, budget or signed-overflow
refusal. Scratch may change. Provider callbacks remain synchronous and bounded
by their declared context and scratch reservation. All owners, callback spans,
workspace, retained memory and stack reserves are charged before callbacks.
The schedule cap is 256 KiB, the scalar projection cap is 4 MiB; these are
literal local admission bounds, not a global application partition.

The qualified 64-bit host layout uses 16,496 bytes for each schedules owner and
workspace, 56 bytes for the scalar projection and 65,536 bytes for its record
workspace. The complete borrowed stream dictionary and provider reservations
are additional and charged; the file remains streamed. These modules do not
introduce a global combined-owner memory allocation.

This is a historical state projection. Original `powerdict_FixPowerSetErrors`
can set temporary powers' MaxBoosts to zero before writing bins; this module
uses the persisted scalar and does not replay preprocessing on an unproven
loader branch. The retained cache is not a current server-generation witness.
No complete `character_ReceivePowers`, `power_LevelFinalize`, character creation,
boost object application, actor publication, wire-profile admission or ACK is
established. Both runtime-generation and actor-authority flags remain false.

Qualification compares all retained BasePower MaxBoosts values with the whole
original binary reader and a separate descriptor decoder. Actual schedules
round-trip through the whole original table reader/writer and reproduce the
original schema CRC. The unchanged original `CountForLevel` and exact four-line
ReceivePowers scalar slice execute on explicit host fixtures, with unsafe
original signed overflow excluded and refused by native code. The qualifier
also covers empty arrays, prefix/duplicate/unsorted/signed thresholds, aggregate
4096-word admission, six source-written MaxBoosts variants, truncation, exact
budgets, callback failures, cancellation and immutable-owner mutations. Host
release, ASan and UBSan plus C++ linkage and bounded-stack checks are recorded;
the original oracle uses explicit host storage adapters and is unsanitized.

Run from the repository root:

```sh
python native-android/engine/character-dictionary/check_power_boost_slots.py --cache-zip /path/to/client-caches.zip --sanitize --output /tmp/power-boost-slots.json.gz
```

No common build/workflow files are changed. The owner needs these new sources
plus existing `coh_power_stream.c`. No lifecycle owner should publish a player
until a current dictionary/packet generation and the complete initial character
transaction are independently established.
