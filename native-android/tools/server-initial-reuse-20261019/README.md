# Reuse the repaired original Map observer with a changed native receiver

This role reuses one already successful observer PE. It does not rebuild Map,
rewrite its compile receipt, or bypass the original verifier's historical source
revision check. The root workflow owns the exact artifact ID, run, attempt,
revision, ZIP hash and receipt hash in its source-pinned origin file.

The root's `admit_reused_map.py` first applies the unchanged GitHub artifact
metadata/member validators to that explicit historical origin. Its exact
`server-initial-observer-recovery.json` sidecar preserves the distinct historical
compile and current execution identities. SHA256 of that sidecar is required by
both the reuse preflight and transaction wrapper.

`reuse.py` requires a separate clean checkout at the actual compile revision,
which must be an ancestor of the current checkout. It invokes the unchanged
historical `recipe.py verify-artifact` in an isolated Python process. That checks
the historical source role, complete PE/source inventory, original stage
reversal and exact original compile receipt. The reuse helper separately requires
the current compiler supplier closure to equal the original receipt's complete
closure, and verifies every supplier against both historical Git and both raw
checkouts. It brackets revision, supplier, receipt, recovery and PE identities.
Native protocol files outside this compiler role may change; compiler supplier
additions, removals or changed bytes refuse reuse.

From the current checkout, after exact artifact recovery:

```sh
python3 native-android/tools/server-initial-reuse-20261019/reuse.py \
  --source-root . \
  --historical-source-root "$GITHUB_WORKSPACE/historical-map" \
  --source-revision "$GITHUB_SHA" \
  --historical-source-revision cf1ab9f7e872467473bc50da822ee6cfc041d639 \
  --compile-directory "$RUNNER_TEMP/groups-inputs/server-initial-observer" \
  --receipt-sha256 "$INITIAL_SERVER_BUILD_SHA256" \
  --artifact-admission-sha256 "$MAP_REUSE_ARTIFACT_ADMISSION_SHA256"
```

Use this directory's `runtime.py capture` with all existing transaction arguments,
plus `--historical-source-root`, `--historical-source-revision` and
`--artifact-admission-sha256`. Use this directory's `runtime.py project` for the
result. The original service supervisor, fixture, authentication/version policy,
native receipt admission, output ownership and cleanup remain in force. Scoped
callable adapters select the historical verification without changing either
recipe. Both new executed sources enter the current orchestration raw/Git
closure. The explicit reuse proof enters the private run identity before Map
startup; final reporting must match it. The public projection exposes only fixed
revision/hash/artifact identifiers, counts and Boolean scope fields.

The current retained receive role must independently match its current compiled
native source closure; Map reuse does not authorize stale native code. The new
public proof grants neither ordinary authentication nor application ACK/world
authority. The Map PE remains a nonshipping hosted diagnostic, distinct from the
physical device server.

`check_reuse.py --output <new-file>` exercises only this new envelope. Final
`qualification/controls-04.json` passes 23 methods using real temporary Git
checkouts, an isolated synthetic historical verifier/image, and explicit doubles
for the accepted runtime lifecycle/projector. No original compiler, server,
physical device or accepted qualifier is executed by these controls. Earlier
control receipts remain retained with their original scopes and failures.
