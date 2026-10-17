# Actual candidate body/header comparison

These standalone host tools consume the actual source resource capture and the
separately pinned candidate manifest report. They introduce no Android, asset
loader, accepted client, renderer or server change.

`acquire_resource_candidates.py` recovers only the selected GEO members from the
two existing nested release ZIPs, with a 128 MiB exact-range budget. ZIP CRC and
full selected-payload SHA256 are checked. Full outer/inner archive hashes are
explicitly not verified. A first attempt stopped after 19 verified bodies on a
403 tunnel failure; its receipt and exact hash-matching original script remain
retained. Explicit resume rehashes existing bodies, preserves prior receipts and
never overwrites a file. It does not rerun a server or rebuild an APK.

`check_resource_candidates.py` compiles release, ASan and UBSan host diagnostics.
The native diagnostic uses the protected loader and A resource index, processing
one GEO file at a time. It compares **every captured model observation for that
file**, including any unreachable owners, with the actual full body's exact
model names, original sorted runtime row versus disk row, version,
vertex/triangle counts and original material texture-ID/name/triangle partitions.
Trick flags, bounds, scale, effective client materials and LOD observations are
not silently declared equal by this check. Named native reservations remain
within 96 MiB; this is not a whole-process RSS or world publication budget.

A tiny new A-owned read-only getter returns the existing immutable decompressed
GEO header, borrowed only until resource index retirement. No new allocation or
protected API modification is needed. An independent bounded derivation follows
the original `geoLoadStubs` envelope/inflate branches and checks its header SHA256
against the native header. Original v0 has a separate four-byte difference
between the read-prefix end and data offset; the report preserves both values.
The original new-format branch excludes version 6. The derivation is a separate
implementation checked against the qualified native reader; it does not claim
an unchanged original `geoLoadStubs` executable was run on these bodies.

A source metadata match and an independently authenticated body SHA are useful
necessary gates. They are not a direct opened-file identity receipt. The capture
retains a SHA256 of the full ordered runtime inventory but not the per-file
leaves or an opened-header hash. Its exact preparation-manifest chain proves the
expected fixture recipe. To establish the exact runtime file selection without
another capture, one would need retained per-file preparation outputs linked to
that inventory, or reconstruct the complete ordered inventory and match its
commitment. Agreement of names, header metadata and versions alone cannot
exclude a different body with the same header. Consequently all outputs keep
`source_generation_admitted`, `assets_admitted`, CLIENT material/LOD and world
authority false.
