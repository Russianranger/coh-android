# Worker C recovery and protocol continuation

Base remote: `66146bbee161304ba4e4e14cbb53cba6958fb03b`.
Isolated worker source: `01c3db24e695e0eb27ded47efb8abcab613a7379`.
Capture receipt provenance follow-up:
`46e4e3373b10639dae53023faf217d250a963227`.
Only the coordinator publishes to `native-android`; this worker did not push,
touch accepted APKs/shared JNI/workflows, change the server or start a real shard.

## Unpublished recovery

The former Worker C entity/parser commits were already present in the recovered
remote tree and were reused. Its `engine/world-capture/` seven-file candidate was
unpublished. All seven original files were copied byte-exact, their hashes are
in `world-capture/recovery.json`, and their original bytes are retained in
`world-capture/qualification/recovery-20261016/original-unpublished-world-capture.tar.gz`
(11,864 bytes, SHA256
`527bae67dae058116321d696291d98535f890688bf2aa483d63322aaf8fc9259`).
The prior worktree remains unchanged. This candidate had not reached qualified
completion: two test-harness failures were recovered and corrected, without
weakening runtime confirmation. No unpublished full-update or actor-publication
implementation was found in that candidate.

## New closed source branch

The complete standalone badge update and badge monitor wire bodies are now
implemented in `engine/entity-globals/coh_badges.*`. They preserve all player,
supergroup, debug, owned/visible/known/progress, optional source filename, recent
history and ten raw monitor-ID branches. This closes the exact source grammar
located after PowerModeUpdate and before generic inventory. It does not close
PowerInfoUpdate, dictionary/UI semantics or any enclosing ALLENTS transaction.

Each update/output workspace is 168,884 bytes. The declared aggregate limit is
4 MiB and includes both PODs, input bytes, an 8 KiB stack reserve and retained
caller data. Ordered duplicate badge IDs remain ordered. Invalid index/count,
filename/pool overflow, malformed flags/pack values and partial late tails leave
the reader/output unchanged. The badge and monitor calls are atomic individually;
the future whole-message owner must stage both together with all remaining data.

The original complete sender/receiver and monitor sender/receiver execute in
170 fixtures; 150 satisfy the declared native bounds and 20 are deliberate
source-valid filename-limit refusals. Badge tests pass 1,038,766 checks in each
release/ASan/UBSan mode, including 191,830 truncations and 10,000 random inputs.
Existing power modes are unchanged. Their combined executable passes 6,968,876
checks in each mode. C++ links and calls all three public APIs. Both native and
original source identities are stable before/after qualification, with clean
worktree receipts at source `01c3db24e`. Worker F independently verified the
21 native inputs, eight original file pins, four grammar functions and results;
no blocking findings. Host and review receipts are under
`entity-globals/qualification/recovery-20261016/`.

The existing globals checker emits one guarded `fixtures.h` for both suites:
SHA256 `31ab9c4aed3756c15006d4d4ff4c00e4727a73bf805a5b18378e53d386030dc1`.
Its existing ABI build path includes both production parsers and both test
sources, with exact source maps and nested badge results. No separate fixture
binding is needed. A local NDK/emulator was unavailable, so fresh ARM64/x86_64
builds and Android 13 execution are coordinator work. Prior Android acceptance
for unchanged modules is preserved but does not qualify these new badge bytes.

## Recovered capture qualification

The diagnostic capture reuses the unchanged local session and restricts map
commands to CONNECT, REQSHORTCUTS and REQSCENE. It validates and owns complete
GROUPS bytes, checks exact footer/count/slot/map/lease receipts, writes a new
mode-0600 output after cleanup and never sends READY/REQALLENTS/full-update ACK.
Expected DBID is explicitly an external row assertion because the DB wire does
not provide it. Nonzero source/generation hashes are attestations, not self-made
authority. A and B can use these diagnostic bytes only after an independently
staged real runtime supplies the matching source/session transaction.

The restored driver now supports sparse checkout oracles and correctly separates
synthetic link ID 17 from map ID 5; wrong-map refusal is explicit. Stage/view
disjoint-memory enforcement was added. Final source `46e4e3373` passed 439,300
checks per release/ASan/UBSan mode, 106,522 truncation samples, 10,000 malformed
inputs and 44 original GROUPS fixtures (32 admitted new worlds). Six independent
UDP cases per mode cover success, wrong footer, wrong character, wrong endpoint,
wrong map and preexisting output preservation. Both sockets close in every case.
Worker A independently reviewed the capture with no blocking findings.

Final capture receipts bind all native input headers/C files, original producer
identity, fixture identity, clean git revision/tree and before/after source
stability. The host probe SHA256 is
`1290c1df5d412a0d85c61b47ec37089305c3bced0630a11886b8fdc2a18790cd`.
The local retained executable is
`/tmp/coh-capture-final-provenance-c/coh-world-capture-probe`; source and evidence
are permanent repository content. No real MapServer capture or Android/Thor
execution occurred. The known authentic 12,179,670-byte saved catalog was neither
recreated nor modified. A stack-usage audit and allocation-failure injection
remain optional strengthening for future deployment, as noted by A's review.

## Remaining authoritative transaction work

`entities/INITIAL_UPDATE_CLOSURE.md` remains the source-order ledger. Specifically:

1. Compose already qualified costume/power/title/taskforce/rare metadata with
   actual dictionary generations and exact retain/clear/stale semantics in the
   complete entity record. Supergroup/leveling-pact/logout/buff continuations and
   unsupported interpolation cases still remain.
2. Reuse the complete qualified `character_Send` wire metadata module. Bind actual
   class/origin/base-power/reward/inventory dictionaries and the shared-powerset
   profile, then complete the surrounding `receiveCharacterFromServer` flags,
   auth data, original set names, tray/UI/help/windows, reward tokens, chat,
   keybind/options, friends and monitoring tails. Raw metadata is not original
   gameplay consumer application or a selected-player certificate.
3. Compose control and deletes at the real offset, implement full PowerInfoUpdate
   and all remaining inventory/invention/team/supergroup/league/attribute/dynamic
   group/sky/slave tails, then require exact packet end and whole-message rollback.
4. Validate selected DBID/self ownership, entity generation, authoritative pose,
   source appearance/animation references and matching scene/resource generation
   before minting any immutable actor snapshot or completion acknowledgment.
5. Obtain complete actual source/runtime packets and dictionary identities after
   prerequisites are ready. The capture candidate solves diagnostic GROUPS
   ownership, not missing ALLENTS grammar or dictionary authority.

`coh_ent_full_update_tail` remains unsupported; no authoritative actor conversion,
READY, RECEIVED_CHARACTER or full-update ACK was added. The renderer must retain
its complete-transaction prerequisite. Gates 25–27 and first server-authoritative
native world entry remain open. No new Combined APK or repeat physical test is
justified by this standalone tranche alone.
