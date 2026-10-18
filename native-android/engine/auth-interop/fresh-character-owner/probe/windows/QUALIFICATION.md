# Private Windows platform source and host API controls

`fresh_probe_windows.c` supplies the previously missing implementation of the
fresh-allocation probe's platform API. It is nonshipping. This qualification
executes the new backend with explicit Windows file/process, transport and
entropy API doubles; host OpenSSL really hashes the synthetic file byte streams.
It does not execute Windows, the CLI, the original owner/controllers, services,
SQL, an original Map process or a character allocation.

The backend has no import effects and permits one live platform lease. Its
caller must be the dedicated, isolated driver-owned CLI process with no prior
or concurrent use of the process-global TCP/UDP adapters. This is not a backend
for co-resident clients. Private policy ancestry/ACLs, fresh nonce creation,
account ownership, Auth/Db/SQL realm, current source/binary admission and actual
same-realm Map registration/readiness remain the independent driver's duties.

The exact96-byte policy is read through a retained regular, nonreparse,
disk-file handle denying write/delete sharing. The backend parses the existing
fixed record, retains the actual Map process handle, checks liveness/PID/creation
time, obtains its executable path privately and retains and hashes that regular
file. File identity, metadata, complete byte count and digest are bracketed;
Map process/file generation is checked at admission, immediately before the
one owner begin and after owner/controller destruction. Its actual self-file
handle similarly remains retained; its MD5 is measured and rechecked privately.
Fresh connect entropy comes from OpenSSL `RAND_bytes` in the production branch.
The configured provider is the unchanged static OpenSSL provider, borrowed
through controller destruction. No path, PID/time, policy, nonce, digest, packet
or credential is printed by this backend.

Those checks admit supplied process/file policy only. They do not prove loaded
image pages, current Db registration, sender attribution, READY_FOR_PLAYERS,
the same service realm, normal client version/checksum acceptance or whole
process-tree ownership. A matching file/hash, nonzero nonce or UDP endpoint
cannot substitute for that evidence. There is no new driver that authors an
allocation policy, no original-service launch and no allocation authorization
implicit in this source qualification.

All independent file/process and transport finalizers are attempted. Failed
`CloseHandle` retains the handle for consuming destroy; the first status is
preserved. The unchanged UDP adapter distinguishes a failed no-acquisition
startup (default-zero diagnostics) from a retained partial WSA acquisition.
Only the immediately observed absence after failed initialize permits its
otherwise unset cleanup-complete bit; a live/imbalanced partial startup still
requires ordinary retirement.

The frozen TCP adapter has a different limitation: it forgets its initialized
flag even after failed `WSACleanup`, and failed wrong-version initialization
does not expose whether cleanup succeeded. Any TCP initialize/finish failure
therefore permanently quarantines this private lease until isolated process
exit. A second no-op finish cannot establish cleanup or free the lease. The
backend emits no success or cleanup-complete claim for that path. The shared
adapters were not altered to obtain a passing result. Cancellation/handle
retirement never removes a server allocation or claims SQL rollback.

Final host qualification `fresh-windows-qualified-04` passed release, ASan and
UBSan separately: each mode170 scenarios,14808 checks,77 runtime plus23 preflight
fallible-operation sites,163 entirely wiped lease frees and8 deliberately
quarantined child leases. Host child-process isolation is part of these new
controls: a quarantined lease is left owned until that child exits, with no
test backdoor clearing production state. The tests cover private record/file
admission, regular/reparse/type/size/EOF refusal, process generation and digest
mismatch, changes before/after begin, known output aliases, partial startup,
independent finalizer failures, close retries, and the exact frozen TCP forgotten
initialized/no-op failure shape. The old owner, encrypted-wire, parser and CLI
qualification entrypoints were not replayed.

The checker brackets17 project inputs,102 host compiler/header inputs,8
`ldd`-resolved linked dependency files and three exact host ELFs. Linked files
are not an observation of actual process mappings. It preserves exact compiler
commands, dependencies, child output and cross-mode equality. The source was
not committed during these controls; primary integration must match all17 raw
pins to committed source. LeakSanitizer alone is disabled for this executor;
intentional quarantine and explicit lease wiping are narrower observations,
not provider/internal allocation leak or whole-process memory claims.

Memory remains unqualified for parent admission. Each production path/image
array is32768 `wchar_t` elements (64KiB on Windows); a nested digest frame also
has a16KiB block plus EVP scratch/locals. The old16KiB caller reserve cannot
cover this backend. Host Linux uses a different `wchar_t` size/ABI, so its stack
or ELF result cannot establish Windows stack, provider workspace, the global
96MiB policy, RSS/PSS or Android/Thor fit. No parent budget is changed here.

`qualification/controls-20261018/final-04-receipt.json.gz` and its exact text
traces are canonical retained evidence. Development01 and02 source predecessors,
receipts and traces remain separately labelled: F found the UDP no-acquisition
cleanup hole after01; E found the frozen TCP retry/no-op hole after02. The first
new strict compile refused a misleading-indentation statement in test code;
its stderr remains in the tool transcript. Development03 then exposed a test
assertion that counted all independent cleanup API calls instead of only TCP
finish calls; its exact failed child/compile traces are retained. That correction
did not change backend production source. No Windows/compiler failure is
inferred from either host test-development error.

For a future changed boundary, use a fresh external destination:

```sh
python native-android/engine/auth-interop/fresh-character-owner/probe/windows/check_fresh_probe_windows.py --source-root . --output NEW_EXTERNAL_DIRECTORY --sanitize
```

Next is a separately admitted real Windows x64 compile against the retained
original OpenSSL/transport/zlib closure, without executing the CLI. Actual
standalone platform preflight then requires its own native Windows evidence.
Allocation remains behind an independently held same-realm original Map READY
and fresh Auth/Db/SQL/profile driver, followed by the ordinary original writer
and server allocation. A later genuine allocation offer still ends in terminal
retirement; full character initialization and authoritative world entry remain
separate and Gates25–27 stay open.
