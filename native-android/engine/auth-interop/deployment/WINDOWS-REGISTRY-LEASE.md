# Empty nonce registry lease

This is a new helper for a separate, disposable development experiment. It does
not change the original source, an existing workflow, or the existing activation
driver. Importing the module and constructing a lease do not load Advapi32 or
access the registry. The committed qualification uses a controlled in-memory API
model; actual Windows registry behavior and an actual Auth/DB transaction remain
unqualified.

```python
lease = RegistryLease(owned_localdb_instance)
client_project = lease.client_project
lease.prepare(owned_services_not_started=True)
try:
    # The separately admitted driver may now start its owned processes.
    ...
finally:
    # The caller must establish that every owned service/descendant has exited.
    registry_cleanup = lease.cleanup(services_stopped=owned_services_stopped)
```

The constructor accepts only `cohauth-ci-` followed by exactly 24 lowercase hex
digits, the existing owned LocalDB naming contract. It derives the only allowed
`ClientProject`, `coh-ci-` followed by the same nonce. No path or app-name selector
is accepted. The caller must source-admit the module before `prepare`, preserve
the same nonimpersonated fresh hosted user's token, and call all operations on
one owner thread. Reentry during a native operation refuses before touching the
API. `.client_project` is the exact private config property. `snapshot()` returns
fixed fields, counts, booleans and failure enums without the nonce; no registry
value body, arbitrary native error text or full registry path is read or exported.
The new driver owns source checks, process identity and stop proof.

## Source behavior and the explicit branch difference

`servercfg.c` copies `ClientProject` into `server_cfg.client_project`; `dbinit.c`
passes it to `regSetAppName`. The original `AppRegCache.c` getter constructs
`HKCU\SOFTWARE\Cryptic\<appname>` and calls `RegCreateKeyExA` with read/write
access. A newly created key immediately returns `NULL`. For an existing key it
queries `Installation Directory`; a missing value also returns `NULL`.

This helper deliberately precreates an **empty** nonce key. The fresh original
getter therefore takes the **existing-key, missing-value** branch, returning
`NULL`, rather than the created-key immediate-return branch. This is an explicit
development experiment setup change, not an assertion of identical source
instructions. It assumes a fresh process whose getter's static installation
buffer has not already cached another path. No `Installation Directory`, version,
reference, account or profile value is installed. `AppVersion.c` can observe this
missing installation result; this helper supplies no version/reference outcome.
The receipt's `source_inferred_getter_branch` is this source-derived expectation,
not an observation of instructions executed by an actual process.

The original getter contains no `RegCloseKey` on these paths. All service
processes must actually exit before cleanup; passing a boolean is the caller's
attestation, not process observation by this helper. Post-delete absence still
must pass. The mock's held-source-handle control demonstrates conservative
failure and later retry when removal remains pending.

## Ownership and teardown

The helper opens existing `HKCU\SOFTWARE` in both explicit WOW64 views. It never
creates that ancestor. It opens and checks the fixed `Cryptic` parent, refusing a
registry link. Before any creation it refuses any existing nonce key in either
view. `Cryptic` is created only when absent in both views; native
`REG_CREATED_NEW_KEY` disposition is required before assigning parent ownership.
An existing parent, including its unrelated values and children, is preserved.

Microsoft documents `HKCU\SOFTWARE` and this `Cryptic` descendant as shared
between WOW64 views. The helper creates the nonce exactly once through the
32-bit view, requires `REG_CREATED_NEW_KEY`, and verifies that the 64-bit view
sees an empty, nonlink key. It does not create a second supposedly distinct key
or assign ownership from an `OPENED_EXISTING` disposition. An inconsistent or
separate-view layout refuses and rolls back only proven owned creations.

Successful creation handles are recorded before the first inspection, so an
inspection failure after creation retains rollback authority. Original parent
and leaf handles remain live while their keys are owned. `cleanup` performs no
registry operation unless `services_stopped is True` (integers such as `1` do not
qualify). It inspects every retained leaf view for zero values and zero subkeys,
then deletes only the exact owned nonce once through its retained parent. It
closes the leaf handles and requires absence in both views. A disposition-owned
parent may then be deleted only if it still has zero values and zero children;
its handles close and its absence in both views must pass. Preexisting parents
are never deleted. There is no recursive deletion or value deletion API.

**Trust boundary:** the fresh hosted user, random nonce and owned process
lifetime are exclusive. No unrelated same-user writer may mutate the nonce or
replace `SOFTWARE`/`Cryptic` during the lease. Query-empty followed by
`RegDeleteKeyEx` is not atomic against such a writer: that Windows API deletes a
key's values. This helper uses neither a transaction nor a security boundary
against the same user's other processes. It makes no universal atomicity claim.

Unexpected content or an API failure yields `cleanup_verified: false`; it never
falls back to clearing values or deleting a tree. Handles needed for remaining
ownership are retained for a safe retry. Every safe secondary close is attempted
independently; fixed failure/count fields preserve the primary prepare failure.
Cleanup can leave owned keys/handles when a native API refuses, and its receipt
reports that possibility. A false stopped precondition never closes a live
lease. A verified cleanup is idempotent and does not repeat native calls.

## Controlled qualification

Run only the new source/mock controls:

```sh
python3 native-android/engine/auth-interop/deployment/test_windows_registry_lease.py --output NEW-RECEIPT.json
```

Controls cover exact nonce derivation; import without WinDLL use; strict booleans;
both-view preexistence and shared aliases; preservation of an existing parent;
zero-value/subkey gates; pending deletion with a retained source handle; owner
thread and callback reentry; unsupported split views and links; unexpected native
dispositions; each prepare/cleanup API failure site; primary-error preservation
with simultaneous close failures; malformed API observations and sanitized
failure fields; native binding prototypes/flags/metadata-only pointers through a
Python DLL double. Source checks bind the original getter/config/app-name code and
label the Python branch projection separately from original C execution.

The proof binds exact current source bytes before/after these controls. It does
not compile or run original C, access Windows registry, start services, or admit
a live development activation. Actual Windows API/OS policy and the driver's
source/profile/process integration require a separately reviewed future run.

Primary API references read for this implementation (2026-10-18):

- [RegCreateKeyExW](https://learn.microsoft.com/en-us/windows/win32/api/winreg/nf-winreg-regcreatekeyexw): disposition, empty new keys, inherited security, missing-path creation.
- [RegOpenKeyExW](https://learn.microsoft.com/en-us/windows/win32/api/winreg/nf-winreg-regopenkeyexw): open existing keys and `REG_OPTION_OPEN_LINK`.
- [RegQueryInfoKeyW](https://learn.microsoft.com/en-us/windows/win32/api/winreg/nf-winreg-regqueryinfokeyw): value/subkey counts.
- [RegDeleteKeyExW](https://learn.microsoft.com/en-us/windows/win32/api/winreg/nf-winreg-regdeletekeyexw): subkey refusal, value deletion and delayed removal until handles close.
- [WOW64 shared keys](https://learn.microsoft.com/en-us/windows/win32/winprog64/shared-registry-keys): shared `HKCU\SOFTWARE` and inheritance for descendants.
