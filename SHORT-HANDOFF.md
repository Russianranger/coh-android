# CoH native: original destruction and dependency lifecycle

native-android ONLY; recovered live2b37d604806caf7fbc34395d35517cc444afe604.
Three concurrent isolated sparse worktrees; B,C,A published sequentially with
expected-parent fast-forward updates. Existing qualified providers preserved.
Old loader/traversal worktree copies matched already-published files; no extra
unpublished implementation was lost. Gates1–24 preserved;25–27 OPEN.
No broad suites, accepted APK rebuilds or physical Thor test replay.

A struct_clear_provider: new cache-hit composition replaces the safe failure
clear shell with original StructClear and exact BodyPart string/struct/nonarray/
earray + TokenStore destruction chain;49 unchanged functions,11 new leaves.
Source dispatch mappings pinned. Success copies pointer-free values then clears;
production failure clears at its original call site. Source reverse row order,
string-before-row releases, numeric preservation, partial/NULL rows, all32string
masks, empty strings, array NULL and repeat clear verified. Owned arena release
adapters retire/wipe exact slots; original StructFree/StructFreeString/eaDestroy
allocator/heap/earray ABI remain UNQUALIFIED. Existing loader provider immutable.
Release/ASan/UBSan each930checks/55fixtures(8loader+47direct),165rows/710strings,
14bounded refusals;10identity/9ledger/11alias-wrap/5budget controls.
44repo inputs stable. Ownstatic110,376B+Adler16B; maxframe41,632B; conservative
own-C stack62,720B<98,304B reserve. Authentic CLIENT2,584B/28rows/CRCcf27aba3,
same supplied handle/one close, production ignoreCRC1 and SMAR_Error retained.
Commite5115c629854e4ba1d95ba692b2ee43cbc521031; CI39328431779 PASS:
https://github.com/Russianranger/coh-android/actions/runs/39328431779

B file_list_compare_provider: original Create/Search/Insert/Find/IsBinUpToDate
over two independently owned lists; source length/name/raw signed32-date equality.
Original first missing/date diagnostic sanitized to numeric kind+sorted index;
no borrowed path escapes. Case/slash/literal-prefix/duplicate spelling preserved.
Release/ASan/UBSan each2,408checks/102fixtures,39comparisons(19equal/20unequal),
81Find calls,9missing/8date diagnostics,63pre-source refusals incl34reservations;
10identity/9ledger/7alias/5budget.14repo inputs stable. Owner35,232B,
wrapper8,912B/providerframes9,880B<16KiB reserve. Nonzero fixture dates only.
Commit31826cea6cb80bb18e50bf5a8ed64fed39fa5c48; CI39327830727 PASS:
https://github.com/Russianranger/coh-android/actions/runs/39327830727

C file_list_lifecycle_provider: original Length/Destroy and exact eaSize macros,
EArray layout,eaClearExDbg/eaDestroyExDbg/eaDestroyDbg. PRIVATE_EARRAY_HEAP0.
NULL destructor really frees non-NULL nodes ascending, clears slots/count,
then frees header and nulls handle. Checked adapters invoke actual registered
host frees; unused/partial reservations cleaned. NULL/repeat destroy, appended
NULL slots, duplicates and borrowed/compressed descriptor refusals qualified.
Release/ASan/UBSan each1,385checks/55fixtures,24transactions/31refusals,
9reservation controls,67node/23header frees.16repo inputs stable.
Owner+reserved heap22,120B; wrapper9,088B/providerframes10,000B<16KiB reserve.
Commit97ec231dd0e32e00cf27968c5ecd3bc513abeb85; CI39328162912 PASS:
https://github.com/Russianranger/coh-android/actions/runs/39328162912

All hosted counters match local in every mode; artifact head/digest bindings
verified. Each qualification/{struct-clear,file-list-compare,file-list-lifecycle}
-20261019 directory has host/ci/frozen/source/build/compiler/input/profile/run/
cleanup receipts. Failed/superseded A and C attempts retained as such; B had no
failed attempt. Full builds/ELFs/inputs retained in CI artifacts, compact snapshots
in git. ASan detect_leaks0 explicit; no external allocator/stack/RSS/device closure.

No real filesystem freshness/current-Map selection or loaded-catalog attestation;
no runtime catalog/default/dictionary generation/character owner/actor/ACK/world
authority. ALLENTS41/43,dictionary-index stops, transport/input/report/resource/
socket cleanup,Combined0.1.9/signing/imports/profiles/saves remain unchanged.

Next THREE independent tasks (fetch latest/read CONTRACT first):
A. Original StructAllocRawDbg/StructFree and StructAllocStringLenDbg/StructFreeString
under pinned PRIVATE_PARSER_HEAPS0, bounded owned allocator adapters; replace arena
retirement only after source ownership proof. No engine/device heap grant.
B. Dependency-bearing original ParserReadBinaryFile supplied handle with non-NULL
FileListRead(COLLECT), then accepted Length/ForEach/Destroy; atomic body+dependency
values and single close. IsBinUpToDate may be a labeled synthetic postcondition,
never ParserIsPersistNewer source flow or authentic current filesystem freshness.
C. Original bounded EArray create/insert/growth and release with actual header
ownership; replace storage constructors only after exact helpers/allocation checks.
These retire ownership/dependency adapters toward runtime integration; authentic
current-Map loaded-input/source/build/profile/run provenance remains a separate
required blocker before catalog admission and authoritative native world entry.
