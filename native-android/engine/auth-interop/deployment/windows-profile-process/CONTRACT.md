# Disposable Windows profile/process experiment

This is NEW scratch source, not a qualified launcher. No Windows API, account,
profile, compiler, inert probe or service has been executed by this tranche.
The only admitted child command in this first design is the separately compiled
`InertProfileProbe.cs`. No arbitrary command, Auth, Db, Map, shell, injected hook,
registry redirection, existing desktop ACL change or existing user mutation is
exposed. A future Map bootstrap is a separate source/runtime admission.

`OwnedProfileProcess.cs` is a dedicated x64 C# console process. It changes only
its own process/thread GUI association, restoring both before closing its new
desktop/station. The parent Python process never changes its station. The
helper's CLI is `--qualify-inert PROBE_EXE SHA256 PRIVATE_PARENT`; all three
arguments are private orchestration input, and the parent must admit the exact
source-owned probe build before calling. The helper accepts no username, SID,
password, desktop, job or child argument selector. Password characters exist
only in a zeroed native allocation; OS credential copies are outside that wipe
claim. User/SID/path/generation information is retained only in a private owner
journal, never in the fixed public projection.

The parent must own a fresh disposable Windows hosted worker, be the exclusive
administrator mutating this lease, and supervise this helper through its own
verified process/job lifetime. Its private parent must already be an ordinary
fixed-drive local directory with an exclusive runner/SYSTEM DACL, with every ancestor free
of reparse points. Nothing changes that parent's ACL. The helper creates only
new nonce children and new account/profile objects. The target user's actual
ability to traverse/open its copied image is tested by process creation; no
logon right, privilege, group membership or existing-object ACL is granted as a
fallback. This scope isolates HKCU/profile, not HKLM, filesystem, network or
kernel-object namespaces. Administrators can override local ACLs; this is not a
boundary against another privileged host mutator.

Order:

1. Refuse LocalSystem, non-admin, impersonated, non-Windows/non-x64 callers.
   Bind a held source-probe file by canonical local path, regular/link/reparse
   identity and supplied SHA before copying. Create a protected runner/SYSTEM
   root, private journal and protected target child, all absent before create.
2. Generate a 19-character nonce account and native secret. Flush the exact
   absent-name creation intent to the protected journal before NetUserAdd.
   Require success, then retain the exact SID through NetUserGetInfo23. No retry/reuse.
   Require no existing SID profile registration, hive or expected profile path.
3. Copy only the exact inert image and private binary input/result files; the
   target child DACL allows only runner, SYSTEM and the newly owned SID. Hold
   file/directory identities against replacement. No inherited stdout handles.
4. Create an unnamed kill-on-close/no-breakaway job and verify initially empty.
   Use CWF_CREATE_ONLY for a new protected window station and create the sole
   desktop within it. Use only the new objects; no WinSta0 ACL edits.
5. CreateProcessWithLogonW(LOGON_WITH_PROFILE), fully specified copied image,
   fixed bounded mutable command line, explicit CWD and NULL environment (the
   documented target-profile-derived environment, never caller credentials),
   CREATE_SUSPENDED | CREATE_NO_WINDOW. Retain returned process AND thread.
   Verify actual token SID, image, process/thread IDs and creation times,
   same session, profile path and loaded hive; assign the exact held process to
   the owned job. Repeat identity/job checks immediately before exactly one
   ResumeThread, requiring previous count1. No retry after a resume attempt.
6. Require bounded direct-child exit0, own job empty, and the exact fixed private
   result after the probe writes/reads/deletes its own HKCU nonce key. It neither
   emits raw text nor touches ordinary application registry locations.
7. Independently attempt job termination and direct-child termination/reaping,
   observe both exact child exit and job-empty list/accounting, close retained
   child/token/thread/profile observation handles, restore original GUI
   association, close new GUI objects and the verified-empty job handle. Keep
   the first refusal and every cleanup failure.
