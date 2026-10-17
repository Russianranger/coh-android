# Streaming source graph instances

A reachable definition is a shared source object. A world occurrence is a distinct root-to-node path. The shortest witness path is useful for ownership evidence but cannot enumerate all instances. `coh_runtime_instances` walks every path in original root-slot and child-entry preorder, retaining shared definitions and repeating their occurrences without a global visited set or eager flat array.

Each value record preserves graph generation, root slot, node, depth, incoming edge, a walk-local ordinal and parent ordinal, source model/external flags and composed world matrix. Parent ordinal UINT64_MAX identifies a root. These ordinals are diagnostic walk identities, not server entities or session capabilities. Empty and no-model objects remain explicit. No CLIENT material, LOD, resource acquisition or draw order is inferred.

Original `Common/group/grouputil.c:groupProcessDef` visits active root references in slot order. Its unchanged `groupProcessDefHelper` processes the current node before traversing each child entry, recursively composing parent world with child local. `Common/group/grouptrack.c:trackerOpen` separately creates child trackers per parent occurrence and uses the same multiplication direction. The walker reproduces this source traversal order without recursive C calls. It starts from observed raw snapshot root matrices and uses the graph's decoded source child matrices. Existing snapshot decoding qualifications apply; this is not a claim that every decoded child basis is bit-identical to an uncaptured original server matrix.

A private numerical adapter preserves original `mulMat4Inline` operation order, including signed zero: basis columns do not add a synthetic zero; only position adds parent translation. The accepted shared compose kernel remains unchanged. Host controls execute unchanged original matrix and traversal function bodies with explicit small fixture type shims; they are source qualification, not original Win32 ABI or server execution.

## Continuation, lifetime and bounds

Caller-owned cursors retain only a bounded path stack. The graph and its exact input owners must remain immutable and externally leased across every continuation and graph-consuming batch borrower. No implicit retain occurs. A same-graph cursor copy is an independent diagnostic continuation, sharing no new authority. Batches are caller-owned immutable value copies after successful return until caller reuse; only batch_count entries are valid. On any error batch storage is scratch to discard, while cursor and report remain unchanged. Earlier successful batches cannot be presented as a complete world when a later attempt refuses.

Capacity is at most 1,024 records per batch; depth at most 128 edges; total count at most 16,777,216 occurrences and total work at most 67,108,864 transition units. A call may perform at most 65,536 transitions, yielding OK with committed progress even when a batch is empty. A child transition adds at most 128 path-cycle comparisons and fixed-size matrix work; these are transition budgets, not processor instruction or elapsed-time bounds. Overflowing transforms, cycles, depth/count/work ceilings and cancellation refuse the entire attempted batch. Known input/control/workspace/output span overlap is rejected before writes. Opaque graph storage and cancellation context disjointness remain caller ownership obligations.

The named aggregate reservation adds graph payload, borrowed catalog/snapshot allocations, cursor, a 64 KiB stack reserve, full caller batch capacity and report under 96 MiB. All other owners/indexes/resources, allocation slack and callback scratch must be charged in retained_bytes. It is not process RSS. Release compiler stack usage is 45,488 bytes at begin and 11,584 at next; source metadata is not copied into the cursor's path frames. The numerical walker allocates nothing.

The separate selection-input helper copies a successful unmodified instance and a computed or explicitly captured local source bound from an externally retained immutable diagnostic with matching graph binding. Missing/blocked bounds refuse. This prepares visibility inputs only. It supplies no CLIENT effective bounds, culling decision, subtree pruning, material/LOD choice, GPU ownership or world permit.

## Authentic retained Atlas diagnostic

The existing run 38994607354 catalog/runtime/resource binding is revalidated before native execution. No new capture, server startup, accepted APK rebuild or asset download occurs. An independent bounded indexed DAG recurrence memoizes each node once, adds its count at every incoming path, and predicts per-root occurrence multiplicity. The streaming walker then independently enumerates every path in bounded batches and must match every predicted root and aggregate count.

All release/ASan/UBSan results agree:

| Observation | Count |
| --- | ---: |
| Unique root-reachable source nodes | 15,353 |
| Unique root-reachable model owners | 3,083 |
| Root-to-node occurrences | 564,559 |
| Model occurrences | 384,280 |
| External future-object occurrences | 4 |
| Active roots completed | 33 |
| Maximum depth | 69 |
| Batches | 2,206 |
| Transition work units | 1,693,678 |

Root 7 alone contains 486,301 node occurrences and 346,908 model occurrences. The complete per-root ledger and ordered node/root/parent/matrix fingerprint are retained in the receipt. The fingerprint is a diagnostic FNV64 checksum, not a cryptographic authority or content-admission digest. Named reservation is 22,952,371 bytes including 688,096 bytes of independent count workspace. Resource join, owned GEO bodies, CLIENT materials, renderer/GPU allocations and source-generation admission are absent from this diagnostic and are not covered by that number.

The test corpus also verifies a repeated shared DAG (10 occurrences from 4 unique nodes) against unchanged original traversal, 2,048 original matrix fixtures including signed zeros, one-record/tiny-step continuation equivalence, cancellation rollback, malformed targets/cycles/depth/finite overflow, count/work/budget ceilings, aliases, bounds blockers and generation mismatch. Source/host qualification and sanitizers do not establish Android execution, Thor acceptance, live GROUPS matching, authoritative actors or rendered world publication. All authority fields remain false.

Exact numerical qualification uses normal finite-value semantics and `-ffp-contract=off`; eventual ARM64 integration must preserve these options and independently qualify execution. Shared CMake/JNI and accepted APKs are untouched.
