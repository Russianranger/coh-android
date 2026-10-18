# Fresh creation allocation-offer owner

Source43bb0484bbd11e9da37287e2a19fe423caeb9663 qualified the new owner in
two distinct new entrypoints. Production source is unchanged froma2b00b8c4.
The original strict empty-list owner, ordinary choose/Map serializers, profile,
protocol and server binaries were not modified or executed by these tests.

| New scope | Release, ASan and UBSan result, each | Evidence meaning |
| --- | --- | --- |
| `--scope doubles` | 127 scenarios,43,771 checks;72 component refusals,14 input refusals,100 busy reentry probes,117 wiped owner frees | Real new owner, controlled public-component doubles. No ordinary controller/network execution is claimed from this entrypoint. |
| `--scope wire` | One transaction,173 checks;4 Auth replies,7 outgoing DB frames including5 encrypted | Real new owner plus public Login/DBSession, original DH/Blowfish, OpenSSL RSA and actual loopback TCP/UDP. Both peers and the list/allocation offer are synthetic. |

The wire entrypoint verifies the actual private Auth authorization is consumed
by the same owner into its DB session, compares the real reliable creation
queue against the unchanged original choose writer, parses MAP_CONNECT through
the ordinary session, then retires it through the new public primitive. It
destroys both controllers before publishing scalar COMPLETE and balances OS
descriptors. It never opens a Map socket or supplies a character body.

The fixture oracle normal-imports pinned project helpers only after byte/Git
admission. Its sole generated-C change is the fixture declaration selecting
slot0, authored name`New Fixture`, local IP0 and original PRIMAL_HERO1; the whole
original choose and bit/string writer blocks stay unchanged. It does not call
an old test main, old fixture generator or login writer. The three Auth replies
are separately labelled synthetic source layouts; the new C peer generates
RSA2048 and checks the actual credential ciphertext privately without logging.

The doubles scope tests consumed begin/shard/bridge/creation/retirement paths,
wrong Auth/shard/grant/list/generation/summary, required encrypted transport,
provider lifetime/callback reentry, cancellation before and after queue/retire,
timeouts, known storage aliases and destruction wiping. Its persistent-row
model deliberately survives cancellation and success: it is a synthetic
nonrollback control, not an observation of a real DB allocation or rollback.

The first doubles attempt stopped at `-Werror=misleading-indentation` in the
new test, before any native child ran. Its stderr is retained. The successor
only split that test statement onto its own line; production source was
unchanged. The wire entrypoint passed its first run. No old Auth, list, C50,
primitive,17-TU, receiver or platform suite/main was invoked. The primitive's
84-input qualification is read as exact fixed historical Git data only.

Each invocation requires fresh external output, current committed source,
compiler dependency admission, source/fixture/binary equality before and after
execution, strict warnings and cross-mode result equality. ASan disables only
LeakSanitizer because this executor does not support its task inspection;
tracked owner wiping and wire descriptor balance are narrower independent
checks. New owner stack rows, all exact compiler commands and executable hashes
remain in the two receipts. No global aggregate/RSS or Android/Windows ABI fit
is established.

Canonical retained data is under`qualification/fresh-owner-43bb0484b/`:
`binding.json`, two deterministic gzip receipts, exact six child stdout/stderr
pairs and the first compilation refusal. The binding records49 current source
inputs and separately labels doubles and real public-controller wire scope.
External binaries/objects are not copied into Git.

For a future source change, the focused commands are:

```sh
python native-android/engine/auth-interop/fresh-character-owner/check_fresh_character_owner.py --source-root . --output NEW_EXTERNAL_DIRECTORY --scope doubles --sanitize
python native-android/engine/auth-interop/fresh-character-owner/check_fresh_character_owner.py --source-root . --output OTHER_NEW_EXTERNAL_DIRECTORY --scope wire --sanitize
```

This source qualification does not admit an actual Auth/DB/Map deployment,
normal version/checksum reference policy, populated/initialized character,
persistent SQL rollback, current world or any READY/character/full-update ACK.
Actual creation would leave a server-allocated UNINITIALIZED container and
requires separately owned same-realm Map readiness, assets and whole fresh DB
cleanup. The current closed terminal offer cannot later resume Map creation.
