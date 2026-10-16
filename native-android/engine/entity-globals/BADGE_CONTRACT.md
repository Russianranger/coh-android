# Complete badge and monitor wire bodies

The recovery continuation adds `coh_global_badges` and
`coh_global_badge_monitor`. They consume the entire original standalone
`entity_ReceiveBadgeUpdate` and `badgeMonitor_ReceiveInfo` wire bodies. Neither
function supplies an ALLENTS entry offset, selected player identity, badge
dictionary authority, full initial transaction, actor snapshot or acknowledgment.
The existing power-mode implementation is unchanged.

Original source order is PowerInfoUpdate, PowerModeUpdate, BadgeUpdate,
full-update-only BadgeMonitor, generic inventory, invention, workshop, team,
supergroup, league, attribute descriptions, dynamic groups, sky and optional
slave orientation. The complete preceding PowerInfoUpdate and following tails
still need implementation/composition. Parsing badge events does not permit
skipping any of them.

`coh_global_badges` retains raw debug mode, ordered player and supergroup records,
owned/visible/known/progress fields, optional filenames and optional recent
history. The source capacities are 4,096 player entries, 1,050 supergroup entries
and 50 recent entries. The sender excludes zero indices; indices outside the
corresponding destination array, including negative signed source indices, are
refused. Duplicate valid indices are retained in exact wire order. The original
consumer's final numeric state follows the last such record. An absent history
is a retain event, whereas a present empty history clears it. Supergroup presence
does not imply that a source supergroup owner/dictionary has been admitted.

Filename presence and an explicit empty string are distinct. Each transmitted
record without a filename clears that record's previous filename in the original
consumer. An optional filename is limited here to 1,023 non-NUL bytes. The total
NUL-inclusive pool is 65,536 bytes. These are explicit native admission limits,
not claims about source path maxima. Over-limit source-produced fixtures are
retained as refusal controls. Filenames are diagnostic strings, never paths to
open or execute.

The monitor body contains exactly ten optional pack8 integer bit patterns.
Zero, duplicates, order and all raw 32-bit IDs survive. The original subsequent
`badgeMonitor_CheckAndSortInfo` depends on actual dictionaries and player state;
it is deliberately outside this raw staging API. A monitor ID is not an
authorized badge, and dictionary-dependent sorting has not been qualified.

## Ownership and qualification

The pointer-free update and caller workspace each occupy 168,884 bytes; a monitor
is 40 bytes. The badge API charges output, workspace, complete input byte span,
an 8 KiB stack reserve and caller-retained data against a maximum 4 MiB aggregate
limit. Old output retained separately by a whole-message transaction must be
included in caller-retained data. This is named component ownership, not process
RSS or total game memory. There are no parser allocations, I/O, UI callbacks or
retained packet pointers. Place the large PODs on a heap/arena, never an Android
thread stack. Reader/output/workspace/input must be disjoint and single-owner.
Reader and output roll back byte-for-byte on every error; workspace is disposable.
Each standalone body is atomic individually. A successful badge parse followed
by a failed monitor parse does not undo that earlier badge output. The enclosing
whole-message owner must stage both PODs and its reader and publish neither until
all later transaction fields and exact packet end validate.

`check_badges.py` pins eight original files and executes the complete unchanged
original badge sender, badge receiver, monitor sender and monitor receiver,
including original BitStream and optional-scalar functions. The original source
runs only on trusted padded fixtures at O0. Test owner/dictionary/earray shells
provide fixed valid records; UI effects are no-ops. The monitor sort hook observes
incoming IDs without claiming original dictionary filtering/sorting.
Numeric destination state, recent history, raw monitor IDs and filename values
are compared with native events. Filename projection uses a non-security FNV
comparison hash, which is not provenance or runtime authority.

There are 170 original-producer/consumer fixtures over ordinary offsets 0–7 and
aligned offsets 0/8. Of these, 150 fit the declared native bounds and 20 are
deliberately refused filename-length/pool cases. They include full/dirty updates,
empty and maximal lists, duplicates, ownership variants, debug levels, source
filenames, 50-entry/empty/retained history and full raw monitor integer patterns.
The native suite adds 191,830 complete/sampled truncations, 10,000 random inputs,
invalid IDs/counts, malformed flags/pack overflow, exact memory budgets, alias
refusal and late-tail rollback. Each release/ASan/UBSan mode initially passed
1,038,766 checks. LeakSanitizer cannot run under this executor's ptrace context;
ASan/UBSan and explicit caller allocation/free checks remain enabled.

The existing globals checker now embeds this suite alongside unchanged power
modes. Both fixture sets occupy one guarded `fixtures.h`, so the existing exact
fixture SHA256 binds both standalone Android binaries. All added inputs are in
the source receipt. No accepted APK or server runtime is changed. Android build
and Android 13 execution require fresh coordinator evidence; physical Thor and
authenticated/server-authoritative acceptance are not implied by host results.
