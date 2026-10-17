# Independent final coordinator native tool review

F found no concrete source/API/admission blocker in coordinator tool source
`431cea8bd0fd1ec93ccfbe4433570b91c1d43f66`. F read the CLI and checker,
verified every one of the 1,738 receipt source hashes against that exact Git
commit, and rehashed the three final x86-64 ELF binaries. Current source files
had zero differences. No tests or qualifier were replayed.

The authoritative 234,882-byte build receipt SHA-256 is
`73624c7f17830c62ece141d86d1b5da7af563180396828e32d8f1fa1297593e4`.
It is preserved exactly in deterministic `build.json.gz` (83,573 bytes), SHA-256
`58a94e876735bea742a7b97860d2533e7abb3976fd803f4410823c101c8483b2`.
All consumed source bytes equal committed HEAD. The dirty-at-start field records
only the separate pending workflow edit; it does not invalidate that source
equality or replace the earlier dirty-worker attempt's historical status.

Release/ASan/UBSan report 91 checks each over four scripted real-socket modes and
argument refusals. The included old GROUPS tool and new Map/Local TUs are in the
compiler-derived dependency closure. The observer streams genuine synchronous
loans directly to fixed private exclusive files, preserves accepted GROUPS when
the optional initial observation refuses, and writes the exact strict private
schema only after network-owner close. A rejects unexpected failed-packet
leftovers. Actual original-server capture, character semantics, forbidden
application commands, current generation, Android and world authority remain
unqualified.
