# Raw costume bodies — host qualification

Parent implementation: `8c742201412316acd0fa0e325596fde676ca48bc`.
Original import: `0b75ade0c801735e10c5798f641948a45cc50488`.
`host.json` binds exact implementation, source-pin, oracle and fixture hashes.

The additive full/owned raw body decoder executes against unchanged original
`costume_send` and `costume_receive`; the custom NPC color body executes against
unchanged `NPCcostume_send` and `NPCcostume_receive`. Original cached and indexed
string/color functions and BitStream functions execute as well. Eight synthetic
fixtures cover both alignment modes, explicit and implicit part counts, zero
parts, all 30 scale values, all 72 supergroup color words, extra-info strings and
colors. Expected values come from independently executed original consumers.
Original engine/storage/dictionary shims are explicit, not authentic captures.

Release, ASan and UBSan each passed **646,790 checks**, **69,163 every-bit
truncations**, and **25,000 randomized bodies**. Dictionary deep-copy ownership,
generation/manifest mismatch, sparse holes, bad cache/index references, nonfinite
scales, string/count bounds and aggregate dictionary memory refusal pass. Every
failure retains the caller reader/output. All prior entity/list/stat/FX tests
also pass. Sanitizers cover new native code/tests; the original trusted source
oracle runs at `-O0` outside sanitizers. LeakSanitizer remains disabled due to
sandbox process-map limitations. No independent human/worker costume code review
is claimed by this receipt.

The immutable copied dictionary owner admits at most 4 MiB total and 65,536 slots
per table. Raw full-body output is 49,008 bytes and separate workspace 80,920
bytes; custom color output is 16,904 bytes. The loader verifies matching supplied
generation/manifest identity; independent external capture/digest verification is
still required. It does not authenticate caller-supplied identity. No authentic
dictionary exists in this checkpoint. See `COSTUME_IMPORT_CONTRACT.md` for
aggregate lifetime and import requirements.

The full/owned/custom **outer entity appearance envelope is still unsupported**;
these are standalone raw bodies. No complete selected-self record, full initial
transaction, authoritative render snapshot or network acknowledgment is enabled.
Android ARM64 build, Android emulator execution, physical Thor acceptance and
authentic server interoperability remain pending. The accepted APKs and saved
profiles are unchanged. Both `fixtures.h` and `costume_fixtures.h` are needed by
the expanded native test target.
