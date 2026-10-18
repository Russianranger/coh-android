# Final aligned-slot TexWord proof

This supersedes the successful 120fd TexWord proof only for a new test-fixture alias correction. Production C/H/table and original-function oracle bytes are unchanged. The destruction overlap control now stores an actual correctly typed `CohWrTexWords*` in aligned allocated cache-tail storage; it confirms refusal without freeing or changing the pointer. This avoids accessing a `uint8_t*` member through an incompatible pointer-to-pointer type.

The implementation/source history is `ffe2d843a` → `120fd255d` → `76fbb9195`; earlier precise evidence is committed at `0f72fd2bb`. The sibling `texwords-120fd255d/HANDOFF.md` describes the full API, input provenance, measured budgets, refusal/source domains, failed development history and remaining blockers. Its all-false authority boundary is unchanged. All36 prior evidence files are hash-bound by this binding, without replaying earlier tests.

The final new focused release/ASan/UBSan runs each pass 205,331 checks, 43,534 unchanged-source lookups and 7,255 root record/name/serialized-span comparisons. All 725 authentic rows, 12,911 nested records and 99,125 fields are consumed. All 9 semantic mutations and actual C-object/C++ call pass. Fourteen source loaders retire; ten authentic provider contexts and byte allocations are actually freed before exercising copied owners. Candidate/source-pin/cancellation/late-final-store/known old+new overlap accounting is unchanged. No old qualifier, capture, helper replay during binding, Android/Windows/GPU/current namespace/material/world/RSS authority is claimed.

The source cache is 694,324 bytes; owner 1,025,196; requested original workspace 1,232,312; two controlled namespace full reservations 6,463,972; static builder 2,097,152. Configured source loader total/allowance 8 MiB and candidate 4 MiB are explicitly charged. Preparation reserve 30,087,417; known old+new overlap 31,112,614; conservative native recursive control 5,192 within 32 KiB. The 16 MiB fixture external allowance is a declared policy, not RSS/global admission. The opaque loader configured total bound remains a caller precondition.

Final retained scratch output: `/workspace/scratch/7ed1da2a7e55/b-texwords-final-aligned`. Same focused CLI as the sibling handoff, with a fresh output directory. No further source changes planned.

Exact binding metadata:

```json
{
  "source": "76fbb91955a6a9f37145002f6b909928abcecb46",
  "raw_bytes": 39109,
  "raw_sha256": "4e1dfddd56f649fb3db70ca33ff8062de484c25cda4e8a656a3489945f824e79",
  "gzip_bytes": 12528,
  "gzip_sha256": "a8076cbdc8556db359a8c1dd3c1a656c92778ec658ab2ae073f8d80d7a17ec8b",
  "binding_bytes": 16625,
  "binding_sha256": "a214ca0c5c8a51953ad45c9bce04f15b77c2d0a4b4f624ea463f02b0e8d87515",
  "source_pins": 29
}
```
