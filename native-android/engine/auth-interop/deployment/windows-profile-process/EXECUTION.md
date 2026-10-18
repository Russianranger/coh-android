# First actual inert Windows execution

`supervise_inert.py` reuses the exact successful compile/model artifact from
[workflow39106023132](https://github.com/Russianranger/coh-android/actions/runs/39106023132).
It never invokes the compiler or the accepted model executable again. Its new
boundary controls do not execute Windows APIs or any accepted model/service.

| Accepted input | Identity |
| --- | --- |
| Original build revision | `362f10cc71148c32b3b84e6c6cbe7ce59ac94480` |
| Artifact ID | `12128507472` |
| Artifact ZIP size | `43251` bytes |
| Artifact ZIP SHA256 | `8d8dfbe59ed5349e1c8468445e7b8b1c005f9e9f189a665a0a96cc67fba9bebc` |
| Helper image SHA256 | `e8662ff392e9cdb1357e153b522fb13ecb4980c397d5cdb27c85703c155fc070` |
| Inert child image SHA256 | `0c1d47938f84cfb4d4dd76d157a7e5585f743e3daf91e8ce2e77356f5e0659d0` |

Root workflow orchestration must verify the exact run, artifact name, ZIP
size/hash and flat archive members before extraction. Pin the current new
supervisor and its existing `../windows_suspended_thread.py` import before any
project Python execution. The driver independently admits the original build,
source-admission, summary and model-result receipts, current frozen C#/manifest/
build-recipe bytes and both executable images. No arbitrary executable, service,
username, profile, desktop or child-command selector is accepted.

On one exclusive disposable `windows-2025` GitHub hosted X64 worker, choose fresh
paths below an existing ordinary fixed-drive private runner directory and run:

```powershell
python native-android/engine/auth-interop/deployment/windows-profile-process/supervise_inert.py --artifact-dir $acceptedArtifact --private-parent $newPrivateParent --public-out $newPublicOutput
if ($LASTEXITCODE -ne 0) { throw 'INERT_EXECUTION_REFUSED' }
```

The driver creates its parent atomically with a protected runner/SYSTEM DACL,
holds both images open without write/delete sharing, starts the exact helper
suspended, assigns the exact retained process handle to an initially empty
kill-on-close job, and calls the admitted one-shot primary-thread resume owner.
The helper then owns its existing fixed account/profile/desktop/HKCU experiment.
No existing Auth/Db/Map executable is started and no authentication, checksum or
version rule is changed.

The outer deadline is180 seconds for resumed helper exit and both bounded pipe
EOF observations. Fixed8192-byte stdout and zero-byte stderr budgets refuse
excess output without exporting it. A strict receipt parser rejects duplicates,
unknown/missing fields, coercions, non-ASCII/multiple-line output and impossible
successful cleanup conjunctions. The public native receipt is reconstructed
from fixed fields. A successful byte/source admission does not change the
helper's own `probe_build_provenance_verified=false`; the independent driver
reports its separate build admission only after the post-execution image
bracket. Loaded OS/CLR mapping closure is not qualified.

Outer termination, direct-child exit, job list and accounting empty, pipe
retirement, retained process/job/file-handle close and empty-parent removal are
separate observations. All independent cleanup paths are attempted. A failed
pipe reader cannot block cleanup on a buffered stream close. Never recurse into
or upload the private parent. On timeout/refusal, account/profile/journal cleanup
remains unobserved unless the valid native receipt actually proves its complete
cleanup. A process/job kill is not account/profile rollback. The fresh protected
parent is retained on uncertain inner cleanup; host disposal is the outer lease
boundary, not proof of observed account absence.

Upload only `supervision.json` and, when produced, `inert-result.json`. Both
exclude private paths, raw output, usernames/SIDs/PIDs, journal bytes and Win32
exception text. Even a fully successful inert experiment leaves service
readiness, live Map lease, Auth/Db/Map interoperability, source generation and
world authority unqualified. The existing fixed helper cannot retain a live
Map process; a separate fixed-role live lease and read-only same-realm readiness
observer are the next implementation prerequisites.
