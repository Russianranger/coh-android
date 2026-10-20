# BodyPart count: client authority and server consistency

1. **Client grammar/count/order confirmed.** The exact member
   `data/bin/BodyParts.bin` in
   `native-android/engine/entities/qualification/costume-export-20261017/exact-client-dictionary-bins.zip`
   decodes to **28 records using the original `ParseBodyPartBegin` / `ParseBodyPart`
   tables and original binary field readers**. The retained original-body-reader
   proof is `qualification/body-read-20261019/host.json`: 6,930 checks each in
   release, ASan and UBSan; the authentic input succeeds through byte 2,584 with
   28 rows. All 24 recorded source pins still match. This executes the original
   grammar with bounded adapters, not a complete engine startup or ParseBoneNames.
   The offline comparison then confirms the same 28 records, in the same order,
   as `upstream/i24/data/defs/ui/bodyparts.bp`, including every text-defined field.
   All five comparison tests were rerun successfully for this follow-up.
2. **Retained running-server count agrees: 28.** Genuine server-consumption
   trace `evidence/consumption/trace.4703` from run `37116009802`, artifact
   `11270589574`, reads the common `data/bin/BodyParts.bin` (2,584 bytes).
   Its retained 128-byte prefix has little-endian count 28 at offset 68 and
   matches the client prefix. This confirms that retained running-server
   observation. No fresh read of the current Thor process was available in this
   follow-up; no complete server-cache hash or ordered-row equality is claimed.

**Authority:** The client's source-pinned, verified count **28** is the
`GetBodyPartCount()` default for the stage-41/43 consumer. The original getter
returns `eaSize(&bodyPartList.bodyParts)`. Flag 0 uses that client default;
flag 1 keeps the original explicit Pack4 count and validation. A server count or
server-file hash comparison is **consistency information only**. Missing,
different or unavailable server comparison data cannot withhold the client
default. No runtime producer lease or current-server cache equality is required.
The local native capacity 30 remains a safety bound, not the default count.

Machine-readable follow-up: `qualification/offline-cache-text-20261020/client-authority-confirmation.json`.

The source follow-up makes the client count independent of optional server-cache
comparison. The previously delivered 0.1.13 APK still contains its earlier
server-hash admission check; it has not been rebuilt for this confirmation.
Its existing package/CI receipts retain that original APK's scope and identity.
The correction passes 3,494 JNI checks and 397 report regression checks per mode
(release/ASan/UBSan), with all 76 current compiler input pins matching. Maximum
report 6,902/7,168 bytes; Interop allocation unchanged at 66,944 bytes. Default
and explicit framing both continue when the server comparison is unavailable or
mismatched. Diagnostic `bodyparts_default:[0,28]` expresses client authority;
`bodyparts_server_cache_status` reports the advisory cache comparison separately.

The retained 2,584-byte CLIENT `BodyParts.bin` and original
`upstream/i24/data/defs/ui/bodyparts.bp` both contain **28 entries**, in exactly
the same order. All text-defined names, geometry/texture/base names, bone counts,
influence values and DontClear flags match; cached indices match source order.
The reusable ordered names/count and source hashes are in
`qualification/offline-cache-text-20261020/client-cache-source-comparison.json`.

- CLIENT binary SHA-256:
  `b0955c46731ed0cb54ad01d96015b301e583bd0224f8d872f50cfefeb08f6beb`
- Original `.bp` (5,218 bytes) SHA-256:
  `21aedaa7b4c901a6e6b8a1a7684f343dba675adc0472bdc6053d378ece37558d`

This does not relabel CLIENT bytes as a server-specific binary. The genuine
retained server-generated cache bundle (artifact11270589574, run37116009802)
contains93 `data/server/bin` files and no BodyParts.bin. Original
`bpReadBodyPartFiles` passes flags0, so it uses the **common**
`data/bin/BodyParts.bin`; server-only files use `data/server/bin` separately.

That artifact's actual server-consumption trace reads2,584 bytes from the common
BodyParts.bin. Its retained128-byte read prefix includes dependency
`Defs/UI/bodyparts.bp` and raw array count28. The syscall text truncates the rest,
so full server-file bytes/hash/order cannot be recovered from it. The exact
source/input search and trace observation are recorded in `server-input-search.json`.
No server was started and no binary cache was generated for this comparison.

Optional server consistency investigation can reuse the existing Parse6 reader:

```sh
python native-android/engine/body-catalog/compare_bodypart_cache.py \
  --server-bin /actual/imported-server/data/bin/BodyParts.bin \
  --bodyparts-bp /actual/imported-server/data/defs/ui/bodyparts.bp \
  --output /new/offline-comparison.json
```

Alternatively, an exact SHA-256 match of the actual device common cache to the
retained binary above reuses this same complete28-row comparison. That device
file match remains unobserved and is not a prerequisite for the client default.
No MapServer witness, runtime process or producer lease is needed. Four focused tests passed against the real retained binary,
including changed source name/count/BoneCount differences; no native build ran.

The existing reader locates the sole Files1 dependency timestamp at zero-based
bytes60–63 (little-endian U32, observed1767225600). The body-size word starts64;
the row-count word starts68. If a regenerated cache differs only by that mtime,
zeroing **only those four bytes in a comparison copy** yields SHA-256
`965964f4e58eb24dbb8b85672fb0bdb9631bfc98d938d3d4444aa09a44c67c83`.
Every other byte, including schema, dependency path, row count/order and complete
row payload, remains part of this identity. The raw file/hash stays available;
no file is rewritten and original cache freshness decisions are unchanged.
The actual device server cache's normalized hash remains unobserved. A fifth
focused test confirms timestamp-only changes match while a row-name change does
not. No build ran.
