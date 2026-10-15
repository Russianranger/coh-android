# Bounded source map selection

Gate 23 connects source map/group semantics to the indexed asset loader and
generic renderer through `coh_world_stream.h`. The integrated client uses this
module to select original instances by view radius while preserving the source
hierarchy, transforms and inherited tint. This is a bounded Atlas station subset,
not full Atlas loading or a general complete map importer.

`tools/map_fixture/prepare.py` reads the pinned original Atlas geometry layer and
RootMod definitions. It retains all 25 hierarchy nodes needed for the three
explicitly admitted model endpoints: station interior floor, two-wide bench and
four-wide bench. Unadmitted map leaves are reported rather than silently loaded
or replaced. Eight genuine raw GEO/texture payloads are packaged without format
conversion in `COHWB001`, an app envelope, **not an original PIGG archive**.
`COHMAP01` stores the bounded semantic index. Source-authentic material rows keep
the original aliases/families, ScaleST0/1, culling and explicit grey fallback.
The client uses controlled neutral ambient/no-fog rendering; original light
grids, ambient zones and broader environment behavior remain future work.
Source cubemap texture swaps remain diagnostic data in the selected low-profile
rendering profile; no cubemap texture sample is claimed.

The source station region contains one floor, four two-wide and six four-wide
bench instances: eleven instances, 22 material partitions and six textures.
Radius 24 selects six instances at the reset spawn; radius 96 selects eleven.
Selection counts vary with actor position. The source endpoint bounds retain floor
support within either runtime query throughout the admitted support region
(825 host samples); each selection bounds admitted bytes before acquisition.
Each unique raw dependency is acquired once per selection. A failed selection
leaves the old selection and its pins unchanged; cache warming/eviction may still
occur. Release selections before destroying the map or loader. Bundle bytes must
stay immutable and alive through loader destruction because read callbacks
borrow those packaged spans. All operations use one owner thread and perform no
hidden filesystem/network/GL work.

The expanded collision preparation uses these same visual source placements for
2,304 authored triangles. The accepted source WALK implementation remains
unchanged. All ten bench contacts are exercised, including steep four-wide
surfaces that can produce source WALK climbing/slope behavior. This is not a
claim that every bench behaves as a flat vertical wall. The initial two-wide
blocking/sliding regression remains valid.

`qualification.json` records 14,842 map assertions, 1,688 known negative cases,
4,000 metadata mutations, 825 support samples, 28 cancellation cutpoints and
500 selection/release cycles. All 300 source hierarchy matrix components match
the original routines byte-for-byte. Visual/collision parity covers 20,736
binary32 position components with zero differences. Expanded WALK adds 3,082
assertions and source contact coverage for all ten benches. ASan/UBSan and strict
ARM64 compilation pass; no LSan result is claimed in this execution environment.
These are host/source/build results. Integrated Android execution and physical
Thor acceptance must be recorded independently by the client coordinator.

Reproduce the scoped checks using `engine/world/check.py` and the pinned full
source checkout/raw corpus described by `tools/map_fixture/prepare.py --help`.
Existing accepted fixtures, earlier physical reports and the conventional
launcher/client are untouched. Roll back additively after checking the
integrated Session Client/bridge dependents; never reset shared branch history
or erase accepted evidence.
