# Opt-in fixed-input DbServer mode

The staged Wine DbServer supports a narrowly scoped mode for the hosted Atlas
gate's immutable schema/configuration inputs. Hosted Windows and ARM64 DbServer
qualification passed in [run 36451873322](https://github.com/Russianranger/coh-android/actions/runs/36451873322),
including default normal-schema startup and an acknowledged fixed-input reload.
See the [acceptance receipt](../../docs/android-evidence/accepted-dbserver-hosted-36451873322.json).
The [hosted Atlas sequence](../../docs/ANDROID_GAME_RUNTIME.md#hosted-sequence-accepted-after-host-validator-correction)
from run `36454174481` is accepted after strict revalidation of unchanged evidence
with a corrected host exit contract. Both protocol saves, exact-name resume,
two acknowledgments and four unchanged input checks passed. Its
[acceptance receipt](../../docs/android-evidence/accepted-game-hosted-36454174481.json)
preserves the original Actions failure separately. This is not a repair of
generic Wine notifications or proof of physical Android execution or rendering.

The sibling DbServer run `36454174374` retains an unexplained SIGSEGV (`-11`)
after `PG_TEST_COMPLETE rebuild` and teardown messages in attempt 1. Attempt 2
passed all 28 stages with the byte-identical package. The
[failure](../../docs/android-evidence/dbserver-runtime-failure-36454174374.json)
and [repeat](../../docs/android-evidence/dbserver-runtime-repeat-36454174374-attempt2.json)
receipts preserve both outcomes; the repeat does not establish a repair, and
accepted donor `36451873322` is unchanged.
The separate loopback listener prerequisite is locally tested but still awaits
hosted source/package qualification and donor adoption.

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

The Atlas harness enables this mode only for DbServer, requires a complete
acknowledgment from each of its two owned launches,
and verifies that the union of the 62 accepted schema inputs and the entire staged
`data/server/db` tree remains unchanged. This includes optional WeeklyTF and
load-balancing configurations and additions/deletions. Hash/inventory and
file/directory identity checks run before first startup, after first save,
before restart and after second save. The initial inventory is taken after
private `servers.cfg` generation and includes empty directories. This mode is unsuitable for hot
reload or editing those inputs during a session; cached metadata may become stale.

Tests compile actual staged FolderCache functions and exercise all five lookup
modes with and without fixed inputs, checking initial scan/hash behavior,
watcher registration, update gating, late activation and attempts to re-enable
updates. Separate Windows tests compile the actual environment helper and check
strict parsing, refusal and acknowledgment behavior. Hosted qualification retained
a default normal-schema invocation and passed an enabled normal-schema reload.
The accepted Atlas evidence establishes map startup with this mode, both saves
and exact-name restart/resume. The original host validator incorrectly required
a field the bridge does not serialize; corrected terminal-exit validation passed
against the unchanged report and captures, with the original failure retained.
