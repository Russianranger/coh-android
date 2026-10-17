# Full backup of a fresh original graphical fixture

`capture_graphical_fixture.py` is an isolated host extension for the missing
complete-database input. It reuses the retained signed .10 APK and its actual
original Win32 client/DbServer/MapServer. It creates **one new disposable
COHLOCAL/THORHERO fixture**, through the ordinary graphical creation and logout
path. It accepts no existing database, account, character ID or SQL seed input.
It does not repeat an APK/client/server build or claim Android execution,
source-generation admission, actor publication or world authority.

This new capture is justified by the audit in
`evidence/live-groups-capture-20261017/existing-character-input-audit.json`:
retained successful creation/reopening receipts and the original hosted artifact
contain only selected SQL projections, not a restorable complete database.
The old creation milestone remains accepted. This run produces a different,
missing full-database witness for the actual source/native GROUPS transaction.

## Exact inputs and runner

Use a new `ubuntu-24.04-arm` GitHub-hosted runner in
`Russianranger/coh-android`, with a non-root account. Do not launch until the
new driver and its workflow have been reviewed. The driver requires committed,
byte-identical orchestration helpers at `GITHUB_SHA` and a separate clean donor
worktree at `204615c6c4a809d6b814c7174b81448cffea3f7a`.

| Input | Exact identity |
| --- | --- |
| Retained APK artifact | run36920583713, artifact11192425448, 553313601 bytes; ZIP SHA256 `82a769943a7237465c26d42e419fa54e39ec6ab6010376f566a752a1c47f6a90` |
| APK member | `COH-Character-Reopen-0.10.0.apk`, 590725465 bytes, SHA256 `ee9c09a3bda8a7f68af1e481e8c85e96c14ee0ea6ab414dbcda2ca730dd73688` |
| Build receipt member | `interactive-apk-build-report.json`, 38185 bytes, SHA256 `587088a83e4d70e8dab88f8362367bc532b94e86412bf372750ac060728a689f` |
| Host-only OCR overlay | `tools/android/interactive/character_host_smoke.py`, SHA256 `c9216504faf04bb4989f6affee11020a17d421cc8cda05490bb672500d6b7e6d` |
| Original game ZIP | release asset588984151, 615541018 bytes, SHA256 `28b4aa8f0b3a71287e9a596df23097722bd71db9ddb9a5a906b5af9d6152cc07` |
| Base rootfs | 353710639 bytes, SHA256 `08c639c26506dc6fbd15464bec475337087bb23cb7c0c5ace2db5240ee36424f` |
| Wine/FEX runtime | 318095727 bytes, SHA256 `030f38066af7b786c142e199cb84adec037840b0f029338849e43f99203a93e1` |

The existing retained-APK workflow demonstrates the download routes and
dependencies in `.github/workflows/android-character-reopen-qualified-apk.yml`.
Its original game ZIP is in a draft release: fetching that already reviewed
asset needs the workflow's scoped `contents:write`; reading Actions artifacts
needs `actions:read`. Neither permission authorizes publishing new binaries.
The .10 and runtime source artifacts were not expired when their current GitHub
metadata was inspected. Availability must be checked again by the workflow.

The first attempt recovered its launcher build inputs from
run36364550345, artifacts `coh-diagnostic-runtime-inputs` (10947225941,
13337866 bytes, ZIP SHA256
`9853b93aa146b125d129f4491f02ff1ad6f0e5752492a3214e619775a179e107`)
and `coh-proot-android-source-and-build` (10946592550, 1162455 bytes, ZIP
SHA256 `ff12b5d7fca65434a5bb6d76e35dafd5f956e10d492086810cb3ca449db7baeb`).
The changed retry must reuse the now-retained Linux ARM64 launcher artifact
12116450116 from39071130820: ZIP1177704 bytes, SHA256
`bf4063b2d15a4cb92127df5b0cf0eabd894a0ecc855ceaa4c0acda3acb772808`,
root `proot-build-receipt.json` SHA256
`6b853fd6732aa57ce4d8d096152f7818f47afdc91b6926fb6492b1ab2da987b5`.
Do not rebuild this unchanged host tool. It includes the exact corresponding
source/license archive. The driver binds actual PRoot/loader ELF64 ARM64 bytes
to this receipt, source/tree, donor build recipe and three donor patches. Pass
the receipt's independently recorded SHA256 as `--proot-receipt-sha256`. The
retained Android/Bionic PRoot binary cannot replace this Linux host launcher.

