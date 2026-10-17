The focused [source-only run](https://github.com/Russianranger/coh-android/actions/runs/39074781865)
succeeded at `fd213266f1b6665acece877dabb7dab6663e647c`, tree
`ff86ef76821a5aace6d4ffb53671cc37aaa2247e`. Its only job, `117519562485`,
completed every step successfully. The log records 11 source-admission controls,
10 fresh-retention controls, and the native verifier's 328 synthetic checks.

| Retained artifact | Identity |
| --- | --- |
| GitHub artifact | `12117045136` |
| Archive bytes | `2794` |
| Archive SHA256 | `dffcbfc3569cd12cb5e4ebc4b3bc9be6aaffa67d6cfb5c6b41e5d4a5af20b7e8` |
| Only member | `native-verifier.json`, 8276 bytes |
| Member SHA256 | `c5a16359e01758c92073b931d64a0aad2f2b42fdf23781deb28907c5884edd84` |

F downloaded and checked the exact archive against both GitHub artifact metadata
and the upload log. All 37 recorded native/checker/inspector/test source hashes
match the exact published Git blobs. Dependency preprocessing over those exact
bytes in a temporary tree reproduces the complete recorded source set. The
6186-byte input fixture also matches its published blob and receipt hash. No
native suite or former qualifier was rerun by this review.

Release, ASan and UBSan each report 29 native cases, including 26 refusals and the
saved-tail/four-roots case. Each mode also refuses all 77 injected linked native
allocation failures and reports zero final tracked native allocations. This
excludes libc/OpenSSL internal ownership; LeakSanitizer is disabled. The
34,081,469-byte named peak belongs to the synthetic fixture and component
reservation. It is not process RSS, Android ABI evidence or complete client
budget admission.

The owner/resource observations are explicitly synthetic. No live capture,
source-generation token, current CLIENT material/LOD/cache equivalence, actor,
renderer, ACK or world authority follows. These receipts continue to describe
the exact published commit if later B/C source work changes the current tree.

`run.json`, `jobs.json`, `artifacts.json` and `job.log` retain the observed hosted
outcome; temporary artifact download credentials are excluded. `artifact.zip`
and its sole extracted member preserve the actual proof. `verification.json`
records F's exact source, fixture and workflow/control pins.

Recheck the retained bytes and published source without running tests:

```sh
python3 native-android/combined-client/diagnostics/continuation-f-20261017/source-snapshot-contracts-39074781865/verify_artifact.py \
  --source-root /path/to/coh-android --output /tmp/FRESH-source-contract-review.json
```
