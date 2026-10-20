# Original costume receiver with bounded platform shims

This compiles and executes the whole pinned original `costume_receive`,
`getCachedIndexedString`, `getCachedIndexedColor`, `pktGetIndexedString`,
`pktGetIndexedGeneric`, `pktGetF` and original bodytype table/count getter.
`prepare_original_costume_receive.py --check` compares every emitted function
against its exact source pins. Packet field order is original source code.

Thin adapters provide bounded existing `CohRepReader` scalar/Pack reads,
finite-float checks, literal scratch, original member subsets and preallocated
parts. The original function's cache globals are macro-mapped to each call's
typed scratch. Its reset, count flag, default-count assignment, bodytype/count
validation and complete part loop are unchanged. The caller supplies the local
catalog count verified from the pinned `.bp`/BodyParts data. This introduces no
producer lease, runtime generation policy, registry or new admission gate.
The current shipping caller can use the independently verified local count28;
this module does not hardcode28 or use native capacity30 as a default.

Both flag0/default and flag1/Pack4 paths reach the same original validation.
Literal, absent and cache-hit paths can finish the entire costume, including
28 parts and both float-scale profiles. At an indexed ordinary/extra string or
palette reference, execution stops in the original default-width dependency
before reading its index Pack. No table width, string, color or skipped part
is fabricated. The result records the exact cursor, table kind, current source
field/part, framing validation and completed cached-string/color progress.
`strings_read` counts successful cached-string calls including optional names;
direct extra-info strings are identified by field/cursor. `parts_read` counts
fully preceding parts conservatively until whole-costume success.
For example, when the first geometry uses an indexed key, it advances three
packed flags beyond part-count framing, then requires the ordinary string table.
The corresponding byte-aligned profile advances24bits. A literal geometry can
advance to a later texture/color/extra-info lookup instead.

The original non-debug profile is fixed; typed/debug packet layouts are not
silently interpreted. Safety shims preserve existing native bounds: at most
30 part pointers,119 cache entries,259-byte NUL-terminated literal payloads,
finite floats and signed32 packed count/bodytype values. Invalid rounded Boolean
widths, empty/invalid cache hits, cache exhaustion and truncation stop before
the original unchecked storage access. A valid complete costume returns COH_OK
only for that original wire body. Entity/world authority or application ACK
does not follow.

The actual typed workspace union occupies65,536bytes off stack. There is no
char-array-to-unrelated-struct cast and no new heap allocation. Every source
pointer/literal/cache and partial scratch byte is wiped before return. The
caller retains its original reader and owns the report. Pairwise control/input/
workspace aliases, endpoint overflow and malformed API descriptors refuse
without modifying output. The caller must reserve the actual workspace,
packet/report,4,096-byte source call-stack allowance and every retained resource
inside the existing8MiB initial budget; this module creates no independent
process-budget claim. Emitted reached native frames sum conservatively to680
bytes in the qualified host release build. These are named payload/stack
reservations, not Android RSS/PSS or physical Thor measurements.

The checker runs64 fixtures produced by the unchanged original costume sender
and original BitStream implementation. They cover packed/unpacked scalar modes,
unaligned packed starts, zero/one/four/28parts, default/explicit framing,
optional names, both scale profiles, repeated string/color cache hits and
extra-info strings. Sender stash adapters force literal misses, so no synthetic
indexed key is accepted. Independent native cases exercise exact unknown ordinary/
palette/extra boundaries, every truncation of a complete empty body, all nine
source bodytypes, invalid counts/bodytypes, packed overflow, NaN, rounded flags,
cache capacity/index refusal, literal endpoints and complete workspace wiping.
Release/ASan/UBSan each passed27,587checks over the same frozen compiled source.
The source BitStream producer retains its inherited O0 unsanitized alias profile;
only the new source-consumer adapter is sanitizer-qualified. LeakSanitizer is
explicitly disabled; no allocation is introduced to fault-inject.

