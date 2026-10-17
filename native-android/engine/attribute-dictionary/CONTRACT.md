# Exact offline attribute description candidate

This module reads the complete authentic recovered `attrib_descriptions.bin`
(5,892 bytes, SHA256 `20f770f406e661050434284e4253f721699df2112ea4481de66b50146304c132`).
The original complete `ParserReadBinaryTable` and writer, original three parse
tables, exact two static-define lists and complete `ParseTableCRC` traversal
(including `UpdateCrcFromStaticDefines`) produce `0x315acdb1`, equal to the
actual cache header. The actual body roundtrips byte for byte. The source
builder/profile differs from a runtime cache association: actual shared-memory
selection/cache branch and a live server generation have not been observed.

Seven categories contain69 ordered descriptions. The native candidate flattens
original forward array order and reverses the complete result exactly as
`sendAttribDescription` and `receiveAttribDescription` loop. It does not remove
duplicate keys, reorder by names, replace unknown IDs or apply gameplay values.
All original raw numeric fields and strings are retained, including the original
U32 word before bool-U8 narrowing. Category/row coordinates and source key
`460*type+offset` are diagnostic source32bit arithmetic; unknown type/offset words
are not admitted as gameplay attribute addresses.

Native parsing validates the complete original Parse6/Files1 envelope, bounded
counts, every nested segment and string, exact end, independently expected
whole-input digest, and explicit borrowed-input lease before atomically exposing
the immutable caller-owned candidate. No allocation occurs. Local limits are
32categories,256totalrows,64dependencies,259B Pascal strings and64KiBinput.
They are refusal bounds, not invented original engine limits. The512KiB owned
budget includes both fixed candidate PODs, input, every named callback/context,
pre-reserved digest scratch and16KiB native stack plus caller retained storage.
Digest callback errors, including cancellation, preserve the public output.
External crypto stack/sanitizer closure and whole process memory are unclaimed.

The unchanged original Parse6 reader/writer executes with explicit previously
qualified host storage/layout/handler shells and bounded SimpleBuffer storage.
The diagnostic projection handles empty arrays; this is fixture plumbing, not a
change to any original parser. Static define pointer/int adapters preserve the
original32bit integer CRC byte contribution on the little-endian host. The CRC
uses the previously qualified zlib Adler32 adapter for original Crypto++ network
order digest bytes; original Crypto++/Win32 runtime is not executed.

Source producer controls change a name, retain unknown signed numeric values,
serialize U8bool255, emit an empty category, and duplicate a row. The independent
Python decoder compares every original scalar/string/category/row in source
send order. These producer variants are synthetic grammar controls, not extra
authentic cache generations. Native truncation/mutation, digest cancellation,
span/alias, budget and atomic-output controls remain distinct from server, actor,
Android and physical Thor acceptance. No accepted APK is rebuilt.
