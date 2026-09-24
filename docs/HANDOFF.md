# City of Heroes Android handoff

Updated: 2026-09-24.

## Active direction

- The user returned to the original imported source and asked whether it contains
  everything for a local server and client. Use `upstream/ouroboros` at
  `0b75ade0c801735e10c5798f641948a45cc50488`; i25 acquisition is not a prerequisite.
- This is a public OuroDev-derived Issue 24/Volume 2 fork with downstream changes,
  not a VM or a verified identical canonical OuroDev export.
- The user has no Windows PC. Use hosted Windows builds/reference tests and Thor
  diagnostic client testing for graphics and gameplay.

## Validation result

The original 5,995 files (173,081,714 bytes) still pass the manifest verifier.
Upstream run `35934567567`, job `107428594341`, built the exact pinned commit,
including DbServer, MapServer, CityOfHeroes and auxiliary services. Nine utility,
archive, development-mode and codec tests passed. We inspected upstream logs;
we did not run a new Windows build or gameplay test.

Server and client source are present. A runnable installation still needs
companion text data, binary assets, generated templates/bins, runtime DLLs and
a database. Read the [completeness audit](LOCAL_SERVER_CLIENT_COMPLETENESS.md).
The companion scripts expect `Game.exe`, fetch an older release by default
and fetch configs from moving `master`. The downloaded release ZIP was checked
against its published SHA-256 and inspected without executing it.

## Next implementation steps

1. Add a root-level hosted Windows workflow using the imported source directory,
   retaining executable outputs, TestClient, runtime DLLs and checksums.
   Nested upstream workflows do not run in this repository automatically.
2. Acquire companion data at `d51533ec8e6a9cf726b9214968077a05fdcf19f3` and
   compatible assets. Record content/config/binary hashes in a runtime manifest.
   Sample asset requests returned HTTP 403 here; full availability and integrity
   remain unverified.
3. Adapt launch/bin scripts to `CityOfHeroes.exe`, pin configs to our source,
   generate templates and use SQL Server/32-bit ODBC in hosted reference tests.
   Prove character creation, map connection and save/reload with TestClient.
4. Progress to PostgreSQL repairs and Thor compatibility probes in the
   [proposal](ANDROID_PORT_PROPOSAL.md). Test mission/map transfers and selected
   auxiliary services separately from the fixed-map developer smoke test.

## Preserved alternative investigation

No canonical i25 source was imported. Its manual discovery workflow and
[findings](I25_SOURCE_ACQUISITION.md) remain for reference. `odtoken` was present,
but credential validity was not tested because TLS failed. Do not print or
request the secret value. The selected public snapshot does not need that token.

`archive/volume2-assessment-2026-09-23` preserves the earlier assessment state.
`docs/VOLUME2_PORT_PROPOSAL.md` is a historical copy; the active proposal is
`docs/ANDROID_PORT_PROPOSAL.md`. There is no scheduled retry, background import,
tested gameplay session or Android APK.
