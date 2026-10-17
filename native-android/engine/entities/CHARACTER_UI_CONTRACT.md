# Raw outer character group4 and composed groups1..4

`coh_character_ui_read` stages the exact `sendTray` through final `sendWindow`
body of `sendCharacterToClient`. Original counts are pinned: eight builds, nine
player trays, ten slots per tray, four current-tray words, 128 help words and five
latest-help words, then 128 window records. Power/inspiration indices, default
power, macro strings, all raw tray types, modes, name, motto, description, help
words and window fields remain ordered and owned. No field is dropped because
its resource identifier is unknown. Raw description retains HTML-like text;
original receiver display rewriting is only projected inside fixture tests.
Macros are never executed and windows/trays are never applied to gameplay/UI.

Tray type1 carries two raw32 words; type2 two packed3 words; macro types6/17
carry three strings of capacities256/32/256. Other pinned-source five-bit types
carry no further body. This does not establish gameplay support for them.
All 720 maximum-size macro bodies fit the explicit391,680-byte text pool.
The parser refuses strings exceeding original receiver capacities rather than
truncating. Window fields retain raw signed words, optional dimensions and
scale presence/raw IEEE bits. Nonfinite scale is refused before publication.
Original zero/absent-scale-to1 display conversion is not applied to raw staging.

Output/workspace are426,056 bytes each. They belong on caller heap/arena. The
8MiB cap charges input, both full PODs,4KiB stack reservation and declared retained
ownership. Reader/output remain unchanged on every refusal. All input/reader/
output/workspace spans are pairwise disjoint with pointer-span overflow refusal.
No allocation, retained input, dictionary lookup, UI mutation or ACK occurs.
Success ends immediately before the reward-token count and is incomplete.

`coh_character_creation_read` composes initial groups1..3 and this group4 in one
transaction. The second child starts at the first child's actual validated cursor;
no caller offset or sentinel search can authorize it. Failure in the final
window leaves every prior account/character/stat/tray/text/help field unpublished.
Output is876,464 bytes and workspace2,202,592 bytes. Aggregate8MiB cap charges
input+complete output+workspace+16KiB stack reserve+retained ownership once.
Each child already charges its own output/workspace/stack; parent passes every
other named byte as retained ownership. Source checks back the reserve with a
conservative sum of all reachable compiler-emitted bounded frames.

Independent F provider is at
`native-android/combined-client/diagnostics/character-outer-20261017/`.
The UI checker hashes all four provider files and original source pins before
and after. Exact original group4 inline sender/consumer blocks and whole tray
iterator/sender/receiver, strings/help/window functions execute with explicit
synthetic storage/dictionary/UI shells. Original window display application is
disabled under TEST_CLIENT. These are source fixtures, not authentic captures.
Original writer runs trusted O0 unsanitized; production/tests separately run
release/ASan/UBSan and C++ linkage. Optional NDK flags build standalone harnesses.

UI qualification:60 exact source fixtures,386,166 checks in each mode,3,581
truncations,24,984 byte mutations and1,000 random bodies. Every raw fixture slot,
string/help/window field is asserted; original consumer fixture projections are
compared separately. Atomic groups1..4 qualification:70 source-component
compositions,17,979 checks per mode,2,544 truncations and4,676 mutations. Inputs
are exact bit concatenations of independently source-produced groups1..3 and
group4 at matching alignment. They do not execute whole sendCharacterToClient
or character_Receive, nor prove one real server generation. Later bytes stay unread;
budget minimum/refusal, aliases and late-field rollback are checked.

Full-character groups5..6 (tokens/chat/keybinds/options/friends/etc.), global
ALLENTS tails, exact-end, selected identity, dictionary/resource authority and
prior-state application remain open. Neither raw prefix can produce an actor,
READY, RECEIVED_CHARACTER or full-update completion acknowledgment. No accepted
APK, protected gameplay module, renderer/JNI, shared CMake or workflow changed.
