# Isolated encrypted-auth deployment candidate

This directory adds read-only metadata admission and original-source audit. It
does not change native authentication. The original metadata/audit tools do not
connect to SQL. The additional [hosted staging candidate](HOSTED-STAGING.md) can
build original AuthServer and run original account methods against a uniquely
owned disposable LocalDB instance; it requires a fresh GitHub-hosted Windows
runner and remains unexecuted on Windows at this checkpoint. It never starts
AuthServer or logs in an account. No real encrypted login or DB-to-Map handoff
was observed.

## Source and schema discovery

The recovered source is already in `native-android`'s Git tree. Missing local
`AuthServer/` and `Assets/` paths were sparse-checkout omissions. The audit reads
missing files from the exact local HEAD blob without expanding or editing the
checkout; all decoded UTF-8/LF content must match `source-pins.json`. Actual byte
hashes and read provenance are recorded separately. The older UTF-16 base schema
is decoded explicitly, so it is not silently excluded from the search.

Two supplied schema generations differ:

| Interface | Current original C++ caller | Legacy `AuthServer/src/schema` | Existing `Assets/DBSchemas/cohauth.sql` |
| --- | --- | --- | --- |
| `ap_GPwd` | 4 bound parameters; hash type bound as `SQL_TINYINT` | 4 parameters, `tinyint` hash type | 4 parameters, `int` hash type |
| `ap_GStat` | 13 parameters, including loyalty and legacy-loyalty outputs | `patch_2.sql` defines 11 | 13; `loyalty_points` and `loyalty_legacy_points` columns exist |
| Block timestamp | ODBC `SQL_TYPE_TIMESTAMP`, precision 23, scale 3 | `datetime` | `datetime2(3)` output |
| Region access | `get_server_groups`, one UID input and integer result | `patch_5.sql` defines it | Existing procedure/table present |
| User data | 16 original bytes plus 112 extension bytes | `patch_8.sql` extends the table | Existing four binary columns preserve both 128-byte pairs |

The 2019 `cohauth.sql` is the existing candidate to investigate. No replacement
schema or zero-valued loyalty shim is needed or provided. Applying every old
patch after that schema is incorrect: it can duplicate existing columns and
replace the 13-parameter procedure with the obsolete 11-parameter version.
The script also hardcodes `USE master`, `CREATE DATABASE cohauth` and subsequent
database options. It must not be run on the user's active SQL instance/profile.

The two type conversions need actual driver qualification: SQL `int` to the
one-byte hash output, and `datetime2(3)` to the C `TIMESTAMP_STRUCT` binding.
This implementation deliberately reports `odbc_conversion_unqualified` instead
of accepting metadata as proof that the actual x86 ODBC driver returns correct
values/status/indicators. Metadata admission compares the source binding
contract; even a perfect match never marks full schema compatibility or a login.
Nullable UID/loyalty/user-data values, account-result semantics, missing accounts,
permissions, logging/logout procedures and server registration need runtime
qualification too. No account values are read by this inspector.

## Reproducible checks

From a clean or sparse checkout, on a Linux x86 compiler host:

```sh
python3 native-android/engine/auth-interop/deployment/check.py \
  --source-root . --output /tmp/coh-auth-deployment.json
```

Only metadata unit tests run if `--source-root` is omitted. These cover missing
and obsolete contracts, every required binding and column, known conversion
refusals, duplicate/aliased metadata, type confusion, large and malformed JSON,
secret-field redaction, UTF-16 source decoding and read-only query shape. Their
passing metadata fixture is synthetic, not a captured database.

The source audit compares actual ODBC bindings and question-mark counts with
both supplied SQL generations. It also compiles the unchanged original
`clientCommLoginVerifyChecksum` as freestanding 32-bit and 64-bit x86 objects.
Both generated functions contain `xor eax,eax; ret` (the 64-bit host compiler
may prefix ENDBR64), with no external `memcmp` reference. The static assertions
check 4/8-byte pointers against the 16-byte checksum array. This independently
corroborates the prior executed host oracle's pointer-size defect. These are
new experimental objects, not disassembly of a deployed DbServer. No server
repair, version exception, checksum bypass, or native policy change is included.
No ASan claim is made for Python metadata inspection or unexecuted objects;
the existing native probe/source-oracle qualification retains its own scope.

## Concrete disposable deployment sequence

1. Provision an independently isolated Windows host/VM with an x86-compatible
   ODBC driver, SQL Server-compatible service, exact matching AuthServer,
   DbServer and MapServer build identities, and no connection to the accepted
   Thor profile or database. Preserve source/config/schema and binary hashes.
   Provisioning must be reviewed for that actual host before execution.
2. Review the existing `Assets/DBSchemas/cohauth.sql` for the disposable SQL
   instance. Do not combine it blindly with old patch scripts. Establish an
   independently verified disposable account, account UID, region membership,
   shard registration and existing disposable character. Keep account/password
   material outside reports, argv and environment variables.
3. In that explicitly identified account database, run `inspect_schema.sql`
   through the operator's private authenticated SQL client. Export the complete
   single JSON value without headers, wrapping/truncation or diagnostic text.
   It requires SQL Server 2016+ JSON support and system-metadata visibility.
   It selects only `sys.*` rows. It never executes `ap_GPwd` or reads password
   rows. Use a separate private session for credentialed connection handling.
4. Inspect the captured metadata locally:

   ```sh
   python3 native-android/engine/auth-interop/deployment/admit_schema.py \
     --metadata /private/auth-critical-schema.json \
     --output /private/auth-schema-admission.json
   ```

   Exit 1 means refused or awaiting qualification. Missing metadata does not
   mean missing columns until DB context and metadata permissions are verified.
   `cohauth.sql`'s two known conversion differences are expected refusals. Review
   stored procedure bodies and execute driver-level positive/negative controls
   in the disposable environment before qualifying conversions; do not silence
   the refusal or narrow procedure outputs without evidence. The new hosted
   original-function ODBC harness is supplied as an execution candidate, with
   actual Windows/ODBC execution still pending.
5. Record actual `Encrypt`, `DesApply`, supported `ProtocolVersion`, nonqueued
   list policy, explicit `UseFakeAuth 0`, version and approved checksum policy.
   Disable packet dumps and verbose/debug logging that can include secrets.
   Verify the AuthServer registered the intended DbServer and independently
   approve every advertised Auth/DB/Map endpoint. Do not infer services from
   open ports. Keep the existing development-auth fallback unchanged.
6. Independently inspect the actual DbServer binary and perform valid/invalid
   checksum and version controls. The known source defect makes checksum
   policy a separate open item. A repair would need a separately versioned
   disposable server build and negative tests, not a silent production patch.
7. Use the existing `../run.py` interactive wrapper and real native probe with
   the approved endpoints/account. Preserve numeric native results and
   independently redacted server-side receipt identities. Check selected DBID,
   auth cache binding, DB/Map handoff and exact socket cleanup. Protocol progress
   alone is not source provenance or authoritative world entry.

The hosted image inventory makes a fresh source-bound AuthServer build and
disposable LocalDB experiment feasible; exact public evidence, commands and
remaining account/probe/DbServer requirements are in `HOSTED-STAGING.md`.
This Linux environment cannot execute that Windows stage. ODBC conversions,
original missing-account behavior and real checksum policy remain unqualified.
No listeners were probed. Rollback is omission of this additive tooling; no
APK, database, profile or active server was changed.
