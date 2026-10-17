# Exact initial character dictionary dependencies

This audit does not admit a runtime generation or apply semantic character state.
The raw transaction composes existing wire parsers and retains unknown raw IDs.

* `Game/src/entity/character_net_client.c::character_Receive` receives class and
  origin **names**, resolves normal classes/origins first, then villain tables.
  `Common/entity/classes.c::classes_GetPtrFromName` and
  `Common/entity/origins.c::origins_GetPtrFromName` search the original earray
  backwards with `stricmp`. Preserve original ordering and duplicate semantics;
  do not sort, densely repack or replace names with offline fixture indices.
* `Common/entity/character_net.c::basepower_Receive` reads an Auto CRC.
  `Common/entity/powers.c::powerdict_GetBasePowerByCRCEx` resolves the integer
  dictionary; `powerdict_GetCRCOfBasePower` is original
  `Crc32cLowerStringHash(0,pchFullName)`. A fixture CRC cannot invent a BasePower.
  `powerdict_CreateDictHashes` preserves original category/set/power arrays and
  rejects duplicate/nonzero-invalid CRCs; names alone are insufficient to apply
  builds, powers, boosts, FX, inventory or combat state.
* `Common/entity/load_def.c::load_CharacterClasses` invokes `classes_Repack` and
  `classes_Finalize` after parsing; origins have no corresponding callbacks.
  Both loads set `PARSER_SERVERONLY` on SERVER. CLIENT cache bytes therefore do
  not by themselves certify the active MapServer cache branch or dictionary.
* `Common/entity/powers_load.c::load_PowerDictionary` tries the shared dictionary
  first. Otherwise it reads categories, powersets and powers in that order,
  including their exact preprocess callbacks and source defines, then creates
  original dictionary hashes/back/forward pointers and finalizes unshared data.
  SERVER uses `PARSER_SERVERONLY`; replacement powers and schema/define/profile
  effects must be bound. No callback or build-order skip is admitted here.

The exact retained CLIENT cache manifest has recoverable raw bytes for:

| Member | Bytes | SHA256 |
| --- | ---: | --- |
| `data/bin/origins.bin` | 504 | `ec13f45bc83815bb6d2c440380360589217919c65cc637f94959e53c5410e033` |
| `data/bin/villain_origins.bin` | 124 | `2432c9d535ef7021d2c86ab9ea2e7049148304721e88163af3a3a2611bbeba3a` |
| `data/bin/classes.bin` | 1,219,292 | `91af1ca0b304d77e56f356d54e1a880309b910c40f1729672cc0af1b83dd6733` |
| `data/bin/villain_classes.bin` | 4,228,088 | `bc0789f03941d845f9574f6df4dd1ad953ad35328a3d7323c07d02d92fdbd523` |
| `data/bin/powercats.bin` | 239,304 | `67b46915b9bf4440de8f5cf8bf7dd4a9047daee7dc5cb96f2c2be3999f8fc5e7` |
| `data/bin/powersets.bin` | 3,179,276 | `afadc5f3ae6fc9c9c413924cec75bb911ff5cd4ce37388c6737cdb5786d9d547` |
| `data/bin/powers.bin` | 62,047,164 | `25641e747c60e066016fcc7d2ce0a2e72f57d7d3953f7b1ff4b18b69e2d49c6d` |

These manifest identities are inputs to the next offline original-schema decoder
and constructor qualification, not current parsed or authoritative dictionaries.
The full powers tree cannot be eagerly retained alongside world metadata under
the existing Android working-set budget. An offline compact export or strictly
phased ownership is required. Before runtime admission, bind actual source
ParseTableCRC/mode, SERVER/CLIENT path, exact cache/shared branch, source defines,
callbacks, original array order and matching server generation independently.
No new server capture or workflow is required merely to inspect retained bytes.

Costume full-slot offline candidate construction is already separately qualified;
its exact holes/palette/body counts do not establish these class/origin/power
semantics or current runtime generation. Inventory/concept/reward and ordered
full-attribute dictionaries remain separate dependencies. Active invention also
has the concrete original sender/consumer mismatch documented in its module.
