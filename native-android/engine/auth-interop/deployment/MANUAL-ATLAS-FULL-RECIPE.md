The complete accepted manual Atlas source lineage is now recoverable in an isolated 6,007-file source copy. This is a static source and build-input qualification. No new compiler, DbServer executable, PostgreSQL transaction, AuthServer connection or shipping runtime replacement has been qualified.

The source recipe starts with the exact 5,995-file `upstream/ouroboros` tree pinned by the accepted base PG/Wine package. It applies these layers in order, verifying the original, patched and added bytes at each step:

| Layer | Accepted source input |
| --- | --- |
| PostgreSQL persistence | `patches/postgresql/0001-dbserver-postgresql.patch` plus two overlay files |
| Wine ODBC/readiness | `patches/wine-dbserver/0001-wine-odbc.patch` plus eight overlay files |
| Manual Atlas startup | `patches/startup-dbserver/0001-manual-atlas-launcher-wait.patch` plus two overlay files |
| Cancelled-child save repair | `patches/startup-bundle/0001-pg-cancelled-child-insert.patch` |
| Empty-row/thread witness repair | `patches/levelup-ui-repair/0001-pg-empty-row-witness.patch` |

The complete accepted manual map differs from the corrected map at exactly `Common/ClientLogin/clientcommLogin.c`, using the existing source-qualified checksum correction. Version/auth-cookie handling, persistence merger/FIFO/thread support and all other first-party bytes remain unchanged. The manual wait mode still requires fake authentication and an absent AuthServer. It cannot be used for an authenticated experiment. No native checksum alias or synthetic production version is introduced.

The exact manual PE is `ea1d43d7a1ed61559376563bd8bad68987fbf47a4ec41f0d6fe8fe16cfe933ba`, not the earlier base normal `535bfd6df77ce09bc3d1048accd95d7910552f8861c3a9c4e356d522786d585c`. The separately compiled MSSQL checksum PE is a different profile and has no runtime replacement permit.

The recovery receipt identifies the single retained historical donor: workflow `38285895633`, artifact `11764118240`. Its original 0.13.33 APK contains the unchanged startup manifest and PE; the committed 0.13.34 publication record identifies that APK as its donor. No APK was installed or executed. The manifest, exact donor/archive hashes, full original/manual/candidate maps and source qualification records are retained under `evidence/manual-atlas-full-recipe-20261017/`.

Run the preparer from a pinned repository checkout with `core.autocrlf=false`, using new external destination and receipt paths:

```sh
python native-android/engine/auth-interop/deployment/manual_atlas_full_recipe.py --source-root REPOSITORY --output NEW_EXTERNAL_SOURCE --receipt NEW_RECEIPT.json
python -m unittest discover -s native-android/engine/auth-interop/deployment -p test_manual_atlas_full_recipe.py -v
```

`build_plan(source, build, patch_exe, candidate_map)` first verifies all 6,007 bytes against the sealed map, then checks the five literal CMake source/header lists (504 entries). It records all in-tree CMake/build-tool resources and the three exact external CPM revisions and source patches. Those external repositories are not materialized by this recipe. A future build requires CMake with the VS18 generator, MSVC x86 and Windows SDK/resource compiler, Git/patch, and network access or independently checked exact CPM cache inputs. StructParser generates target-owned sidecars and SparseHash generates a build-local configuration. Precise-floating-point execution, StructParser and LogServer alias staging remain required by the original CMake dependencies.

The proposed configure command explicitly enables only registered Common and DbServer projects and disables the other 41 registered projects, MapServer, BeaconServer, fixture mode and test/tool groups. Root CMake still configures its unconditional UtilitiesLib, StructParser, CrashRpt and pig targets. This narrows configuration dependencies without editing accepted source. It is a proposed new build configuration; it does not claim the historical cache or binary is reproduced. The only build command targets DbServer/OptDebug/Win32 with two workers.

Before any execution, a coordinator-reviewed compile-only driver must seal the complete recipe and dependencies, run the exact plan in a fresh disposable source/build copy, capture full compiler/configuration/source-generation receipts, inspect PE imports and emitted runtime DLLs, and independently admit the resulting binary. Actual PostgreSQL persistence, normal version/checksum acceptance and authenticated DB handoff require later independent runtime qualification. Historical runtime DLL records are evidence of the old product, not admission of newly generated dependencies.
