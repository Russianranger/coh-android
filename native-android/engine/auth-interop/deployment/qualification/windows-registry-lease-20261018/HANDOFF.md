# Source/mock registry lease handoff

New source only: `deployment/windows_registry_lease.py`, its new controlled
tests, `WINDOWS-REGISTRY-LEASE.md`, and this proof directory. No original C,
profile, workflow, activation driver, credentials or existing evidence changed.

Frozen `mock.json` passed 22 controlled methods on Linux/Python 3.12.14, with
1,885 modeled API calls, all 14 prepare and 22 cleanup failure sites, at most
7 simultaneously live modeled handles (including the held source-handle control),
and 18 calls through a Python DLL double exercising native ctypes declarations.
These counts describe this finite fixture, not an OS or driver resource budget.
Eight exact input SHA256 values are checked before and after the new test run.
No original C compilation/execution, Windows registry, service or runtime ran.

API:

```python
lease = RegistryLease(owned_localdb_instance)
private_client_project = lease.client_project  # exact coh-ci-<same24hex>
lease.prepare(owned_services_not_started=True)
# Separately admitted source/profile/process work belongs to the new driver.
result = lease.cleanup(services_stopped=all_owned_services_and_descendants_exited)
```

Constructor/import are platform inert; `prepare` lazily loads the System32
Advapi32 binding. Strict true preconditions, owner thread and busy guards precede
API operations. Caller-selected paths are unavailable. Snapshots omit the nonce
and contain only fixed fields and enums. The private property remains available
for the new typed source config; it is not a public runtime identity witness.

Source setup is deliberately different: an empty precreated key sends the fresh
original getter through existing-key/missing-value `NULL`, instead of the
created-key immediate `NULL` branch. `source_inferred_getter_branch` labels only
that source-derived expectation. No installation, version or reference value is
created, and no actual branch/version/checksum result is qualified here.

Root/D explicitly approved the fresh hosted user, same token, exclusive random
nonce and owned process lifetime as the trust boundary. Empty checking followed
by `RegDeleteKeyExW` is not atomic against an unrelated same-user writer. Within
that contract, only native-disposition-owned empty keys delete. Unexpected
content/API status refuses and can leave owned handles/keys; cleanup verifies
both-view absence and never deletes a preexisting parent or clears content.
The primary failure survives independently attempted secondary closes.

Actual Windows shared-view/ACL/API behavior, actual process exit, source-driver
integration and a live development activation remain future independent gates.
No prior qualifier or capture was replayed.
