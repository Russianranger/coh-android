# Source evidence and compatibility boundary

The recovered, read-only `upstream/ouroboros` source and `upstream/i24` data
trees supplied the evidence. Their checked-out parent repository commit cannot
identify an upstream source revision, so this module does not invent one.
Exact SHA256 file identities are recorded in
`fixtures/source_graph.json:source_sha256` and rechecked by the standalone driver.

| Original file/function | Admitted behavior |
| --- | --- |
| `Common/seq/TriggeredMove.h`, `seq.h` | 876 state bits; 12 sparse requirements; 14 interruption words; five cycle choices; original timing flag values |
| `seqload.c:setSparseBit`, `setBitsFromString`, `seqCacheMovesPerBit` | Unique append-order sparse requirements; first declared required bit is search anchor; moves with no requirements or no interrupts do not enter cached interrupt search |
| `seqload.c:seqLoadTimeProcessor` | Interruption string/membership overlap, including move-name membership; fixture IRQ IDs are local equivalent names rather than serialized full-player IDs |
| `seqstate.h`, `seqstate.c:seqLoadStateBits`, `statebits.statebits` | Fixed code IDs followed by data-file insertion order, first occurrence wins; no alphabetical state renumbering |
| `seqsequence.c:sparseRequiresMet` | All required bits must be set |
| `seqSearchInterrupts` | Highest valid candidate priority, group interruption, source tie ordering/incrementor, explicit supplied qrand value |
| `seqProcessInst` | State/move-change search, force search, immediate requirements release, FinishCycle deferral, transition order |
| `seqStep`, `seqCycleFrame` | TypeGfx scale precedence, strict last frame, one-wrap fallback, complex cycles and NextMove |
| `seqSetMove` | Phase preservation rules and previous-frame reset; draw side effect excluded |
| `libs/UtilitiesLib/src/utils/mathutil.c:randUIntGivenSeed` | Source wrapping 32-bit Windows random-cycle arithmetic, expressed with unsigned math to remove signed-overflow undefined behavior |
| `i24/data/sequencers/player.txt`, `player/motion.inc` | Relative declaration order of selected graph files |
| `motion_fall.inc`, `motion_jump.inc`, `powers.inc`, `reactions.inc`, `emotes.inc` and selected member includes | Eighteen named original move definitions; twelve ranges with explicitly authored first and last frame; six unresolved durations |

`tools/original_oracle.py` extracts eight unedited functions from
`seqsequence.c` plus the original random function to temporary build output.
Minimal host structs and graph-array adapters replace external facilities;
rendering, debug, ragdoll, predicted-network transmission and actor-size scaling
calculation are excluded. The oracle receives the same explicit scale and random
sample as the module. It compares move, frame, previous-frame, tie incrementor
and predictive random seed after every admitted update. It is independent
original-kernel execution, not a second call to the new implementation.

`tools/source_fixture.py` is intentionally a restricted metadata exporter, not
the game's complete parser. It expands the selected Member includes, preserves
source requirement/declaration order, duplicates neither character clips nor
decoded poses, and refuses a selected unhandled CycleMove. Unselected external
NextMoves remain unresolved. Reduced-graph timing parity is not a claim about
all possible moves competing in the full player graph. The public simulation
already accepts additional data-driven moves and source complex-cycle targets;
the full graph importer remains unqualified.

The accepted `animation/coh_animation.{h,c}` kernel is used read-only through a
thin pose adapter. Existing ground locomotion and scene implementations are
neither included as fixture replacements nor modified. New clips must pass that
decoder's admitted raw-format and hierarchy requirements before any renderer
or physical-device parity claim.
