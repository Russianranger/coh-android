# Android-only cleanup receipt precision

The host proof in this directory remains the exact qualification of frozen
source `166fdb04f30ff52d2f000af478e2dc953d7cc438`. Its driver was 19,324 bytes,
SHA256 `9fce46b8476668b401c9ad8da6630d0beda1f1fbc84913c70517696cf80063c9`.

Before any Android build or execution, a separate two-hunk receipt-only driver
change makes failed execution cleanup precise. The new driver is 19,808 bytes,
SHA256 `86f7afd87039eb6c8a7a0bfc5a520e24a57ddc9ab6766c8318fa4079a7aefb7b`.
The production code, native test, fixture generation, compiler and device
commands, timeouts, path ownership and cleanup operations are unchanged.

After the existing remote removal and absence checks,
`device_path_cleanup_verified` describes that path result. Native process
cleanup is verified only when no native launch was attempted or the native
process completed. An attempted launch whose completion was not observed sets
`process_cleanup_unobserved` true and leaves `device_cleanup_verified` false,
even if path removal succeeded. No process-absence observation is inferred from
removing executable files. Successful qualification still requires both path
cleanup and observed native completion.

This change received Python syntax and static diff review only. It does not
claim an Android build, device execution, or new native host execution. The
unchanged 367-check host modes and exact host receipt remain pinned to their
original source commit; a future Android build must bind the new driver bytes
and its own actual source revision.
