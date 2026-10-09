# Client native diagnostic UI profile — 2026-09-30

Decision: use the source-supported `-nogui 1` argument for the embedded client startup diagnostic, with a verified parent console and inherited output pipes. Despite the argument's name, the audited client still creates its OpenGL game window, loads and validates game data, and enters its ordinary main loop. This is an intentional change to native diagnostic dialogs and the initial Win32 splash. It is not a claim of identical desktop GUI policy, a successful startup, or gameplay qualification.

The implementation must retain the full 900-second startup bound, 30-second live observation, renderer/data/main-loop markers, exact owned-process window checks, external RFB/Android surface evidence, and cleanup requirements. Actual hosted qualification remains required; source analysis does not establish the speedup or a pass.

## Fixed inputs

- Game source: `0b75ade0c801735e10c5798f641948a45cc50488`; reviewed data: `d51533ec8e6a9cf726b9214968077a05fdcf19f3`.
- Unmodified reference run `36088012664` `CityOfHeroes.exe`: SHA-256 `81885ffa8838ef8759c3526fa1cc0bd44f9108e92698b29054256dd0eb97a0ca`. No PE-header change, injected game code, or rebuilt game executable.
- Reused cache donor run `36707839624`: 100 Parse6 caches, 364,703,716 uncompressed bytes. `client-caches.zip`: 27,071,659 bytes, SHA-256 `5d7f5b5c1932cf755f4063092ba56a30b16d1a705c6716a98b71f9738d61c051`. All 92,046 dependency dates equal `1767225600`.
- Exact accepted prerequisite manifest SHA-256: `32c27465763cd08b9a210a75f0661634143f39fbe02d4bdaec43c819715a3c1f`; the same three attribute files remain installed. See `client-cache-manifest-36707839624.json` and `client-cache-generation-36707839624.json`.
- Normal startup does not enable `createbins`, `quickload`, production mode, or any data-validation bypass. The accepted cache-generation profile already used `-nogui`; this decision changes normal client launch only.

## Why the output path matters

Run `36711916066` used source `36a9a4e1942ff09f91ee54224b6e1de0b6c07475` and APK SHA-256 `30caaf872ad085abd7ffc197351ce3d5a0f45a2cfee873ab5586e173447dcd4d`. It consumed the prepared caches and continued loading until the 900-second startup deadline. NPC loading/texture validation took about 272 seconds; costume loading/texture validation about 242 seconds. It reached mission-maker generation and then `Preloading player_library/`. The 12 small player-created-definition cache reparses took roughly 1.5 seconds and do not explain those long stages. See `client-startup-hosted-36711916066.json`.

`Game/src/render/tex.c:1775–1850` performs missing-texture lookups in in-memory hash tables. `Common/gameComm/NPC.c:151–200` and `Common/gameData/costume_data.c:966–1029` report missing textures through `ErrorFilenamef`. `libs/UtilitiesLib/src/utils/error.c:249–297,620–623` prints the affected filename; `Game/src/clientError.c:37–44` prints the diagnostic. `libs/UtilitiesLib/src/utils/utils.c:449–468` redirects newly allocated consoles to `CONOUT$` and makes stdout/stderr unbuffered. The proposed change preserves these validations and error text while avoiding repeated console-screen-buffer operations and capture duplication.

The final owned-process snapshot supplies supporting, not causal, evidence of substantial Wine/console work. These are summed Linux task `utime+stime` ticks at the sample, not measured stage timings:

| Process | Linux PID | Tasks | User ticks | System ticks |
| --- | ---: | ---: | ---: | ---: |
| wineserver | 6136 | 1 | 923 | 16,009 |
| CityOfHeroes | 6253 | 14 | 3,868 | 9,713 |
| conhost | 6256 | 1 | 1,428 | 5,383 |
| client-launcher | 6244 | 1 | 63 | 225 |

Evidence members: `client-evidence/owned-processes.json`, 212,752 bytes, SHA-256 `ba1d994c23e323b0f104abdc9510c0d36fdfb5da0126ce9222041901fc515bdb`; `client-evidence/client-console.log`, 5,793,250 bytes, SHA-256 `50e8c7086646d433a9a2fe41a6349a8077b038dc57b60bfbfce808f79bd1f13b`. Both are in the guest support archive for that run.

## Pinned Wine behavior

`android/runtime-lock.json` pins Wine commit `b073859675060c9211fcbccfd90e4e87520dc2c2`. The hashes below cover the unmodified upstream UTF-8 source bytes retrieved from that commit.

