# Source Win32-width hash and shallow integer-prefix staging

Implemented: defined uint32 Burtle default-string hash and single-int hash,
plus bounded no-delete integer insertion/duplicate/zero-skip/75%-resize/ascending
old-storage reinsertion. These are prerequisites for reconstructing original
costume dictionaries. They do not build the complete costume tree/dictionaries.
No original server/world capture or workflow is run.

Critical source ABI issue: HashFunctions.h declares ub4 as unsigned long int.
That is32bits on original Win32 and64bits on Linux/AndroidLP64. Original
burtlehash3StashDefault also dereferences ub4* at potentially unaligned string
addresses. Directly compiling that source for native ARM64 would change hash
width and/or introduce alignment/aliasing UB. Native code deliberately uses
uint32_t wrap arithmetic and explicit little-endian byte loads. Default string
hash ORs0x20 into EVERY byte (including punctuation); it is not locale/Unicode
case folding and does not define the string-equality policy.

Source oracle extracts and executes whole unchanged burtlehash2/3/default
functions and original mix macro with an EXPLICIT uint32_t ub4 binding, modeling
Win32 unsigned-long32 on an x86_64 host. Original raw word loads, including
unaligned fixtures, run only in that UNSANITIZED source oracle. This is not
whole original Win32 binary/ABI execution or a sanitizer qualification of those
original loads. Native byte-safe code is qualified separately with ASan address
checks and UBSan. Hash fixtures cover every length0..259, alignment offsets0..3,
three seeds and raw byte patterns (including NUL/punctuation/nonASCII) for the
primitive function. Ordinary original C-string admission/equality/normalization
is NOT inferred from primitive hash support for arbitrary bytes.

The table oracle executes unchanged original stashFindIndexByKeyInternal,
stashAddValueInternal and stashTableResize, including quadratic probe progression,
75% threshold, duplicate refusal and reinsertion in ascending old storage order.
Original hash functions drive those source loops. Table layout/zeroed initial
shallow-int constructor, allocator/profiling/shared/deep-string branches and
pointer-word conversions have declared host bindings. Original constructor and
whole string-table engine are not executed. Deep strings/shared heap/deletion
branches are never entered. Integers use exact U32 bit identities in the host
pointer carrier; sizeof(pointer) allocation cost is not a claim about Win32
runtime memory. Native key zero is skipped as original addPaletteToTables does;
raw integer hashes still accept zero as a primitive input.

Native prefix takes an original ordered U32 key stream and an already admitted
initial power-of-two capacity8..65536. It owns no allocations or key pointers.
Input count<=4096, full slot max65536. Workspace has two full65536-U32 arrays;
output owns one full slot array plus compact metadata. Complete capacities,
input,16KiB native stack reserve and caller retained bytes are charged before
workspace mutation under1MiB named budget. Input/workspace/output disjointness,
overflow and input scalar alignment are checked. Output commits after the ENTIRE
sequence; workspace may change on refusal. Each probe has an explicit65536step
bound; a source pathological/nonterminating key stream may be refused rather
than bypassing that bound. Original unbounded-loop behavior is not emulated as
an obligation to hang. No delete/tombstone/update-value interface exists here;
adding it would require separately qualified source semantics.

One test consumes the authenticated recovered160-entry supergroupColors.bin via
the already qualified whole original small-table consumer. Exact float RGB
words are passed to unchanged source getRGBAFromVec3 (finite source0..255).
Those source-produced keys feed the original integer insertion sequence starting
at128 as costume_initHashTable's FIRST palette prefix. Native exact slots match
that original prefix. This is NOT the final costume_PaletteTable: original
builder subsequently adds every origin's skin/body palettes in its exact source
order, and later resizes can relocate earlier keys. Neither the prefix nor its
max_size may be admitted as the complete global palette. Test also covers the
prefix repeated twice, synthetic zero/duplicate/high-bit keys, resize thresholds
and larger ordered sequences.

Returned source_hash_bits=32/source_prefix_only=1 are diagnostic recipe labels;
complete_global_dictionary and actor_authority stay0. Complete costume.bin tree
reader, original preprocess/fillExtraData/order and string equality/ownership,
full ordinary/extra/palette slot generation, generation/source/profile admission,
asset resource resolution, original32bit execution/equality and full actor/ACK
publication remain open. No Android or physical qualification is claimed.
