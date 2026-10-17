# Accepted PostgreSQL/Wine lineage and corrected-checksum source recipe

The separately built MSSQL checksum candidate from run39000395572 is not a replacement for the accepted PostgreSQL/Wine runtime. Exact identities differ:

| Product | Bytes | SHA256 | Boundary |
| --- | ---: | --- | --- |
| Accepted PG/Wine normal DbServer, run36460867428 | 1,661,440 | `535bfd6df77ce09bc3d1048accd95d7910552f8861c3a9c4e356d522786d585c` | Win32 OptDebug, persistence fixture OFF; separate hosted/Thor persistence and startup evidence |
| Accepted PG/Wine persistence fixture | 1,674,240 | `77d4677904d967dfdeffa3c6b2609ae0620ccc28177655c6f5f975a7ec4c2212` | Fixture ON, controlled14-phase/21-group persistence suite; not a normal game binary |
| Later retained manual Atlas DbServer | 1,664,512 | `ea1d43d7a1ed61559376563bd8bad68987fbf47a4ec41f0d6fe8fe16cfe933ba` | Separate launcher-wait/save/read/thread layers; physical.13 and retained.31 evidence; current Combined payload must independently match |
| New standalone original MSSQL checksum candidate | 1,654,784 | `9dd91e456484c3fde1d9832163c2bbdad97d6a3f4db4db6a7773fddffe3319c3` | Compilation/header provenance only; no PostgreSQL/Wine overlays or runtime execution |

The accepted base PG/Wine package manifest is exactly SHA256 `95f62cc81b0743c13652e55aee01aed6871fc96d70a84b8dfd62fb8a0d9fe0d6`, repository `eed2ce1f5388195f65a07853919761a93657aca6`, imported source `0b75ade0c801735e10c5798f641948a45cc50488`, original tree `f634e21e230009fa8edc91d15429cd4da69eee8c`. PostgreSQL patch precedes Wine ODBC/dispatch/fixed-input/loopback source. Accepted Wine commit label is `b073859675060c9211fcbccfd90e4e87520dc2c2`. Exact patch, overlay and resulting source hashes remain in the accepted manifest and the new inventory receipt. This inventory reads committed qualification records; it does not freshly execute or rehash the historical PE bytes.

## Implemented reduced source composition

`pg_wine_checksum_recipe.py` reconstructs a **36-file reduced source closure**, not a buildable tree. It loads exact Git originals and the externally pinned accepted manifest, applies the exact PG patch then Wine patch, and verifies every accepted patched-file hash. Overlay LF/CRLF profiles are selected only when their complete bytes match the exact accepted digest. No arbitrary byte-profile substitution is admitted. It adds the previously source-qualified checksum verifier correction to `Common/ClientLogin/clientcommLogin.c`, then verifies that this is the sole additional changed path.

The complete PG-modified clientcomm source, SQL FIFO, container SQL, production merger, auth cookie consumer and actual version provider remain unchanged relative to that reconstructed base. The first original login version/protocol/checksum policy block is compared byte for byte after composition. Missing reference still fails in the candidate; no version skip, fake-auth relaxation, reference alias or generated native checksum is introduced. A valid matching recipe always leaves buildability, runtime admission and shipping replacement permission false.

Three host suites pass: exact accepted composition and one-path delta; critical FIFO/clientcomm/auth/version mutation and linked-file refusal; existing/repository destination and invalid patch refusal. Source outputs are made only in a new external directory. Failure leaves the caller-owned staging evidence; no original worktree, accepted runtime or profile is reset or cleaned. Temporary test directories are owned and scoped by those tests.

```sh
python3 native-android/engine/auth-interop/deployment/pg_wine_checksum_recipe.py --source-root . --output /tmp/coh-new-pg-wine-checksum-closure
python3 -m unittest discover -s native-android/engine/auth-interop/deployment -p test_pg_wine_checksum_recipe.py -v
```

This source recipe composes existing qualified inputs; it does not rerun accepted persistence tests, execute a compiler/server or transfer their runtime acceptance to a new binary. The existing full-checksum policy oracles remain valid for the identical candidate function and unchanged first caller block; actual binary negative cases remain unqualified.

## Preserve the later manual runtime separately

Later manual Atlas lineage adds `startup-dbserver` launcher-wait, `startup-bundle` cancelled-child INSERT handling, and `levelup-ui-repair` empty-row ordering/thread-name correction. These changes preserve source completion/rollback/save-ACK semantics and must not be silently removed when replacing that product. They are **not** composed by this base-only recipe. Its accepted ancestor must not be mislabelled as the current complete Combined runtime.

The manual launcher-wait function requires fake_auth=true, absent AuthServer, no queue/logserver/launcher, fixed inputs and loopback acknowledgements. `COH_WINE_DB_MANUAL_ATLAS=1` therefore cannot be used for a real-auth profile; leave its guard intact. A future authenticated experiment must follow ordinary owned launcher/startup readiness or separately qualify a new source-defined mode. Do not weaken that guard merely to reuse the offline manual path. The actual current startup manifest (retained ancestor SHA `949a15e5a796c5c63cf94d3b16072762f9f310545ca28184f5a714d897c9f087`) and full layered source receipt must be recovered and matched before a current-runtime replacement recipe is admitted.

## Before any new build or service

First select the explicit target: accepted base PG/Wine normal product versus the current full manual-derived runtime. Recover and verify that product's exact full source/build receipts and existing PE. Materialize the complete original archive in a new owned tree, apply its immutable qualified layers in order and verify the full source map. Apply only the reviewed checksum correction; verify all other resulting files, persistence FIFO/merger, version provider, auth cookie consumer and build profile. Preserve normal fixture OFF and retain a separate fixture product if later persistence qualification is needed. Do not deploy the reduced closure.

Only after independent source review and a documented need should a coordinator prepare a matching Win32 OptDebug build experiment. Retain complete source-map/HEAD/helper/argv provenance and exact PE/cache/import identity. Preserve original persistence retry/rollback/commit-before-ACK tests. Binary/full-checksum and version/protocol/missing-reference refusals need actual future execution. Fresh encrypted authentication, full UserData=true nonqueue profile, owned registered shard/channel, real normal-version provider result, explicit reference interoperability policy, generation/session binding and cleanup remain prerequisites. No Windows CI or service was dispatched by this component; shipping accounts, character data and profiles remain untouched.
