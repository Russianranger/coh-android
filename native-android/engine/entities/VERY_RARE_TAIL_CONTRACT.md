# Consecutive very-rare entity suffix

`coh_ent_very_rare_tail` stages the three consecutive original bodies after the
already qualified AFK prefix and before the teammate-buff presence flag:
`entSendOtherSupergroupInfo`, `entSendLevelingpactInfo` and
`entSendLogoutUpdate`. The new module is standalone. It does not change the
existing entity parser, compose a complete entity/ALLENTS transaction, interpret
a selected identity, publish an actor or enable any completion acknowledgment.

The exact original sender and receiver functions are pinned in
`very-rare-tail-source-pins.json`. The checker also pins the enclosing source
statement order. A caller must already know the correct offset from a complete
outer grammar; scanning for a plausible suffix is never valid.

| Order | Wire body staged |
|---|---|
| 1 | Supergroup update flag; optional packed ID; name/emblem; two color words; item-of-power spaces |
| 2 | Optional complete `TaskStatusSend` mission: debug filename, description/owner, task IDs/level, difficulty, alliance, state, timers and all nine status flags |
| 3 | Mission position/type/map/name, or absent-position optional explicit-map branch; optional zowie metadata, seed/map/type/name and raw pool-size string |
| 4 | Ordered reward tokens with name/value/timer; ordered recipe unlimited/count/name records; ordered special-detail name/creation/expiration/flags records |
| 5 | Pact update flag; ID or removal; member count and ordered DBID/name-presence/name records |
| 6 | Logout update, bad-connection bit and optional packed timer quanta |

Absent supergroup update, a zero group ID, absent mission, zero collection
counts, absent pact update, zero pact ID and absent logout update remain distinct
wire events. Empty strings and duplicate records are preserved in wire order.
Recipe counts, task integer/timer fields and token values retain raw 32-bit words;
no signed overflow or timebase conversion is introduced. The raw logout unit is
30 original client ticks, not an admitted authoritative timer.

The module retains named recipe/detail/emblem/task resources without resolving
them. It does not supply authentic dictionaries, filter inventory, update a
compass, split zowie pool text into gameplay state, replace prior generations or
apply stale-packet rules. Both actual dictionary authority and outer-message
state ownership remain required.

## Bounded ownership and refusal

The original pact limit is two members, each with at most 63 bytes plus NUL in its
64-byte `MemberName`. Other limits are explicit local admission bounds: 256 token,
256 recipe and 256 special-detail records; 1,024 bytes per string including NUL;
and a 65,536-byte combined owned string pool. These do not claim corresponding
upper limits on the original dynamic arrays. Any over-limit body is refused,
never truncated or represented by a placeholder. Mission coordinates must be
finite; aligned boolean and auto-width-selector bytes must be canonical.

Each output and workspace is 79,184 bytes on the qualified 64-bit host. They
belong in a caller heap or arena. The maximum aggregate budget is 4 MiB and
charges both full PODs, the entire borrowed input span, an 8 KiB production stack
reservation and all caller-declared retained ownership. No dynamic allocation,
I/O, per-frame work, retained input span or hidden owner exists in the parser.
This is named ownership accounting, not process RSS.

Reader, output, workspace and input spans are checked for pairwise overlap before
any write. Invalid arguments, malformed late logout data, missing collection
records, truncation, nonfinite coordinates and exhausted budgets leave the
reader and output byte-for-byte unchanged. Workspace is private scratch and
unspecified after refusal. The eventual whole-message owner must stage this
suffix together with preceding appearance/taskforce/prefix events and subsequent
buffs/global tails; success here cannot publish earlier partial state.

## Original receiver differences retained explicitly

The pinned original leveling-pact receiver does not consume member bodies when
`oo_packet` is true and the pact ID is nonzero. The original sender still emits
those bodies. The oracle demonstrates the cursor mismatch rather than silently
changing the source function. The native raw parser consumes the complete
producer-defined body, without claiming equivalent stale-state application.

Other source behavior is also deliberately not generalized into an inferred
state machine. A supergroup update clears displayed group name/emblem and assigns
the group ID even on stale packets, while colors and displayed strings have
separate stale guards. Removing a group ID does not destroy its retained group
object. Zero token count retains previous tokens; recipes and details use their
own replacement behavior. A stale zero pact ID can destroy the old pact while
leaving the numeric pact ID unchanged. Original receiver controls exercise these
cases separately; the native module emits only raw events.

Original `entSendOtherSupergroupInfo` advertises the recipe array size but skips
null recipe entries. Such an array can produce an incomplete wire body. A
source-produced null-recipe fixture is retained as a malformed-input refusal;
its unsafe original receiver path is not executed or treated as valid data.

## Qualification

Run `check_very_rare_tail.py --source-root REPO --sanitize --output NEW.json`.
`--prepare-only --fixtures-output FILE` produces the portable native harness
fixtures without rerunning native tests. The optional `--ndk DIR
--android-output DIR` builds ARM64 and x86_64 standalone harnesses; it never
builds an application. No shared workflow, CMake, renderer or JNI edit is needed
for host qualification. Coordinator registration can compile exactly:

- `coh_very_rare_tail.c`
- `../replication/coh_replication.c`
- `test_very_rare_tail.c`, with generated `tail_fixtures.h` on its include path

The native harness uses only the existing replication reader and C library.
Fixture expectations serialize original receiver strings and numeric state
exactly, not through lossy hashes or native-parser-derived expected output.
The original eight complete sender/consumer functions execute with controlled
synthetic owner, dictionary, location and UI shells. The complete enclosing
`sendEntity`/`entReceive` functions and live packets are not executed. Legacy
original bit packing runs at trusted O0 without sanitizers; new parser and native
harness execute independently in release, ASan and UBSan modes. The source and
helper closure, original full files/function bodies, generated fixtures and
native binaries are hashed before/after qualification. C++ linkage is checked.

Cases cover all original branches, bit offsets 0..7, both byte-alignment modes,
mission locations and zowie data, negative source words, string/count boundaries,
duplicate and unknown dictionary names, current consumer state and independently
stale supergroup/logout observations (pact stays fresh in that projection),
source-only prior-state controls and the separate stale-pact cursor defect. Native controls
exhaust every truncation at both canonical alignment profiles, mutate every byte
of those accepted fixtures, exercise malformed counts/strings/scalars/nonfinite
positions, check aggregate budget boundaries and aliases, and run deterministic
random input. Appended later bytes must remain unread.

Host qualification does not establish Android execution, physical AYN Thor
acceptance, a full entity or character transaction, resource binding, live
interoperability or server authority. The existing `coh_ent_full_update_tail`
remains unsupported and the production entity parser still rejects uncomposed
very-rare records. No READY, RECEIVED_CHARACTER or full-update ACK is enabled.