8. Observe both HKU\SID and HKU\SID_Classes absent with a bounded poll. Only
   after complete process/job/handle gates and exact name-to-SID revalidation,
   delete the newly owned profile with DeleteProfileW. Check ProfileList, both
   hives and the latched profile path absent. Delete only the same owned local
   account and requery name absence. Refuse changed identity; no prefix delete.
9. Retire only fixed identity-latched private files and empty directories, never
   recurse unknown entries/reparse points. Retain a private journal whenever
   cleanup is incomplete. No automatic recovery/deletion of another run's data.

The explicit cleanup polling bounds do NOT make synchronous Win32 API calls
deadline-safe: NetUserAdd/Del, profile loading/deletion and process creation have
no documented timeout argument. A parent watchdog kill must report cleanup
unobserved, retain the private journal, and must not infer successful absence.
Likewise a documented API refusal/partial acquisition must not be promoted to a
successful target process or profile. The source preserves first cause and
attempts independent safe cleanup; it cannot promise that external OS calls
always complete. NetUserDel is name-based, not an atomic SID-conditioned delete;
exclusive account mutation is an explicit host precondition and immediate SID
revalidation is an observation, not protection against a concurrent admin.
Account creation and suspended process creation are not crash-atomic with
their returned-identity journal updates. An outer crash/timeout must preserve
the private intent and report cleanup unobserved; neither a name prefix nor an
intent alone authorizes account deletion. If process creation was attempted
without a returned held process handle, the helper quarantines the account,
profile and private journal instead of claiming observed process absence.
If account creation was attempted without a bound successful account, orderly
cleanup must requery the exact private name as absent before reporting the
no-launch profile/account branch clean or retiring its intent journal. Any
present or unqueryable unbound account is quarantined and never deleted.

No profile handle is invented for implicit LOGON_WITH_PROFILE loading. This
implementation does not call LoadUserProfile/UnloadUserProfile or request
backup/restore privileges. Actual hive absence is mandatory before deletion.

`TestOwnedProfileProcess.cs` uses a fake platform only. It covers one-shot
ordering, errors after acquisition, assignment/resume barriers, every cleanup
attempt, first-cause preservation and cleanup conjunction. These source tests
are not Windows API evidence. Future first Windows qualification must compile
these NEW sources only and execute only the inert child, preserving private
journals/raw outputs separately from the fixed public receipt. No accepted17
or older Auth/parser/control suites belong in that qualification.
The helper binds the supplied probe image bytes, but the public projection
keeps `probe_build_provenance_verified` false: the external qualifier must
independently admit the source-owned build before invoking this private CLI.

Official API sources read before implementation (2026-10-18):

- https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-createprocesswithlogonw
- https://learn.microsoft.com/en-us/windows/win32/procthread/process-creation-flags
- https://learn.microsoft.com/en-us/windows/win32/api/lmaccess/nf-lmaccess-netuseradd
- https://learn.microsoft.com/en-us/windows/win32/api/lmaccess/nf-lmaccess-netusergetinfo
- https://learn.microsoft.com/en-us/windows/win32/api/lmaccess/nf-lmaccess-netuserdel
- https://learn.microsoft.com/en-us/windows/win32/api/userenv/nf-userenv-getuserprofiledirectoryw
- https://learn.microsoft.com/en-us/windows/win32/api/userenv/nf-userenv-deleteprofilew
- https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-createwindowstationw
- https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-createdesktopw
- https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-setprocesswindowstation
- https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-setthreaddesktop
- https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-getuserobjectsecurity
- https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-getuserobjectinformationw
- https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-closewindowstation
- https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-closedesktop
- https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-getprocessidofthread
- https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-getthreadtimes
- https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-resumethread
- https://learn.microsoft.com/en-us/windows/win32/api/jobapi2/nf-jobapi2-assignprocesstojobobject
- https://learn.microsoft.com/en-us/windows/win32/api/jobapi2/nf-jobapi2-queryinformationjobobject
- https://learn.microsoft.com/en-us/windows/win32/api/jobapi2/nf-jobapi2-terminatejobobject
- https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-getdrivetypew
