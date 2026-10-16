# Independent bounded scene receive review

These host review receipts bind the clean integrated source commit
`648ebf2d0c2cca9dfa5ef9acf9b1fe705ffe9c01`, tree
`15cce2275e7d6c55b4b4f0acddd62c6803174e76`. Each recorded production hash was
compared with the previously reviewed draft and matched before these receipts
were written. The scope is the files listed in the receipts, not an assertion
that every file in the repository was independently reviewed.

- `source-review.json`: transport, Map owner, replication and UI review. The
  reviewer identified a stale owned-view collision across UDP resume when an
  allocator reuses an address. The transport implementation now preserves the
  UDP lease generation across replacement NetLinks. The reviewer contributed
  the delegated UDP regression to the transport worker's test file. Actual
  controlled OS UDP testing passed 1,194 checks, 61 negative cases and 22 socket
  scenarios under ASan and UBSan, including release, suspend, close, cancel,
  disconnect, timeout and descriptor balance. LeakSanitizer was disabled on
  this restricted host.
- `source-oracle.json`: seven additional synthetic fixtures compared the
  complete unchanged pinned `bsCompress` producer with an independent Python
  zlib producer and the owned native decoder. The fixtures include persistent
  dictionary continuation, independent packets, tiny uncompressed tails and
  decoded bodies through 4 MiB. All 49 assertions passed. A linker allocator
  probe observed one owned allocation per valid body and zero allocations for
  an over-budget 32-bit hostile declaration. A truncated `Z_SYNC_FLUSH` marker
  poisoned its streaming decoder. The legacy producer's trusted test storage
  wrapper was expanded for these fixtures; its function body was unchanged.
- `jni-serialization.json`: the actual combined JNI serializer was compiled
  unchanged with `-Wformat=2 -Werror`, ASan and UBSan, using a host JNI capture
  shim and synthetic numeric diagnostics. Eight JSON outputs parsed correctly,
  including counter extremes, all decode failure kinds, declared length
  4,294,967,299 and invalid-phase fallback. The six-field receipt was preserved;
  the largest output was 2,804 bytes within the 6,144-byte report buffer.

The original 16 KiB compressed wire/reassembly bound, queue sizes and sibling
limit remain unchanged. The expanded decoded budget is explicit and at most
4 MiB; one owned decoded body is released after inspection. Large Map bodies
remain restricted to the GROUPS prefix inspection path. Unknown entity and
group tails do not authorize READY, full-update ACK, character identity or an
authoritative spawn. UI failure hints contain fixed app text and numeric
failure classification, without interpolating remote packet bodies.

These are controlled synthetic host checks. They do not demonstrate a real
server session, Android execution, physical Thor acceptance, complete GROUPS
tail decoding, authenticated account login or server-authoritative rendering.
Those qualifications require their own evidence.
