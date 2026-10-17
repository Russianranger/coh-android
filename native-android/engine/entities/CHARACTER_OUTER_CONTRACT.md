# Complete raw outer-character wire transaction

`coh_character_tail_read` consumes original outer groups5..6: ordered reward and
active-token lists; lfg/hidden/supergroup/skills/buff/dock/inspiration/features;
chat settings; titles; repeated description/motto/comment; key profile and256
keybind records; saved114-field option schema or default mouse settings; eight
dividers; control flags; friends; ten combat monitor records; rename. It stops
at the final inline wire bit in `sendCharacterToClient`. Later contact/task/clue/
mission source calls send separate packets. Enclosing ALLENTS still has further
fields and must not infer exact message end from this boundary.

`coh_character_outer_read` now composes all six raw outer groups in actual order:
account/auth prefix→whole character_Send metadata→set names/ally/PvP/self stats→
tray/name/strings/help/windows→complete groups5..6. Every child receives only the
previous child's actual validated cursor. Failure in the final rename rolls back
all account bytes, character metadata, stats and UI/account tails together. The
old groups1..4 implementation and accepted application paths remain unchanged.

These are raw wire transactions. They do not execute original character_Receive
creation/dictionary application, resolve class/origin/power references, validate
selected DBID/entity ownership, apply prior state or admit original gameplay
semantics. Required semantic presence masks and original generation/resource
binding still belong to the complete initial-update owner. No actor conversion,
certification token, READY, RECEIVED_CHARACTER or full-update ACK is supplied.
Completing this nested body does not validate enclosing entity/control/delete/
power-info/inventory/team/global tails or exact packet end.

Raw ordered token names/value/timers preserve duplicates and unknown identifiers.
Chat tabs use original byte-array alignment even in bit-packed mode; all20 two-
word system arrays retain raw bytes. Raw titles and repeated descriptions remain
separate events; no HTML rewriting occurs. Key commands are retained, never
executed. Wire key/profile/modifier are preserved rather than overwritten by
source development-profile substitution or key masks. Options retain114 source
enum-ordered raw words; floats must be finite. Default mouse branch is distinct.
All eight wire dividers survive even when original UI application would ignore
later dividers after a zero first value. Friends preserve presence, full-update
word, unresolved class/origin indices (including UINT32_MAX), online/map branches.
Combat monitors preserve separate presence/value words. Rename never invokes UI.

Local token count256 per list and name1024-byte limits are explicit admission
bounds, not asserted original dynamic-array maxima. Fixed source limits are
hash-pinned and checked: friends25, chat5/20/15, tab/channel name capacities19/22,
keybinds256, monitors10. Original fixed receiver strings refuse overflow instead
of truncating. The640KiB pool can retain all512 maximum token names plus256
maximum key-command strings. All spans are pairwise disjoint with overflow
checks before writes. Output/workspace belong on caller heap or arena; no hidden
allocation or borrowed input survives the synchronous call.

Tail output/workspace are679,280 bytes each. Full outer output is1,555,768 bytes
and workspace4,437,640 bytes. Full named fixed admission is6,026,176 bytes,
including32KiB stack reserve, before input/caller-retained ownership. Existing8MiB
cap remains. Child extra-retained accounting excludes each child's output,
workspace and stack reservation before the child recharges those bytes, naming
every owned byte once. Conservative sum of all reachable emitted host frames is
3,464 bytes within32KiB. This is codec ownership accounting, not whole-app RSS.
A caller must separately admit complete world/dictionary/render ownership.

F's independently authored provider `group56_oracle.py` executes unchanged whole
original group5/6 inline sender/consumer blocks and complete chat, titles,
keybind, friend, option/divider/monitor helpers using explicit dictionary/UI/
storage shells. Whole original character_Receive and enclosing complete producer
do not execute. Chat migration/default behavior is outside its already-migrated
fixture profile. Every case includes complete numeric/string observations and an
independent Python decoder agreement. The native harness compares every semantic
POD byte and owned string-pool byte against those independently generated
expectations, with cursor fields checked separately. Source/provider/native/helper
hashes are stable before/after, including option-width host-proof dependency.

Tail release/ASan/UBSan each pass211,918 checks:100 original cases,2,024 cuts,
19,390 mutations,1,000 random bodies, plus explicit too-many-token/friend,
overlong token/key-command and nonfinite late-mouse controls. Full outer modes
each pass22,641 checks over70 synthetic joins of independently source-produced
first3/group4/group5..6 bodies at matching alignment, with2,986 cuts and6,204
mutations. These joins validate composition, not an authentic packet or whole
sendCharacterToClient execution. All later bytes remain unread. C++ linkage and
bounded stack checks pass. Optional NDK builds are available; no Android/emulator/
Thor execution, new APK or live-authority acceptance occurred in this environment.