Install `build-essential gawk default-jdk-headless tesseract-ocr python3-pil`.
The Java compiler is used only for the existing exact asset importer, which
imports 985644857 bytes/16721 files. No game binary is compiled. The retained
APK is verified against the exact donor Java/native/guest sources. The OCR
overlay is compiled with the donor filename in memory, so its explicit sibling
imports resolve to unchanged donor helpers. Neither checkout nor the APK is
patched. Its only source difference from the donor is the reviewed selected-name
grayscale/PSM7 OCR correction.

The driver requires **16GiB free after input acquisition and PRoot preparation**,
before asset extraction/import or any graphical process. This is conservative
headroom, not a measured peak-disk or RSS claim. Record `df` before choosing the
runner; fail before the boot if capacity is insufficient. There are already
about1.88GB of APK/game/base/Wine compressed inputs, in addition to source
worktrees, extracted rootfs/Wine, exact imports, game worktree, Wine prefix,
PostgreSQL and screenshots. The new dump is admitted at most512MiB and is copied
once into retained output. The post-write bound and polled partial-size limit
are not filesystem quotas. The local recovery host is x86_64 with about5.1GiB
free, so it cannot execute this native ARM64 flow as configured.

## Invocation and save hook

From the current committed checkout, after acquiring the inputs and creating a
clean detached donor worktree, run:

```sh
python3 native-android/engine/scenecatalog-server/capture_graphical_fixture.py \
  --donor /absolute/clean-donor-204615 \
  --ocr-overlay /absolute/current/tools/android/interactive/character_host_smoke.py \
  --apk /absolute/client/COH-Character-Reopen-0.10.0.apk \
  --build-report /absolute/client/interactive-apk-build-report.json \
  --archive /absolute/client-assets.zip \
  --proot /absolute/native/linux-arm64 \
  --proot-receipt-sha256 RECORDED_HOST_PROOT_RECEIPT_SHA256 \
  --work /absolute/fresh-graphical-work \
  --evidence /absolute/fresh-standard-evidence \
  --output /absolute/fresh-fixture-output
```

All three output directories must be absent and mutually disjoint. The original
900-second startup, 1200-second interaction and 5400-second guest overall bounds
remain. Give the complete job the existing100-minute budget. A prior accepted
creation run took roughly29minutes; this new run has not been timed. The backup
must fit inside the original live interaction interval; no guest timeout is
extended. The helper has a240-second deadline, the host allows at most300seconds
and continually refuses a dead main guest, premature finish or oversized partial.

The original `character_saved` event requires successful delivery of ordinary
`/quittologin`, the source logout timer, disconnection and a committed SQL check
on the current session/client/character. The inherited host action then collects
three fresh post-save frames. An external `interaction_factory` subclass stops
at the completed action count **before** the inherited host writes its finish
request. It launches a separate PRoot client using the exact command prefix,
filesystem binds, guest identity and environment. It does not share the running
server's PRoot tracing/SysV-IPC session: psql/pg_dump use the owned Unix socket.

`graphical_fixture_backup_guest.py` checks the original profile marker, its
actual live `postmaster.pid`, actual SQL data directory/socket/port/durability,
and exact18.6 client/server versions. It reads private role credentials without
printing them. It requires one source-created COHLOCAL account and one THORHERO
on Atlas with the observed ID; no ID value is supplied to creation or SQL writes.
An administrator's read-only repeatable-read transaction exports a snapshot,
counts every ordinary user table, and remains open while original `pg_dump`
creates the **whole database**, custom format, no table/row filters. No role or
role-password definitions are dumped. The same original `pg_restore --list`
checks versions and a TABLE DATA entry for every inventoried table. Counts and
dump use the same exported snapshot. The helper only then closes the snapshot
and commits its archive/receipt. Its tool stdout limits are post-read admission
limits, not live stdout-memory caps; no RSS limit is claimed.

