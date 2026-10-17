# Independent actual hosted wire artifacts

Read-only GitHub inspection of run `38993564322` and actual artifact
`12086321527` verified successful standalone prefix/range Android13 execution.
Whole-ZIP size/SHA, all CRCs, both exact ABI ELF/fixture/build receipts,
Release/ASan/UBSan equality, original fixture identity, executing driver identity,
and all 15/19 native source entries were independently admitted. Source entries
were compared against Git blobs at exact qualified `d949c59f` and tree identity;
the current integration worktree was not rewritten or mislabeled as that commit.

Both source-bound execution receipts and actual native output logs match host
results. Cleanup receipts are true; retained numbered removal and absence-check
logs are present. The runner raises on failed cleanup before setting acceptance.
Logs contain raw bounded command output, not separate per-command exit receipts;
the exact execution receipt records native exit 0 and final cleanup outcome.

ARM64 is compiled, not executed. Android13 execution is x86_64 only. No full
character/power-info transaction, actor publication, acknowledgments, real world,
GLES, APK rebuild or physical Thor acceptance is implied. No job was rerun or
cancelled and no native corpus was independently re-executed by this review.
