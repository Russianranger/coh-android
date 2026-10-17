# Isolated corrected AuthServer with the qualified 1024-MiB host SQL profile

Actual readiness-only run `38995104446`, source `7b2067d`, closed all sixteen
observations: four phases × x86/x64 × named-instance/owned-pipe. Every observation
opened three connections, queried the exact same SQL PID/generation and closed
all connections. Original schema, public credential and account seed succeeded;
schema DROP, LocalDB stop/delete, private-file removal and source checks passed.
No memory/error-log markers appeared. AuthServer was never started by that run.

The exact artifact `12086284710` is retained under
`../evidence/sql-readiness-1024-38995104446/`: 2,856 bytes, SHA256
`bbdae68f07c98c818d24ce21611b64aa26a5426afaca61a40dd6ee52c40d64e8`.
The complete receipt SHA256 is
`4c06409b977495d9db6dc42fcd1c0148005487fd3086c97a9fc1d45bf63a5e86`.
It is distinct from the failed 256-MiB evidence; no old failure is relabeled.

`hosted_candidate_login.py` now supports the explicit optional flag:

```powershell
--sql-memory-limit-mb 1024
```

Append it to the existing exact corrected-server command in
`.github/workflows/native-auth-candidate-login.yml`. Reuse the same already-built
corrected AuthServer PE, seven-byte probe, 1024-byte-cap probe and successful
original ODBC evidence. No server, probe or OpenSSL source is rebuilt. The
existing default remains 256 MiB, and no accepted shipping/server/Android profile
is changed. The new option changes the owned disposable LocalDB's memory setting,
not AuthServer encryption, password policy, checksums, protocol or fixture data.

Before resource creation, `candidate_sql_memory.py` admits the exact receipt bytes
and explicitly verifies all sixteen health records, pointer sizes, three real
connections, SQL generation consistency, clean error-log flags, original/public
seed results and complete cleanup. A historical diagnostic's `passed` flag alone
cannot select this profile. Selection records no inherited authentication success.
The new service instance still must pass the existing independent x86 ODBC health
guard immediately before AuthServer startup; the guard is never bypassed.

The 1024-MiB path also uses the already-reviewed redacting SQL/LocalDB runner for
create/start, memory configuration and cleanup. Version/PID capture emits only
fixed admitted scalar values. Raw SQL and LocalDB console text is discarded.
The 256-MiB default path keeps its existing behavior. Both paths retain the
exact corrected-server/probe admissions, owned listener checks, all eight normal
and capped-send positive/negative cases, and full service/SQL/firewall/private
cleanup. No registered shard, DbServer/MapServer handoff or Android acceptance
is inferred from an AuthServer-only result.

Local qualification passed 29 host suites: five new receipt/profile suites,
eight existing candidate-service suites (fresh-readiness refusal now exercised
with both memory selections), seven independent ODBC suites and nine diagnostic
privacy/transport suites. Mutation controls reject every failed matrix entry,
wrong process identity/generation, incomplete phase, SQL error/memory marker,
failed seed/cleanup and modified receipt bytes. These tests do not execute a real
AuthServer or infer encrypted-login success. The first actual corrected-service
1024-MiB run remains coordinator-owned and requires independent source review.