| Wine path | SHA-256 | Relevant behavior |
| --- | --- | --- |
| `dlls/kernelbase/process.c` | `703568c2809695b1942b36c621e6df3923c0943f7c3d79456c9d661edf71f450` | Lines 195–202 select allocation or parent-console state; 206–211 preserve explicit standard handles. |
| `dlls/ntdll/unix/env.c` | `fb335752f8095704fb10a53906baee2a360d4de1e36e150a2826208458089f7d` | Lines 2190–2191 send the console handle only for the console PE subsystem. GUI executables receive no inherited console. |
| `dlls/kernelbase/console.c` | `e84018b3e30c42aa5832e374e830ac4d126c4a23e0cf0368c364e4a83825b591` | Lines 2378–2385 allocate a requested console only for the console PE subsystem. Lines 360–385 implement explicit attachment and preserve `STARTF_USESTDHANDLES`. |

Source URLs are the corresponding paths under `https://github.com/wine-mirror/wine/blob/b073859675060c9211fcbccfd90e4e87520dc2c2/`.

Consequently, `CREATE_NEW_CONSOLE` alone cannot preattach this GUI executable, and keeping a real parent console with creation flags zero is also insufficient. No such flag-only change should be presented as a fix. The supported client route is `Game/src/game.c:1486–1513`: `-nogui` explicitly calls `AttachConsole(ATTACH_PARENT_PROCESS)` before `newConsoleWindow()`. With a live verified parent console, the latter's `AllocConsole()` fails because the client is already attached, so its `freopen(CONOUT$)` branch does not run. Inherited output pipes stay in use. The helper must keep the parent console alive, verify the exact child PID joined it, and retain its existing process deadline and cleanup ownership.

## Complete audited effect list

Paths below are relative to the pinned game source at `upstream/ouroboros`. Repository-wide searches for `nogui`, `gui_disabled`, `isGuiDisabled`, and `setGuiDisable` found no additional game-data or game-UI switch.

| Source | Effect of this profile |
| --- | --- |
| `Game/src/game.c:1498–1513`; `Game/src/cmdparse/cmdgame.c:1575` | Attach parent console, set `gui_disabled=true` and `g_win_ignore_popups=1`; command-table argument targets temporary storage, not a renderer/game-UI disable field. |
| `Game/src/win/win_init.c:956–1004` | Still creates the actual 800×600 game window. Suppresses only the separate initial Win32 splash via `g_show_splash=0`. |
| `Game/src/game.c:1629–1640` | Uses `ASSERTMODE_STDERR | ASSERTMODE_EXIT` instead of interactive developer assertion UI. Data checks remain active; assertion handling changes. |
| `Game/src/win/win_init.c:1593–1687` | Native error/alert wrappers print instead of displaying popups. Native OK/Cancel and Yes/No wrappers print and return false; `winMsgError` prints and returns. |
| `libs/UtilitiesLib/src/utils/winutil.c:414–496` | Direct `errorDialog`/`msgAlert` calls print, flush, and abort; generated colored-letter icon creation returns null. |
| `libs/UtilitiesLib/src/utils/genericDialog.c:122–310` | OK-to-all/Cancel returns Cancel; OK-to-all and OK/Cancel return OK; text input returns null; native progress-dialog creation returns false. These are explicit native-dialog policy differences, not game-data validation results. |
| `libs/UtilitiesLib/src/utils/utils.c:449–714` | Disables later console creation, raising, title/color updates, console snapshot/dimension/resize operations; console Yes/No returns false. Diagnostic text itself remains emitted. |
| `libs/UtilitiesLib/src/utils/sysutil.c:268–274` | Console-window lookup returns null. |
| `libs/UtilitiesLib/src/utils/file.c:1096–1109` | Skips textual percentage display and returns the continue-processing value; does not skip file work. |
| `Game/src/render/renderUtil.c:389–390,1372–1390` | Driver diagnostics do not re-enable popup UI. Graphics capability checks still execute; unsupported required graphics capabilities still take the quit path. |

`Game/src/main.c:286–338` still runs `game_initWindow`, `game_loadData`, `game_beforeLoop`, and `game_mainLoop`; only `create_bins` takes the cache-generation early return. NPC validation (`Common/gameComm/NPC.c:151–200,300`) and costume validation (`Common/gameData/costume_data.c:966–1029,1080`) have no `nogui`/`gui_disabled` branch. Their existing production/quickload/create-bins exceptions are not enabled by this normal startup profile. OpenGL drawing, login/world UI, and the complete hosted acceptance gate must be demonstrated by the next actual run; native desktop dialogs and gameplay remain outside this qualification.
