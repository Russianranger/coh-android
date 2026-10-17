# Historical immutable named-table semantics

The new owner borrows the exact immutable raw class owner and its leased input.
It preserves original class/table order and names, requiring unique ASCII keys
within each class as original classes_Finalize does. Same-class duplicates refuse
the whole preparation. Different classes may retain the same named-table key.
Empty value arrays remain represented; lookup refuses their original undefined
negative-index path. Missing keys explicitly report found=false and source1.0
fallback, while present arrays repeat their final value beyond their last index.
Native lookup conservatively refuses nonfinite values and negative-int profiles.
No floating-value arrays or per-level tables are eagerly materialized.

The oracle executes unchanged whole classes_Finalize/class_GetNamedTableValue
with whole original stash constructor/add/hash/probe/resize/find interfaces.
Binary parser/earray/float storage and heap interfaces are explicit fixture
adapters. Original named stash insertion order and lookup winners are retained.
The original empty-value lookup is deliberately not executed. This is historical
host source qualification, not Win32 ABI, live class/application/current cache
ownership, complete set/power dictionary, authoritative actor or ACK admission.

Both prepare and lookup charge the borrowed dictionary/input, compact output,
query bytes, retained storage and8KiB native reserve before traversal under8MiB.
No allocations; every refusal preserves the complete output.

The borrowed owner is56 bytes; each immutable value observation is24 bytes.
Fourteen source-written caches include actual normal/villain bodies and duplicate,
empty-values, empty-key, unknown-name and empty-table-list variants. Every query result
are independently compared to raw values and original source lookup, including
case folding, missing fallback, final-value extension and empty refusal. Native
release/ASan/UBSan, C++ linkage, measured stack frames and exact budget/alias/late
record refusal/source-owner mismatch controls are retained. Query bytes must be
disjoint from owner, raw dictionary/input and output; all are budgeted explicitly.

Empty string keys and empty queries are source-supported, with nonnull borrowed
query storage; original stash/value lookup exercises an exact empty-key writer
variant. They remain distinct from a missing table and an empty value array.

Duplicate checks fully validate each raw record/value array once. Previously
validated prior keys are accessed in constant time, with no repeated float scan.
Preparation precharges at most8,388,608 comparison work units before comparing:
one for every candidate length check, plus full key length when equal-length.
Exceeding this fixed work cap returns LIMIT with the complete output unchanged.
An original-writer/source-stash profile with256 distinct259-byte keys is accepted
by original Finalize but deliberately refused by this bounded native profile.
No increased memory cap or silent table/reference truncation is used.
