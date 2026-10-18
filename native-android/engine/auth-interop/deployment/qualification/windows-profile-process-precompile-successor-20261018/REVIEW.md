# Precompiler helper source successor

This supersedes only two of the seven source/build inputs at published revision
`9c29e08c8d7e0ab38cff00f2997c39738a56ad07`. The original files and historical
source-only freeze remain unchanged in Git and the parent scratch directory.
No compiler, models, helper, probe, Windows APIs, account or profile have run.

The helper changes only these two locations:

1. `Identity` splits `Need(GetProcessTimes(...) && GetThreadTimes(...), IDENTITY)`
   into sequential same-cause `Need` calls. This makes the thread FILETIME
   definitely assigned in C#. The original left-to-right order and refusal
   behavior are retained: a refused process-times call still prevents the
   thread-times call. No identity predicate or resume behavior changes.
2. `JobIsEmpty` starts both unmanaged pointers at zero, allocates inside the
   protected `try`, then uses guarded nested-finally frees. Failure of the
   second allocation can no longer leak the first, and either free is attempted
   independently. Every original query, count, accounting and return predicate
   remains identical.

The build recipe changes exactly one literal: the expected helper SHA256.
Its three target source lists, compiler flags, references, manifest, outputs
and no-execution behavior remain identical. The other five producer inputs are
byte-identical to revision9c29. The model source still contains the same 36
unexecuted source scenarios; no previous model pass or Windows result exists.

Root independently confirmed both raw source issues and approved the narrow
proposal. Worker D reported source-only CLEAR for this exact diff. Worker F
independently cleared the same exact two-hunk/one-literal successor and full
seven-input map in source review commit17dcced30. This file does not invent an
execution receipt.
The exact F review is
`native-android/combined-client/diagnostics/continuation-f-20261017/windows-profile-helper-precompile-successor-review-20261018/review.json`,
5,141bytes/SHA256`79e58afc7b536032325e14bd265e275cc1467018ec4e71ca48f90714e3ae7542`,
schema`coh-f-windows-profile-helper-precompile-successor-review-v1`,passed=true.
This successor is source/compiler-readiness work, not an inert runtime or Map
lease qualification. The new supervisor and its separate two-target additive
recipe are outside this seven-input compiler/model-only role.

Historical freeze reference:
`native-android/engine/auth-interop/deployment/qualification/windows-profile-process-source-20261018/source-freeze.json`
was3,321bytes/SHA256`a973e47495640bbcf31fca99cb0916b9533ff3db4cab58cfc8683115cead7196`.
It truthfully remains the prior uncompiled f23a source review. This successor
does not rewrite it or retroactively qualify it.
