# Fresh power empty boost slots

`coh_initial_power_slots_create` constructs the boost-slot container for a NEW
power, following original `power_Create`'s empty `ppBoosts`, the initial
`character_ReceivePowers` purchased-slot arithmetic, then `power_LevelFinalize`.
The finalizer adds purchased slots and `CountForLevel(age)`, caps that signed
target at BasePower.MaxBoosts, and grows only when the actual persisted
BasePower.BoostsAllowed array is nonempty. Every constructed slot is empty.
Native slot markers use `UINT32_MAX`, not a fabricated Boost object or pointer.

The existing complete selected-record parser now retains field80 BoostsAllowed
COUNT alongside field93 MaxBoosts. It still validates every array word, field,
nested record and exact end; there is no second provider pass or eager graph.
The constructor invokes that canonical parser/scalar computation once, instead
of accepting a caller-populated prior projection or prior-slot count. The
positive slot bound4096 follows the coupled ReceivePowers arithmetic, rather
than an independently supplied purchased count. Write F=free<=4096, W=wire<=2048
and M=MaxBoosts. If M>=F, purchased=max(W-F,0), so the uncapped target is
max(W,F)<=4096. If 0<=M<F, the final cap gives target<=M<F. Negative maxima
retain their source negative target
and produce no slots. Signed addition overflow refuses before the cap and the
BoostsAllowed condition, matching the original operation order without UB.

CLIENT ReceivePowers first destroys the received build sets and recreates empty
shared sets; CLIENT BuyPowerSet does not execute SERVER-only free-power grants.
First-seen powers use this fresh empty-container branch. Regular repeated powers
reuse their owned instance; temporary powers always create a new instance. This
constructor does not select those branches or pretend that a reused instance
has an empty prior array. The complete future character owner must own source
order, unique IDs, set/shared ownership, repeated-power state and boost objects.

Output/workspace are fixed size. All transitive stream/schedules/context/scratch,
output/workspace/retained and both outer/child16KiB stack reserves are admitted
before callbacks under the literal4MiB module cap. The nested admission charges
the outer live storage while avoiding duplicate charges for its two subobjects.
Provider reads are at most4096B and exactly one pass over the selected record.
Output commits only after construction and final cancellation; every failure
preserves it. Scratch may change. Borrowed stream/schedules/provider/file leases
remain immutable and live until the constructor output retires.

On the qualified64-bit host, the constructor owner is16,464B and workspace
82,000B. The extended scalar owner is64B (previously56B). The new receipt binds
that ABI extension and all transitive source/header inputs.

Qualification executes whole unchanged original power_Create, character_GetLevel,
power_LevelFinalize and power_AddBoostSlot on explicit host Power/Character,
clock, memory-pool and earray fixtures. It compares authentic historical records
against an independent descriptor projection, then tests source-written empty/
nonempty/signed BoostsAllowed and MaxBoosts variants, 4096-slot growth, empty and
ordered-prefix schedules, signed-overflow order, budgets/aliases, I/O and every
cancellation point. It does not execute the whole character receiver, original
Win32 ABI, global registry, source runtime allocator or current loader branch.

```sh
python native-android/engine/character-dictionary/check_initial_power_slots.py --cache-zip /path/to/client-caches.zip --sanitize --output /tmp/initial-power-slots.json.gz
```

This is historical fresh-slot construction only. Full power initialization,
reused-instance updates, boost object application, character creation and
transaction ownership remain open. Current-generation, actor and ACK authority
remain refused. The previous boost-slot receipt remains bound to its previous
source commit; this scalar-owner extension is qualified by the new receipt.