Only a successful helper lets the inherited host issue finish. The original
guest must then pass its full creation/save and PostgreSQL/Wine/display/owned
process cleanup validators. The host checks its owned process group is gone,
rehashes all source/input/launcher bytes, and rehashes the complete dump after
cleanup. No successful fixture receipt is written after forced stop/kill.
Partial/failed creation never becomes a retained fixture.

## Retention and next native capture

Only successful `fresh-fixture-output` contains `fixture.pgdump`, `account.txt`,
the exact validated original guest report, external observer, backup request
and backup receipt, plus the commit-last `fixture-capture.json`. The receipt
binds all evidence bytes and full dump hash/length/version/table counts,
fresh profile/source creation, ordinary logout and owned cleanup. Actual fresh
PostgreSQL role-secret tokens are checked across copied outputs, including
chunk boundaries, and must not be exported. This output is a new disposable
source-produced test input; its receipt explicitly permits retaining this
fixture dump. **Never upload the live work directory, PG cluster, credentials,
Wine prefix or arbitrary host logs.** Existing private-user-backup supervisors
and their output prohibition remain unchanged.

An independently pinned successful fixture receipt and its exact artifact/run
are prerequisites for the next job. Run `admit_graphical_fixture.py --fixture
DIRECTORY --receipt-sha256 INDEPENDENT_PIN` to verify the fixture/evidence byte
closure. It returns the exact dump hash, fixed fixture account file and wire
slot0 candidate. The actual native DB-to-Map handoff still derives selected
character ownership; the original observed character ID is never a native
selection argument. Artifact extraction may reset modes: after admission set
the dump/account to0600 for the existing private supervisor.

The packaged runtime is PostgreSQL**18.6**, not16. A PG16 `pg_restore` cannot
consume this custom archive. Use a separately qualified x86_64 PG18+ tool/server
installation for `capture_groups_transaction.py --pg-bin`; its existing
`--pg-bin` interface already supports this, and its restore uses a fresh NEW
database with `--no-owner --no-acl`. The portable archive contains database
objects/data rather than architecture-specific `pgdata`. The native x86_64
receiver and admitted Win32 source observer need no rebuild. No source/native
supervisor modification is required to consume the exact private-mode fixture
files. Follow `PRIVATE_GROUPS_RUN.md` for remaining original runtime/.34 donor
and native-build/observer inputs. That supervisor's raw outputs still carry
`public_upload_permitted:false`; retain only its allowed sanitized summary
unless a separate reviewed fixture-output policy is implemented.

## Local qualification

`python3 native-android/engine/scenecatalog-server/test_graphical_fixture.py`
passes22 offline test methods. These cover the **actual inherited** finish-hook
order, refused save gates and backup failures, strict malformed receipt shapes,
source/launcher pin drift, downstream fixture artifact closure, private
retention/secret scanning, original-error-preserving rollback, a real owned
Linux child-group cleanup and a real JSON pipe lifecycle. The full database
tool operations are explicitly mocked in these tests. No actual PG18/Wine/
graphical creation/dump/restore/source-native capture or world admission has
been established by this local suite.

