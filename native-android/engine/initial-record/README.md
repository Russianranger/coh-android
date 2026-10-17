This module stages complete initial full-create records for the selected player,
other players and NPCs, and composes a bounded complete entity-list fragment.
It consumes every record in source order through the final teammate body before
accepting the canonical list sentinel. It preserves signed negative index deltas
and tests the sentinel before dereferencing its synthetic index. Full-create
mode, position, quaternion, movement and rare flags are required; later update
and interpolated profiles refuse. The existing selected-only public API remains
strict and reuses the same private grammar kernel.

Actual decoded self controls costume/power profiles, target clear application,
inventory-size presence and architect/taskforce presence. No other entity is
skipped. Duplicate slots, source entity generations, player DBIDs or selected
self, a nonself selected DBID alias, and missing selected self all refuse. The
existing local 256-record limit is retained; it is not claimed as the original
server's complete visibility bound. Larger input fails transactionally.

Each compact entry is 80 bytes on the qualified host ABI and retains raw
identity/pose plus its exact packet span. `begin_bit` includes the list delta;
the full selected report begins after its delta. Original row order and the
preceding entry index permit replay without scanning. A single 54,248-byte
workspace includes the candidate compact table and reusable record workspaces;
large appearance/power/SG/buff PODs remain sequential scratch loans. The public
entry array, result and reader change only after all records and uniqueness
checks pass. Concurrent publication still belongs to the enclosing owner.

The named 8 MiB aggregate charges complete supplied output capacity, workspace,
input, immutable dictionary, provider/context, retained state and 96 KiB native
stack. Child SG/buff stages retain their stricter 4 MiB aggregate caps. A loan
adapter refuses aliases against every enclosing span, including output tables
that the child decoder alone cannot see. Provider preallocation receives the
remaining permitted charge before allocating. Exact allowance checks verify
that parent/child spans and input are charged once. External allocator stack,
resident libraries and whole-process memory are outside this owned budget.

`check.py --sanitize --output NEW.json.gz --fixtures-output NEW.bin` executes
720 original outer-control record profiles and 58 list cases, using separately
qualified actual original child writers. It exercises other players, owned/NPC/
mission costume bodies, no-character and NetFX-only records, selected-last and
negative deltas, MAX-index sentinel, duplicate identities, later-record failures,
capacity limits, trailer preservation and allocation/alias cleanup. Child spans
are checked at all bit offsets before relocation. Whole original source control
and child functions execute with explicit independent fixture objects; the
complete original engine, visibility builder and shared object graph do not.
Original trusted host producers remain unsanitized; new native code runs release,
ASan and UBSan with leak detection disabled. C++ header/link compatibility is
also checked. Frozen selected component and original outer regressions are run
when the shared kernel changes.

These are raw wire views. Supplied context numbers/handles do not authenticate
an actual DB or Map owner. The exact packet and admitted dictionary/source
leases must remain immutable while views are used. Authentic dictionary/cache
generation, class/origin/power/animation/resource resolution, control/deletes,
character/global suffix, normal viewed-entity identity and appended command
framing must compose in one enclosing owner before any authoritative actor or
application ACK. No READY, RECEIVED_CHARACTER or full-update ACK is enabled.
No game APK, emulator/Thor execution or live server acceptance is claimed here.
