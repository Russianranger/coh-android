# Original CLIENT TexOpt persisted input contract

The exact retained CLIENT-generated `data/bin/tricks.bin` is now recoverable locally. The source-only immutable `texopt_cache_contract.py` admits its complete SHA and exposes ordered TexOpt prefix records and opaque record spans. It does not parse effective material fields or create a native TexOpt/TexBind.

## Exact recovered identity

The previously qualified client cache artifact is run 36707839624, artifact 11092897979. Its retained outer artifact SHA is `51b5519f86896a846eebd6a20de15c935d788af70d9986083df361af57fdcfae`; inner `client-caches.zip` is 27,071,659 bytes, SHA `5d7f5b5c1932cf755f4063092ba56a30b16d1a705c6716a98b71f9738d61c051`. C recovered this archive and F independently verified all cache members. No download, build or capture was repeated. The archive was preserved; one fresh external member copy was extracted.

`tricks.bin` is 13,537,052 bytes, SHA `cf9595e54bc65a40d2dddc3a5a13c475d7c2ce07a96420e6001b0e2312926bc1`. Its observed schema word is `5ba1b0e3`. Manifest identity: source commit `0b75ade0c801735e10c5798f641948a45cc50488`, data commit `d51533ec8e6a9cf726b9214968077a05fdcf19f3`, producing executable SHA `81885ffa8838ef8759c3526fa1cc0bd44f9108e92698b29054256dd0eb97a0ca`, asset archive SHA `28b4aa8f0b3a71287e9a596df23097722bd71db9ddb9a5a906b5af9d6152cc07`. These are historical producer identities, not the current live CLIENT generation. Cache consumption/gameplay/Android validation in the original manifest remain false.

The entire cache contains 1,585 FileList records, 14,715 ordered TexOpt records and 3,644 ordered Trick records. The file table uses normalized timestamp 1767225600. It is a sorted dependency table (`FileListInsert`), not evidence of text parse order. Persisted array order is preserved independently.

TexOpt ordinal 2,913 has actual name `asphalt_squaremask`, source `TRICKS/COH_R/BUILDINGS/COHR_SHADERS_BRICKFILLER.TXT`. Ordinal 273 is `asphalt_squaremask2`. There is no direct TexOpt name equal to `Bar_vert_sign` in this cache; inherited directory rules still need complete semantic evaluation. One genuine name contains a high byte. Names are retained as immutable bytes without inventing an ASCII case-fold policy for that record.

## Exact source branch and schema

`trickLoad()` under `#if SERVER` calls `ParserLoadFilesShared("SM_Tricks", "tricks", ".txt", "tricks.bin", 0, parse_trick_list, ...)`. The CLIENT `#else` calls nonshared `ParserLoadFiles` with flags zero, then calls `trickLoadPostProcess(NULL, &trick_list, false)`. The SERVER shared memory object is not a substitute for this CLIENT result.

`parse_trick_list` serializes Texture/TexOpt array followed by Trick/TrickInfo array. `parse_tex_opt` begins with the struct-param name string, current filename string, timestamp word, and InternalName string (same target field); the contract projects only these four entries. Exact complete table declarations, including fallback and Trick tables, are source-pinned and their lexical hashes are emitted. Compiled parse-table CRC is **not recomputed** here: source hashes and an observed matching cache word must not be confused with that qualification.

`ParserLoadFiles` resolves `bin/tricks.bin` through original virtual file lookup, validates persistence via `ParserIsPersistNewer`, and reads the binary if accepted. That successful return bypasses text preprocessing. Production mode does not fall back to raw text when the cache is unavailable. Original production reading may ignore CRC differences; this contract always requires the exact pinned word and full body SHA.

On the text branch, `fileScanAllDataDirs` and its overlay order supply raw records. After loading, `trickLoadPreProcess` iterates TexOpts in reverse, skips null names, advances past one leading slash, removes the last extension, and copies the resulting string. The binary is written after preprocessing and before runtime `setupTexOpt`. Therefore the recovered persisted names are preprocessed input names, not proof of effective postprocessed materials.

CLIENT `trickLoadPostProcess` creates fresh name stashes, runs `setupTexOpt` in reverse array order, then `setupTrick` in reverse array order. `setupTexOpt` resets/recomputes derived flags, scales, reflection/specular/layer defaults and more; its non-overwriting duplicate insertion means reverse-order ownership matters. The contract does not silently recreate this table from names or pretend lexical raw-text parsing reproduces it.

## Framing and ownership

The wire envelope is `CrypticS`, little-endian schema word, aligned U16 Pascal `Parse6`, aligned Pascal `Files1`, bounded FileList byte segment, then a whole top-level data segment. Each dynamic array has a U32 count; each nested parser table has a U32 payload length. Original `ReadPascalString`, `FileListRead`, `earray_readbin`, `struct_readbin` and `ParserReadBinaryTable` establish these rules.

The import requires immutable Python `bytes`, bounds input at 16 MiB, files at 4,096, each array at 65,536, projected strings below 1,024 bytes (a conservative supported subset), and file paths below 260 bytes. It preserves raw string bytes, exact ordinals, offsets, sizes and opaque remaining payloads. It refuses embedded zeros, out-of-bounds lengths/counts and trailing input. Frozen data classes/tuples provide source-input views; this host tool does not claim native allocation-peak, native material grammar, Android execution or world publication qualification. Unprojected nested fields are deliberately opaque and are not validated as TexOpt semantics.

The qualifier executes unchanged original `ReadPascalString` and `FileListRead` under release, ASan and UBSan, using bounded memory/filelist harnesses. Every actual projected prefix and record span is compared through a complete binary transcript. It does not execute the complete original material parser or postprocessor. GCC's original FileListRead maybe-uninitialized diagnostic is retained as a warning; the harness uses complete admitted input. LeakSanitizer is disabled because this container cannot inspect `/proc` tasks; ASan and UBSan remain enabled separately.

## Concrete remaining implementation

The cache closes recovery of an actual historical preprocessed TexOpt array and exact record order. Next is a complete bounded `parse_tex_opt`/fallback/Trick grammar decoder against the original reader, including tokenizer storage/default definitions and compiled schema CRC qualification, followed by original `setupTexOpt`/`setupTrick` qualification. Then exact active Basic namespace/overlay identity, capability profile, scene/locale swaps, all texture layers and current generation admission must be joined. None is supplied by this prefix contract. No active overlay, default material seed, material callback or world permit is invented.
