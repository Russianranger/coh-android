# Local BodyParts default and original costume continuation

The shipping Combined interop path can pass stage41 using the actual local
server's common `data/bin/BodyParts.bin`, without a source process/witness/lease.
Before each connection, `configureBodyPartsCache` reads that real file read-only,
checks its exact2584-byte length and full SHA256 against the retained cache that
was independently compared to all28 ordered source BodyPart rows/fields. Only
its one original Files1 dependency timestamp (bytes60..63) may differ; a second
full-content hash normalizes exactly that word. Every other2580 bytes, including
schema/path/count/order/all row data, must match. Missing/different data preserve
the ordinary connection and report an unresolved default. No guessed count is
substituted. Source comparison commits:47fd09b3a and6a13bc92e.

After an actual match, the same ALLENTS synchronous observation calls the whole
unchanged original `costume_receive` at the existing first costume-body cursor,
with that verified28-row default. C's thin primitive shim handles original
bodytype/count checks, literals, caches and all complete supported parts. It
stops at the first unknown ordinary/extra/palette dictionary before its index
Pack; no index width, string or later field is guessed or skipped. This path
uses C's834437f79/f320c3e6c implementation and its separate qualification. A
complete costume result is only that wire body, not a complete entity or ACK.

Essential native JSON adds `bodyparts_default:[status,count]` and
`costume_continuation:[status,field,part,part_count,parts_read,strings_read,
colors_read,dictionary_required,count_validated,costume_complete,end_bit,
failure_bit]`. Source fields3/4/5/6 are geom/texture1/texture2/fx,7 color,
8 region and9 body-set. Dictionary1 is ordinary strings,2 extra strings and
3 palette. Once count validation succeeds, `catalog_boundary` is null; the
historical intermediate part-count observer remains available in optional
progress. All fields remain within the unchanged7168-byte report ceiling.

The additive `observedSelfPose` JNI getter returns16 little-endian bytes:
U32 entity index followed by three F32 source coordinates. It uses the actual
selected-self create/raw DBID comparison and D's fully decoded position sample.
It is available independently of a later costume dictionary boundary. It returns
null before observation, for another entity, while busy or after owner release.
This is an observed server-entity marker, not a complete authoritative actor.

Memory: actual Interop owner66,944B includes the fixed65,536B source-receiver
workspace. That workspace is wiped after every original receiver result and
again when the Interop owner retires. The cache comparison uses a2584B stack
buffer,32B digest and bounded path storage, never a world archive. Observer
preflight includes its actual fixed owner, borrowed decoded packet, lease and
4KiB source-call reserve under the unchanged8MiB initial domain. This named
accounting does not represent the server/Android process set's RSS/PSS; current
headroom/low-memory controls remain active. Transport4MiB decoded/ordinary16KiB
and all existing policies are unchanged.

Focused host qualification runs the shipping callback and whole original
receiver over the retained source-layout packet fixture plus explicitly
synthetic first unknown part flags, transport and JNI doubles. Release, ASan and
UBSan each pass2665 controls/32 captures. It covers default28 and explicit Pack4,
exact-file and timestamp-only matches, changed/short/long/missing caches,
interrupted/short/failed reads, selected-self raw pose bytes, cleanup and maximum
request/receive scalar reports. The measured report maximum is6726B<7168.
40 file opens and40 closes balance per mode. A fortified `__read_chk` test-only
wrapper makes Linux UBSan fault injection consistent with ordinary read paths.
The historical qualifier main is not run.

No physical raw ALLENTS packet was retained in the supplied reports. Therefore
actual Thor file matching, later physical costume progress and box drawing await
the new APK test; the host fixture is not a replay of that physical packet.

```sh
flock /tmp/coh-cycle-build.lock python3 \
  native-android/combined-client/tools/check_bodypart_continuation.py \
  --output /tmp/bodypart-continuation.json --work /tmp/bodypart-continuation
```
