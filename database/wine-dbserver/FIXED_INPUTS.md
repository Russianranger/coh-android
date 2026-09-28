# Opt-in fixed-input DbServer mode

The staged Wine DbServer supports a narrowly scoped mode for the hosted Atlas
gate's immutable schema/configuration inputs. It is prepared for qualification;
it is not an accepted runtime result or a repair of generic Wine notifications.

With `COH_WINE_DB_FIXED_INPUTS` absent, existing startup, folder-cache mode,
directory watching and callback behavior remain unchanged. The exact value `1`
requests fixed inputs; empty, `0`, or any other value fails normal startup.
The request runs after the persistence-fixture bypass and before normal startup
can create a FolderCache. Activation refuses once any FolderCache was created.
The fixture's `-pgpersistencetest` entry retains its existing initialization and
does not apply this normal-startup mode.

Successful activation writes this exact acknowledgment to stderr:

```text
COH_WINE_DB_FIXED_INPUTS=1 active: directory monitoring disabled; initial reads and lookup mode preserved
```

`FolderCacheSetFixedInputsMode` sets a one-way flag. `FolderCacheAddFolder` still
records data directories and performs ordinary initial scan/hash work for the
selected mode, but skips directory-watcher registration. `FolderCacheUpdate`
returns before notification polling. Later `FolderCacheEnableCallbacks(1)`
cannot undo the mode. Ordinary cached/filesystem lookups and initial reads remain
in place; no cache mode is substituted and no active watcher is canceled or freed.
The build receipt's `fixed_inputs` metadata binds this contract together with
the helper, patched library source/header and startup call site.

Simply stopping notification consumption while leaving watchers alive can
accumulate notifications in the pinned Wine server. This mode prevents watchers
from being created. SQL workers, schema loading, networking, character creation,
saves and restart/resume checks remain active. The mode does not clear previously
queued callbacks or change archive callbacks; the intended gate uses reviewed
loose assets and activates before filesystem monitoring can queue anything.

The harness must enable this mode only for DbServer, require the acknowledgment,
and verify that the union of the 62 accepted schema inputs and the entire staged
`data/server/db` tree remains unchanged. This includes optional WeeklyTF and
load-balancing configurations and additions/deletions. Hash/inventory checks
surround first startup/save and service restart/second save. The initial inventory
is taken after private `servers.cfg` generation. This mode is unsuitable for hot
reload or editing those inputs during a session; cached metadata may become stale.

Tests compile actual staged FolderCache functions and exercise all five lookup
modes with and without fixed inputs, checking initial scan/hash behavior,
watcher registration, update gating, late activation and attempts to re-enable
updates. Separate Windows tests compile the actual environment helper and check
strict parsing, refusal and acknowledgment behavior. Hosted qualification must
retain a default normal-schema invocation and run an enabled normal-schema reload
before Atlas adopts the new donor. The complete Atlas gate remains necessary to
establish enabled ARM64 behavior and character restart/resume results.