Existing reusable dictionary data is already present at
`entities/qualification/costume-builder-20261017/offline-primary-slots.bin.gz`:
32768 ordinary slots/13209 keys,256 extra slots/156keys,512 palette slots/224keys.
Its raw641477-byte complete source-built projection preserves holes and first
duplicate spelling. The existing dictionary loader/parser can consume full slots
without another builder or owner layer. To connect those slots to this original
receiver, add thin lookup adapters to the existing dictionary data API. What is
currently missing is the actual local server costume/supergroup-color input
comparison; the recovered93-entry server-generated bin bundle contains none of
those inputs. A run/producer lease is not required to describe that concrete
missing file comparison. The next physical report should identify the actual
first indexed dependency rather than assume all costume fields are unknown.

```sh
flock /tmp/coh-cycle-build.lock python3 \
  native-android/engine/entities/check_original_costume_receive.py \
  --source-root . --work /tmp/fresh-original-costume \
  --output /tmp/original-costume.json
```

The bounded outer adapter (`coh_original_ent_costume_receive`) compiles whole
unchanged `entReceiveCostume`, `entReceiveXlucency`, reward and custom NPC receive
functions from the pinned original sources. It replays from the actual appearance
selector, using the same verified CLIENT ordinary, extra and palette tables and
original body receiver for each stored and Supergroup costume. It consumes SG
mode/emblem, literal FX, optional NPC identifiers/custom colors, then translucency.
The original discard/out-of-order profile suppresses cosmetic/UI actor mutation;
this does not authenticate a selected NPC model or publish an actor. Capture is
only the selected completed main body. A component COH_OK leaves entity/message
completion false; it never sends ACK, READY or RECEIVED_CHARACTER.

`check_original_ent_costume.py --work <new-scratch-dir> --output <scratch-json>`
compiles unchanged original entity/body senders as independent fixtures and runs
release, ASan and UBSan tests, including stored counts 1/2/10, SG, FX, NPC custom
parts 0/2/63, both wire modes, truncation, alias/overflow and unknown-tail retention.
No actual Thor ALLENTS bytes are available in this qualification. The caller must
charge its complete old/candidate owner, immutable raw/index spans, 65,536-byte body
workspace, optional 48,352-byte snapshot and 32,768-byte stack reserve inside the
existing 8 MiB aggregate; no heap allocation occurs in the adapter. Source payload
and compiler stack measurements are separate from device RSS/PSS observations.

The same source adapter now runs whole `entReceivePowerCust` and
`powerCustList_receive`. Absent and empty source lists continue. A nonempty list
follows the original NULL-tolerant BasePower lookup: missing definitions yield
NULL and fullname "none"; both tint Autos and the literal token are still read.
The original NULL-last comparator runs over bounded discard-only storage. Its
result never publishes a semantic customization list. Unresolved CRC counts and
first/last CRCs remain visible; no dictionary is required to determine framing.
The same exclusive 64KiB body workspace holds typed pointer-list scratch after
the main costume; its size does not grow, and it is wiped on every parser exit.

The additive `_initial` entry accepts the actual earlier `pchar_things` flag in
the already validated selected-self/all-rare initial profile. Empty power paths
continue through whole original titles, ragdoll-ignore and character-stat receive
functions, reusing the existing source-qualified `SendBasicCharacter` parser.
The original unchanged vision/target/status/inventory statement block now runs
next, reusing existing qualified scalar/reference/status/inventory parsers. The
two whole original taskforce functions now run with the same CLIENT slots for
any contact costume, preserving the selected main-body capture. The source
closure then leaves later very-rare entity fields (`entReceiveSendOnOddSend`
onward) unread: this is remaining implementation, not a missing table claim.
No entity or message completion is asserted. The original taskforce parameter
function alone retains a narrowly scoped shift-sanitizer exclusion for its
existing signed `1 << 31`; all adapter reads remain instrumented, and bit31 is
covered by the independent original-sender fixture.
No live receipt establishes which power branch the Thor packet will take.

`check_original_ent_costume.py --replay <saved-initial-replay.bin>` additionally
verifies the actual user-exported88-byte header/payload hashes and replays that
packet in release/ASan/UBSan. No raw packet or decoded snapshot is committed.
The retained301656-bit packet consumes all343 unresolved customizations through
bit39216; its first CRC is0x80443357 and last0x7e9e7869. The initial source path
continues through titles/ragdoll/basic statistics, then uses the whole original inventory receiver to preserve signed row words
(such as -1) and reaches the later very-rare suffix at41312. The older standalone
inventory parser remains unchanged in its documented stricter scope. No new
dictionary requirement or full-packet completion is asserted.
