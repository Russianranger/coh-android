# Automatic source LOD construction handoff

Pinned recovery base: `d96354411d2f69ec325b1bfe9d0e14999626ba91`.

This change extends only the existing LOD projection module and its additive
source qualifier. It implements complete `lodinfoFillInAutoData` numerical
construction, with four fixed source rows, no allocation and atomic refusal.
It does not expose a receipt that could substitute for the actual CLIENT
LOD dictionary, reduction array, material or resource generation.

`host.json` records exact source/capture/root-ledger/binary identities and the
three host modes. Each mode passed 74,366 checks and 17,799 comparisons; five
semantic mutations failed as required. `alpha-regression.json` records all
311,296 unchanged `modelCalcAlpha` comparisons in each mode. Both original
functions execute under explicit observer type/lookup/storage boundaries.

Source bytes changed after the historical Android standalone evidence. A new
Android build/execution must run before this change is called Android-qualified.
No APK, workflow, protected rendering/support path, profile, server, credential,
asset import or persistent user data changed. Revert this additive change to
roll back; accepted application behavior is unaffected because no runtime
caller exists yet.
