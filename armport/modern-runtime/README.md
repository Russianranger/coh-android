# Exact modern MapServer runtime qualification

Production source stays frozen at `e563fe5664cd13570899800695c7e9680ac68877`.
Native build: 41363927704. Supporting test code is independently identified and
cannot replace those candidate identities.

Implemented: full .36 donor hydration, exact native/source admission, the four
additional asset stages, actual completed-tick/DbServer readiness, Atlas creation,
ordinary committed save, explicit shipped zoning reopen and unchanged profile,
character, save and owned-cleanup validators. The task-gate payload stays intact.

Nine controls pass with:

```sh
COH_CANDIDATE_ROOT=/path/to/candidate python3 armport/modern-runtime/test_modern_runtime.py -v
```

Local full hydration passed: 23 external payloads / 4,786,799,760 bytes; 89 runtime
and 81 client pins; original importer contract 173,011 leaves / 2,977,730,517 bytes.
Evidence: `armport/evidence/modern-runtime-donor-hydration.json`. This did not
execute a native program or access a database.

Next: wait for the exact candidate build and retained app runtime to succeed.
Replace BOTH runtime-ID zero placeholders in the supporting workflow with the
actual successful runtime ID, then make one workflow-only kickoff. Setup commits
use [skip ci]; the frozen production branch is untouched. The job uses separate
candidate and c86 baseline checkouts and consumes exact existing native/PRoot/
client artifacts. It installs no alternate server and signs no APK.

Each guest has its own existing 5,400-second correctness timeout. A passing pair
qualifies Atlas creation/save/reopen only. King's Row, combat, rewards, collision,
zoning, memory/thermal behavior and Thor cold-start acceptance remain separate.
No <=60-second performance or physical-device result is claimed.
