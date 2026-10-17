# Fresh-fixture-only source payload retention

`retain_fresh_source_snapshot.py` permits reusable source test data only after
one genuine fresh graphical fixture and its actual original/native capture have
passed the complete immutable source snapshot admission. It accepts no generic
existing database, caller-supplied account, character ID or selected cookie.

The fixed exported directory is a **new** `fresh-source-snapshot`, mode0700.
It contains exactly these files, mode0600:

| File | Retained meaning |
| --- | --- |
| `catalog.cohcat` | Exact same-envelope catalog body |
| `runtime.cohrts` | Exact same-envelope runtime snapshot body |
| `resources.cohres` | Exact same-envelope server resource associations |
| `public-bounds.cohrbw` | Exact same-envelope original public-bounds body |
| `manifest.json` | Fixed sanitized fresh-fixture/snapshot/payload binding |

Each payload's native format header remains byte-exact so existing bounded
parsers can consume it. The COHGTX envelope header/footer, owner, packet,
packet metadata, eligibility, inspection report, capture/run receipts, selected
IDs, account, cookie, logs and private filenames/paths are never exported.
The source observation sequence embedded in native format headers is not an
identity or a current-generation lifetime token.

The gate requires actual hosted current committed orchestration and the exact
independently supplied genuine fixture and source-admission receipt SHA256 pins.
It runs the already-reviewed source admitter again in a separate owned Python
child against the **same already-cleaned inputs**, then compares the entire
result to the original pinned public admission receipt. The original admitter's
project import closure and token stay identical in the separate interpreter.
This repeats file/source/native dependency checks only; it starts no PG, Wine,
MapServer, DbServer or capture and builds no client/server/capture producer.
The trivial compiler dependency probes are inherited from source admission.

The complete fresh ordinary-save fixture scope must still pass: original source
creation into a fresh disposable COHLOCAL/THORHERO profile, no accepted private
user input, complete source-produced PGDMP and creation evidence, explicit public
fixture dump retention permission, cleanup and exact actual restore/owner pair.
This prevents a caller from turning arbitrary existing private dumps or a generic
private capture into public test data.

The four copies are admitted only against E's exact private verifier receipt and
the same independently checked source envelope. Payload names and maximum sizes
are fixed. Hash/length are checked before/after each bounded streamed copy and
again before manifest publication. A final callback rechecks the genuine fixture,
source admission, source envelope, native verifier receipt, all four extracted
inputs and committed retainer/import source bytes. A 900-second owned readmission
child timeout is separate from copy time; captured child output has a post-read
1MiB admission cap, not a live memory/RSS claim. Pipes are explicitly closed on
success/failure, and process-group cleanup must succeed.

The sanitized manifest contains only fixed scope booleans, public source code
identities, the opaque previously admitted snapshot token, the public source
admission/fixture receipt hashes, the already-public fresh fixture dump hash and
four payload lengths/hashes. Private capture/run hashes and selected identities
are not serialized. The manifest references an admitted immutable source snapshot;
it mints no new runtime authority. Post-release current lifetime, CLIENT
materials/LODs/cache equivalence, actor, renderer and world remain false.

All four payloads must be fully written, flushed, fsynced, closed and rehashed
before the manifest is published through the admitter's exclusive commit-last
writer. Any copy/hash/flush/fsync/close, final check or manifest failure attempts
independent rollback of every owned payload/manifest and the new directory while
preserving the primary error. Existing directories are never replaced or removed.
An uncommitted partial directory without an admitted manifest is never an accepted
retention artifact. CLI failure status is fixed `FRESH_SOURCE_RETENTION_REFUSED`;
private child output, exception text and expanded commands are not printed.

Use all the same path/pin arguments as `admit_source_snapshot.py`, replacing
`--output` with the new fixed-basename directory, and additionally supply
`--source-admission PUBLIC_SOURCE_RECEIPT` and its independently latched
`--source-admission-sha256`. The same private E verification directory must still
contain its exact verified `source/` extraction. Generic private capture/work/input
paths remain excluded from uploads. The owned workflow must upload only the
explicit four files and manifest after successful gate completion; never widen an
artifact glob to the private capture or verification directory.

Run the new host suite with:

```sh
python3 native-android/engine/scenecatalog-server/test_fresh_source_retention.py
```

Ten methods cover exact four-body byte identity/commit order, forbidden owner/
packet canaries, wrong envelope/hash/Boolean length, fixed new destination and
existing-tree preservation, later-copy/final-check/manifest failure rollback,
late flush/fsync/close plus secondary-close rollback, manifest public allowlist,
source change before commit, a real trivial owned child with closed pipes/group
cleanup, timeout plus pipe-close failure/FD leak controls and private CLI canary
refusal. Copy tests use offline `passed:false` manifests; no PG/Wine/graphics or
actual source capture is run and no live source token is minted by this suite.