The pidfile READY parser uses the source-defined eight-character `ready   `
value, including its three trailing spaces, from PostgreSQL
[`src/include/utils/pidfile.h`](https://doxygen.postgresql.org/pidfile_8h_source.html).
The initial14-method mock used an unpadded word and missed this real-format
refusal. The added status method admits the exact upstream field and refuses
unpadded/truncated/tab/starting/stopping/standby states. This correction was
identified while the first hosted attempt was still acquiring its inputs,
before its graphical boot or any actual save/backup evidence.

The first attempt39070610494 subsequently refused `REGULAR_INPUT` in preflight,
before extracting/importing/launching the game. Its complete exact input
acquisition and small PRoot build passed. The donor's unchanged
`docs/data-manifest.json` is44,476,275 bytes (Git blob
`e65bdb51bcc4f6bff4a5294bc559bee753e41907`), exceeding the original generic8MiB
source-file cap. Only that known metadata inventory now has a64MiB admission
cap, still fully hashed and bound to the clean exact donor; source bodies keep
the8MiB cap. The16th method uses this actual unchanged donor blob and verifies
both admission and continued refusal of oversized source bodies. No graphical
boot, character save or database backup is claimed from the failed attempt.

## Retained failed run and real-file publication correction

Run39071130820 at08e6a96f2af9cb317eecd6629e99db4200df177f reached real
fresh original graphical creation and ordinary logout. The guest reported a
committed `character_saved` at22:02:06UTC, three post-save host frames were
retained and original cleanup stopped PostgreSQL/Wine and reaped ownership.
The outer result was `CHARACTER_OBSERVER_FAILED`, followed by cancellation of
the guest's completion flow. That is a failed fixture, with no admitted PGDMP.
The exact initial helper/observer subcode was not retained by that revision.

Exact archive listings show182 outer diagnostic files and13 nested report files.
They contain the8683-byte selected saved-character projection, screenshots,
redacted report/log evidence, but no full database dump or cluster. The failed
1474-byte fixture artifact contains only its2678-byte refusal receipt. The
source-produced full input cannot be recovered from those retained artifacts.
Small original receipt/report/projection/listings/events/diagnosis and all three
artifact IDs/lengths/SHA256 pins are preserved under
`evidence/graphical-fixture-retry-39071130820/`; the76MB diagnostic ZIP and1.17MB
launcher ZIP remain external pinned inputs and are not copied into Git.

Independent source review found a definite environment incompatibility even
though the lost first subcode prevents attributing it as the first runtime
failure. Exact retained PRoot source7266fb3e8516535682f5a9c8f3a7e70f6506eddb,
`src/extension/link2symlink/link2symlink.c` SHA256
e92e8878d400d0c2e27db82964e0061b7814d39f8a7b2d050cf092bf00339eb8,
unconditionally emulates `link`/`linkat` with host symlinks under the actual
`--link2symlink` option. Guest stat/lstat is faked regular, but the host's real
lstat correctly refuses the dump after the old `os.link(partial,final)` publish.
The builder's three admitted patches do not modify this extension.

The guest helper now publishes via an exclusive real-file O_EXCL/O_NOFOLLOW
bounded streamed copy. It flushes, fsyncs, closes and rehashes source and final
before the commit-last backup receipt, preserving all host no-symlink/single-link
checks. It independently attempts close/unlink rollback without hiding primary
errors; a fixed rollback-complete diagnostic becomes false if cleanup fails.
No existing target or source/profile/game input is replaced.

`capture_graphical_fixture.py` automatically runs the same pinned helper's tiny
`publication_probe` through the exact retained PRoot prefix/binds/UID/environment
before launching the diagnostic guest, PostgreSQL, servers or graphics. The probe
creates only a fixed41-byte marker in a fresh private state subdirectory. The
host checks its **real outside-PRoot** lstat, single-link file and hash, then
reaps the probe group and removes its owned files. Typed probe ownership/cleanup
facts are combined with the full invocation's cleanup guard; failed cleanup
cannot inherit the main guest's absent-group claim. This probe qualifies only
this publication mechanism, never PG/Wine/graphics or the lost prior subcode.

Helper stdout is now a private bounded4096-byte fixed-schema status file.
The owner exports only strict Boolean facts and fixed source-defined stage and
failure enums after parsing that status. Duplicate/extra/type-unsafe fields or
unknown child codes are refused. Raw stderr, arbitrary helper text, exception
strings, observer text and IDs are not added to the new diagnostic summary.
Fixed observer fields retain saved-frame count and finish-request state even
when observation fails. Input/source/cleanup failure stage is retained through
teardown. Successful fixture admission now requires the actual regular-file
preflight and complete helper status/host-file closure.

The changed host suite has22 methods, including six new publication/status
controls: native-host real-file/no-link and existing-target preservation, late
write/flush/fsync/close/hash rollback and cleanup-failure reporting, strict helper
and observer privacy, a real tiny Linux child's outside-process file admission,
symlink-result refusal, failed probe cleanup visibility, and exact helper failure
status propagation without raw child text. These host controls use no actual
retained ARM64 PRoot, PG, Wine or graphical run and admit no live source token.
The next owned hosted attempt must supply that real PRoot/runtime evidence; it
can reuse exact launcher artifact12116450116 rather than rebuild it.
