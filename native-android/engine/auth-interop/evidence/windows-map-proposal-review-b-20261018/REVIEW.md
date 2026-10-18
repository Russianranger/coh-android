# Independent Windows Map proposal review

CLEAR for publication as source/API research at D commit
`da4d9ff674fd28ab236ec6d282d0da5d0c76ae96`. No concrete proposal blocker found.
This does not admit an actual Map, Windows profile, account, registry action or
readiness transition.

Read-only checks verified all 31 immutable file pins and all 66 raw definition
spans for the 59 named functions at
`d9adf2b431a039357f8bfe878d3d0da991a81b19`. The additional definitions are
alternate platform stubs; the audit explicitly selects the first desktop body.
The old retained ZIP and its executable, receipt, staged initializer and startup
input hashes match. An independent data-only PE directory read finds the same
11 direct imports, i386 machine and absent delay directory. That evidence stays
historical; it does not qualify the new Map or dynamic/transitive DLL loading.

The source supports the fixed TestClient/CS write, CoH key creation and
wrong-type value deletion, constant English locale branch, Db-owned log listener
when UseLogServer is zero, original positive-map/manual-cookie registration and
separate ready-send/Db starting-clear transitions. `regGetInstallationDir` can
retain an HKEY on its NULL-return paths, so actual complete process/job retirement
remains necessary before profile teardown. A new profile is HKCU isolation,
not filesystem, HKLM, kernel-object or network isolation. The proposal says so.

Microsoft's documented [CreateProcessWithLogonW contract](https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-createprocesswithlogonw)
supports the conditional loaded-profile plan, with local-logon rights, a caller
other than LocalSystem, mutable bounded command line, explicit executable and
target-user file/desktop access. Function success is not DLL initialization or
Map readiness. Private output capture remains unqualified until the new launcher
proves valid target handles or its separate bounded bootstrap.

[Job assignment](https://learn.microsoft.com/en-us/windows/win32/api/jobapi2/nf-jobapi2-assignprocesstojobobject)
also requires compatible nesting/UI limits, session and handle rights; it cannot
be assumed from CREATE_SUSPENDED. A successful complete
[job process list](https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-jobobject_basic_process_id_list)
includes child jobs and must report both counts zero while the handle remains
owned. Returned process and primary-thread handles must bind the actual launch
before resume. An assignment or resume refusal remains a failed attempt with
owned cleanup duties.

The proposal correctly keeps implicit LOGON_WITH_PROFILE separate from explicit
[LoadUserProfile](https://learn.microsoft.com/en-us/windows/win32/api/userenv/nf-userenv-loaduserprofilew)
and [UnloadUserProfile](https://learn.microsoft.com/en-us/windows/win32/api/userenv/nf-userenv-unloaduserprofile)
handle ownership. Historical XP/Server 2003 unload notes do not establish current
host timing. Actual hive-unloaded observation and exact owned SID/profile
[deletion](https://learn.microsoft.com/en-us/windows/win32/api/userenv/nf-userenv-deleteprofilew)
remain gates, distinct from account deletion. User creation requires the native
fresh-success boundary and a valid bounded name; an existing account is not
owned by the proposed lease.

Only ordinary data reads, Git byte reads and public primary documentation were
used. The D audit helper was not imported or executed. No project import,
compiler, test, capture, account, registry, service or target Windows API ran.
E's new scratch launcher implementation is outside this review.
