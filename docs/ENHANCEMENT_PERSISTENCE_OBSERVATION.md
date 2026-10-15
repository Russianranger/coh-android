# Enhancement persistence observation

The published .32 save/reopen proof selects `ents`, `ents2`, `powers` and
`costumeparts`. It does not select the enhancement rows in `boosts`.
`powers.powernumboostsbought` describes purchased slots; it does not prove the
enhancement in each slot. The supplied .31 reports therefore support ordinary
character saves and user-observed enhancement persistence, with no independent
enhancement SQL comparison. This remains a physical .32 acceptance gate.

`tools/android/interactive/analyze_enhancement_persistence.py` adds an offline
diagnostic contract without changing the app, database or shipping save gates.
It checks the existing accepted generated `ents.template` archive and all 34
Boosts fields, including implicit row keys, against the native persistence
descriptor. It prints a read-only PostgreSQL query; it never executes SQL.

```sh
python3 tools/android/interactive/analyze_enhancement_persistence.py --query
```

For a future qualified diagnostic capture, retain the existing ordinary
logout/native/committed-save proof and capture the query output after that save.
Reopen the same character, inspect inventory and slotted enhancements, perform
another ordinary verified save, and capture a second output. Run the query in
the matching owned PostgreSQL profile with `psql -qAt` so the result is one JSON
object. The query uses one repeatable-read, read-only transaction and includes
the exact character identity, LoginCount, complete Boosts payload, Powers
relations and matching attribute names. No migration, repair or SQL mutation
is needed. The .32 launcher does not yet expose this extra capture; regular
.32 reports alone cannot supply these missing rows.

```sh
python3 tools/android/interactive/analyze_enhancement_persistence.py \
  --before saved-enhancements.json --after reopened-enhancements.json
```

Native `character_db.c` serializes inventory enhancements with `PowerID=-1`
and `Idx` equal to the inventory slot. Slotted enhancements reference the
serialized `Powers.PowerID` and use `Idx` for the power slot. The older comment
in `containerloadsave.c` describing `Idx=-1` for inventory is inconsistent with
the actual producer/consumer and is not used. Serialized PowerID/subid can
change when rows are repacked, so the comparison resolves a slotted power to
its stable UniqueID, build and attribute names. It compares all remaining
Boosts payload fields and rejects incomplete rows, ambiguous relations,
duplicate locations, foreign identities and nonconsecutive LoginCounts.

`observed_equal` means the separately supplied snapshots have equal semantic
enhancement rows. Both empty arrays remain explicitly empty observations.
`observed_changed` means the observed enhancement contents or placement differ.
Old snapshots without boosts/name mappings return `missing_evidence`.
All outputs keep `session_attribution_verified`, `committed_sql_verified`,
`enhancement_persistence_verified`, `observed_snapshot_schema_verified` and
`physical_device_verified` false. An external file's claimed session ID is
not authentication. Source/schema validation and semantic equality cannot
establish real SQL commits, successful Android gameplay or enhancement effects.
These require the current owned device session and ordinary save/reopen evidence.

This tool adds no runtime overhead and requires no APK, native binary or Assets
release. Its query contract is validated from accepted schema bytes; executing
the query against a live device profile remains a separate diagnostic gate.
