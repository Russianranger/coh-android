# Opt-in disposable hosted native capture

`capture_disposable.py` prepares the missing runtime attempt using the exact
existing nonshipping PE. The first hosted attempt, run38939438638 at source
`cc92cad36eb8136274794a2beed9c6945647abbe`, executed DbServer but reached its
600-second readiness deadline before MapServer launch. No catalog was captured.
Owned process/prefix/PostgreSQL cleanup and unchanged source inventory passed.
The second attempt, run38943674136 at source
`140ee62d7b648de737fcec5e7d80b52bfbb9ae67`, qualified Wine10 Windows ODBC,
started the disposable database and reached the real Atlas catalog hook. The
unchanged sink refused its output path before serialization. No catalog was
captured; its source inventory and owned cleanup checks passed.

The reusable `.github/workflows/android-map-startup-native.yml` FX job already
prepares complete public .31 Atlas assets and runs actual Win32 code under Wine.
Its `-tsr2` preload exits in original `checkTsr`, before DB registration or world
load, so invoking that unchanged driver cannot reach the catalog exporter.
The new runner instead combines that private asset fixture with the separately
qualified .34 manual DbServer/62-file schema and `pg_local` disposable cluster.
It invokes normal accepted map arguments including `-donotautogroup`. The exact
exporter's normal startup hook follows `groupLoadMap` and `dbSetupMap`.

This attempt uses **public test assets and an empty new database**, never a Thor
profile. Even an exact historical footer match does not establish the device's
asset generation, selected character, complete live GROUPS transaction or world
rendering. Those receipt flags remain false. Do not rename this a Thor capture.

## Coordinator workflow prerequisites

Use a full checkout of the new `native-android` commit, preserving LF bytes.
Sparse local checkouts must include `android/guest`, `android/native` and
`database/postgresql`; these paths are present in repository HEAD.

