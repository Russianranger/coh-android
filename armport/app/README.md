
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
