# Namespace and diagnostic capture budget boundary

This update reads committed source and existing host receipts only. It executes no compiler, old qualifier, capture, renderer or provider and supplies no RSS, Android ABI, current peak or available-capacity result. The old parent ledger remains a historical comparison; neither new owner has a ticket in an executing common 96 MiB parent adapter.

| Named item | Existing evidence | Charge boundary |
| --- | --- | --- |
| Diagnostic initial capture plus private Map wrapper | 1,072 + 1,280 = **2,352 B**, unchanged by the explicit timeout API | Additional host owner types; the embedded 1,016 B diagnostics, 24 B first snapshot and 8 B private phase are already inside these owners. |
| Ordinary Local / Map / callback lease | 1,040 / 2,536 / 1,344 B | Separate existing types, plus transport, decoded-message, caller callback/context and stack storage. No extra packet copy is introduced by the synchronous loan. |
| Namespace module preparation | **65,536 B** fixed reservation; existing measured native frame sum 18,408 B | Provider, loader, callback, libc and Android stacks remain external. |
| Namespace owned heap and peak | **Exact cohort totals not retained** | All metadata/tree/hash/Basic/body-handle allocations, plus temporary PIGG name/offset arrays, are independently allocated from the namespace owned limit. |
| Namespace loader | **Full configured `loader.total_bytes`** | Separate from namespace owned bytes even if only a few blobs are resident. Provider source storage remains external. |

The implementation admits roots and PIGGs each up to 32,768, records/nodes up to 262,144, Basic rows up to 65,536 and body leases up to 256. These are count bounds, not an observed provider inventory or measured owner size. For example, 32,768 root-path slots alone would allocate 32 MiB (`char[1024]` per root); no such configuration was executed by the retained proof. The test loader's 32 MiB reservation is a different quantity from a 32K count bound.

The source budget equation is:

`candidate reservation = external_bytes + 65,536 + full configured candidate loader + borrowed input spans + candidate peak_owned_bytes`.

`borrowed` includes the request/limit descriptors, ordered root/PIGG/prefix arrays and input path strings. It does not measure or automatically charge the source bytes behind `read_at`, digest/provider contexts, file mappings, decompressor/runtime peaks, caller work or any GPU allocation. A real producer must charge those actual owners externally and deduplicate only a proven shared reservation identity.

| Existing controlled test cohort | External reservation | Full loader reservation | Control reservation | Fixed configured floor before input spans and namespace allocations |
| --- | ---: | ---: | ---: | ---: |
| 22 authentic cached bodies, one explicitly controlled subset root | 1,048,576 B | 33,554,432 B | 65,536 B | **34,668,544 B** |
| 8,936 retained paths with generated header bodies, one controlled root | 67,108,864 B | 33,554,432 B | 65,536 B | **100,728,832 B** |

Both cases use a 201,326,592 B local aggregate limit. The second configured floor already exceeds the historical 100,663,296 B parent cap before any candidate owner or caller input. Reusing that test configuration under the parent cap must refuse. The authentic bodies total 1343668 B on disk/in the fixture input; that is neither a production provider charge nor the namespace heap size. The 8,936-path projection is not an authentic complete provider. Neither cohort retains an exact measured `owned_bytes`, `peak_owned_bytes` or `aggregate_reserved_bytes` result in the committed proof; transient assertions do not supply recoverable measurement values.

The authentic fixture also exposes an incomplete external charge: `authentic_cases` allocates and loads all 22 source bodies before namespace construction. Their exact 1,343,668 B of live caller payload alone exceeds its configured 1,048,576 B external field by 295,092 B, before the separate input/descriptor/oracle arrays and allocator costs. The loader's full configured reservation belongs to a different owner and cannot absorb these source buffers without a real shared reservation identity. Thus the retained functional/header comparison and local admission-boundary controls are useful, but this test setup is not a complete actual fixture-memory admission. A future real producer must supply the missing source/provider charge before any aggregate fit can be claimed.

A later LWC successor has a mandatory old/candidate overlap. Before callbacks or source reads, `external_bytes` must cover at least **old namespace owned bytes + full old loader reservation**. The candidate then adds its own full loader, control reserve, inputs and heap peak. This enforced minimum still excludes any unbilled old provider/context/input/runtime storage. The predecessor remains guarded and live throughout construction; copying its Basic rows is not retirement. Each namespace holds its own successful provider lease.

After successful construction, an old namespace can retire only when all of its real body loans are released and its checked destroy succeeds. Actual loader destruction precedes the old provider drop. The successor still borrows source reader/digest contexts and bytes through its separate provider lease, so matching generations or freeing old metadata cannot retire source storage still serving the successor. A provider callback alone gives no evidence that a file, mapping or heap buffer was actually closed/freed. No retirement subtraction is taken here.

Future texture decode/upload adds another overlap: the namespace and its loader/provider remain live while an acquired body is copied or uploaded into an independent destination. The pending RGBA32 codec has no frozen proof in this note and contributes no measured size or retirement credit. The existing GPU lease/presentation owners, deferred GL deletion and source geometry copying remain separate reservations. Before enabling a real producer, one parent admission must book these simultaneous old/candidate/provider/body/destination owners and actual cleanup transitions; passing each standalone limit independently is insufficient.
