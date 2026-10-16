# Recovery and next-milestone scope

The recovered remote and initially clean primary checkout were at
`131c806cfff7fc0e162a51f47999ea8e30f4e705`, the completed 0.1.5 Return to launcher
qualification/handoff. This supersedes the much earlier `2c32f568...` checkpoint
in the initial recovery request. Existing successful workflow `38818477241` and
its exact 0.1.5 APK remain preserved; it was not restarted because an agent had
stopped responding. The recovered stopping point was a natural qualified handoff,
with the next compressed-scene receive work explicitly deferred.

No actual stalled process was established. Local process enumeration failed with
`fatal library error, lookup self`; this is a visibility limitation, not proof
that no older subprocess existed. There is no local accelerated Android emulator
or independently available compatible disposable game server for this batch.
Hosted Android qualification and the later Thor run have separate scopes.

Legitimate earlier unpublished files were preserved in their existing worktrees:

- `batch-immutable`: older import publication and setup changes/tests.
- `coh-memory-policy`: staged memory-policy work/checks.
- `fix-combined-build-012`: older app/runtime/build/tools changes.
- `fix-combined-build-012-qualified`: earlier qualification-driver changes.
- `fix-server-memory`: older runtime/test changes.
- `fix-server-runtime`: older runtime/check/test changes.

These are earlier partial states rather than a reason to overwrite the latest
qualified branch. They were left untouched, not discarded, reset or blindly
reapplied. Existing temporary inputs, SDK/NDK/crypto outputs, donor, accepted scene
APK and previous deliveries were reused after their existing pin checks. No
unpublished root change needed recovery before new implementation began.

Five workers actually ran concurrently in isolated worktrees with nonoverlapping
production ownership: network/UDP, replication, Map/local, Android tooling/build,
and independent source/JNI review. Review delegated one UDP test-file change under
the network owner's agreement. The coordinator owns JNI/UI/release integration
and the final handoff. Local integration history is retained on
`preserved/combined-016-local-validation`; no history was reset or force-pushed.

The new runtime source is `7c9cfdb9d5f87c2297f8772fc3aeff528577728f`, with tree
`15cce2275e7d6c55b4b4f0acddd62c6803174e76`, identical to the clean locally tested
integration `648ebf2d0c2cca9dfa5ef9acf9b1fe705ffe9c01`. Publication freshly checked
the remote and used an expected-parent, non-force update of `native-android`.
Neither `main` nor any imported data, account, character or report was modified.

The exact 0.1.4 Thor evidence already proves local-server startup/clean stop,
native DB character list/selection, initial Map CONNECT/SHORTCUTS and REQSCENE.
It ends before scene-prefix parsing with a queued decompression `COH_LIMIT`.
The failed body's declared size was not recorded. This batch adds one bounded
owned decoded Map body and numeric failure receipts rather than repeating Gates
22–24 or rewriting accepted transport kernels.

Gate 25 advances bounded large-message transport and lifecycle qualification;
new authentic-server scene reception remains pending. Gate 26 retains the
existing real local development DB/character handoff, with encrypted AuthServer
authentication still pending. Gate 27 advances bounded GROUPS-prefix admission
and source-tail contracts; complete scene/entity replication, selected-character
identity/position and authoritative rendering remain pending. All Gate 1–24
physical acceptance is preserved within its previously documented scope.

Authentic encrypted login is still blocked on a separately authorized compatible
AuthServer session and its native integration/evidence. Combined's current manual
test uses the local `UseFakeAuth` DB path; its real DB/Map replies do not establish
encrypted AuthServer authentication. A compatible full server cannot be executed
in this work environment. The new Thor report must first establish actual large
scene reception; full scene/entity decoders and source-asset resolution then
remain necessary before authoritative world rendering can be accepted.

The accepted standalone Session Client 0.3.0 remains available from
[workflow 38673357918 / artifact 11945445541](https://github.com/Russianranger/coh-android/actions/runs/38673357918/artifacts/11945445541),
APK SHA256 `75ff158c3e1387671ff2a47f0aa6a126b9c93389fd16685d78a9fcf4ed164639`.
Its consolidated instructions remain
[`native-android/session-client/THOR-TEST.md`](../../../../session-client/THOR-TEST.md).
It was not rebuilt. The user's later physical acceptance of Gates 22–24
supersedes the original awaiting-device checkpoint, within the documented scope.

Next independent work can proceed on: (1) a transactional, source-oracle-qualified
GROUPS tail decoder with explicit unsupported base/raid handling; (2) imported
library/asset graph resolution and checksum contracts; (3) initial entity identity,
server position and replication lifecycle; and (4) encrypted AuthServer/session
negotiation tests with an authorized real disposable server. Final integration
must keep these dependencies. Separately, allowlisted cache/graph reuse outcomes
and a clean Stop/restart timing comparison can address startup diagnostics without
weakening runtime ownership or claiming an unmeasured speed improvement.
