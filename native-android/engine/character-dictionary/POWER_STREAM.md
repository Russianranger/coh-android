# Raw full-power streaming index

This additive raw component traverses the complete persisted original BasePower,
AttribModTemplate, SuppressPair, PowerVar and PowerCustomFX binary tables in
source order. It keeps a compact record/name/CRC index and a 4 KiB read buffer.
The 62,047,164-byte exact historical powers.bin remains in an immutable borrowed
file provider. No full power object graph is retained.

The provider owns a nonzero source lease, pre-reserved read/digest state and all
callback scratch. The complete fixed owner and workspace, provider descriptor,
context, expected digest, 16 KiB native stack reserve, callback scratch reserve
and literal caller retained bytes are charged before any callback. No implicit
nested global budget partition is granted. Provider callbacks cannot allocate
above their pre-reserved charge. Failed begin/read/update/finish/cancel/parse
invokes abort; successful finish retires the digest transaction even if its
result mismatches the expected SHA. Output commits only after complete parse,
individual CRC consistency, bounded indexing and exact whole-file SHA equality.
Provider context and immutable file lease must outlive the returned owner.

The source full static table bodies and original binary reader/writer execute
record by record in the host oracle. Original enums/defaults are explicit binary-
only shells: binary read/write does not use those values. No original
ParseTableCRC claim follows from whole-file or per-record round trips. Native
Parse6 strings are limited by the original 12,000-byte bound; raw full-name CRC
lookup is deliberately limited to nonempty ASCII names under 260 bytes. Unknown
numeric dictionary identifiers and nonfinite float words remain raw. Source
boolean/color serialized byte values are checked before narrowing. Recursive
records have a deliberate 64 KiB profile limit; no source field is skipped.

The raw index uses the already qualified source32 integer hash and source square
probe ordering. Duplicate CRC records remain in source order and lookup returns
the first winner. Zero CRC refuses pending explicit source zero-key semantics.
The whole original integer stash prefix executes on the authentic ordered CRC
sequence; that is not execution of the full global dictionary constructor.

Host qualification covers every 20,241 original record round trip and individual
CRC match, every 65,536 diagnostic integer-stash slot, positive original-written
PowerVar/unknown-identifier/backslash-name/duplicate-first-winner cases, malformed stored CRC, sampled
strict truncations and byte mutations, late IO/update/cancel/digest refusal,
last-refill and final-publication cancellation, pre-callback exact budget and aliases, C++ linkage and native stack. Release,
ASan and UBSan each execute over 434,000 assertions. LeakSanitizer cannot execute in
the traced host environment and is explicitly disabled; original host oracle
functions execute unsanitized. Native owner is 1,048,744 bytes and workspace
1,052,840 bytes; the host fixture aggregate including context/reserves is
approximately 2.14 MB. No 62 MB retained heap is charged as a file.

Independent review F43ed6d67d seals the standalone historical raw stream/index
scope and the late-cancellation correction. Still required: actual
power schema CRC with complete dynamic/static DefineContext, source cache loader
mode/path/callback association, set/power/category joins, complete class-power
semantics and current server generation. No actor, world, rendering or ACK
permission is produced. OpenSSL is a host-test digest provider; its stack and
whole dependency sanitizer closure are outside the native stack receipt.
