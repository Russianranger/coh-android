# COH Atlas Gameplay 0.13.37: M5 Thor test (ARM64 client)

**Status:** candidate built and signed, waiting for review. It has not been
installed or played. M5 is not complete.

## The build

| Item | Value |
|---|---|
| APK | `COH-Atlas-Gameplay-0.13.37.apk`, versionCode 52, 80,894,808 bytes |
| APK sha256 | `4660d133ef28bf7ffbbc6df5975b7c0b1e703dd68eab60d86c05687f21677ada` |
| Built by | run [40429374356](https://github.com/Russianranger/coh-android/actions/runs/40429374356), artifact `coh-atlas-gameplay-0.13.37-apk` (12701606266, kept until 2026-11-26) |
| Application ID | `io.github.russianranger.cohclientinteractive`, the same as 0.13.36 |
| Signer | retained development certificate `92955353…c282`, the same as 0.13.36 |
| Donor | the public 0.13.36 APK (`14d88da1…3b12f`) |
| ARM64 client | executable `ef9f2932…3aef` and package `e7957b33…a491`, from M3 run 40407492746 |

The ARM64 package is the one M4 run 40417983694 qualified, byte for byte.

Changes from 0.13.36. Every other member of the APK is byte-identical:
- `classes.dex` and the version in `AndroidManifest.xml`;
- `character_creation_diagnostic.py` and the runtime/client manifests;
- four added ARM64 files.

x86 is still the default client. ARM64 is selected only with
**Client for next launch → "ARM64 client (Atlas)"**.

## Install (keep everything)

1. Install the 0.13.37 APK over 0.13.36. Do not uninstall, and do not clear
   app data, THORHERO, the database, the Wine prefix or Assets 1.0.0.
2. Run **Set up / update runtime** once. This is needed for the changed guest
   files and the added ARM64 client.

## Test (about 10 minutes)

1. Do one normal x86 **Reopen saved THORHERO** to confirm the update kept
   everything. It should behave as it did in 0.13.36. Save/Logout normally.
   - THORHERO must be in Atlas Park. ARM64 supports Atlas only, so if the
     character is elsewhere, return to Atlas with x86 first.
2. Choose **Client for next launch → ARM64 client (Atlas)**. The renderer
   becomes Software and the graphics become standard; that is expected.
3. **Reopen saved THORHERO.** Note:
   - the time from the tap until the client takes input;
   - the time until the world is usable;
   - whether Atlas Park draws (statue, stairs, City Hall);
   - the FPS, if shown.
4. Move around, open the map, and try one power and a short combat.
5. Use **Save/Logout**, wait for the save result, then **Finish** and
   **export the outer diagnostic ZIP**. Send the ZIP and your notes.
6. Switch **Client for next launch** back to **x86** afterwards.

## Known limits

- **ARM64 options:** Software rendering only, Atlas only, no zone travel.
- **Colours and icons:** some surfaces may be purple or flat, and some HUD
  icons may be blocks. M3 recorded the same on the CI renderer.
- **Not yet run in CI:** the complete 0.13.37 runtime with ARM64 selected.
  M4 qualified the same ARM64 package on the 0.10 runtime, and the 0.13.36
  guest/Java sources differ from that only by the reviewed M4 changes.

## If something fails

Export the ZIP and switch back to x86. Do not recreate the character or edit
the database.

Rollback is the x86 setting. 0.13.37's x86 path differs from 0.13.36 only in
the reviewed Java option code. Android does not allow installing 0.13.36 over
0.13.37 without uninstalling, so do not try a downgrade.
