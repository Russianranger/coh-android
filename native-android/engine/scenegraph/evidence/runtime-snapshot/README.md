# Runtime snapshot diagnostic qualification

`1f90d3a-source-qualification.json` is the final exact-source receipt for
decoder commit `1f90d3a58243ed41e56674e8857bac18cf48ebb0` and producer commit
`ee3ab936b6e805f6b25fadc21395e66e0fa310a5`. Its SHA256 is
`5d2df90ce4bafc77afabc442bbbfc42d32985946fba56aa319490683765138f5`.
The accompanying source-commits receipt verifies the recorded native, producer,
helper and original-source hashes against retained Git objects.

Release, ASan and UBSan each passed 21,726 controls across eight original-source
fixture pairs. These cover sparse root slots, two separate future objects with
the same original numeric ID, shared future references, unreachable futures,
lookup bounds, packed rotations, zero scale, a reachable cycle, excessive depth,
an unreachable cycle and the accepted depth-128 boundary. Malformed input,
cancellation, allocation failure and exact memory-budget boundaries preserve
output and release candidate allocations. The modes produce identical reports.

The largest admitted fixture charges 511,270 bytes including both input spans,
the diagnostic pool, one decoded record, output, 192 KiB of parser stack
reservations and 256 KiB of host harness/provider reservations. Its measured
native heap peak is 18,326 bytes. These fixture measurements are not authentic
catalog or process-RSS measurements. Emitted compiler stack frames include
38,192 bytes for the top-level audit and 80 bytes per recursive visit, within
the explicit reservation at the supported depth.

The earlier `fa4e499b-pre-review-*` receipts are retained unchanged. They precede
the full original `group.h` source pin and packed-root fixture correction; the
final receipt above supersedes them for admission.

This qualification is host-only and publishes no graph, assets, actor or world.
It changes no production scenegraph source, Android package or physical
acceptance. An authenticated, same-boundary runtime sidecar paired with the
preserved authentic catalog is still required to determine the seven missing
names' actual ownership and root reachability. A source runtime snapshot does
not establish a received live GROUPS transaction.
