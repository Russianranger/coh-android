
### Interactive dependency failure, 2026-10-24

Run 40092467628 at 58841f92 passes app-source compilation and guest boot,
but interactive job 120869513876 fails before client launch. Artifact
12560285530 (SHA256 6b2154ae35d12a6d1f29e26507e2a38f064c1c58d00c5725146af4041ba40ff4)
records `No module named 'client_visual_assets'` at local_dbserver_startup;
the host's RFB closure is a consequence of guest cleanup, not a renderer fault.
The current server imports that helper for immutable input-copy budgets.
Stage the helper, and in the ARM64 adapter treat this helper-only legacy
inventory as no optional visual payload. Any archive/manifest/animation
helper still invokes the original complete-bundle checks. No data validation
is disabled. `python3 -m unittest discover -s armport/tests -p
 'test_client*.py' -v` passes 19 tests, including helper-only and incomplete
payload cases. Execution of this correction is pending; M4 remains incomplete.

Run 40094077884 at 723bbc32 passes app compilation and guest boot; the guest
advances through immutable server-data staging, then fails importing
native_monorail_contract. Verified artifact 12560278798 SHA256
2e235dac44752ac51bd097858bd8335e77e9e43ba7f3cf92c910a4fd6d6b669a
records that failure. Include the cache ancestry helper and its startup
contract dependency. Unsupported producers remain rejected by the existing
validator and may take its existing optional-cache/original-loader fallback;
no native provenance check is removed. The app test command above now passes
20 tests, including that rejection path. The correction still needs execution.

### Actual client startup fault, 2026-10-24

Run 40095316035 at 589a015b passes source compilation and guest boot, then
starts the ARM64 client after the local Atlas server becomes ready. Interactive
job 120878044811 fails on a read of NULL at 0x140204184; the RFB-close message
is again a consequence, not the root cause. The exact executable identity is recorded in its report. Downloaded Release artifact
12544637038 from client run 40054327137 matches API SHA256
1d73144e96e83112ea8c317bc4ddaf13f0ec11dd1fe0eed4eb7805a0773c1a08.
`llvm-symbolizer --obj=CityOfHeroes.exe 0x140204184` identifies
texResetTrickBasedParametersComposite, Game/src/render/tex.c:1081:61;
`llvm-objdump` shows the NULL dereference of the generic texture's name.
The executable's full SHA256 is
0392424f466ceb6cbcb31d6c40252eace3570319db071369711ef35b74a6a00f.

The retained stdio tail contains widespread texture-open errors and missing
white/grey defaults, although the reviewed reference manifest contains them.
The adapter stages files with os.link inside the app's --link2symlink PRoot,
then renames the temporary tree. That is not the native-hardlink path used by
M3's host. The current correction makes private ordinary copies, requires
regular output files, and prevents client writes from changing server inputs.
This is a staging hypothesis to verify under the same runtime; no texture
NULL check or renderer fallback masks the fault.

Base save_evidence was also inspecting the retained x86 server worktree's
cache/logs, yielding `Linked private cache entry refused`. During that bounded
capture the adapter now selects the ARM64 tree and restores the server root
in finally. All original evidence bounds remain. The authenticated failure
artifact is 12561646531, SHA256
dcdfe341528f83182530ca04ae3dc64c4b27ce4cf0b42842a4192cd1a887125b.
The inspected final PNG is black; renderer_initialized is true, but
all_data_loaded and client_main_loop_reached are false.

`python3 -m unittest discover -s armport/tests -p 'test_client*.py' -v`
passes 22 tests, including immutable-source independence without link(),
ordinary output files, and restoring the server root after capture failure.
The correction needs CI execution. M4 remains incomplete; no APK or signing.
