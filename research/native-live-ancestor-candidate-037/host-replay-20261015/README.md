# Fresh independent host replay — 2026-10-15 UTC

The exact preserved execute-only ancestor candidate was recovered from
`7cf6fd23d4d4319bdbc456df89df1a2428885197`. Both candidate source files match
the historical source pins byte for byte. The original `qualification.json`,
`source-pins.json`, original producer and all retained binaries remain unchanged.

All 51 Linux kernel controls passed: the original 42 and all nine proposed
permission/refusal controls. The test driver built one new GCC host-only C test
library in a disposable stage containing the unchanged original dependencies
plus the two exact candidate files. No ARM, JNI, Game or probe compilation ran.

The child controls set no-new-privileges before exec, remove all effective,
permitted and inheritable capabilities, and assert that state after exec. The
readable-root control requires actual EACCES from opening its mode-0111 parent
read-only. It verifies a readable final root descriptor rather than O_PATH,
namespace revalidation, real emitted directory rows and descriptor cleanup.
Further controls reject unreadable final roots, denied search, symlink ancestors,
ancestor replacement and same-inode symlink substitution before and after rows.
Post-row errors retain terminal status and forbid stock fallback.

The authenticated retained CEC249 host JNI library reproduced the old refusal
without a rebuild: directory read on the execute-only parent failed EACCES while
a direct known-name open of the final readable app root succeeded. The old native
namespace open refused EACCES before rows and cleaned up every descriptor. The
separate locally compiled B264121 library was not recovered or replayed.

`qualification.json` records exact source hashes, scope and observations;
`candidate-51-tests.stderr` contains the complete test log.
`retained_baseline_dac_child.py` is the exact fresh negative-control child; invoke
it with the authenticated host library, disposable app-root pathname, its
execute-only parent and a JSON object containing device/inode/uid pins, using the
candidate test module's `_permission_capability_drop` as subprocess preexec_fn.

Root independently reviewed the exact C delta and accepted its host scope: only
nonfinal flags/lookahead change, with final readability and all existing root
identity/revalidation checks retained. Any justified ARM ABI rebuild, Android admission,
retained PRoot/Wine parity and physical Thor testing remain later gates. These
host controls do not measure startup or zoning and do not authorize an APK.
