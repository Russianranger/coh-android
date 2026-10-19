# Original ordered-fragment compatibility — 2026-10-19

The original `pktSendDbg` chooses its direct path only for `stream.size <
maxPacketDataSize`. At equality its ordinary split path creates one sibling.
The unchanged `pktMakeCompatible` copies ordered/reliable/compression flags,
without copying an ordered ID. `lnkAddToSendQueue(..., i != 0)` assigns a new
ordered ID only to the first part. `pktWrap` serializes later zero IDs; original
`mergeSibs` sorts by part number and adopts part zero's metadata.

Native frame validation previously refused a one-sibling envelope and every
ordered zero ID. Its merge required identical IDs for all fragments and used the
last-arriving part's ID. This repair admits zero only for a later sibling,
retains mandatory nonzero first-part IDs, permits the original single sibling,
and derives complete-message metadata from part zero. Previously admitted
repeated identical nonzero IDs remain supported; conflicting nonzero IDs or
ordered/compression flags refuse. The request-Tx diagnostic copy receives the
same merge correction and reverses byte-exactly to the ordinary source after
its existing marked observer hooks/include wiring are removed.

`check_fragment_compat.py` executes unchanged original send/queue/wrap/bit-writer
function bodies against explicit host packet allocator, queue, locking, clock
and dummy-link providers. Original bit writers run on trusted aligned padded
inputs at O0 without sanitizers; none ships. Twelve original cases exercise
1199/1200/1201/2400/2401/8192-byte packets in unordered and ordered mode. They
produce 32 exact source frames and 48 native full-message deliveries across
forward, reverse, first-part-last and rotated arrival orders. Independent zlib
streaming fixtures test source-form reassembly before dictionary decoding. All
three native release/ASan/UBSan modes pass 134,879 checks, 11 focused refusal
cases and two streaming deliveries. Actual executed binaries, original producer
source/library and exact generated fixtures are retained in the proof archive.

The 16-fragment, 16KiB compressed-wire/reassembly and 4MiB opt-in decoded caps,
first-failure/timeout, duplicate, queue-backpressure, ownership and authentication
policies are unchanged. No new allocation or retained owner is introduced.
LeakSanitizer remains disabled on this managed host. These checks establish
source compatibility only: no original server transaction, Android build/device
execution, world publication, application ACK or gate promotion is claimed.
This finding alone does not establish the cause of the Thor timeout.

Reproduce from the repository root with a new output directory:

```sh
python native-android/engine/network/check_fragment_compat.py --output /tmp/coh-fragment-new-proof
```
