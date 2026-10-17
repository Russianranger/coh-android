# Original normal GROUPS omission witness

This private observer supplies previously absent producer eligibility inputs. It
has not run in MapServer or supplied a live Android transaction. It changes no
shipping source and never sends an application acknowledgement.

The retained Thor 0.1.7 export reports 343,112 consumed bits but retains neither
those bytes nor root names/matrices. `primary-recovery-next/accepted-017-catalog-
comparison.json` explicitly records that limitation. Other 1,118,352-bit files
are scripted source fixtures. A future capture cannot recover the historic Thor
packet or retroactively bind its generation.

`source_groups_eligibility.inc` observes every original allocated slot, including
inactive definitions: `sendDef` still emits their deletion grammar when eligible.
It records PRE-call link update time/world ID, actual world ID, full-update,
file order/count/checksum/modification/force-reload/modified-on-disk, definition
slot/ID/modification/file_idx/saved/in_use, root slot/modification/active state,
active-root count and exact branch decisions. Source CRCs remain in the
original final packet footer, rather than invoking the mutable global original
CRC accumulator a second time from this observer. The 64-byte little-endian record has
sixteen U32 words. Unused words are zero; layouts are explicit in the source.
Kinds are begin1, file2, definition3, root4, end5. Records are provisional until
all records and the associated original packet have been retained and bound.
There are at most 4096 files, 65536 definition slots and 65536 root slots;
callbacks receive stack bytes synchronously. There are no allocations.

The original rule is not “saved objects never appear”: force_reload bypasses
both filters; full_update bypasses time filters but DOES NOT bypass saved
omission. A file can be present while all definitions are omitted. The first
file_idx-zero definition is not subject to the saved filter. File0 has no special
exception in the original rule: assuming all its definitions always emit is a
restriction of the existing compatibility comparator, not a producer invariant.
The root time test uses the PRE-call link time, not the eventual maximum time.
`sendGroupFile` resets force_reload and `worldSendUpdate` updates link state, so
post-call sampling cannot reconstruct eligibility. Unsigned comparisons and
zero update-time semantics are preserved, with no wraparound reinterpretation.

`stage_groups_transaction.stage` accepts only the pinned complete original LF
source and returns a private copy with two calls: after worldSendUpdate local
declarations, and immediately before reliable pktSend. The original sendDef,
sendGroupFile and packet-writing bodies remain unchanged. The static hook is
disabled until a private caller installs every callback. Eligibility failure
aborts only the diagnostic transaction; original packet production continues.
The finish callback borrows exact `pak->stream.data`, logical bitLength,
byteAlignedMode and compression flag BEFORE packet ownership passes to pktSend.
The bytes include the original command; they are not normalized post-command
Android-reader bytes or a compressed/encrypted UDP datagram. Unused final-byte
bits are outside the bitLength. Limit: 16MiB logical payload. No sink is installed
by this change. Serial, nonreentrant, exclusive owner-thread callbacks cannot
load, yield, modify engine/link/packet state, replace hooks or retain pointers.
Callbacks/report/control/source storage must be disjoint and valid.

The source-only host replay executes unchanged original sendGroupFile over 1728
combinations of full/time/force/modified/saved/file-index/in-use inputs. Packet
bits, bytes and maximum definition time match the independent witness decisions.
A staged worldSendUpdate replay captures original pre-reset force_reload and
exact original final packet; refusal discards the witness while original producer
still runs. Release, ASan and UBSan instrument new code; legacy original bit
packing is separately marked outside UBSan. None is a real network capture.

## Minimal future capture and admission contract

A justified new run must capture genuinely new actual GROUPS transaction bytes
and eligibility, not merely repeat known catalog/runtime/resource byte files.
Its nonshipping caller must establish and document the exact owner-thread
quiescent boundary and register a one-shot sink for the requested real link.
Before the actual producer mutates link/file state, bind the source inventory
(catalog, runtime roots/futures, resources, and missing per-opened asset/trick
state where needed) AT THAT SAME boundary, together with observation ID, complete
source/build/run identity and exact link/session/map/selected-character identity.
Existing detached old capture hashes may be reused only after actual same-boundary
byte equality has been established; caller-supplied hashes alone are insufficient.
The begin callback cannot simply claim an old graph generation equals the new
producer generation. Resource quiet-lease and hook lifetime orchestration still
need an independently reviewed private caller; this patch supplies neither.

Retain raw packet logical bytes/bitLength plus exact prefix normalization rules
so the existing post-command observer can compare the same payload. Seal all
eligibility records, packet and matching source inventory in a manifest only
after complete write/flush/close, packet validation and owned cleanup; CREATE_NEW
private temporary paths, failure receipts and no-replace final publication are
required. Partial record/payload output must never be admitted. Checksums/counts
alone do not bind generation. Connection/link addresses must not become durable
identity tokens. Run/session-local correlation and authenticated ownership remain
separate from raw bytes.

The current compact comparator must subsequently consume this complete witness,
verify exact file/slot/ID and root association, rederive every emission/omission
and require the actual observed wire set equals precisely that eligible set.
Missing saved definitions require source-qualified CLIENT import/load provenance:
`receiveGroupFile` first finds an existing file or invokes bounds/full load before
applying transmitted records. A SERVER catalog is not proof the CLIENT imported
those omitted definitions from matching assets. An absent file/delta root needs
prior admitted CLIENT state. Full NEW_WORLD, normal files and complete root
emission are the smallest initial scope; base/raid remains refused. The witness
must not silently relax the existing comparator or its all-file0 restriction.
Final world admission still requires same-session live generation, complete CLIENT
material/LOD/resource state and authoritative actor transaction. These remain
false/unresolved here. No server run, workflow or accepted APK rebuild is needed
to review this source change.