Use a fresh nonroot GitHub-hosted Ubuntu24.04 runner, at least30GiB initial free
space, a pinned Wine release supporting Windows ODBC drivers and PE32 execution,
Xvfb/xauth, PostgreSQL16 and `gcc-mingw-w64-i686` for the read-only path observer. Ubuntu24.04's default Wine9.0 is unsuitable: its
[original ODBC manager](https://github.com/wine-mirror/wine/blob/wine-9.0/dlls/odbc32/proxyodbc.c)
forwards to Unix libodbc, while
[Wine9.13](https://github.com/wine-mirror/wine/blob/wine-9.13/dlls/odbc32/proxyodbc.c)
introduces Windows-driver loading. The runner refuses versions below9.13;
passing this necessary floor does not qualify a particular Wine build. Preserve
the installed package/version evidence and execute the exact retained driver's
preflight. No root PostgreSQL,
existing database/service or installed user runtime is admitted. Source fixture
copying must retain at least16GiB free at capture admission. The runner's output
and work directories must be absent, private and separate from all inputs.

1. Reuse `tools/android/interactive/map_startup_inputs.py` and
   `qualify_runtime_asset_preflight.ensure_assets` to obtain hash-pinned original
   .31 donor and Assets1.0.0. The existing complete control preparation also
   fetches/verifies its original Audio volume if missing. Do not generate new
   assets or loosen donor hashes.
2. Run `tools/android/atlasgame/prepare_server_fx_control_fixture.py` exactly as
   in the existing FX workflow. Keep its original `control-fixture.json` and
   read `runtime_host_path` from that receipt. The fixture uses173,011 original
   imported files /2,977,730,517bytes plus qualified supplements.
3. Download exact public .34 donor using
   `tools/android/interactive/build_client_manual_session_apk.py download-donor`.
   It is42,048,020bytes/SHA256
   `c2d859621476e22add673a76c4b6aae65c2143671e50c085d020108b6e19d95e`.
   `qualify_minimal_db_runtime.donor_inputs` verifies native package closure,
   manual DbServer, schema and retained Map identities; its62-file fixture must
   match before any process is launched.
4. Download the existing compile ZIP from run38926873046/artifact12058121070;
   call `delivery.py candidate` to stage its unchanged exact PE. No MSVC rebuild
   or accepted-APK rebuild is required.
5. Use `python native-android/engine/scenecatalog/check_file.py --source-root .
   --output /private/validator-qualification.json --binary /private/coh_catalog_validate
   --sanitize` (one command). It retains the exact release executable only after
   original-source acceptance and12 malformed/generation refusals in each of
   release/ASan/UBSan. No untested recompilation follows. The receipt retains the
   exact binary and fixture hashes, compiler commands and full native header
   closure. The compile consists of `scenecatalog/validate_file.c` together with
   `scenecatalog/coh_scenecatalog.c`, `scenegraph/coh_scenegraph.c`,
   `replication/coh_replication.c` and `replication/coh_groups.c`, with C99,
   strict warnings and `-lm`. Record the exact compiler command, source commit,
   every source/header digest and resulting executable SHA256 in workflow
   evidence. The runner observes binary identity; it cannot infer source
   provenance merely from a caller-supplied executable.
6. Compile the separate read-only path observer with
   `python3 native-android/engine/scenecatalog-server/build_path_probe.py
   --binary /private/catalog-path-probe.exe --output /private/path-probe-build.json`
   (one command). It compiles the exact unchanged sink path/reserved-name
   functions and original 240-byte cap into a PE32/I386 observer. The small
   executable and receipt bind the builder, observer and sink source hashes.
   This does not rebuild or replace MapServer.

Invoke the runner under `xvfb-run -a`, substituting actual prepared paths:

```sh
python native-android/engine/scenecatalog-server/capture_disposable.py \
  --runtime /private/fixture/runtime \
  --control-fixture /private/fixture/control-fixture.json \
  --db-donor-apk /private/donor-034.apk \
  --candidate-directory /private/catalog-candidate \
  --native-validator /private/coh_catalog_validate \
  --path-probe /private/catalog-path-probe.exe \
  --path-probe-receipt /private/path-probe-build.json \
  --pg-bin /usr/lib/postgresql/16/bin \
  --work /tmp/coh-catalog-attempt \
  --output /private/new-capture-output \
  --generation 1 --timeout-seconds 2400
```

The generation is owned by this isolated attempt and must be bound to its
retained source inventory. It is not silently substituted for an existing
Android asset generation. Source identity and exact SHA256 facts are retained
in `capture-receipt.json`.

## Isolation, validation and failure handling

After fresh Wine initialization, the runner creates only its owned
`drive_c/coh-native-catalog` directory. The hash-bound observer performs read-only
Win32 attribute queries and executes the original sink path admission function.
It requires the private C-drive destination to pass and the equivalent Z-drive
spelling to fail with the observed root reparse flag. Both observations retain
root/parent/target attributes and final error codes. These checks happen before
the expensive asset copy or any database/MapServer launch. The existing sink's
reparse policy and exact MapServer PE remain unchanged.

The runner deep-copies the complete prepared namespace, dereferencing files into
new private files. It refuses linked directories and limits source inventory to
350,000files/12GiB and512MiB per file. It inventories source contents before and
after the attempt; native processes cannot write through copied symlinks.
Original donor native dependencies are validated against the candidate's import
closure. Only the disposable copy receives the candidate MapServer.exe.

A fresh PostgreSQL cluster uses loopback15437. Exact .34 DbServer uses the original
fixed-input/loopback/manual-map startup controls and a separate62-file schema
namespace. The runner verifies original acknowledgments, stable advancing
DbServer dispatch and the full original schema snapshot. It installs the exact
pinned x86 ODBC MSI into a new private Win32 Wine prefix. MapServer uses loopback
UDP7001; original listener acknowledgment and actual bind records are checked.
There is no account login, network endpoint discovery, real profile import,
TestClient/Game launch or READY/full-update acknowledgment.

The maximum attempt deadline is3600seconds. Polled stdout/stderr limits are8MiB
per process; they are not a kernel write limit. Retained tails are at most256KiB
each and disposable database secrets are redacted. This first runner does not
establish a hard runtime RSS/process-memory cap or a performance improvement.
MapServer's existing32MiB catalog sink remains the payload cap. Complete native
record validation retains the original catalog ownership cap and exact decoder.
Successful source output is preserved even if downstream native admission fails.

Owned process handles/groups, the private Wine prefix and the fresh PostgreSQL
cluster are cleaned up on success/failure. If initialization raises after
starting PostgreSQL, cleanup reconstructs only this invocation's private cluster
from its descriptors, stops it if live and requires `pg_ctl status` to report
stopped. Unknown cluster state makes cleanup fail. Existing user clusters are
never opened. Helpers receive only the isolated Wine prefix; no global Wine kill
is used. Input inventory and source code bytes must remain unchanged.

`passed:true` means this runtime attempt captured and completely decoded a
source-produced catalog and verified cleanup. `historical_thor_footer_matches`
compares508files/33roots and original CRCs3173822562/3649375123 separately.
`matching_groups_transaction_captured` and
`physical_thor_generation_verified` remain false because this runner does not
receive live GROUPS or inspect device assets. No graph, actor, auth, render or
physical acceptance is granted by this receipt. A mismatch retains the authentic
isolated export as evidence; it must not be imported as the device's catalog.

## First hosted failure and bounded follow-up

The first receipt is retained in `evidence/capture-38939438638/`. Full artifact
12062693451 has SHA256
`3bc0763b51f3923d8d4367ea0d014b41c96a7da3c1583ca9deadb15da90e388c`.
The DbServer emitted fixed-input and loopback acknowledgments and six verified
TCP binds, but no manual-map acknowledgment or SQL-connected message. Original
`dbInit` next enters name/hostname and SQL initialization. This bounds the last
observed location; neither a particular stalled instruction nor an SQL failure
was captured. The Wine9.0 manager mismatch is independently source established,
not inferred solely from the timeout.

The follow-up preserves the exact DbServer/MapServer binaries. Before database
startup it executes the hash-verified `.34` donor's existing `runtime-probe.exe
--odbc-driver` and applies the unchanged accepted `validate_odbc_driver` parser.
The actual registered name, including `PostgreSQL Unicode(x86)` where selected,
feeds the original guest configuration. No connection/checksum policy is skipped.
On a later failure the receipt retains the validated dispatch stage and a
three-second read-only query of private PostgreSQL session/activity/lock/DDL
counts. SQL statements are not retained in that query. Redacted PostgreSQL log
tails and labeled owned process logs accompany it. These controls are host
qualified and were executed by the second hosted attempt described below.


## Second hosted failure and private-drive preflight

The second receipt and selected exact diagnostics are retained in
`evidence/capture-38943674136/`. Full artifact12065056438 has SHA256
`9e7dc17a0d3e96f402dda30a841e13abf10f7670768c5593d97a29ef6ff2123e`.
Exact Wine10 loaded the original 32-bit PostgreSQL Unicode driver. DbServer
reached its manual-map readiness acknowledgment with the complete expected
schema. MapServer registered map1, loaded the original Atlas path, and reached
`COH_NATIVE_SCENE_CATALOG_V1 status=3 producer_status=0`. All file/definition/
byte counts were zero; this is sink destination refusal before serialization.
No source catalog, live GROUPS transaction or Thor world-entry result exists.

The destination used the Z-drive mapping to the Unix filesystem root. Original
Wine10 `get_file_info` marks a directory as a reparse point when its inode equals
its parent's, which holds for `/` and `/..`. The unchanged sink checks and refuses
that drive-root flag. An independent execution of this unchanged Wine function
against real Linux `stat`/`lstat` and fresh C/Z mappings observed attributes1040
for Z and16 for C. Its deterministic helper shells and exact source provenance
are recorded in `evidence/path-probe/`; this is a source control, not actual Wine
WinAPI execution. The added observer will measure the actual APIs before a new
expensive attempt. The new destination lies in the invocation's ordinary private
C-drive directory; no guard is relaxed and no existing path is overwritten.

The observer is separately PE32 compile qualified with strict GCC warnings.
The runner's28 host controls include source-extraction identity, malformed
observations, redirected drives, symlink refusal and destination non-overwrite.
Actual observer execution, complete catalog serialization, native import and
comparison to the historical508-file/33-root footer remain pending the next
hosted attempt. These staging changes require no Android rebuild or device test.
