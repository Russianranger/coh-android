# Source-sorted power gameplay IDs

Original `powerdict_FinalizeDict` sorts category pointers with case-sensitive
`strcmp` before assigning BasePowerID(category,set,power). These are sorted
category positions and local set/power positions, never raw cache or global
allocated row ordinals. The bounded `coh_power_ids_prepare` projects that exact
assignment order from a complete compact forward join. Repeated references
retain source last-write IDs; subsequent reverse `SetBackPointers` retain source
first-parent precedence in the sorted hierarchy. Unreached raw powers have
assigned=false and cannot gain a fabricated valid zero ID.

This immutable view borrows the entire join and all transitive dictionaries,
set input and power provider/file leases. Its standalone8MiB budget charges all
those owners, output/workspace, reserved provider scratch and16KiB stack. All
work, complete key scans/comparisons and validation/assignment passes fit an
explicit64MiB work cap. No file callback, heap allocation, caller reader mutation
or acknowledgment occurs. All failures preserve output. `coh_power_ids_find`
resolves an exact category/set/power triple back to the source power row.

The qualifier executes whole original FinalizeDict, category comparator,
basepower_SetID, FX finalization leaf, ResetStats and reverse SetBackPointers on
explicit compact source fixture storage. Diminishing returns, synthetic normal/custom FX values
and disabled development-art override are fixture interfaces; this does not
qualify real FX/resources, dimensional-return data or complete FinalizePower.
Existing original raw record roundtrips and complete native bounded imports are
reused. An independent model compares source sort order, every assigned ID,
parent precedence and all reverse triple lookups on authentic and small inputs.

The loader audit pins the complete original ParserLoadFiles function: successful
binary cache admission returns before its preprocessing callback. Thus original
DuplicateMissingPowers belongs to the text/rebuild callback path; it is not an
unconditional prerequisite for an observed valid cache hit. The actual live
SERVERONLY/CLIENT/shared/cache branch remains unobserved. Historical cache
integrity and projected IDs establish no current server generation, complete
dictionary finalization, semantic character, actor authority or READY/ACK.

In the exact historical input, 185 of186 category positions change during source
sorting: raw row0 `Base_Defenses` becomes sorted position7; sorted position0 is
`5thColumn`, originally raw58. All20,241 authentic power IDs and reverse lookups
are compared. Synthetic repeated/shared references separately prove the
last-ID/first-parent distinction. The immutable view and workspace each retain
689,184B; caller-retained live owners are never omitted from the standalone cap.
