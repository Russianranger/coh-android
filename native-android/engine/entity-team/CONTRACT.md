# Raw original team and league lists

`coh_team_list_read` reads the complete body of either `team_sendList` or
`league_sendList`, selected explicitly by the caller. The original source width
for optional team/league identity is packed22, not packed20. Teams admit the
source maximum8 members, leagues48. The original source sender reorders mentor
or leader first; native staging retains that actual wire order unchanged.

Each member retains its raw DBID, on-map flag, conditional off-map changed flag,
conditional name/map strings, and for leagues team leader and lock words.
Absent names/maps remain absent (zeroed storage). They are not invented from
prior state or a local entity lookup. The qualified original consumer's applied
state can differ from these wire fields; staging does not apply either prior
state or local UI/entity semantics. A selected-character DBID is not established
by any of these raw team rows. Unknown IDs and numeric lock words remain raw;
no team membership, dictionary or gameplay authority follows from parsing them.

Identity absence terminates the league body immediately; the team body still
contains taskforce and LFG fields. Presence followed by a raw zero identity
retains that distinction and follows the source zero-ID tail branch. Strings
are bounded by the source64-byte member name and256-byte map storage, including
NUL. Counts and scalar-width overflow fail before any out-of-bounds access.

Output/workspace must be caller-owned heap or arena storage. All reader/input/
output/workspace spans are pairwise disjoint and overflow-checked. Input, both
PODs, a4096-byte conservative stack reserve and caller-retained storage must fit
the8MiB aggregate ceiling. The decoder allocates nothing and commits the caller
reader and output only after the entire selected list validates. Workspace is
scratch. It stops at the exact list cursor, preserving subsequent commands.
It does not assume this is the packet boundary or a complete ALLENTS update.

`check.py` executes F's whole unchanged original team and league producers and
consumers using explicit fixture storage, entity lookup, localization and UI
shells. Exact field projections and cursors are compared against1000 source
fixtures across both alignments, mentor/leader ordering, full/delta map names,
empty lists and48-member leagues. Native release/ASan/UBSan additionally exercise
truncation, mutation, malformed count, budget, alias and random-input rollback.
C++ linkage and conservative emitted reachable stack frames are checked.
Original source oracles run unsanitized. Source and provider hashes are pinned.

This is independently qualified raw list staging. It is not the enclosing
team-up-to-date flag or global inventory/team/supergroup/league transaction,
source dictionary admission, Android execution, authoritative actor publication,
initial-update acknowledgment or live server acceptance.
