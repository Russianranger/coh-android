# Milestone 13 — bounded complete raw power stream

Publication parent: `70b16f73b424351a1e69eca9b21b831371e51e27` on **native-android only**. This is a source component milestone, with no new APK, disposable server capture or repeated Android job. [MILESTONE12.md](MILESTONE12.md) remains the complete world/resource/authentication/memory checkpoint; its accepted boundaries remain unchanged.

## Implemented and independently reviewed

`engine/character-dictionary/coh_power_stream.[ch]` traverses the entire historical powers cache using a 4 KiB buffer, validates every persisted BasePower/AttribModTemplate/SuppressPair/PowerVar/PowerCustomFX record, and retains source-ordered record/name/CRC spans and a bounded original-order integer index. No full object graph or 62 MB heap copy is retained. Exact input: 62,047,164 bytes, SHA256 `25641e747c60e066016fcc7d2ce0a2e72f57d7d3953f7b1ff4b18b69e2d49c6d`.

The complete original binary reader/writer round-trips all 20,241 records and compares each original name CRC. The original integer-stash prefix supplies independent slot/first-winner comparisons; duplicate records remain in source order. EOF, recursion/count/string bounds, aliasing, complete pre-callback budget, malformed numeric byte domains, I/O/digest failure and cancellation all refuse transactionally. Unknown numeric identifiers and float words remain raw.

Required production fix `3630447e179f11ef956315836b11158bd9d47da8` closes cancellation raised by the final buffered read/update or during index/finish. Successful digest finish retires digest state even if subsequent cancellation prevents publication; no abort is then issued on retired state. Earlier source53aaceb4f/proofece221a3b remain historical and are superseded by the final cancellation proof.

| Qualification | Exact result |
| --- | --- |
| Tested source | `9f7362cbf3fe12d2a6d4870c71f357061df94bcf` |
| Final proof commit | `9d5c8dd8399c26e9ec3e13f20509940b39b0fa06` |
| Independent review | `43ed6d67d890248cef3cc2f7d2213c9d0a7d5f9a` |
| Release / ASan / UBSan | 434,417 checks **each** |
| Source receipt | 60 exact Git blobs, independently compared |
| Proof compressed SHA256 | `f55992b31591bf4ce9e96a341cf0fb59f283adea2ff117940d6627c429c96513` |
| Proof uncompressed SHA256 | `9ede3f41a4b97ecad9c3b55cbe3886163789065bd0fa2d86bd98f35707bf4ace` |
| Fixed owner / workspace / fixture provider | 1,048,744 / 1,052,840 / 180 bytes |
| Fixture aggregate including reserves | 2,134,652 bytes; literal module cap 4 MiB |
| C++ linkage / frozen helper controls | Passed; stale-PYC ignored and changed-source refused |
| Android ARM64 / emulator / Thor / live server for this module | Not executed |

The original binary codec uses explicit enum/default/storage shells appropriate to binary read/write, not a source schema-CRC constructor. Original oracle, external OpenSSL sanitizer/stack closure and Win32 ABI are outside this native sanitizer claim. LeakSanitizer is disabled because this traced environment cannot run it. Provider context, immutable input identity/file descriptor, callback code and pre-reserved scratch must outlive the returned borrowed owner. This is not an executable global parent/child memory adapter or a measured combined pipeline.

Post-review documentation `153a14ff2` records the seal; parser/oracle/test blobs are unchanged. The exact older tested documentation remains recoverable at9f7362cbf, so the 60-file receipt is not silently reassigned to a later revision.

## Remaining authority and implementation gates

Observed cache schema word `0xb553b8ff` is not yet a qualified recomputation of the original full ParseTableCRC. Complete static enum/default dependencies and actual dynamic DefineContext must be executed and independently checked. An unfinished experiment is preserved only in the recovery bundle at4f14384c6; it is not installed as a production or qualified helper.

Original loader cache-hit/source branch association, current dictionary generation, category/set/power joins, DuplicateMissingPowers, Finalize, SetForwardPointers and back-pointer semantics remain open. SetForwardPointers may resolve a set-qualified short name, and DuplicateMissingPowers can allocate source-defined copies: raw index counts alone cannot qualify the complete global runtime dictionary. Complete initial character transaction, selected DBID/entity generation and immutable authoritative actor publication remain open. READY, RECEIVED_CHARACTER and full-update application ACK stay disabled.

The new 2,134,652-byte fixture aggregate is **not** added to the M12 global memory ledger as a qualified runtime composition. A real provider/owner adapter must charge its actual live leases and reserve/retire child allocations through the parent contract before claiming the 96 MiB combined budget.

The authentic snapshot already resolves all seven formerly missing names as original runtime future objects; only `_mmayhem_curtain_8_01c` is root reachable. No recapture is needed to reproduce these bytes. Actual same-boundary live GROUPS association, 14,346 public raw-bounds rows, current client material/default/locale/LOD dependencies and atomic world+actor GLES publication remain prerequisites for a new Combined APK. Endpoint remains **SCENE_INCOMPLETE**; no genuine native world/actor or Thor session is accepted.

## Recovery and six-workstream state

All original trees remain preserved. `milestone13-source-history.bundle` (50,997 bytes, SHA256 `6d8a98b1c5650deb33129229bf8083dcd3e4b5af968353a0efecc5c9ca1b2d03`) is additive to the existing M12/public recovery prerequisites; its JSON records exact references and verification. It preserves C through4f14384c6 and F43ed6d67d, including superseded receipts and the explicitly unqualified schema experiment. The separate tiny doc-append bundle preserves153a14ff2 without replacing that archive.

A catalog/sealed geometry c48e57126d, B raw bounds545296bf33, D Wine inventory04bfd7d8d4 and E locale frontierf5cbc1d3a6 remain pinned and unchanged from M12. C has completed this raw stream component and continues the original schema-CRC qualification in its isolated tree. F has completed independent review of this component and is available for that next candidate. No worker edits shared JNI, Gradle, CMake, launcher or gameplay-owned paths. No server, emulator or expensive capture job was started for this cut.

The actual Android13 source01cbd run39011930318 remains successful within its original UDP/DB-to-Map contract scope; later modules gain no Android execution claim from it. Accepted Session0.3.0, Combined0.1.7 and Support0.2.0code201 APKs, profiles and deferred physical tests remain untouched.
