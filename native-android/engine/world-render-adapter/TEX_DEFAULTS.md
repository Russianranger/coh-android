# Cold initial default binding owner

`coh_wr_tex_defaults` completes the whole original `texFindNeededBinds` operation
over a real immutable `CohWrTexNamespace`. It selects the seven fixed Basic keys
in source order and holds their existing namespace body leases. White, grey and
dummy dynamic cubemap are required at the original assertion boundary; other
missing roles remain absent. Missing dependencies never become a guessed white
resource.

The effective Basic view clears `TEX_ALPHA` only on the selected invisible row.
Every alias obtained through that owner sees the same flags. Other duplicate
basename rows keep their flags, and the underlying cold namespace is unchanged.
Later source Basic reset preserves this alpha change. Consumers must use the
effective view for alpha policy; `source.initial_basic_flags` remains the source
header state. This phase does not perform Basic TexOpt/sampler reset, swaps,
composites or material selection.

The original `texFind` calls `texFixName` with bare white, grey and black. Their
lengths reach the known legacy read before the array at `res[-8]`. This module
requires the already qualified guarded short-key policy and cold initial state.
The oracle executes whole unchanged `texFindNeededBinds` and `texFind`, with the
same explicit two-location guarded `texFixName` correction. Results for those
repaired names are not described as unchanged legacy semantics. Release debug
sentinel assertions are disabled; the original required-default assertion is
observed as a Boolean and becomes an atomic native refusal.

Ownership follows the actual source pin. Every selected role transfers one real
namespace body lease, and a default owner keeps namespace destruction refused.
Getters borrow body and metadata spans until default-owner destruction. Neither
source bytes nor provider contexts can retire while those pins remain live.
After all default pins retire, normal namespace destruction drops its real
provider lease and the fixture can zero and free its original bodies/context.
No new generation or provider identity is invented.

All calls use the source's one owner thread and immutable inputs/provider.
Callbacks cannot destroy the source/provider or change current inputs/output.
Namespace acquire itself
guards cancellation/read/digest callbacks before publication. The module's
first cancellation poll happens inside acquire; final cancellation is protected
by the held leases. An unrelated default owner can retire its own pins in that
final nonbusy poll; this external action is not rolled back or restored on
candidate failure. A dedicated control actually retires that old owner, cancels
the candidate, verifies only its own unchanged output, and retains the source
until the candidate's last pin is released. The full old-owner reservation
remains charged throughout preparation; no early retirement credit is taken.
Rollback releases acquired same-thread handles with no
external callback, so release is total under these preconditions. Public
destruction independently attempts every release and retains its owner on a
refusal. Caller output spans must also be disjoint from opaque source/provider
storage, which the public API cannot enumerate. Exposed metadata/body spans and
the local owner/configuration spans are checked explicitly.

Before any allocation or external callback, the owner charges its allocation,
input/control spans and a 16 KiB preparation reserve in addition to at least the
source's full recorded aggregate reservation. The source reservation includes
the full configured loader, recorded immutable inputs and provider/context
policy. Simultaneously live old default owners and other runtime/provider peaks
remain caller charged; no retirement credit is taken merely because a new owner
is being prepared. Getters visit at most the namespace's bounded 65,536 Basic
rows and seven selected leases, with no heap or external callbacks. The 16 KiB
module stack/control reserve excludes namespace, loader, provider and libc
frames. Configured admission is not measured RSS or a complete global budget.

The new focused checker reuses the exact seven-body artifact from run
39078874753/artifact12118720382 (12,308 bytes, SHA-256
`87a999e6c1c003b96a9fa169ce11637b61eb696766517e063fafce73fdc39c24`).
Its seven bodies total 16,514 bytes. The real invisible source has alpha 1, so
the source alpha clear is observable. Each fixture declares a complete finite
controlled provider; these seven files are not the original full FolderCache
inventory or a current CLIENT namespace witness.

Run only this new qualification from a committed source tree:

```
PYTHONDONTWRITEBYTECODE=1 python3 native-android/engine/world-render-adapter/check_tex_defaults.py \
  --actual-defaults-zip /absolute/retained/default-bodies.zip \
  --output /absolute/fresh/directory
```

The checker admits every current/Git source byte before helper execution and
before each mode. It executes release, ASan and UBSan new tests, a real C-object
to C++ call/link check, and nine semantic code mutations. It retains generated
oracle/fixture, compiler commands, logs and failed outputs. The positive source
comparison covers all seven outputs and every row's effective flags, all 128
presence masks, duplicate first ownership, optional NULLs and required refusals.
New controls cover acquisition/digest/cancellation/lease-capacity/owned-budget
failures, final actual-selection cancellation, real simultaneous old and new
owners, source namespace preservation and actual final provider/body retirement.
LeakSanitizer is disabled for the known host task-enumeration restriction;
owned calloc and provider/body retirement are tracked separately.

No previous qualifier is rerun. No original/current CLIENT namespace, sampler,
material, GPU, Surface, Android execution or world authority is claimed.

The first new development run at source `f9002a331` compiled successfully but
its first release positive refused: the fixture had copied an old one-resident-
entry loader configuration, which cannot retain seven distinct body pins. The
test-only successor sets cache entries to16, within the unchanged128KiB cache
and1MiB full loader reservation; the seven actual bodies total16,514B. Production
and whole-original oracle are unchanged. The failed directory/logs are retained
and never overwritten. This is not a legacy qualifier replay or a source-owner
algorithm failure.

The second run at `8a42b347d` passed the finite-provider cases and reached the
simultaneous-owner control. Its test expected an old default owner to refuse
destruction even at the final direct cancellation poll. Only namespace acquire
callbacks have the namespace busy guard; at the final poll the candidate's real
pins protect the source, while an independent old owner could legitimately
retire. The corrected test asserts old-owner refusal only in actual busy
callbacks, keeps source-destruction refusal at every poll, and leaves both owners
live for the overlap comparison. Production algorithm and oracle remain
unchanged. The final successor additionally qualifies the explicitly permitted
independent old-owner retirement during final cancellation, without claiming
that external state was preserved.
