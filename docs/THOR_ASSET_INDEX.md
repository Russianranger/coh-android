# Thor asset index assessment

Assessed 2026-09-24. The device index locates candidates for the previously
missing animation tracks and all seven startup texture names. The next step is
to inspect three targeted base archives; no repeat index run is needed.

## Input and limits

The uploaded `coh-asset-index.json` is preserved byte-for-byte as
[thor-asset-index.json](thor-asset-index.json). Its SHA-256 is:

```text
8748d312ed2889e7e28f00ab1a3fa3a83b8c4a4d67f2b8514dc78da53bb77700
```

The report lists **95 archives**: 73 under `piggs/` and 22 under `i26/`, with
**no reported indexing errors**. It contains **96,379 archive-table entries**
across 5,710,198,235 reported archive bytes. Entries are not deduplicated across
archives. Archive counts, extension totals, animation counts and the list of
archives with animations are internally consistent.

Its status is `index_only_not_integrity_verified`. Every archive has
`integrity_checked: false` and `payloads_read: false`. Filename-table success
does not establish payload integrity, source-format compatibility, dependency
completeness or runtime usability. The earlier payload-verified total remains
22 archives; see [base asset coverage](BASE_ASSET_COVERAGE.md).

## Next uploads

Upload these files from the Thor directory:

```text
/storage/emulated/0/Download/cityofheroes/piggs/
```

| Archive | Exact bytes | Size | Indexed contents relevant to startup |
| --- | ---: | ---: | --- |
| `stage1a.pigg` | 61,306,611 | 58.5 MiB | 5,878 `.anim` entries; the MALE/THUMBSUP fallback is flagged present |
| `stage1b.pigg` | 144,033,704 | 137.4 MiB | 7,033 `.texture` entries, including four startup texture names |
| `stage1f.pigg` | 124,587,057 | 118.8 MiB | 1,903 `.texture` entries, including the remaining three startup texture names |

Together these are 329,927,372 bytes (314.6 MiB). Start with `stage1a.pigg`,
then upload `stage1b.pigg` and `stage1f.pigg`. No additional font archive is
needed for the current startup-font check.

### Located startup texture paths

| Archive | Path recorded in its filename table |
| --- | --- |
| `stage1b.pigg` | `texture_library/WORLD/Filler/black.texture` |
| `stage1b.pigg` | `texture_library/WORLD/Filler/grey.texture` |
| `stage1b.pigg` | `texture_library/WORLD/Filler/white.texture` |
| `stage1b.pigg` | `texture_library/WORLD/World_fx/PORTAL/invisible.texture` |
| `stage1f.pigg` | `texture_library/btest/buildingLightPattern.texture` |
| `stage1f.pigg` | `texture_library/btest/dummy_bump.texture` |
| `stage1f.pigg` | `texture_library/static_cubemaps/dummy_dynamic/dummy_dynamic_cubemap_face0.texture` |

These seven names cover the startup defaults identified in the pinned source.
They do not establish full UI, world, costume or character texture coverage.
Preserve recorded path case and check the loader's case handling during
Linux/Android integration.

## Keep the custom patch separate

The only other archive reporting `.anim` entries is `i26/geobin.pigg`:
158,275,451 bytes (151.0 MiB), with 5,896 animations, 2,268 geometry entries
and 25 compiled bins. It also flags the MALE/THUMBSUP fallback as present.
It is an optional later comparison, not a required next upload.

The user identified `i26/` as a custom patch directory. Its name does not prove
the client's issue/version. The difference between animation counts does not
prove 18 unique added animations: the index lacks complete animation path lists
and payload hashes. Compare full inventories and bytes before selecting any
custom overrides. Keep the accepted Issue 24/Volume 2 source baseline unchanged.

## Validation after upload

1. Inspect archive bounds, decompression, entry sizes and checksums. Record
   complete inventories and archive hashes without running supplied executables.
2. Check animation and texture formats against the pinned source, including
   fallback animation loading and the seven startup defaults.
3. Stage verified base assets separately from custom variants. Regenerate
   matching compiled caches and database templates from the chosen baseline;
   custom Parse7 caches remain incompatible with the source's Parse6 loader.
4. Validate a matching reference runtime through character creation, map entry,
   saving and reloading before Android runtime integration.

The PostgreSQL controlled persistence milestone is unchanged; see the
[current handoff](HANDOFF.md#current-database-work). This index assessment does
not claim a working MapServer gameplay session, client startup or Android APK.
