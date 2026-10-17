# Nonshipping receive-candidate encrypted account suite

`hosted_candidate_login.py` is a separate disposable-service driver. It changes
neither the shipping server nor the existing original-server experiment. It
builds nothing. Original AuthServer source tree remains
`f634e21e230009fa8edc91d15429cd4da69eee8c`; the only executed server candidate
change is the previously reviewed `DecPacket(inBuf+pi, ...)` correction.

The actual successful run 38991372131 artifact was independently opened and
admitted again with the stricter recovered host-corpus validator. Its candidate
PE is `9cd262dd862d14bf2d696de65cb70f155f25473503d7fd0968de9969e0ac8003`;
receipt SHA256 is
`25ee2415a280e7b3800808824d95d05b862acca9d4d4879f5fccb5605d6a2451`.
This proves compilation/admission, not service execution or account login.

The existing intact-send probe was also independently admitted from its actual
historical artifact. Its PE SHA256 is
`7cb5672c32c1d304efea9590366250437687e3b0c8c1fafae5e4ec7cf536f29c`;
receipt SHA256 is
`d857ef8fd309149e92de8a8abe6423d0a8d13c338adc64990fbf8dcccefcfe5e`.
It compiled in the failed original-listener experiment; neither its old receipt
nor the new admission establishes an executed encrypted login. Source closure,
project/build function identities, policy, fixture header and binary all bind.
The fixture's retained Windows file hash uses CRLF; source generator comparisons
use its normalized Python source. OpenSSL static linkage is already in that PE.

## Coordinator-owned hosted preparation

Use a fresh `windows-2025-vs2026` GitHub-hosted runner, clean exact
`native-android` commit, Python 3.12, and LF-preserving checkout. Before extraction,
hash each downloaded outer archive against the table. The driver independently
admits the required inner files; it does not claim to validate an outer ZIP that
it is not given.

| Extracted directory | Run / artifact | Outer ZIP SHA256 |
| --- | --- | --- |
| candidate | 38991372131 / 12085517046 | `da7fa3172867eabd9a652d36a4545cb78e91983123f85d894d18a9b3bac8d04d` |
| odbc | 38948147656 / 12066189514 | `0f032ce2232e0501b47918db55c41a3f35a92fda290252bd18d4c1c9ff209c4b` |
| capped | 38970381430 / 12076876614 | `b02c3f81e6c77aa2c5f48df6f0adefccb88b66fe98624bd6eeebfd631b35d3c7` |
| intact | 38974164017 / 12078663003 | `aa7a1badbeb8926cec15009f7f87ebb797aa2345c0c97a183cd1e23866a3499b` |

The candidate directory needs its complete original build artifact. ODBC and
capped directories need the existing reuse-pin file sets. The intact directory
needs only the unchanged `receipt.json` and `coh-auth-intact.exe`; its 384-file
crypto payload need not be extracted or rebuilt. No OpenSSL archive is an input
to this new driver.

```powershell
python native-android/engine/auth-interop/deployment/hosted_candidate_login.py `
  --source-root . --expected-commit "$env:GITHUB_SHA" `
  --output "$env:RUNNER_TEMP/coh-candidate-login" `
  --candidate-stage "$env:RUNNER_TEMP/candidate" `
  --reuse-odbc-stage "$env:RUNNER_TEMP/odbc" `
  --reuse-probe-stage "$env:RUNNER_TEMP/capped" `
  --intact-stage "$env:RUNNER_TEMP/intact" `
  --intact-receipt-sha256 d857ef8fd309149e92de8a8abe6423d0a8d13c338adc64990fbf8dcccefcfe5e `
  --intact-binary-sha256 7cb5672c32c1d304efea9590366250437687e3b0c8c1fafae5e4ec7cf536f29c
```

Archive **only** the new `coh-candidate-login` output, including on failure. Never
archive its private sibling temporary tree or a working configuration. The
coordinator owns workflow creation and execution; this continuation ran no
Windows job or service.

## Runtime contract and limits

All exact artifact/source admissions precede SQL, firewall or service changes.
The driver creates one uniquely owned LocalDB instance with the original schema,
seeds only the existing known disposable fixture, requires the exact x86 ODBC17
binary and qualified SQL version, and performs a fresh three-connection x86 ODBC
readiness observation before attempting AuthServer launch. The observation must
query the expected owned SQL PID successfully and close all connections. Failure
records its bounded receipt, aborts before service startup, and still drops,
stops and deletes the owned SQL instance and removes private files.

Only after that gate does the driver create the original encrypted auth-only
configuration, block nonloopback IPv4 access to the exact private executable,
assign the candidate to a kill-on-close Job Object, and require all three original
listeners to belong to that process. A 90-second listener deadline retains its
failure and attempts another independent SQL observation; this does not convert
the timeout into success or prove the AuthServer's internal pool state.

The admitted normal-send (cap 1024) and historical capped-send (cap 7) probes each
run valid, wrong-password, missing-account and corrupted-frame cases. All eight
must satisfy the original exact numeric receipt, exit successfully, clean their
socket/password state, and leave the owned listeners alive. Failed probes retain
only selected bounded integer observations; arbitrary child strings/stderr never
enter artifacts. Normal-send caps do not control TCP receive segmentation;
`general_tcp_segmentation_accepted` stays false. The exact-function source oracle
separately qualifies receive split/coalescing behavior.

Final `passed` also requires job termination, absent owned listeners, firewall
removal, SQL schema DROP plus stop/delete, private-tree removal and unchanged
tracked source. A failed member diagnostic cannot skip job termination. A valid
positive observed before a later failure remains separately recorded, while
aggregate success stays false. SQL process identity and job membership are
retained without exporting account rows, raw private logs, packet bodies or keys.

The Windows/x86 observer executed and refused readiness in the first attempt
recorded below. The candidate service and account probes remain unexecuted.
Host controls use mocked process/SQL boundaries; actual observer results do not
qualify any encrypted account case. Modal DB failure and
an empty internal SQL pool remain source-supported possibilities if listeners
still fail after independent connection health succeeds. This suite admits no
DbServer, MapServer, shard, selected character, world, Android or Thor success.

## Actual first candidate-suite attempt

Run38993564320 at d949c59 failed the mandatory independent x86 SQL check before
starting the corrected candidate. First connection failed08S01/native233 and
08001; no probe ran. SQL process identity stayed unchanged, but later SQLCMD
DROP also failed; stop/delete succeeded and aggregate SQL cleanup remains false.
Private files and source cleanup passed. Exact receipts, archive and comparison
with the earlier successful ANSI native connection are retained in
`../evidence/candidate-login-runtime-20261017/`. This exposes a pre-service SQL
connectivity blocker; neither encrypted login nor the receive correction was
exercised in that run. No subsequent service attempt was made.
