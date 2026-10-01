# City of Heroes Android handoff

**Current: Thor 0.9.0 creation, Atlas connection and ordinary save are accepted. Preserve THORHERO; Atlas scenery/collision and exact-character reopen are next.**

The user completed `coh-character-creation-20261001-162621.zip` on Android 13 / AYN
Thor and confirmed the default Male costume, visible character/UI, normal save
and return from the game. The [device review](android-evidence/character-creation-thor-20261001.json)
accepts this session without another boot. Native evidence verifies COHLOCAL,
THORHERO ID 1, current CLIENT_READY, requested `/quittologin`, the live logout
timer and committed rows (`ents=1`, `ents2=1`, `powers=7`, `costumeparts=14`).
All 17 Android PNG records and four SQL table hashes were checked; three fresh
post-save captures show the login screen. Cleanup completed with zero remaining
owned workers and zero inspection failures.

The original wrapper remains `client_incomplete`: its final window check accepts
only the login title, whereas the same PID 672 retains
`City of Heroes : City_Zones/City_01_01/City_01_01.txt  PID: 672` after entering
Atlas. The corrective Android source accepts that exact map title with the owned
PID and valid mapped window dimensions. It preserves every import/asset,
SQL/logout, fresh capture and cleanup requirement. All 188 interactive tests
passed, including the actual retained title and rejection regressions. This fix
is for the next APK; the installed 0.9.0 report and uploaded evidence are unchanged.

The scene is still an empty flat backdrop with a visible avatar and HUD.
Native position records show THORHERO falling to Y=-2000 before ordinary logout,
and the logout location is map 1 `(106.453125, -2000, -114.453125)`. This is a real
world/collision issue, separate from the reporting bug; its complete cause is
not established. Keep the existing database and character. The next candidate
must reopen this exact saved character, resolve Atlas geometry/collision and
provide safe relocation of the retained character if required. No character
deletion, recreation or SQL synthesis, and no repeat creation-only device test.

The delivered signed APK is from source `bc4d750deab00f0fdbbd084b32b563aa3abdddce`,
[run 36862027713](https://github.com/Russianranger/coh-android/actions/runs/36862027713),
386,658,292 bytes, SHA-256
`001e1dc4db87f1184814a8f75a33953504d6ee06b238490a8c26c71c4ca7f963`.
Independent [package](android-evidence/character-package-review-36862027713.json)
and [hosted](android-evidence/character-hosted-36862027713.json) reviews passed.
The Male/Clear creator renders its full body and both hands. The owned client
reached CLIENT_READY on Atlas, submitted `/quittologin`, ran the live logout
timer and committed one ents row, one ents2 row, seven power rows and fourteen
costume-part rows. Three fresh host captures follow login, connection and save;
the final view returns to login. Cleanup completed with no remaining workers.

Atlas reaches its HUD and welcome, but the scenery is black without visible
ground or buildings; the in-world avatar is a dark silhouette. Missing Atlas
geometry is consistent with this result, but sole cause is not proved. This is
creation/connection/save qualification, not rendered Atlas or playable gameplay.
The [one-session Thor instructions](ANDROID_CHARACTER_CREATION_TEST.md) are now
historical reference: their creation/save session is accepted above.

The user confirmed local login and supplied `coh-local-login-20261001-010523.zip`.
Independent review matched the 0.8.1 APK and runtime identities, verified all
14 Android PNG and four guest image records, and reviewed the empty 0/12
character-selection screen. Three post-login Android captures, 272 successful
inputs, preserved database/profile/assets/caches and clean owned cleanup are
recorded in the [acceptance receipt](android-evidence/local-login-thor-20261001.json).
The session ended at its 180-second interaction limit. No repeat is requested.

The accepted creation candidate retains package `io.github.russianranger.cohclientinteractive`,
the accepted signing key and profile `android-local-login`. It adds the accepted
Atlas MapServer package because actual character data is sent during the map
handoff. The new target is graphical creation of **THORHERO**, a first connection
to map 1, ordinary logout and read-only verification of committed character,
power and costume records. The interaction window is 1,200 seconds. No existing
character is deleted or synthesized in SQL. A preexisting THORHERO stops this
creation-only candidate while preserving its data.

Thor 0.9.0 creation/save qualification is accepted by the device review above.
Exact-character reopen, Atlas scenery/collision asset closure, gameplay controls
and performance remain pending. Initial map entry completes creation/save; it
does not establish sustained gameplay or hardware acceleration. The following
0.9.0 attempt notes preserve historical checkpoints.

The first 0.9.0 [hosted attempt](android-evidence/character-hosted-36801130531-failed.json)
failed before client launch: Wine could not enumerate directory links in the
new server data tree. The correction uses real directories and the accepted
client's individual immutable file-link pattern. It also waits for the real
client's world-ready record and binds the completed logout command delivery to
fresh logout-timer and SQL evidence; the unmodified server does not log the
individual logout packet. Keep the failed candidate's receipt and clean cleanup
result. No device test of that APK is requested.

The second 0.9.0 [hosted attempt](android-evidence/character-hosted-36802634099-failed.json),
run 36802634099 at source `ae8054d6430c194e32344f47678e134395419046`,
started Atlas, verified local login and reached the creator's Register page for
THORHERO. Host OCR timed out after 20 seconds on the actual tutorial Yes/No
prompt. No character creation, character map entry or committed save is accepted.
PostgreSQL stopped gracefully, but the host killed PRoot before a final guest
report was exported, so full cleanup is unverified. The male avatar preview was
absent, with missing geometry and texture errors: base avatar geometry/textures
are outside the accepted import. Avatar assets remain separate work before
costume rendering or gameplay claims; this candidate keeps the existing assets
and targets registration, Atlas environment loading and ordinary logout/save.
No extra import or device test is requested for this failed candidate.

The subsequent [protocol-flow attempt](android-evidence/character-hosted-36805992804-failed.json),
run 36805992804 at source `335688677eb1fe67e31089b35b3f685bebaf04f6`,
started Atlas and verified login, declined the tutorial and selected Hero.
Its final frame shows the creation confirmation with the pointer covering Yes;
host OCR reported `Rendered Yes button not found`. The guest also failed its
inherited 2 MiB server-log bound during observation and evidence collection.
No character map connection or committed save was proved. This time the guest
report was retained and confirms graceful PostgreSQL shutdown, stopped Wine,
zero remaining owned workers or inspection failures, and preserved database;
the host needed no forced quit or kill. Keep this failed result separate from
qualification of the later avatar-supplement candidate.

The next retry parks the pointer outside each dialog before OCR and waits for a
fresh settled frame. Character mode now retains complete bounded server logs in
one archive with per-file hashes and redaction metadata; final cleanup replaces
live snapshots with closed logs. Its support-evidence budget is 256 MiB with a
260 MiB ZIP guard, while login-only defaults remain unchanged. Local validation
passed 168 interactive tests, 26 client/cache tests and the full Java compile.
Hosted creation, save and avatar rendering still require a passing runtime run.

The [13-file avatar attempt](android-evidence/character-hosted-36807202335-failed.json)
at source `80e776f30de896605b6db4101baa5ab16957a29a` hit the same confirmation
OCR and log-export failures, with full graceful cleanup. All 13 supplement files
installed correctly, but screenshots show a head and fragmented white torso,
without a complete body. Source review explains why: entering the costume screen
applies a random preset. This run selected Military, whose parts were absent.
The normal **Clear** control resets to deterministic tights, smooth gloves/boots
and Martial Arts hair, without a confirmation or another random choice. The next
candidate adds that explicit test step and its seven missing asset dependencies;
partial installation or a partial preview is not a visual qualification.

That candidate contained a pinned 20-file supplement for the Male body
and the costume selected by **Clear**. A bounded source audit recovered only
the missing entries from the original project's PIGG donors;
[entry integrity and format checks](android-evidence/character-avatar-source-review-20261001.json)
passed. The 1,722,790-byte ZIP adds 2,737,564 bytes to the private client worktree,
preserving the imported archive, client prerequisites, cache identity and saved
profile. Installation rechecks all files on reuse and refuses conflicting files
or links. The 13-to-20-file upgrade also preserves the original files' inodes,
bytes, modes and timestamps. Male rendering after reset and character saving still require hosted
qualification; other bodies and costume choices remain outside this small
supplement. The next Thor instructions explicitly use **Male → Costume → Clear**.

The [confirmation retry](android-evidence/character-hosted-36809680532-failed.json)
at source `b17457ec83aa705b1c265f8d511da08b5823c382` passed all three dialog OCR
steps and delivered the final Yes. DbServer then reported THORHERO assigned to
map 1, loaded and connected. The guest stopped during world loading because the
client changed its window title to include the map path; the inherited check
accepted only the menu title. The same owned client and display were still
running. No CLIENT_READY, rendered Atlas environment or ordinary logout/save is
accepted. Full bounded server logs were retained, PostgreSQL stopped gracefully,
and zero owned workers or inspection failures remained. The next candidate
recognizes the source's two PID-bound title forms and preserves rejection of
unrelated windows, while retaining the existing renderer and startup checks.

The [owned-window retry](android-evidence/character-hosted-36846149988-failed.json)
at source `e00f04970fa438864c08c339e5f6c65515b7ecdc` kept the map-title window
observed and delivered the same creation steps. Clear rendered textured tights,
boots and head/hair, but the forearms and hands were absent. The native launcher
then returned 67 at its inherited 1,200-second deadline from launch; the guest's
1,200-second interaction window starts after client readiness, reached at
419.223 seconds. This cutoff is not evidence that the game process crashed.
The last console stage was `AutoGroup..` during map loading. No CLIENT_READY,
rendered Atlas or ordinary logout/save is accepted. Guest cleanup completed
without forced host termination, remaining owned workers or inspection failures.
The next correction gives only character mode a 2,160-second launcher bound
(900 startup + 1,200 interaction + 60 completion grace), and adds the missing
smooth glove geometry using its source-pinned donor entry.

The corrected supplement contains 21 files in a 1,842,488-byte ZIP, adding
2,980,122 bytes to the private worktree. Its only new file is
`data/player_library/male_glove.geo`, containing the two Smooth forearm/hand
models used by Clear; the matching glove texture was already included.
The source entry MD5 and decoded GEO model names were checked, and all original
20 file bytes and provenance records remain unchanged. Installation tests cover
both 13-to-21 and 20-to-21 upgrades without replacing accepted files or changing
the import, worktree identity or caches. Visual completeness and the full
creation/save milestone still require the corrected hosted run.
The combined correction passed all 173 interactive and 27 client/cache tests.
Independent review checked the exact glove model names, previous file pins and
provenance, strict launcher modes and the production deadline regression.

Source review also found an existing native MapServer option for the costly
`AutoGroup..` stage: **`-donotautogroup`**. Production servers already default to
this setting; the development server used by character mode does not. The stock
world packet sends the setting to the client before map loading, so both sides
use the same load policy. The next candidate requests this option only for its
owned Atlas launch and records the policy in its report. Normal map parsing,
tracker activation, welding, collision setup, CLIENT_READY and ordinary
logout/committed-save gates remain. No binaries or imported assets are rebuilt
for this change. The development client also sets `iAmAnArtist` under this stock
policy; do not claim identical internal group topology or physical visual and
collision acceptance before runtime review. See the
[source review](android-evidence/character-atlas-autogroup-policy-source-review-20261001.json).
The [full-budget retry](android-evidence/character-hosted-36852214162-failed.json)
at `cdff43b4` exhausted its full twenty-minute interaction window while the client
remained at `AutoGroup..`. Both forearms and hands visibly rendered after Clear,
alongside the tights, boots and hair. The owned client was still alive; its
1,641.351-second launcher lifetime was below the new 2,160-second bound.
No CLIENT_READY or requested ordinary logout/save was obtained. A later server
logout-timer expiry followed no logout input and is consistent with the normal
connection timeout, so it is not accepted save evidence. Guest cleanup completed
with no remaining owned workers, inspection failures or forced host termination.
The production-policy candidate at `19879ed5`,
[run 36855035567](android-evidence/character-hosted-36855035567-failed.json),
failed before login because the external host driver opened Settings and never
dismissed its overlay. The tiny red-X click failed visibly before Escape was
sent; fresh frames continued but never matched the restored login panel. No
credentials were entered, creator opened or Atlas client policy exercised.
Its full interaction-bound failure therefore does not establish that the Atlas
policy failed. Cleanup again completed without remaining workers, inspection
failures or forced host termination.

The signed APK is already built and
[independently verified](android-evidence/character-package-review-36855035567.json):
386,658,292 bytes, SHA-256
`1da4719cf7af825092199c73067fb5fd3423fcaa8543a37d366ad1a0557ed681`.
The next qualification uses that immutable APK. The corrected character-only
host driver omits the previously accepted optional Settings probe, preserves
ordinary login actions, and requires the current login event plus three fresh
post-event captures within 180 seconds. The login-only driver remains unchanged.
Full map-ready, ordinary logout and committed-save acceptance remain pending.
The dedicated `android-character-qualification.yml` workflow checks the exact
donor run, successful APK job and artifact digest before reusing the APK and
its build receipt. It records the current external-driver commit separately
from APK source `19879ed5`; packaged Java/native/guest source closure remains
checked, and neither the APK nor prepared caches are rebuilt. This host-only
correction passed all 181 interactive and 27 client/cache tests, including
failed/forged donor rejection and login event/fresh-frame/deadline regressions.
All 174 interactive tests passed after the policy change, including an integrated
Atlas startup regression that rejects tick zero and NotReady, and requires
advancing completed ticks around the successful current-map protocol query.

The [immutable retry](android-evidence/character-hosted-36862027663-failed.json)
at driver `bc4d750d` reached an empty character list using **OHLOCAL**: the host
lost the initial C during typing. Exact COHLOCAL identity proof correctly failed
at the new 180-second login bound. No character or Atlas client policy was tested
in that retry. Its already-verified source-19879ed5 APK remains unchanged.
The parallel normal run at the same driver did enter COHLOCAL and passed the
full flow; its reviewed APK and scope are the current result above.

The subsequent host-only typing correction separates focus and Ctrl-release
from text by fresh frames, uses longer key settles and requires the entire
rendered account field to read COHLOCAL before submitting login. Replacements
are bounded to three attempts within the existing login deadline. All 186
interactive tests passed; the 27 client/cache checks remain unchanged and passed.
Actual OCR rejects the failed OHLOCAL frame and accepts a correct COHLOCAL frame.
This correction changes no packaged APK payload. It is a future host-driver
improvement, not the tested `bc4d750d` driver: the historical passed report lacks
the newer OCR receipt fields and must remain bound to its original validator.

**Historical hosted 0.8.1 qualification — the following device instruction is superseded by the accepted report above.**

**0.8.1 passed the hosted saved-Wine-profile refresh regression and graphical local login. It is ready for one Thor login session as an in-place update.**

Qualified source `1fb4c6057fda579da1913670889922ba8e53bbdc`,
[run 36785793934](https://github.com/Russianranger/coh-android/actions/runs/36785793934),
passed all 11 guest stages. The test first created a genuinely ready Wine profile
using the exact APK and real PE32 probe, stopped it cleanly, then made only its
stored registration timestamp stale. The login run performed exactly one real
registration pass (3/1/1) in 38.481 seconds, retained the prefix inode and sentinel,
matched the new timestamp, and renewed readiness after the real PE32 probe.
The seed's retained raw timestamp bytes confirm CRLF (`0d0a`) line endings.

Root screenshot review confirms **Server Used/Total: 0/12** with twelve empty
Create Character slots. Local authentication, the sent character list and SQL
account identity agree. Client startup took 439.248 seconds, followed by 48.585
seconds of observation. All 63 login-run child records closed with zero remaining
owned workers or inspection failures; PostgreSQL stopped gracefully and retained
its database. The separate prefix seed also cleaned up successfully.

The qualified `COH-Local-Login-0.8.1.apk` is 373,849,564 bytes, SHA-256
`2f9663f43c24b071714a7ea2f63a2f8abd624a49bca4b64298f58c7e56278a20`.
It retains the installed app identity and signing certificate, increments version
code to 3, and preserves the imported assets, client caches and Wine state.
All 86 interactive and 26 client/cache automated checks passed. See the
[hosted review](android-evidence/local-login-hosted-36785793934.json),
[package review](android-evidence/local-login-package-review-36785793934.json)
and [one-session Thor instructions](ANDROID_LOCAL_LOGIN_TEST.md).
Physical Thor local login remains pending; no new Atlas, Settings, general input,
character creation, or restart/reopen device test is requested in this pass.

**Historical Thor 0.8.0 failure: Wine profile refresh was rejected before DbServer or the game launched. No repeat of 0.8.0 is requested.**

The supplied `coh-local-login-20260930-220534.zip` records a 76.956-second
operation. Imported assets and the generated client caches were successfully
reused through the wrapper-only migration. PostgreSQL initialized its persistent
profile and started successfully. Wine then exited initialization with code 0,
recording one complete registration pass (three registration processes, one
WoW64 process), but the reused-prefix validator expected no registration and
reported `Wine initialization registration evidence differs`. No client inputs
were sent. All 21 child records closed; PostgreSQL stopped gracefully, its
database remained intact, and no owned workers or inspection failures remained.
See the [device failure receipt](android-evidence/local-login-thor-review-20260930.json).

Source review explains the upgrade-specific mismatch: the Android extractor
recreates Wine files with extraction-time modification dates on a new runtime
generation. Wine compares the installed `wine.inf` modification time with the
decimal value inside the preserved prefix's `.update-timestamp`. Our marker
only compared the unchanged runtime archive identity. The device report did
not contain those timestamp values, so the timestamp mismatch is a source-based
explanation; the complete unexpected registration pass is directly recorded.
The correction reconciles this metadata before calling the existing strict
initializer, preserves the prefix, and requires the real PE32 runtime probe before
writing readiness. The hosted stale-timestamp regression seeds a real prefix
using the exact APK's Wine and PE32 probe, proves cleanup, changes only the
stored timestamp, and requires a real registration refresh before graphical
login. Prefix inode/sentinel and Wine input hashes must survive. This regression
passed in corrected run 36785793934, as recorded above.

The first corrective hosted run
[36784616495](https://github.com/Russianranger/coh-android/actions/runs/36784616495)
successfully seeded a real Wine profile and performed the required saved-profile
refresh. It then failed because the new timestamp reader accepted only LF line
endings. Pinned Wine writes this file through CRT text mode, which uses CRLF.
Corrected source `1fb4c6057fda579da1913670889922ba8e53bbdc` accepts complete decimal
timestamps ending in LF or CRLF, retains all registration/probe checks, and adds
raw timestamp-format evidence to the hosted seed receipt. Keep the
[failed hosted receipt](android-evidence/local-login-hosted-36784616495.json);
that candidate was not delivered for a device test. All 86 interactive and 26
client/cache automated tests pass; corrected hosted run 36785793934 passed.

**Historical 0.8.0 fresh-profile hosted qualification passed; the Thor result above supersedes its device-test recommendation.**

Accepted source `a80bc9c9df684779987dd6d1c146c66960db9458`, run
[36779011148](https://github.com/Russianranger/coh-android/actions/runs/36779011148),
passed all 11 guest stages and independent package review. Root visual review of
fresh post-response screenshots confirms **Server Used/Total: 0/12** and twelve
empty Create Character slots. The owned local DbServer authenticated `COHLOCAL`,
sent the character list, and matched SQL account ID `1353310574` with zero
characters. The graphical client became ready in 441.389 seconds; total hosted
execution took 671.270 seconds. Finish completed after 49.235 seconds of live
observation. All 63 child records closed, PostgreSQL stopped gracefully, the
database was retained, and no owned workers or inspection failures remained.
The same run also recovered the login screen after Settings X/Escape.

The accepted `COH-Local-Login-0.8.0.apk` is 373,845,468 bytes, SHA-256
`76723c1b2f52d351f48d3b46a15625414c3977fdb8230965d83ec939d2af88fd`.
It retains app ID `io.github.russianranger.cohclientinteractive` and the 0.7.0
signing key, increments version code to 2, and preserves imported assets, Wine
state and compatible prepared/generated caches. All 77 interactive and 26
client/cache automated checks passed. See the [hosted receipt](android-evidence/local-login-hosted-36779011148.json),
[package review](android-evidence/local-login-package-review-36779011148.json)
and [one-session Thor instructions](ANDROID_LOCAL_LOGIN_TEST.md).

The scope is hosted graphical local login and an empty character list. Android
local login, account reopening after restart, character creation and world entry
are not yet accepted. This hosted run initialized a fresh persistent profile;
retaining its database at cleanup does not prove a subsequent reopen. Raw
automation reports intentionally leave visual-validation flags false; the
separate review receipt records the screenshot assessment.

Sequential targets:
1. Confirm this APK's local login and clean Finish on Thor in one session.
2. Create and save one graphical character against the persistent profile.
3. Restart and reopen that exact saved character, proving durable persistence.
4. Enter a local map with MapServer and verify initial world interaction.
5. Refine gameplay controls, performance, audio and hardware acceleration.

The first hosted attempt below remains a failed historical result.

Candidate source `8d8ebd35396e193f426df686167c87e3d2eeee7a`, run
[36775940197](https://github.com/Russianranger/coh-android/actions/runs/36775940197),
passed signed packaging and independent package review. PostgreSQL and the pinned
loopback DbServer started, and the graphical client reached its login screen in
438.599 seconds. Root screenshot review confirmed Settings X/Escape recovery,
`COHLOCAL`, masked password entry and the single `127.0.0.1` shard. The client
then displayed **Wrong game version** and the bounded interaction timed out.
All 67 owned child records closed; PostgreSQL stopped gracefully, its profile
was retained, and no owned workers or inspection failures remained. Preserve
that failed result: see the [runtime review](android-evidence/local-login-hosted-36775940197.json)
and [package review](android-evidence/local-login-package-review-36775940197.json).

Pinned source explains the malformed development version strings: its getter
expects `Ouroboros.exe`, ignores the failed timestamp lookup in these differently
named executable layouts, then formats uninitialized date fields. The accepted
headless TestClient already requests the supported development version exception.
The correction adds `--local-login` to the native launcher, which alone appends
`-noversioncheck 1`; ordinary startup and cache generation are unchanged. The
separate DbServer wire-protocol check and exact source/executable/data pins remain
enforced. Corrected run 36779011148 passed as recorded above.

The update keeps the installed app identity/signature, imported assets, Wine
prefix and compatible prepared/generated caches. The new persistent
`android-local-login` profile starts PostgreSQL/DbServer with no MapServer. Login
acceptance requires current owned-server authentication and a sent character-list
response, matching SQL account identity and fresh captures; actual empty-character
selection requires visual review. The [one-session Thor instructions](ANDROID_LOCAL_LOGIN_TEST.md)
now identify the accepted APK receipt/hash. Do not repeat earlier
startup, menu input, Atlas, or synthetic display device tests.

**Physical Thor startup and basic menu input are accepted within their reviewed scope. The 0.7.0 device session failed its final-frame check during a graphics reload; cleanup passed.**

The supplied `coh-client-interaction-20260930-201926.zip` records 174 input
events with zero transport failures. The user confirmed touch and right-stick
pointer movement, A as left click, and text entry; retained Android captures
show `COHINPUT` in Account Name with Settings open. All 40 owned child records
closed, with zero remaining owned workers or inspection failures. Preserve
the original failed result: Finish captured an all-black guest desktop after
58.427 seconds of observation, reporting `Observed client desktop became blank`.
See the [device interaction review](android-evidence/client-interaction-thor-review-20260930.json).

The last Android capture shows loading artwork. The console continues through
shader compilation. Source review shows that the Settings red X invokes the
settings-close path, which reapplies graphics settings and can show loading
artwork while rebuilding rendering resources. This supports a graphics-reload
explanation; it does not prove eventual recovery or that B caused the blackout.
B maps to Escape; its separate visible effect remains unverified. Do not call
the complete session passed or suppress the blank-frame acceptance check.

No repeat device menu test is requested. Carry the confirmed input results
forward. The source correction now adds bounded final-frame settling within the existing
interaction deadline, retaining blank samples and checking the exact client
window/process, display and complete console evidence. Fresh nonblank output
is required before acceptance; permanent blank output, client exit, window loss
and deadline expiry still fail. At most three raw blank images are retained to
preserve the existing support archive limit. All 53 interactive automated tests
passed after this correction, including transient blank recovery, permanent
blank output, deadline, process/window loss and truncated console cases.
Hosted run 36775940197 now demonstrates the Settings-close/Escape sequence
returning to the login screen; corrected run 36779011148 also passed local-login
qualification. Install 0.8.0 over 0.7.0 and retain its imported/runtime state.

The supplied `coh-game-client-test-20260930-141120.zip` passed the exact shipped
Java cleanup and PixelCopy acceptance checks. Its pinned actual client reached
renderer, all-data completion, main loop and the exact-PID window. All three
Android screenshots show the Freedom login screen and first-launch graphics
prompt; they span 2.037 seconds after current-session readiness. The client
remained observable for 34.810 seconds, and all 38 child records closed with
zero remaining owned processes and zero inspection failures. Renderer startup
at about 5m56s explains the user's reported first visible boot; full readiness
was 10m20s after client launch and the entire first operation took 16m24s,
including private-data preparation and Wine initialization. See the
[physical client receipt](android-evidence/accepted-client-startup-thor-20260930.json).
No repeat startup, Atlas, synthetic presentation, Stop/rerun or screen-lock
acceptance test is requested.


The corrected interactive APK from source
`fdd0acc492485455ce0fc8b43eb4b406da529ba1`, run
[`36736910061`](https://github.com/Russianranger/coh-android/actions/runs/36736910061),
passed all seven guest stages and independent package/session checks. Root visual
review confirmed that Cancel dismissed the graphics prompt, `COHINPUT` appeared
in Account Name, and Settings opened. Startup took 362.627 seconds, followed by
33.543 seconds of live observation; all 27 child records closed, with zero
remaining processes or inspection failures. The APK is 370,560,140 bytes,
SHA-256 `8ada2e23cf8cf4986b4faacdff1839233ef6538cf4eb12602d2e11d1cb3d36ca`.
All 44 automated checks passed. See the
[hosted interaction receipt](android-evidence/client-interaction-hosted-36736910061.json),
[package review](android-evidence/client-interaction-package-review-36736910061.json)
and [one-session device instructions](ANDROID_CLIENT_INTERACTION_TEST.md).
The later physical review above accepts the user-confirmed basic menu inputs;
input counts alone do not establish a visible game response.

The **COH Client Interaction 0.7.0** milestone adds touch, text and basic
Thor controller menu input, then Finish and verified cleanup in one session.
It starts no server. The old 0.6.0 development signing key was not retained,
so its installed package cannot be updated while preserving private state.
The new package `io.github.russianranger.cohclientinteractive` installs beside
it and requires its own one-time runtime setup and asset import. The new
development signing identity is retained, backed up and pinned to certificate
`92955353965f118a748f1f2cadc00dfb39b3e8ade0a6cdd7d44058a3a776c282`;
future builds fail rather than silently generate another certificate.
The accepted old apps stay installed. Login, world entry, audio, hardware
acceleration, B/Escape behavior and recovery after a settings reload remain
separate unproven outcomes.


The first interactive hosted candidate, run `36732627939`, passed startup,
observation, Finish and cleanup, but failed visual input qualification: Settings
opened while the graphics prompt remained and `COHINPUT` was absent. That APK
was not delivered. Source review found that Cancel and account focus use stored
button-down coordinates, while Settings uses the current cursor position. CoH
polls the absolute pointer at the end of its input frame, so a combined pointer
warp and press can leave stored click coordinates stale. The correction sends
neutral pointer movement before a bounded settling interval and button-down;
the hosted check also waits for fresh frames before clicks and text entry.
No game binary, accepted startup gate or window-focus behavior is changed.


With basic physical menu input now accepted, the next smallest gate is graphical
loopback login to an empty character-selection screen using PostgreSQL/DbServer;
MapServer and world entry can follow later. Update the retained-signature 0.7
package so its imported generation, Wine prefix and prepared caches survive.
Start the server pair once for that client session and initialize a persistent
server profile once. The accepted Atlas diagnostic dropped its database and
deleted its run tree during cleanup; it preserved import data and evidence, not
a resumable `TEST50056` character. Reuse the accepted implementation and receipts,
not a nonexistent live database or another app's private files. Verify the actual
client protocol and local `-db` authentication path in a hosted session before
requesting this later device gate.


**Historical hosted qualification for the accepted 0.6.0 build follows.**

Exact APK source `5e4e8f2f0acc78e397a3ee8c1eb7df6f661953cb`, run
[`36719533060`](https://github.com/Russianranger/coh-android/actions/runs/36719533060),
passed all six guest stages. Startup reached the renderer, all-data completion,
main loop and exact-PID 800×600 window in 362.742 seconds, then remained live
for 33.433 seconds. Three fresh external frames span 2.566 seconds after
readiness, and final cleanup left zero owned processes or inspection failures.
Root visual review sees the Freedom login screen with its first-launch
Quality/Ultra graphics prompt. Interaction remains untested; leave that prompt
untouched for the physical run. The full 39,463,670-byte console is retained.
The exact APK is 370,539,567 bytes, SHA-256
`ca506e5c22369de04d80cb98b6a747bd818ef20c81245806b6d7271357f3377d`.
See the [hosted qualification receipt](android-evidence/client-startup-hosted-36719533060.json)
and [one-run device instructions](ANDROID_CLIENT_DEVICE_TEST.md). Hosted evidence
does not establish Android execution, PixelCopy, input, world entry, hardware
acceleration or playable performance for this actual-client build.

**Physical Thor presentation 0.5.0 passed and remains accepted.**
The supplied `coh-client-test-20260930-094646.zip` verifies all 120 current-session
PixelCopy frames over 62.758 seconds. The full operation took 128.592 seconds;
all five guest stages and six child records passed, and cleanup left zero
owned processes or inspection failures. Exact shipped Java acceptance and
runtime identities were independently replayed. See the [physical presentation
receipt](android-evidence/accepted-presentation-thor-20260930.json).

The separate **COH Game Client Test 0.6.0** packages the pinned actual
`CityOfHeroes.exe` and matching DLLs. Reuse the reviewed asset ZIP for one
private import, then attempt visible game loading/login without a server boot.
The one-run instructions are in [the client device test](ANDROID_CLIENT_DEVICE_TEST.md).
Earlier hosted attempts below are historical; their proposed next actions are
superseded by the exact-APK qualification above.

The initial actual-client hosted attempt [36700734062](https://github.com/Russianranger/coh-android/actions/runs/36700734062)
displayed the Freedom loading artwork but timed out before `game_mainLoop`;
cleanup was complete. Do not deliver that APK as qualified. Its later console
output was redirected away from the inherited pipe. See the
[first failed startup receipt](android-evidence/client-startup-hosted-36700734062.json).
The next diagnostic [36704251918](https://github.com/Russianranger/coh-android/actions/runs/36704251918)
confirmed owned-console capture and a correctly fitted 800×600 loading screen.
Renderer, texture headers, fonts, group libraries and LOD data completed; the
300-second diagnostic deadline expired during sequencer text parsing. Nine
private caches were generated and cleanup was complete. This establishes cold
data processing, not a rendering deadlock or complete startup. The next work
is to prepare compatible client caches off-device and qualify a normal startup.
See the [second failed startup receipt](android-evidence/client-startup-hosted-36704251918.json).
Native x86 cache generation then finished in 221 seconds with the game completion
marker, but correctly failed its output checks because three badge/pophelp
attributes were absent. The next candidate includes those exact accepted lookup
files for both cache generation and normal startup. See the
[cache generation receipt](android-evidence/client-cache-generation-36706745544.json).
The corrected candidate `a40250b0032bd05a333514920722ddffa4427730` produced
100 verified caches and a verified 0.6.0 APK in run `36707839624`. Its short
300-second hosted diagnostic consumed those caches without rebuilding them and
continued through powers, NPCs and items to FX loading when the diagnostic
deadline expired. Cleanup was complete. The next qualification uses this exact
APK and its existing normal 900-second startup budget, with all readiness,
observation and cleanup checks unchanged; do not rebuild or repeat phone tests.
See the [cached diagnostic receipt](android-evidence/client-startup-hosted-36707839624.json).
The full-budget run `36710174172` advanced through FX, villains, cape FX and
body parts, then hit the diagnostic 1 MiB console limit during NPC costume
missing-texture warnings. It did not exhaust the startup deadline, and cleanup
was complete. The next wrapper increases bounded observation capacity, preserves
all failure/readiness checks, and reuses the exact verified caches. See the
[observation-budget receipt](android-evidence/client-startup-hosted-36710174172.json).
Run `36711916066` then retained the complete 5.79 MB console capture but reached
the 900-second startup limit just after mission-maker data, at the start of
player geometry preload. NPC and costume checks consumed about 514 seconds;
the main loop was not reached and cleanup was complete. See the
[full-budget receipt](android-evidence/client-startup-hosted-36711916066.json).
The next wrapper reduces repeated parsing of the same diagnostic log and uses
the client's native-diagnostic-UI mode to preserve direct pipe logging. This
changes native prompts and the small initial splash, while retaining actual
game window creation, graphics, data loading and texture validation. It needs
fresh hosted qualification; no phone rerun is requested for failed candidates.
See the [console profile review](android-evidence/client-console-profile-20260930.md).
The profile worked in `36716064689`: the child attached to the real parent
console and preserved direct logging. The full warning stream exceeded the
10 MiB guest limit during NPC validation, about 321 seconds into startup;
the deadline was not reached and cleanup was complete. NPC warnings alone
are estimated to exceed 20 MiB. The hosted Raw-only RFB viewer also disconnected
on a desktop-size change; Android's existing viewer already handles that event.
The next candidate retains up to 128 MiB of complete raw output, streams the
bounded support archive into the Android export, and fixes the hosted viewer's
resize and post-readiness frame checks. It keeps the same startup deadline,
full data validation, and exact game/cache inputs. See the
[direct-output receipt](android-evidence/client-startup-hosted-36716064689.json).
Physical synthetic presentation is closed; do not request another pattern,
Atlas, Stop/rerun or screen-lock test. Actual client, menu, input, hardware
acceleration and gameplay claims remain separate.

**COH Atlas Test 0.4.4 also passed on the physical AYN Thor.**
The supplied `coh-atlas-test-20260930-003609.zip` verifies all 18 stages in
55 minutes 52.7 seconds: both protocol saves committed, `TEST50056` resumed in
the same cluster with 12,345 influence and login count 1 → 2, and all 102 child
captures closed. Restart and final owned cleanup had zero inspection failures
and zero remaining processes. The device exercised the EACCES exit recovery;
the separate ESRCH path was not exercised. The exact original report also passes
the Java acceptance/cleanup checks and Python capture/startup checks.
See the [physical acceptance receipt](android-evidence/accepted-atlas-test-thor-20260930.json).

The user explicitly asked to advance without manual Stop/rerun or another long
server boot. Manual Stop/rerun and screen-lock checks remain **skipped at user
request, unvalidated** for 0.4.4; they are not prerequisites for the next APK.
The 177 ms activity visibility gap does not prove sustained background operation.
Do not request another full Atlas test to close those checks.

Keep the accepted Atlas app and its private runtime installed. The separate
**COH Client Test 0.5.0** implements the next [presentation gate](NEXT_ANDROID_PRESENTATION_GATE.md):
a session-bound animated Wine/OpenGL fixture, app-private Unix RFB, an Android
SurfaceView, and actual PixelCopy frame verification. It starts no game server
or SQL service and imports no game data. The exact signed APK passed hosted qualification in
[run 36654262400](https://github.com/Russianranger/coh-android/actions/runs/36654262400):
the external private RFB viewer observed all 120 frames in 109.26 seconds, and
all six children and the socket cleaned up. The APK itself is from build
`36653423058`, source `6fdeef4494dd41f6137ee51d80ec4e39cf687b01`; only the
host viewer changed for qualification. See the [receipt](android-evidence/accepted-presentation-hosted-36654262400.json).

That physical [display test and export](ANDROID_PRESENTATION_DEVICE_TEST.md) has now passed,
as recorded above. Its installation instructions are retained as historical evidence.
A visible fixture does not establish actual CoH menus, world rendering, controls
or gameplay. Preserve the separate APK and do not repeat the accepted server test.

The 0.4.4 exact signed APK remains hosted-qualified in
[run 36638344040](https://github.com/Russianranger/coh-android/actions/runs/36638344040)
at `e30c0b58b0e53534f92e77cdb7b8b93fe3ddc5ce`.
See the [hosted receipt](android-evidence/accepted-atlas-test-hosted-36638344040.json).

The earlier checkpoints below preserve their original successes and failures.
Their installation and retry directions are superseded by the physical pass and next-step direction above.

**Qualified MapServer diagnostic donor: run 36630872719.**
Run `36630872719` passed all six real Windows producer contracts and all eighteen
ARM64 game stages in 31 minutes 23.5 seconds. Independent review verified both
committed saves, exact-name resume, 122 closed children and zero ownership
inspection failures at restart and final cleanup. Raw records show 8,226 completed
ticks on the first launch and 2,425 on restart, with distinct file identities.
Only the separately identified MapServer changed; accepted supporting binaries
and their original source identities remain exact.

The successful run also captured a 114.233-second interval inside the first
`FolderCacheDoCallbacks` call, with one tick started and none completed. Existing
freshness checks rejected protocol-ready samples aged 23 and 85 seconds. This
does not prove the cause of earlier uninstrumented failures or repair the folder
work. The qualified 0.4.4 profile additionally requires a freshly validated
completed tick and the two-phase startup guard described above, preserving
startup deadlines, 20-second freshness and 30-second observation.

0.4.4 carries these diagnostics from donor commit
`003b07bcd98cb100c1505c15670c07d11a240c8f`, separately from its Android
wrapper and guest-adapter commit. Only the instrumented MapServer is replaced;
accepted supporting binaries and their original source identities remain exact.
See the [hosted diagnostic qualification](android-evidence/accepted-mapserver-progress-hosted-36630872719.json).

**0.4.3 remains unqualified after two hosted Atlas heartbeat failures.**
All 113 candidate checks and exact APK verification passed. Both runtime attempts
of the same signed APK in run `36621227369` passed nine stages, then failed
`Atlas lost current readiness during observation`, before character creation or
restart. DbServer kept dispatching and both services were alive at capture.
Both final cleanups completed with zero ownership inspection failures and zero
remaining owned processes. Neither attempt exercised the targeted restart race.

Identical 0.4.3 retries are stopped. The separately receipted MapServer diagnostic
above now exposes fresh late-startup and main-loop stages while preserving all
readiness, listener and cleanup checks. Buffered stdout and saved thread contexts
from these failures do not prove the blocked operation. Do not install 0.4.3 as
a qualified candidate. The 0.4.4 hosted pass does not establish the root cause or
repair of either earlier uninstrumented failure.
See the [attempt 1 review](android-evidence/atlas-test-review-36621227369-attempt1-failed.json),
[attempt 2 review](android-evidence/atlas-test-review-36621227369-attempt2-failed.json),
and [observer design](android-evidence/atlas-test-heartbeat-observer-plan-20260929.md).

**Thor 0.4.2 follow-up (2026-09-29, 18:57 UTC): cleanup is blocked again.**
The first 13 stages passed, including Atlas live-heartbeat observation and the
committed save of `TEST24402` with 12,345 influence. `game_restart` failed with
`Cannot verify Wine descendant ownership` after Wine stop/wait both returned 0.
Final cleanup subsequently found zero remaining owned processes and closed all
84 child records, but one earlier inspection failure remained latched. The app
correctly refused reuse. This run did not reach PostgreSQL restart, the new
restart startup budget or exact-name resume. No Stop or cancellation was recorded.

The report has zero permission-read retries and no permission observations. Its
message comes from the generic OS/parse-error path and omits the underlying
exception, errno and process identity. A reproduced proc-file exit race is a
candidate mechanism, not a proved explanation of this particular device run.
The narrow correction introduced in 0.4.3 and retained in 0.4.4 handles
ESRCH from status/stat as task disappearance.
Environment/namespace ESRCH requires a fresh exact-identity check and preserves
inspection of live workers behind a stopped leader. Live unreadable ownership
still fails; retries and diagnostic records are bounded. The original operation,
exception type, errno and process/thread IDs are retained without raw contents.
See the [owned-child reproduction](android-evidence/atlas-test-proc-exit-reproduction-20260929.json).
The accepted base runtime, identity/token signaling checks and Java cleanup
gates remain intact. Do not repeat 0.4.2. The current 0.4.4 procedure supersedes
that failed app's recovery and retry sequence: one full Thor test/export first,
with Stop/rerun and lifecycle checks held until report review.
See the [device failure review](android-evidence/atlas-test-thor-cleanup-failure-20260929-185717.json).

**Previous hosted checkpoint: COH Atlas Test 0.4.2 passed on attempt 2.**
The exact signed APK completed import and all 18 create/save/restart/resume stages
in 32 minutes 11 seconds, with both committed saves and complete owned cleanup.
All 100 candidate checks passed. That checkpoint qualified the bounded
DbServer startup correction; the subsequent failed Thor run is preserved above.
Attempt 1's separate Atlas heartbeat failure remains preserved. The unchanged
repeat passed, but does not establish a repair or root cause for that failure.
See [run 36599606621, attempt 2](https://github.com/Russianranger/coh-android/actions/runs/36599606621/attempts/2)
and the [acceptance receipt](android-evidence/accepted-atlas-test-hosted-36599606621.json).
That 0.4.2 candidate code was `ea5c0e18d2971d8ae9ade3f6655cea7da87e30f5`.
Its installation instructions are superseded by the current 0.4.4 procedure;
the acceptance and subsequent device failure remain separate historical records.

Previous device checkpoint (2026-09-29, 16:32 UTC): **0.4.1 recovered the ownership
read race and passed 15 stages, then hit a separate DbServer startup deadline.**
The first committed save, owned service stop and PostgreSQL restart passed.
Both restart and final cleanup reported zero inspection failures and zero
remaining owned processes. Two denied worker-environment reads ended in verified
disappearance; the app was not cleanup-blocked. The report records a timeout,
not cancellation. Screen off/on events were recorded during the earlier startup,
but the full lifecycle/device milestone remains unaccepted.

At restart the retained 5,935-column schema was ready at 16:31:28; this started
the inherited 30-second dispatch deadline while DbServer was still initializing.
Its normal minimum 15-second launcher wait began at 16:31:50. The deadline fired
at 16:31:58.99, before that wait could finish. Pre-cleanup publication was valid
but still at SQL_KEEPALIVE_QUEUE with loop count zero. The test correctly refused
to call this ready. The 0.4.2 adapter correction uses one shared 600-second startup
budget across schema/listener readiness and positive-loop dispatch, retaining
the existing overall deadline, cancellation, health and readiness predicates.
Accepted base payloads and Java guards remain unchanged. See the
[failure receipt](android-evidence/atlas-test-thor-dispatch-failure-20260929.json).
The 0.4.2 APK built successfully and its 30 payloads and 12 Java source identities
match candidate commit `ea5c0e18d2971d8ae9ade3f6655cea7da87e30f5`. All 100 candidate
checks passed. Hosted run `36599606621` attempt 1 passed nine stages, then failed
`atlas_ready_observation`: Atlas heartbeat ages reached 29 seconds while DbServer
dispatch continued. The first DbServer startup milestones passed in 42.468 and
57.217 seconds. Final cleanup completed with zero inspection failures and no
remaining owned processes. This is a separate failure, not accepted runtime
qualification. The [failed evidence](android-evidence/atlas-test-evidence-36599606621-attempt1-failed.zip)
and [partial review](android-evidence/atlas-test-review-36599606621-attempt1-failed.json)
are preserved. Atlas publishes readiness before its final startup work, and the
stdout tail can be buffered; these observations do not establish an SG permission
verification defect. The runtime-only retry of the exact same signed APK and
unchanged guards passed as attempt 2, as recorded above. That repeat does not
establish a repair of this separate failure.

The DbServer startup correction remains part of 0.4.4. Follow the current
0.4.4 procedure above for the next physical check; the older 0.4.2 installation
sequence is superseded.

For any repeated Atlas heartbeat failure, preserve the existing 20-second
freshness requirement and 30-second observation. `dbReadyForPlayers` precedes
late initialization; registration sets the initial age timestamps. Later stats
come from `dbComm` inside `svrTick`. Unbounded directory/callback draining later
in that tick is a plausible source of delay, not an established cause. The
[exact-PDB context review](android-evidence/atlas-test-context-review-36599606621-attempt1.json)
identifies folder/path/hash words but explicitly cannot prove current execution.
The separately qualified MapServer donor now supplies bounded, fresh
main-thread stage/tick publication around late startup, `dbComm` and folder
callbacks. The completed-tick guard is integrated in 0.4.4. Callbacks and the
original heartbeat requirements remain intact; earlier root causes remain unknown.

Previous hosted checkpoint (2026-09-29, 14:49 UTC): **COH Atlas Test 0.4.1 passed hosted
qualification** in [run 36579726816](https://github.com/Russianranger/coh-android/actions/runs/36579726816)
at `6b50467a1b96133acc92a378617ff961733f288c`. All 91 candidate checks, 65 import
checks and 142 of 143 existing game checks passed (one Windows-only skip).
The exact signed APK's import and all 18 stages passed in 1,968.534 seconds.
Independent review verified 25 capture files, both committed saves, same-cluster
restart, exact-name resume and all 122 closed process records. Restart and final
cleanup each had zero inspection failures and zero remaining owned processes.
The Java gate compatibility replay also passed while retaining the original
report's hosted identity. See the
[acceptance receipt](android-evidence/accepted-atlas-test-hosted-36579726816.json).

The candidate-only scanner correction handles identity-verified worker exit
during ownership reads and bounded full-read retries; persistent live denial
still fails. It adds sanitized failure details without changing accepted base
payloads or Java acceptance guards. Hosted cleanup needed no permission retry;
the later Thor run above exercised that recovery successfully. Its new startup
failure supersedes the old 0.4.1 retry instructions. Keep the accepted
0.1.5/0.2.0/0.3.0 apps installed.
After the first pass is reviewed, complete Stop during active services and a
successful rerun with app switching and screen lock/unlock. Graphical client
work remains later. See the [device procedure](ANDROID_ATLAS_DEVICE_TEST.md).

Thor follow-up (2026-09-29, 13:50 UTC): **0.4.0 reached Atlas Park and committed
the first character save, then failed the restart ownership check.** The first
13 stages passed; `TEST-47452` (container 1) saved influence 12,345. Wine stop and
wait finished, but the process scanner reported `Cannot inspect same-UID Wine
ownership`. Final cleanup subsequently reported zero remaining owned processes
and closed all 86 child records; the cumulative inspection failure correctly
kept the Android guard blocked. The full restart/resume milestone is not accepted.
The failed PID/read is absent from this report; a worker-exit race in the scanner
is consistent with the captured zombie leaders and surviving Wine workers.
The isolated 0.4.1 correction is now hosted-qualified above, retaining strict live
ownership checks and adding bounded failure context. Do not repeat the remaining
device tests on 0.4.0. See the
[failure receipt](android-evidence/atlas-test-thor-restart-failure-20260929.json).
The user confirms following the force-stop instruction at the end, probably
after exporting the report. This was recovery after the recorded failure.

Previous hosted checkpoint (2026-09-29, 12:18 UTC): the separate
[COH Atlas Test 0.4.0 candidate](ANDROID_ATLAS_DEVICE_TEST.md) **passed hosted
qualification** in [run 36563104664](https://github.com/Russianranger/coh-android/actions/runs/36563104664)
at `4a8534b46ec024ca8f97bcbdc689f5fe23746a69`. The exact APK passed full import,
all 18 server stages, two committed saves, same-cluster restart, exact-name
resume and cleanup of all 122 captured process records. Import plus runtime
took 1,947.999 seconds. All 77 new contract tests and existing regression gates
passed (one existing Windows-only test skipped on Linux). The downloaded APK,
payloads and source identities match their receipts; the current report also
passed the scratch JVM validator compatibility check without being relabelled
as device evidence. See the
[acceptance receipt](android-evidence/accepted-atlas-test-hosted-36563104664.json).
The next gate at that checkpoint was Thor success/Stop/success with lifecycle
checks. Later failed runs superseded that sequence: follow the current candidate's
full run/export and pause for review, as directed in the current checkpoint above.
The candidate combines content import with the accepted local server/runtime
package and the automatic Atlas Park create/save/restart/resume test. It uses a new
application ID, so its private content must be imported once; accepted 0.3.0 data
cannot be read across Android app sandboxes. The unchanged accepted executable
package is reassembled from run `36510836956`; current wrapper/guest provenance
is recorded separately. The new workflow is `android-atlas-game.yml`.

Latest device checkpoint (2026-09-29, 11:11 UTC): **COH Atlas Setup 0.3.0 passed
physical import/Stop/retry on Thor (Android 13 / SDK 33)**. Both full imports
verified 173,011 files / 2,977,730,517 bytes, taking 56.610 and 61.822 seconds.
The intervening cancelled import stopped during extraction after 4,552 files
and retained the first completed generation. Retry published a new complete
generation. All three raw contracts exactly match hosted-qualified build
`2f828ca3e626245ea9fd60055745980bc3f32001`. Original report ZIPs and their hashes
are preserved in the [device acceptance receipt](android-evidence/accepted-asset-import-thor-20260929.json).
No repeat of import/Stop/retry is required. The reports do not separately record
app switching, screen locking, a reopen, process death or Stop latency; carry
explicit lifecycle/resource checks into the next combined game-service candidate.
That combined server candidate is now hosted-qualified above; its physical
create/save/restart/resume and Stop/rerun checks are next. Graphical client
execution remains later work. Keep all existing diagnostics installed.

Earlier hosted import checkpoint (2026-09-29): **COH Atlas Setup 0.3.0 passed hosted
qualification** in [run 36556279364](https://github.com/Russianranger/coh-android/actions/runs/36556279364)
at `2f828ca3e626245ea9fd60055745980bc3f32001`. All 65 checks, the signed APK
build, full 173,011-file import, cancelled re-import and abandoned-stage recovery
passed. The complete inventory matches the accepted game data. The downloaded
APK and all four payloads were independently rehashed against the reports.
See the [acceptance receipt](android-evidence/accepted-asset-import-hosted-36556279364.json)
and [candidate/device instructions](ANDROID_ASSET_IMPORT.md).
Physical Thor import/Stop/retry is now accepted above. The subsequent 0.4.0
candidate failed its first restart check; the current candidate's retry instructions
above supersede its device test sequence. The 0.3.0
app imports content only; Android Atlas game services and graphical
gameplay remain unvalidated. Accepted listener and diagnostic evidence below
remains unchanged. The candidate uses a development/ephemeral signing certificate.

Continuation recovery (2026-09-29 UTC): recovered branch head `7aea5ee` and
confirmed its completed GitHub checks. Independently replayed the preserved
Thor and hosted loopback evidence: both 28-stage physical runs, clean Stop,
and the hosted 18-stage create/save/restart/resume sequence remain accepted.
The original uploaded ZIP downloads returned HTTP 502 during this recovery;
the replay used the receipt-bound reports and captures already in this repo,
not newly downloaded archives or fresh device execution.

**Previous hosted runtime milestone accepted:** the separate [MapServer/TestClient
listener profile](ANDROID_GAME_RUNTIME.md#mapserver-and-testclient-listener-candidate)
passed all four jobs in
[run 36510836956](https://github.com/Russianranger/coh-android/actions/runs/36510836956)
at `ac4c1f7978be444a893f65f5177641191861d42f`. Windows passed 17 native Winsock
contracts; all 18 ARM64 stages and final host validation passed in 1,873.269766
seconds. Both DbServer starts proved 14 local endpoints, both Atlas starts
proved UDP `127.0.0.1:7001`, and each TestClient session proved two loopback UDP
bindings. Character `TEST33790` / container 1 retained influence 12,345 and
selected SQL rows across both committed saves, same-cluster restart and
exact-name resume with creation disabled. LoginCount progressed 1 → 1 → 2.
All 122 process captures closed, with zero remaining owned processes or
inspection failures. The
[acceptance receipt](android-evidence/accepted-game-listeners-hosted-36510836956.json)
binds the [raw report](android-evidence/game-listeners-arm64-36510836956.json)
and [preserved captures](android-evidence/game-listeners-evidence-36510836956.zip).

Verified file-picker import is implemented and accepted on Thor above. The
separate Android Atlas runtime/lifecycle integration was subsequently built and
hosted-qualified; the current candidate's physical retry is the next gate. The hosted
namespace remains mandatory;
the local binding policy does not establish device-wide network isolation.
Keep installed 0.1.5 and 0.2.0; no repeat of their passed diagnostics is needed,
and the listener milestone itself supplies no physical Atlas result.
Local verification: 162 checks ran (161 passed, one Windows-only observer
skipped), including 17 actual socket contracts and eight source-preparation
checks. Both complete creation/resume staging commands verified the immutable
5,995-file source snapshot and produced the expected separate receipts.
The three new game executables were also downloaded and independently checked
against their source receipts, byte hashes and PE metadata. Existing Wine,
DbServer console/launcher and orphaned Atlas door-point warnings match the
previous accepted run; no new failure diagnostics were found.

Previous device checkpoint (2026-09-28, 22:28 UTC): **COH Server Test 0.2.0 passed
on Thor**. The [receipt](android-evidence/accepted-dbserver-thor-20260928.json)
records two complete 28-stage real DbServer passes, a clean cancellation between
them, exact local listener coverage and complete owned cleanup. App switching
and screen locking are user-attested; peak memory is unmeasured. The subsequent
hosted Atlas loopback integration passed in `36493722153`, including both local
DbServer starts and both committed saves. MapServer/TestClient local bindings
subsequently passed hosted qualification in `36510836956`. Asset import has
since passed on Thor with 0.3.0; Android Atlas integration remains next.
Physical Atlas execution and rendering remain unvalidated.

Updated: 2026-09-29 (UTC). PostgreSQL controlled persistence, targeted stage1 inspection,
matching Windows packaging, base runtime assembly and data-only database schema
generation have passed their current checks. Normal fixture-OFF DbServer schema
initialization/export/reload and normal MapServer network save acknowledgements
have also passed against fresh PostgreSQL clusters.
The refreshed runtime and schema artifacts share repository commit
`775a0dd770adac045484805dbbb5f68054c7a354`. Ordinary asset-backed reference
comparison and Atlas Park protocol readiness have now passed. Fresh fake-auth
character creation, live currency change, protocol logout/save, database and
game-service restart, and exact-name short resume also passed in
[run 36282414135](https://github.com/Russianranger/coh-android/actions/runs/36282414135).
The follow-on [sustained-session run 36295176484](https://github.com/Russianranger/coh-android/actions/runs/36295176484)
also passed: exact-name resume, missing-name refusal without mutation, 66.953
seconds connected, restored live currency and a second protocol save.
The follow-on [Atlas transfer run 36297542986](https://github.com/Russianranger/coh-android/actions/runs/36297542986)
also passed: the same character moved map 1 → prestarted clone 101 → map 1,
preserved committed state at each arrival and completed the final protocol save.
The [primary M2 device diagnostic and headless client capability gate](THOR_DEVICE_ACCEPTANCE.md)
is now accepted on Thor with 0.1.5. The supplied combined report passed all twelve
stages, reused the database cluster and ready Wine prefix, and completed owned
cleanup with all 30 process input/output captures closed. The user also attests to
a preceding database-only pass; its separate archive was not supplied. Device
cleanup observed exited leaders with live owned workers, while the exact writer
of the earlier pipe was not inventoried. The subsequent 0.2.0 device gate now
proves Stop followed by a successful fresh rerun; app switching and screen
locking are user-attested, while peak memory remains unmeasured.
The [first hosted M3 DbServer gate](ANDROID_DBSERVER.md)
also passed in run 36369485666: 21 persistence check groups across 14 fixture
invocations, then two fixture-OFF schema exports with 99 tables, 5,935 ordered
columns, 58,272 exact attribute IDs/names and a stable catalog on reload.
All 28 ARM64 stages passed, with all 111 process input/output captures closed and
zero remaining owned processes or inspection errors. The
[acceptance receipt](android-evidence/accepted-dbserver-hosted-36369485666.json)
binds the reports and inputs. Physical Android DbServer execution has since
passed with 0.2.0; Android presentation and game rendering remain unvalidated. The separate
[hosted Atlas gate](ANDROID_GAME_RUNTIME.md#accepted-full-hosted-workflow)
passed its full workflow in run `36460005201`: all three jobs, all 18 guest
stages and the final host validator succeeded, including both protocol saves,
same-cluster restart and exact-name resume. The
[acceptance receipt](android-evidence/accepted-game-hosted-36460005201.json)
binds independently verified reports and captures. The earlier `36454174481`
workflow failure and separate post-correction acceptance remain preserved,
alongside the first-save, restart-port and startup-timeout history below.
The follow-on diagnostic DbServer package passed all three jobs in run
`36425508780`. Windows verified enabled dispatch-record publication; the ARM64
fixture/schema gate used the observer disabled. Atlas run `36428915900` then
verified enabled ARM64 publication with this qualified donor and captured the
folder callback boundary during the intermittent timeout.
The current fixed-input successor is qualified in run `36451873322` at
`53c6270dff8a0efcc6be09da756408504d8313bd`: all three jobs passed, including
default normal-schema startup and acknowledged fixed-input reload on ARM64.
This remains the default Atlas donor; preserve the earlier first-save and
dispatch evidence. The accepted device diagnostics are 0.1.5 and 0.2.0.
The separate opt-in loopback listener package passed all three hosted jobs in
[run 36460867428](https://github.com/Russianranger/coh-android/actions/runs/36460867428)
at `eed2ce1f5388195f65a07853919761a93657aca6`. Its
[acceptance receipt](android-evidence/accepted-dbserver-hosted-36460867428.json)
records 28 ARM64 stages in 191.502348 seconds, all 13 required loopback binds
(12 TCP plus UDP 7000), and the optional asynchronous TCP 6992 bind. Windows
passed all eleven native loopback contracts and the existing persistence,
dispatch and fixed-input checks. Both schema exports and the catalog were
stable; all 111 captures closed with zero owned processes or inspection errors.
The first attempt `36460005041` failed before DbServer builds or runtime execution
because its Windows test fixture applied a CRLF patch to LF source files.
The correction normalizes only that fixture's patch input and adds a CRLF
regression; preserve the
[failure receipt](android-evidence/dbserver-qualification-failure-36460005041.json).
This qualifies the hosted listener prerequisite. Physical DbServer listener
execution and app integration subsequently passed with 0.2.0. The default Atlas
donor remains `36451873322`; its separate loopback profile uses `36460867428`.
The first attempt with the preceding diagnostic donor `36425508780`, run
`36427680960`, stopped before game execution
when the pinned talloc download timed out during the PRoot build. A bounded
download retry is now applied. The next run passed dependency preparation with
no retry line observed; the transport remedy supplies no startup-fix evidence.
The reviewed asset ZIP has been uploaded to a draft release and downloaded by
the hosted runner with its exact size/hash verified. That attempt then stopped
on Windows manifest line endings before game execution. The byte-preserving
checkout fix is applied and run 36176806895 completed successfully: all 56 fresh
template outputs matched, then Atlas Park remained ready for 62.235 seconds.
Earlier character attempts exposed harness status parsing and console capture
issues; the final corrected run completed all eight phases with no failures.

Continuation on 2026-09-26 recovered the completed 2026-09-25 run after this
handoff had retained an in-progress status. At recovery, GitHub showed no queued
or running workflow and the latest commit was `04d62616e2e1b41b10f35a04d4c798e43680d5ba`
(2026-09-25 19:05:39 UTC). The workflow finished at 19:16:38 UTC. These observations
do not reveal the internal status of the other Codex session.

## Earlier hosted DbServer-loopback checkpoint (2026-09-28)

[Run 36493722153](https://github.com/Russianranger/coh-android/actions/runs/36493722153)
at `708878f78a3361b595dcc03a0c4b14fb6cd2e6c3` **passed the separately identified
Atlas loopback DbServer profile**: all three jobs, all 18 guest stages and final
host validation. The [receipt](android-evidence/accepted-game-loopback-hosted-36493722153.json)
binds independent replay of the unchanged reports and captures. Runtime took
1,883.535869 seconds; first service readiness took about 17 minutes 32 seconds
and restart readiness about 3 minutes 13 seconds.

Both DbServer starts proved all 14 observed local endpoints, including optional
TCP 6992. Character `TEST-60538` / container 1 retained influence 12,345 and its
selected committed SQL rows through same-cluster restart and exact-name resume
with creation disabled. LoginCount progressed 1 → 1 → 2 across both protocol
saves. Both fixed-input acknowledgments and all four inventory checks passed.
All 122 process input/output captures closed, with complete cleanup and zero
remaining owned processes or inspection failures. Preserve the
[raw report](android-evidence/game-loopback-arm64-36493722153.json) and
[captured evidence](android-evidence/game-loopback-evidence-36493722153.zip).

The workflow explicitly selects loopback donor `36460867428`; default assembly
and the earlier accepted profile retain `36451873322`. This qualifies DbServer
binding within that earlier Atlas sequence. The subsequent `36510836956`
profile qualified MapServer and TestClient local bindings as well. The private
hosted network namespace remains mandatory; outgoing TCP and device-wide
isolation are outside the binding proof. Physical Atlas execution remains
unvalidated. Follow
the [remaining device preparation](ANDROID_GAME_RUNTIME.md#remaining-preparation-for-a-physical-atlas-candidate),
keeping accepted 0.1.5 and 0.2.0 installed.

### Earlier accepted default-profile workflow

[Run 36460005201](https://github.com/Russianranger/coh-android/actions/runs/36460005201)
at `cfc8ac477e449037213d5242f43480acf4f1cb85` **passed all three jobs and the
complete hosted Atlas gate**. The [raw report](android-evidence/game-arm64-36460005201.json)
records all 18 stages in 1,963.43549 seconds, `TEST48625` / container 1 /
account `CohAa82e8aaa56`, live influence 12,345, first protocol save, Wine and
same-cluster PostgreSQL restart, exact-name resume at slot 0 with creation
disabled and a processed server update, and the second protocol save.
LoginCount progressed 1 → 1 → 2; selected SQL retained one `ents` row, one
`ents2` row, seven powers and 13 costume parts. Atlas readiness was independently
observed for 31.421914 seconds with current heartbeats.

Both fixed-input acknowledgments and all four unchanged input checks passed
(62 files / 4,402,846 bytes). Schema, attribute IDs/names and the full catalog
stayed stable. All 123 process input/output captures closed; graceful PostgreSQL
and Wine cleanup left zero owned processes or inspection failures. Independent
full report, character/SQL capture and service-capture checks passed with the
exact tested validator modules. Preserve the
[acceptance receipt](android-evidence/accepted-game-hosted-36460005201.json) and
[captured evidence](android-evidence/game-evidence-36460005201.zip).
Atlas donor `36451873322` at `53c6270dff8a0efcc6be09da756408504d8313bd` and
APK 0.1.5 remain unchanged. Physical Android game execution, presentation and
rendering remain unvalidated.

### Testing takeover verification (2026-09-28)

A fresh checkout at `d1907db` independently replayed the accepted `36460005201`
evidence. All 43 preserved archive members matched their recorded sizes and
hashes; the raw report was byte-exact. The exact tested validator modules passed
`validate_report`, `validate_capture_files` and `validate_service_captures`.
The [verification record](android-evidence/atlas-takeover-verification-20260928.json)
delimits the retained-evidence scope: no fresh runtime or device execution,
and no recomputation of the omitted full data inventory or executable payloads.
The current focused suites passed 103 tests with one Windows-only observer test
skipped locally; the accepted hosted Windows job covers that observer.

Live GitHub inspection confirmed the successful full Atlas run and zero queued
or running repository workflows. This does not reveal another agent's internal
session status. README and Thor next-work instructions now point to Android
integration and physical device qualification instead of repeating the accepted
hosted Atlas milestone. The 0.1.5 APK and Atlas donor are unchanged.

### Earlier acceptance after host validator correction

[Run 36454174481](https://github.com/Russianranger/coh-android/actions/runs/36454174481)
at `8944bd598990b33b63a750a64ae448403e4542cd` has an **accepted runtime sequence
after host revalidation; the original workflow conclusion remains failure**.
All 18 guest stages passed in 1,867.229988 seconds. The
[raw report](android-evidence/game-arm64-failed-36454174481.json) records
`TEST01443` / container 1 / account `CohA318dc5a821`, live influence 12,345,
first protocol save, Wine and same-cluster PostgreSQL restart, restarted Atlas
readiness, exact-name resume at slot 0 and the second protocol save. LoginCount
progressed 1 → 1 → 2; selected SQL retained one `ents` row, one `ents2` row,
eight powers and 14 costume parts. Atlas readiness was independently observed
for 31.564746 seconds.
Both DbServer fixed-input acknowledgments and all four unchanged input checks
passed (62 files / 4,402,846 bytes). All 122 input/output captures closed;
cleanup left zero owned processes or inspection failures.

The original host validator incorrectly required `child_exited: true`, which
the bridge does not serialize. The correction requires the existing exit code
to be a terminal DWORD and rejects `STILL_ACTIVE` (259). Both clients recorded
exit code 125 after forced termination following independently committed
protocol saves. Strict full report, character-capture and service-capture
validation passed against unchanged evidence. Preserve the separate
[acceptance receipt](android-evidence/accepted-game-hosted-36454174481.json),
[failure receipt](android-evidence/game-runtime-failure-36454174481.json) and
[captured evidence](android-evidence/game-evidence-36454174481.zip).
The actual C serializer, real guest stop validation and host consumer are
covered by a regression; the runtime, bridge producer and evidence bytes are
unchanged. The original Actions run remains failed. Keep donor `36451873322` at
`53c6270dff8a0efcc6be09da756408504d8313bd`
and the accepted 0.1.5 APK unchanged. Physical Android game execution,
presentation and rendering remain unvalidated.

The separate sibling DbServer [run 36454174374](https://github.com/Russianranger/coh-android/actions/runs/36454174374)
failed attempt 1 with SIGSEGV (`-11`) after `PG_TEST_COMPLETE rebuild` and
teardown messages. Attempt 2 reused the byte-identical package and passed all
28 stages in 190.362494 seconds, with all 111 captures closed and complete
cleanup. The [failure](android-evidence/dbserver-runtime-failure-36454174374.json)
and [repeat](android-evidence/dbserver-runtime-repeat-36454174374-attempt2.json)
receipts preserve both outcomes. The failure remains intermittent and
unexplained; the passing repeat does not establish a repair or replace the Atlas
donor.

### Earlier hosted ARM64 checkpoints

[Run 36416020268](https://github.com/Russianranger/coh-android/actions/runs/36416020268),
commit `324823be6ca9713bdc60446eb31596004ff6286a`, is an **overall failure with
new partial runtime evidence**. Atlas stayed independently ready for 31.519
seconds. Stock TestClient created `TEST02279` / ID 1, entered Atlas, changed live
influence to 12,345 and completed protocol logout with an independent committed
SQL snapshot (LoginCount 1) before forced cleanup. Wine and PostgreSQL shut down
cleanly; the same PostgreSQL cluster restarted. The next service-launch
preflight failed immediately with `[Errno 98] Address already in use`, before
replacement game services started. No exact-name resume or second-save proof
was obtained. Preserve the [raw report](android-evidence/game-arm64-failed-36416020268.json)
and [detailed evidence](ANDROID_GAME_RUNTIME.md#first-arm64-creation-and-protocol-save-restart-gate-failed).

The bounded fallback snapshot found no owned Wine processes or game-role SQL
sessions after the verified shutdown. Review confirmed that the TCP preflight
lacked the native `SO_REUSEADDR` behavior used by pinned Wine. An isolated Linux
experiment reproduced the bare-bind error with TIME_WAIT and passed with TCP
reuse while retaining rejection of live listeners and occupied UDP ports. The
hosted report has no socket table proving that state, but the behavior is
consistent with its failure. The narrow harness correction and tests were
applied for the subsequent run described below; restart validation was still required. The
prior startup timeout did not recur: one query returned after 78.833 seconds and
AutoCommands retrieval completed after 82.71 seconds. This does not establish
that intermittent startup delay as fixed. Do not repeat the successful first
save as if it were still unknown, or mark the full hosted gate accepted before
restart/resume/second-save pass. Keep the accepted 0.1.5 device diagnostic;
Android game presentation and gameplay remain unvalidated.

The subsequent [run 36420158506](https://github.com/Russianranger/coh-android/actions/runs/36420158506)
at `04b9771120737f3e8daf7b4740d2a9fcd6850f28` failed a startup query in the first
service phase after 13 preceding readiness queries had completed. The failing
query reached 90.041 seconds, so it did not exercise the restart-port correction.
Preserve the prior first-save evidence above. The new
[failure receipt](android-evidence/game-runtime-failure-36420158506.json),
[raw report](android-evidence/game-arm64-failed-36420158506.json) and
[pre-cleanup snapshot](android-evidence/game-hang-36420158506/snapshot.json)
show live DbServer/Atlas/query processes and 65 idle SQL sessions. All Windows
capture APIs completed (three processes, 72 threads, 114 modules, zero errors),
but inspection of pinned Wine/FEX shows `GetThreadContext` supplies saved WOW64
context rather than current translated x86 execution state. Decoded DbServer
pointers lead to an already-completed startup path, so they do not identify the
live blocker or justify a main-loop change. Final cleanup passed with all 59 process
captures closed and zero remaining owned processes or inspection failures.
This run did not validate the full hosted restart/resume/second-save gate or
Android gameplay.

[Run 36425508780](https://github.com/Russianranger/coh-android/actions/runs/36425508780)
at `41f3aff596826e22e2774375e11590de895ca33d` qualified the separately receipted
DbServer package containing [opt-in source dispatch markers](../database/wine-dbserver/DISPATCH_PROGRESS.md):
all three jobs passed, including the Windows enabled-record contract. The ARM64
fixture and normal schema checks ran with the observer disabled. Preserve the
[new acceptance receipt](android-evidence/accepted-dbserver-hosted-36425508780.json)
alongside the original acceptance. The donor manifest SHA-256 is
`656c7e764798dc7ecee01cef836cd758177fd9cdcf1477799517e9d5a959c632` and the normal
executable SHA-256 is
`3d6098da1655a380f09d7c0ba5b984c98b68b1294f75128c28b08be851cf1830`.

Atlas adopted donor `36425508780`, with separate fresh records required for
first startup and restart. Enabled publication on live ARM64 was subsequently
verified in run `36428915900` below. Bounded stage/sequence observations distinguish progress
through startup, dispatch, SQL keepalive and console handling without relying
on stale WOW64 contexts. A stopped marker identifies an operation and its nested
calls; it does not prove a deadlock or gameplay success. No startup blocker fix
has been established, and the accepted device APK remains 0.1.5.

[Run 36427680960](https://github.com/Russianranger/coh-android/actions/runs/36427680960)
at `82386fd48c2352a2ce65d5920f7857e8b92ec442` passed source, package and data
staging, then failed on a read timeout downloading pinned talloc for the PRoot
build. No game diagnostic ran, and no runtime report or dispatch sample exists.
The [infrastructure failure receipt](android-evidence/game-infrastructure-failure-36427680960.json)
preserves this result. It adds no evidence about the intermittent startup
stall. The isolated retry correction allows at most three transport attempts,
discards partial downloads and preserves the size/SHA-256 gates; Atlas tooling
now explicitly runs its regression tests. The next run passed dependency
preparation without an observed retry. This download remedy is not a game
startup fix; this attempt did not reach restart/resume/second-save.

[Run 36428915900](https://github.com/Russianranger/coh-android/actions/runs/36428915900)
at `f32ccd7c0f1aa950d1f87ceb81ab09b2dba4e2ac` failed a first-phase startup query
after 90.030 seconds, following 13 completed readiness queries. Enabled ARM64
source markers are now validated: the initial record had sequence 28 / loop 1
at `NM_MONITOR`; the same DbServer PID 412 / main thread 416 and mapped file
later held `FOLDER_CALLBACKS`, sequence 2,449,552 / loop 43,741. Identical before
and after records span 13:55:20.897–13:55:23.957 UTC. This localizes the observed
work to folder callbacks or nested calls. Separate non-atomic native snapshots
showed `read` and `fchdir` operations under PRoot, so a deadlock is not established.
The specific nested operation and throughput remain unknown.

The query, DbServer and Atlas were alive before cleanup, and the query remained
alive after the 3.061-second capture. All 65 SQL sessions were idle in
`ClientRead`, without active transactions; the foreground last query was `;`,
about 134.9 seconds old. Atlas ended at `Retrieving AutoCommands..`. Preserve the
[failure receipt](android-evidence/game-runtime-failure-36428915900.json),
[raw report](android-evidence/game-arm64-failed-36428915900.json) and
[snapshot](android-evidence/game-hang-36428915900/snapshot.json). Archive and all
eight service/hang capture hashes were independently verified. Final cleanup
passed with all 57 process input/output captures closed and zero remaining owned
processes or inspection failures. No new character or restart result was obtained.

The opt-in [fixed-input DbServer mode](../database/wine-dbserver/FIXED_INPUTS.md)
is now qualified in [run 36451873322](https://github.com/Russianranger/coh-android/actions/runs/36451873322)
at `53c6270dff8a0efcc6be09da756408504d8313bd`. It prevents watcher registration
before the first cache while preserving initial reads and lookup mode; it does
not establish a generic Wine notification fix. All 28 ARM64 stages passed in
192.280590 seconds, including 21 persistence groups across 14 fixture phases,
default normal-schema startup and acknowledged fixed-input reload. Both fresh
empty exports preserved 99 tables, 5,935 ordered columns, 58,272 exact attribute
IDs/names and the full catalog. All 111 process captures closed; cleanup left
zero owned processes or inspection errors. Preserve the
[acceptance receipt](android-evidence/accepted-dbserver-hosted-36451873322.json).
The donor manifest SHA-256 is
`e4f8a66802f29643b13aec2228ada1549a80c22efa11de1549a9b145bb43e06b`;
normal executable SHA-256 is
`659e9072234f75ad02c8cac2636df93f5249ff1de385c1ed7d6c6fc0c04a453a`.

Earlier fixed-input qualification `36434692816` passed Windows/source checks,
but both ARM64 attempts failed before DbServer execution on talloc HTTP 503
after all three transport attempts. Successful qualification `36451873322`
recovered the identical archive from accepted runtime `36364550345`'s verified
corresponding-source bundle. Atlas uses the same source recovery; the build
recipe and source pins are unchanged.

The Atlas harness now enables this mode only for DbServer and requires its exact
startup acknowledgment on both launches. After private `servers.cfg` generation,
it binds all 62 accepted schema inputs plus the entire staged `data/server/db`
tree. Four unchanged snapshots are required: before first startup, after first
save, before restart and after second save. Run `36454174481` subsequently
completed this sequence; its unchanged evidence passed strict host revalidation
after correction of the bridge exit contract. Preserve the original failed
workflow, earlier first-create/save evidence and accepted 0.1.5 APK; Android
game execution and rendering remain unvalidated.

## Continuation validation checkpoint

The accepted character run is **36282414135**, tested commit
`86e512e85c8350714bc7b58668bf11443dc164f8`, completed 2026-09-27 00:40:07 UTC.
It verified `TEST20636` / container ID 1 with live influence 12,345, committed
protocol logout before forced cleanup, restart of the same PostgreSQL cluster
and game services, and exact-name short scene resume with creation disabled.
Selected identity/rows remained unchanged (1 parent, 1 `ents2`, 7 powers,
13 costume parts); `LoginCount` progressed 1 → 1 → 2. The resume exited
naturally with code 0 and both console observers finalized successfully.
The [report](postgresql-evidence/character-persistence-36282414135.json),
[complete artifact](postgresql-evidence/character-persistence-36282414135.zip) and
[acceptance/provenance record](postgresql-evidence/accepted-character-persistence-36282414135.json)
are preserved. Windows passed 67 tooling/map checks; Linux passed 62 with five
Windows-only skips. All four same-commit
[PostgreSQL regression jobs](https://github.com/Russianranger/coh-android/actions/runs/36282414187)
passed. The short resume does not establish sustained gameplay or Android execution.

### Accepted next milestone: sustained second session

The [sustained-session implementation](SUSTAINED_SESSION_VALIDATION.md) adds a
separately identified diagnostic TestClient with creation disabled and a normal
connected command loop. [Run 36295176484](https://github.com/Russianranger/coh-android/actions/runs/36295176484)
passed all 12 phases at `4e8058c3ffe20acda61b55023202d409ed1d0df1`, completing
2026-09-27 05:08:11 UTC. `TEST-37762` / ID 1 resumed with live influence 12,345
and a processed server update confirming its identity. Ten samples covered
66.953 seconds connected on Atlas Park, with a maximum gap of 7.625 seconds.
The second live influence command produced 23,456 and committed through protocol
logout before forced cleanup. Missing-name refusal exited naturally with code 3
and left the entire character inventory and selected SQL unchanged.

`LoginCount` progressed 1 → 1 → 1 → 2 across first logout, restart, missing-name
probe and second logout. Selected identity/rows stayed identical except for the
intended influence change (1 parent, 1 `ents2`, 7 powers, 16 costume parts).
All three console observers finalized successfully. The [raw report](postgresql-evidence/character-session-36295176484.json),
[complete artifact](postgresql-evidence/character-session-36295176484.zip) and
[acceptance record](postgresql-evidence/accepted-character-session-36295176484.json)
are preserved. Windows passed 103 tooling checks; Linux passed 98 with five
Windows-only skips. The same-commit [stock regression](https://github.com/Russianranger/coh-android/actions/runs/36295176352)
and all four [PostgreSQL regression jobs](https://github.com/Russianranger/coh-android/actions/runs/36295176473)
passed. The accepted stock TestClient and server reference binaries remain
unchanged; the diagnostic client has separate source/build receipts.

The first hosted attempt
[36293644180](https://github.com/Russianranger/coh-android/actions/runs/36293644180)
passed stock creation/save/restart and missing-name refusal without mutation,
then rejected the positive selection because the character-list packet does not
populate its `db_id` field. The correction checks exact name/slot there and binds
the actual MapServer entity ID after the processed update to independent SQL.
The [failed evidence](postgresql-evidence/character-session-36293644180.json) is
preserved. The corrected retry above proves the sustained resume and second save;
the failed attempt remains identified as a failure.

### Accepted next milestone: Atlas instance transfer

The [Atlas instance transfer gate](MAP_TRANSFER_VALIDATION.md#accepted-hosted-validation-36297542986)
passed all 15 phases in run `36297542986`, tested commit
`5f2c561058a186de59d3f27301eea210bd4bb66d`; terminal success was recorded
2026-09-27 05:56:06 UTC. `TEST59440` / ID 1 stayed in the same client process
for map 1 → clone 101 → map 1. Fresh player updates carried transfer epochs 1
and 2 on ports 7002 and 7001, while independent character status confirmed
MapId/SmapId 101 then 1. Each arrival had current heartbeats, live influence
12,345 and unchanged committed selected state. Per-leg SQL reads establish that
state, not a fresh identical-write acknowledgement. The subsequent live change
to 23,456 and protocol logout supplied a fresh final-save proof before cleanup.
LoginCount stayed 2 across both transfers and final logout; no extra character
was created. All three console observers finalized successfully.

The [raw report](postgresql-evidence/character-transfer-36297542986.json),
[artifact](postgresql-evidence/character-transfer-36297542986.zip) and
[acceptance record](postgresql-evidence/accepted-character-transfer-36297542986.json)
are preserved. Windows passed all 119 tooling checks; Linux passed 114 with
five Windows-only skips. The same workflow passed the 12-phase sustained
regression using the same diagnostic bytes (62.532 seconds over 10 samples).
The stock-client and all four PostgreSQL regression jobs also passed at
`3848133e5e644f4c166cc9e7f3e027288d06c2fd`, with identical runtime code;
the retry changed only the test fixture and documentation.
The first transfer attempt stopped before the build on a Windows C-test fixture
portability error. The fixture now uses Winsock on Windows; client and server
code are unchanged by that correction. The [tooling failure record](postgresql-evidence/character-transfer-tooling-36297326622.json)
is preserved separately from the successful retry.

### Historical hosted M2 gate (0.1.0)

[Run 36336644450](https://github.com/Russianranger/coh-android/actions/runs/36336644450)
passed all four jobs at source `0b61d7455f40f05709f912338cd5de8b1d72d750`,
completing 2026-09-27 17:29:16 UTC. All 80 tooling tests passed without skips.
The APK's exact guest assets passed eleven stages on Linux ARM64, including
real PE32 DLL/driver loading, all 65 stock ODBC connections, transactions,
rollback, UTF-16/binary values, column metadata, schema rebuild/reopen, graceful
same-cluster restart and a second Win32 verification of persisted data. All
three cleanup checks passed. The same-source [PostgreSQL regression run](https://github.com/Russianranger/coh-android/actions/runs/36336644454)
also passed all four jobs. Preserve the [acceptance receipt](android-evidence/accepted-hosted-36336644450.json)
and [raw guest report](android-evidence/runtime-smoke-report-36336644450.json).

`COH-Diagnostic-0.1.0.apk` is 13,309,477 bytes, SHA-256
`80e53b03d95ec851623b8b743b067e87642e392a387d24679adcd81d119d38ac`.
Download the `coh-diagnostic-apk` artifact from the accepted run. It contains
no game binaries or assets. The native Java app and owned PRoot session combine
pinned Bookworm/Wine 10/FEX inputs with PostgreSQL built from official pinned
source; its ephemeral CI signing certificate is not a stable update identity.

Physical Thor acceptance was pending at this checkpoint. The current
[device acceptance record](THOR_DEVICE_ACCEPTANCE.md) preserves the later 0.1.5
pass and remaining lifecycle checks. Hosted Linux execution alone does not prove
Android SELinux, foreground-service lifecycle, device shutdown, performance or
gameplay. Mission/new-zone transfers, automatic Launcher startup and combat remain
separate unfinished scope.

### Accepted hosted client prerequisite milestone (0.1.1)

Continuation on 2026-09-27 found the hosted M2 gate complete, with physical Thor
acceptance still pending. The branch had no unfinished result to recover from its
latest completed workflows; this does not expose another Codex session's internal
state. Work advanced to the independently permitted
[basic client capability probe](CLIENT_RUNTIME_PROBE.md).

Commit `c1097bdc0aab433fd3cb1560fd07175c6c3dc6b0` adds a separate **Run client probe**
operation to 0.1.1. It exercises a real PE32 WGL context, a textured quad with four
verified RGB readbacks, buffer swap, own-window keyboard/mouse messages and
DirectInput device creation. Audio enumeration and extension availability are
observations only. The original database-only operation remains available and
both modes require complete owned cleanup. The app now scrolls on short displays.

Local validation passed 93 tests with two environment-dependent skips; the actual
PE32 program also cross-compiled warning-free with `-Werror` and its Windows
imports were verified. Hosted workflow [36349552245](https://github.com/Russianranger/coh-android/actions/runs/36349552245)
passed all five jobs at 20:59:41 UTC, including all 93 tooling tests without skips.
Database mode passed eleven stages; client mode passed twelve. The observed
renderer was llvmpipe/Mesa 22.3.6 OpenGL 4.3, all four RGB readbacks were exact,
and synthetic input plus DirectInput device creation passed. Both modes proved
graceful PostgreSQL restart and complete cleanup. DirectSound enumerated zero
devices, with no playback claim. All same-source PostgreSQL regressions passed.
The [acceptance record](android-evidence/accepted-client-probe-36349552245.json)
preserves report hashes, observed capabilities and the verified 13,477,490-byte
APK. Preserve it as the historical 0.1.1 result; the later
[Thor acceptance record](THOR_DEVICE_ACCEPTANCE.md) describes current device evidence.
A fixture result cannot establish CoH rendering, Cg shaders, physical controls,
audio playback, Android presentation or GPU acceleration. Thor reports were still
needed at this checkpoint; M3 minimal game-server/device execution remains unfinished.

### Historical Thor wineboot failure and hosted 0.1.2 result

The user supplied two Thor/Android13 reports from 0.1.1. Both passed native
PostgreSQL initialization, restricted fixture SQL and owned cleanup, but failed
at the 150-second wineboot wait before Windows ODBC or graphics. The second run
reused the same diagnostic database cluster. This is partial real-device database
evidence; complete M2/device acceptance remained pending at this checkpoint.

[The selected device evidence](android-evidence/thor-wineboot-failure-20260927.json)
records both failures. Their exit-code0 values were captured after forced cleanup
and do not establish the initializer's status before the timeout. A real subprocess
regression reproduced a false timeout when a successful initializer's background
service retains stdout. Commit `1afb0610095ebe3cb8aba591ea22d749613b7276` applies
[the narrow 0.1.2 fix](ANDROID_WINEBOOT_RETRY.md): wineboot alone may complete on
its own exit, with captured background output retained under owned cleanup. Live
initializer timeouts, nonzero exits, cancellation and output limits remain errors.
Receipts now record pre-signal state and require capture/writer shutdown too.

[Hosted run 36352420585](https://github.com/Russianranger/coh-android/actions/runs/36352420585)
passed all five jobs at this commit on 2026-09-27 21:44:41 UTC: all 99 tests
without skips, eleven database stages, twelve client stages and complete owned
cleanup. The [acceptance receipt](android-evidence/accepted-wineboot-retry-36352420585.json)
preserves that historical build and reports. Hosted wineboot exited with output
capture still open; capture closed during cleanup. This proves the corrected
wait path was exercised, not that inherited output caused the Thor failures.
The subsequent Thor retry failed; the inherited-output correction alone did not
resolve device initialization.

### Historical 0.1.3 cold initialization qualification

[The 0.1.2 device report](android-evidence/thor-initializer-timeout-20260927.json)
records wineboot still running at 150.040 seconds before cleanup signals. Four
early native database stages passed; Windows ODBC and graphics were not reached.
PostgreSQL and prefix shutdown passed, but output capture remained open, so
complete cleanup was not proved.

Commit `49c1626c10636e46a38493047f34ab61a9a5d5ca` applies the
[0.1.3 initialization correction](ANDROID_WINE_INITIALIZATION.md): use `wineboot -i`
to avoid a forced second registration pass, invalidate only the timestamp of an
unready prefix, allow 600 seconds with progress every five seconds, and write a
readiness marker only after the real PE32 fixture passes. Successful warm runs
preserve the timestamp. Wine bootstrap errors, fixture failures and open captures
still fail the diagnostic; Stop and the overall fifteen-minute limit remain.
This addresses startup behavior without identifying the exact internal component
delayed on Thor.

[Hosted run 36354263676](https://github.com/Russianranger/coh-android/actions/runs/36354263676)
passed all five jobs on 2026-09-27 22:16:35 UTC at this source. All 109 tests passed
without skips. Fresh and repeat runs each passed eleven database stages or twelve
client stages, including all Windows fixtures and complete cleanup. Cold Wine
initialization took 39.911 seconds in database mode and 40.305 seconds in client
mode, with one registration pass each; both warm runs took 4.629 seconds with zero
registration passes. These timings describe the hosted environment. The
[same-source PostgreSQL regressions](https://github.com/Russianranger/coh-android/actions/runs/36354266044)
also passed. The [acceptance receipt](android-evidence/accepted-wine-initialization-36354263676.json)
binds the verified APK, payload hashes and runtime evidence.

The subsequent device run passed initialization and all eleven functional stages;
its remaining cleanup failure is recorded below. Preserve the 0.1.3 artifact and
receipt as historical evidence.

### Historical 0.1.4 Wine helper cleanup qualification

[The 0.1.3 Thor report](android-evidence/thor-functional-pass-cleanup-failure-20260927.json)
completed initialization in 90.927 seconds with one registration pass, then passed
native PostgreSQL, real PE32 DLL loading, all 65 ODBC sessions, SQL/value/metadata
checks and durable same-cluster restart verification. The sole recorded failure
was `Owned process input/output capture did not close: wineboot`. The Wine prefix
lock and socket were inactive, and PostgreSQL shut down cleanly; that does not
prove every detached Unix helper exited. The remaining pipe writer is unidentified.
Client graphics were not requested.

Accepted source `83f132ddb8077c9d5175ae7cd039e0754b70074e` applies the
[0.1.4 cleanup correction](ANDROID_WINE_CLEANUP.md). Wine helpers carry an exact
per-run ownership token; bounded cleanup verifies the real UID and PID identity
before signaling. Output captures must actually reach EOF, and unrelated processes
must survive. The menu-helper override is corrected to `winemenubuilder.exe`;
its earlier launch does not prove it caused the retained pipe.

The initial [hosted attempt 36356073708](https://github.com/Russianranger/coh-android/actions/runs/36356073708)
stopped on ownership inspection of an unreadable, unrelated same-UID CI process.
The accepted correction safely excludes processes strictly older than diagnostic
startup, which cannot inherit the new child-only token; current or newer processes
still require inspection.

[Run 36356283176](https://github.com/Russianranger/coh-android/actions/runs/36356283176)
passed all five jobs on 2026-09-27 22:50:49 UTC. All 116 tests passed in 11.510 seconds
without skips. Database fresh/repeat runs passed all eleven stages; client
fresh/repeat runs passed all twelve. Every owned input/output capture closed,
ownership cleanup completed and no helpers remained. Cold initialization took
39.397 seconds in database mode and 37.973 seconds in client mode; warm runs took
4.276 and 4.126 seconds respectively. These are hosted timings.

Both detached-helper fixtures exercised one TERM and one KILL through two pidfd
signals, with zero remaining helpers or inspection failures. The unrelated
sentinel survived and the capture reached genuine EOF. All twelve embedded APK
assets and all six hosted reports were hash-verified. The
[same-source PostgreSQL regressions](https://github.com/Russianranger/coh-android/actions/runs/36356285898)
also passed. The [acceptance receipt](android-evidence/accepted-wine-cleanup-36356283176.json)
preserves the build identity, payload hashes and reports.

The subsequent 0.1.4 Thor run again failed capture closure; the hosted receipt
and APK remain historical evidence.

### Hosted 0.1.5 Wine thread cleanup qualification

[The 0.1.4 device report](android-evidence/thor-capture-still-open-20260928.json)
passed all eleven functional stages and initialized Wine in 85.957 seconds. The
same wineboot capture failure remained after graceful PostgreSQL and Wine prefix
shutdown. Ownership scanning reported zero candidates, zero inspection failures
and completion, so its accounting did not explain the still-open pipe. Graphics
was not requested.

The [thread cleanup investigation](ANDROID_WINE_THREADS.md) reproduced a native
thread-group leader in `Z` state while a live worker retained the exact ownership
token and inherited output pipe. The old policy skipped that group, reported zero
candidates and left the capture open. Signaling the authenticated group allowed
genuine EOF. This confirms a real cleanup defect; the physical report has no
thread inventory and cannot identify its remaining writer.

Version 0.1.5 inspects surviving tasks of an exited leader and verifies UID,
thread-group ID, start time, PID namespace and the exact run token before group
signaling, preferring a group pidfd. A true zombie without live tasks needs no signal.
Unknown ownership, surviving owned tasks or missing output EOF must still fail.
Thread observations in reports exclude environment contents and ownership tokens.

Accepted source `9dc58f62c58dc4fc5c01288071429bf2aa06d2f4` includes the final
state-transition race and missing-task checks.
[Run 36364550345](https://github.com/Russianranger/coh-android/actions/runs/36364550345)
passed all five jobs on 2026-09-28 01:12:14 UTC. All 125 tests passed in 15.591
seconds without skips. Fresh/repeat database runs passed eleven stages each;
client runs passed twelve each. Cold initialization took 39.343 seconds in
database mode and 39.747 seconds in client mode; warm runs took 4.176 and 4.277
seconds respectively. These timings describe the hosted environment.

The ordinary detached-helper and exited-leader/live-worker fixtures passed in
both modes under the pinned PRoot. Each thread fixture observed a zombie leader
with an authenticated worker holding the exact inherited pipe, which the old
policy would miss. Cleanup exercised one TERM and one KILL through two pidfd
signals and reached genuine EOF. An unrelated, TERM-sensitive sentinel running
the same executable survived. These are direct fixture observations, not evidence
of the identity of Thor's remaining writer.

All twelve APK payloads and all eight hosted reports were hash-verified. The
[same-source PostgreSQL regressions](https://github.com/Russianranger/coh-android/actions/runs/36364553676)
also passed. The [acceptance receipt](android-evidence/accepted-wine-threads-36364550345.json)
preserves build identity, payload hashes and reports.

### Accepted primary M2 Thor diagnostic and headless client gate

The [device acceptance record](THOR_DEVICE_ACCEPTANCE.md) and
[selected evidence](android-evidence/accepted-thor-20260928.json) preserve the
supplied `coh-diagnostic-20260928-012426.zip` report. It identifies app 0.1.5 on
AYN Thor/Android 13 and runtime manifest
`fba5afaeb8ceaa4fb113102e436f3677d957a1c09d1d20f543cca630979d4203`, matching the
accepted hosted build. The `database_and_client` run completed at
2026-09-28 01:24:05.958172 UTC with all twelve stages passed, no failures and
complete owned cleanup.

This report proves a successful subsequent combined run: the existing database
cluster and ready Wine prefix were reused. The user says both operations passed, including
the preceding database-only run; the supplied archive directly documents only
the subsequent combined run. It verifies native PostgreSQL, real PE32 DLL and ODBC driver
loading, all 65 ODBC sessions, SQL/value/metadata fixtures and durable same-cluster
restart. Headless WGL rendering through llvmpipe/Mesa 22.3.6 returned all four
expected pixel colors; synthetic window input and DirectInput device creation
passed. This is a software renderer. DirectSound enumerated zero devices, with
no audio playback claim.

Device cleanup now observed three exited-leader groups and three authenticated
live-worker witnesses. It issued three TERM signals and one KILL signal through pidfds,
finished with zero remaining helpers or inspection failures, and closed input and
output for all 30 recorded processes. This observes the reproduced dead-leader/
live-worker condition on Thor and completes cleanup successfully. The report does
not inventory the exact earlier pipe writer, so that identity remains unknown.

**The primary M2 device diagnostic and headless client capability gate are
accepted.** Android surface presentation, hardware acceleration, physical input,
audible playback and CoH gameplay remain unvalidated. The subsequent 0.2.0
DbServer test passed two full runs with a clean Stop between them. App switching
and screen locking are user-attested; peak memory remains unmeasured. Keep both
accepted installations. The next device work is verified asset import and the
combined Atlas runtime with Android lifecycle handling. The
[first hosted M3 DbServer gate](ANDROID_DBSERVER.md) subsequently passed in
run 36369485666. The latest managed Atlas result above accepts hosted
MapServer/client local bindings; Android packaging, network integration and
app lifecycle checks remain before physical Atlas acceptance.

### Earlier attempts and corrections

The recovered evidence and new character harness are on
[`codex/character-persistence-continuation`](https://github.com/Russianranger/coh-android/pull/1)
in draft PR #1. Implementation commit: `3d61ca929dc825ba9424279553797b66498df418`.
[Hosted run 36269025801](https://github.com/Russianranger/coh-android/actions/runs/36269025801)
passed both tooling jobs: all 55 Windows checks, including three live named-pipe
checks; Linux passed 52 with those three platform checks skipped. The game
experiment failed with `Unknown character status flags`: a multiline whitespace
match consumed process output after a valid status line. Character ID 1 and its
name agreed between TestClient, stock `-find` and independent SQL, but no save or
restart pass was reached. The [full failed attempt](postgresql-evidence/character-persistence-36269025801.zip)
and [report](postgresql-evidence/character-persistence-36269025801.json) are preserved.
The status parser is corrected at `cc3c82a87e2c3eabe1478b13ea031e3923423b10`,
without relaxing identity or flag checks. The reproducing regression passed;
all 40 portable character checks passed, with three Windows transport checks
skipped locally. [Fresh retry 36270565732](https://github.com/Russianranger/coh-android/actions/runs/36270565732)
failed after the status fix worked: character ID 1/`TEST-43027` was connected on
Atlas Park, but TestClient's GUI entry allocated its own console and reopened
stdout/stderr to `CONOUT$`. The harness could not see the required creation
branch text. The [artifact](postgresql-evidence/character-persistence-36270565732.zip)
and [report](postgresql-evidence/character-persistence-36270565732.json) are preserved.
The attempted console preallocation fix was rejected by its Windows GUI
regression in [run 36280623154](https://github.com/Russianranger/coh-android/actions/runs/36280623154):
`AllocConsole` still succeeded, so the runtime job was skipped. The replacement
uses a bounded observer attached to the actual TestClient console before the
launcher version exchange, preserving the console across the short client exit.
[Run 36281372316](https://github.com/Russianranger/coh-android/actions/runs/36281372316)
then passed all 66 Windows tooling/map checks and reached real character creation,
live currency 12345, protocol logout and independently committed SQL. The first
saved snapshot contains one parent, one secondary row, seven powers and twelve
costume parts. It failed on observer cleanup before restart acceptance: forced
client-tree termination closed the console before its final snapshot. The
[artifact](postgresql-evidence/character-persistence-36281372316.zip) and
[report](postgresql-evidence/character-persistence-36281372316.json) are preserved.
The follow-up finalizes the observer after proven logout/save but before residual
client cleanup; exact resume acceptance remains required.
All four [PostgreSQL regressions](https://github.com/Russianranger/coh-android/actions/runs/36269025871)
also passed on the implementation commit.

The final cleanup-order correction in `86e512e8` completed the restart/resume
gate. Its accepted evidence and remaining scope are recorded above; earlier
failed attempts remain as diagnostic history.

## Active direction

Use the original public OuroDev-derived Issue 24/Volume 2 source fork at
`0b75ade0c801735e10c5798f641948a45cc50488`, under `upstream/ouroboros`. The user has
no Windows PC: use hosted Windows builds/reference tests and Thor testing.
Canonical i25 acquisition is deferred.

## Current database work

PostgreSQL is the selected database alternative. The implementation lives in
`database/postgresql`, with an immutable-source patch under `patches/postgresql`.
The actual Win32 DbServer now has an opt-in, asset-independent persistence test
entry. It exercises the original container parser, writer, SQL FIFO/worker pool,
reader and template updater with controlled templates and records. PostgreSQL
saves commit before completion; serialization/deadlock retries replay the whole
transaction. Permanent or uncertain failures stop without acknowledging the
failed command. Child/parent deletion is atomic.

All four jobs in the current [regression run 36088012670](https://github.com/Russianranger/coh-android/actions/runs/36088012670)
passed at repository commit `775a0dd770adac045484805dbbb5f68054c7a354`:
Linux PostgreSQL 16/18, Windows x86 ODBC/PostgreSQL 17, and the actual Win32
DbServer. The latter passed 21 check groups across 14 process invocations,
including connection loss, failed-save rollback, restart/WAL recovery, template
rebuild, backup/restore and foreign-key removal against absent tables. The
narrow PostgreSQL guard fixes the fresh-database initialization failure without
changing the preserved source snapshot.

The earlier [20-group implementation run 35962572993](https://github.com/Russianranger/coh-android/actions/runs/35962572993)
at `0827ccc992daa7530d9f98d742122238197847df` and
[regression refresh 36071558686](https://github.com/Russianranger/coh-android/actions/runs/36071558686)
remain historical evidence. The separate normal fixture-OFF DbServer
[startup/export/reload run 36125829298](https://github.com/Russianranger/coh-android/actions/runs/36125829298)
also passed using the accepted schema/runtime pair and a fresh disposable
PostgreSQL database. This exercises normal game-schema initialization in addition
to the controlled persistence fixtures; it does not create or save characters.

**Normal network acknowledgements passed:** [run 36125829311](https://github.com/Russianranger/coh-android/actions/runs/36125829311)
verified creates, an update after restart, and a two-container request held behind
an actual PostgreSQL row lock. No ACK arrived during the 2.078-second observed
write block. After release both rows were committed; an injected COMMIT failure
then produced zero ACKs, preserved the previous row, and stopped DbServer with
exit 3. The normal reference package had fixture mode OFF. The report and all
redacted logs are [preserved](postgresql-evidence/network-ack-36125829311.json).
Batches are not atomic as a whole, and player-session completion is untested.

The latest test drivers distinguish the specific observed benign PostgreSQL
catalog notices from real errors. Both new normal-process gates passed at
`a0ae66d72648d33a7f70b3116d1e1800d9164184` using the accepted `775a0dd...` builds.

Migration 2 adds transactional table rebuilds preserving sequence high-water,
indexes and foreign keys, explicit ASCII case-insensitive name equality, and the
PostgreSQL auction timestamp filter. Stop DbServer, back up and run
`pg_local.py migrate` for an existing development cluster. See the
[persistence design and test scope](POSTGRESQL_PERSISTENCE.md),
[database instructions](../database/postgresql/README.md) and
[validation record](VALIDATION.md). This database milestone does not establish
gameplay; the separate diagnostic APK's current acceptance is recorded above.

**Stage1 asset inspection complete:** `stage1a.pigg`, `stage1b.pigg` and
`stage1f.pigg` have been received. All **14,814 entries** passed archive integrity
and offline structural checks; 5,878 animations and 8,936 textures were staged
separately. All seven startup texture names and MALE/THUMBSUP are present.
Every base-animation reference resolves within `stage1a.pigg`. Preserve warnings
for 216 legacy hierarchy layouts and 193 DDS surplus-byte cases; runtime use
remains unvalidated. See [the stage1 assessment](STAGE1_ASSET_ASSESSMENT.md).
No repeat index run, repeat upload or custom `i26/geobin.pigg` upload is needed.

**Reference runtime refreshed:** [run 36088012664](https://github.com/Russianranger/coh-android/actions/runs/36088012664)
passed with the exact source pin, PostgreSQL patch and fixture mode OFF at
repository commit `775a0dd770adac045484805dbbb5f68054c7a354`.
Download `reference-win32-runtime` (artifact `10843979104`) from this run;
it supersedes [the earlier package 36069123663](https://github.com/Russianranger/coh-android/actions/runs/36069123663).
Client, MapServer, DbServer, TestClient, pig and Launcher are packaged with
required supplied DLLs and app-local x86 MSVC runtime libraries. The package
passed hash, PE and dependency checks. The verified base assembly contains
173,011 data files / 2,977,730,517 bytes, with no conflicting donor paths.
The preflight's earlier 173,008 count excluded three additional source-pinned DB
config files added by final assembly. See [current assembly evidence](reference-runtime-evidence/assembly-775.json)
and [reproduction/build instructions](REFERENCE_RUNTIME.md).

Local game execution is blocked by this environment's wineserver IPC restriction.
Use hosted Windows for further runtime validation. The separate data-only schema
patch remains isolated from the reference package and retains error/output
gates. Its incidental caches must not be reused as gameplay caches.

**Data-only schema generation refreshed:** [run 36088012666](https://github.com/Russianranger/coh-android/actions/runs/36088012666)
passed at the same repository commit as the current reference package. Bootstrap
took 31.468 seconds and strict reload 5.750 seconds, with zero queued errors and
identical bytes for all six attribute maps. All 51 required outputs plus five
dbidmaps are preserved in [the current accepted artifact](schema-generation-evidence/accepted-36088012666.zip).
Every one of these 56 generated payloads is byte-identical to the
[earlier accepted run 36072787971](schema-generation-evidence/accepted-36072787971.zip),
which remains historical evidence. Keep the accepted attribute-ID mappings with
any database initialized from them.

**Normal DbServer schema startup/reload passed:** the first hosted attempt
exposed a fresh-database FK-removal ordering bug. The narrow correction passed
its regression suite and is included in both current artifacts. With that pair,
[run 36125829298](https://github.com/Russianranger/coh-android/actions/runs/36125829298)
completed fresh initialization/export in 13.219 seconds and a second pass in
5.718 seconds. Both exited successfully with no failure diagnostics and produced
fresh empty dumps. Both passes found 99 tables and 58,272 attribute rows
(56,411 general, 1,771 badge-stat and 90 pop-help IDs), with identical catalog
hashes and attribute mappings. Both catalogs contain the verified 5,935 columns,
119 indexes and 734 constraints.
The tested DbServer has persistence fixture mode OFF; its executable SHA-256 is
`fb62028b24bf3165bdcf09e80909d02df5391f89986b9e0454934909a67d93f8`.
See the [downloaded evidence](postgresql-evidence/generated-schema-36125829298.zip)
and [summary](postgresql-evidence/generated-schema-36125829298.json).
The later asset-backed comparison and Atlas Park gate below passed. Complete
serializer semantics, complete asset coverage and character gameplay remain
unvalidated.

**Normal templates and Atlas Park readiness passed:**
[run 36176806895](https://github.com/Russianranger/coh-android/actions/runs/36176806895)
used the accepted reference/schema pair and all 16,721 reviewed binary assets.
Ordinary `MapServer -templates` freshly reproduced **56/56** accepted files
byte-for-byte in **25.89 seconds**. A separate fresh runtime, without comparison
caches, then started normal DbServer and Atlas Park against PostgreSQL. Independent
DbServer status queries confirmed the initial not-started state and subsequent
ready state with continuing updates for **62.235 seconds**. Both reports have
empty failure lists. Preserve the [comparison report](reference-runtime-evidence/reference-template-comparison-36176806895.json),
[comparison artifact](reference-runtime-evidence/reference-template-comparison-36176806895.zip),
[map report](postgresql-evidence/one-map-36176806895.json),
[map artifact](postgresql-evidence/postgresql-one-map-36176806895.zip) and
[accepted gate identities/hashes](reference-runtime-evidence/accepted-gates-36176806895.json).
The normal executable does not report queued startup error counts; these gates
do not establish complete assets, character login/persistence or gameplay.

## Completed

- All 5,995 source files verified; exact-commit upstream Windows build and nine
  utility/archive/codec tests passed, as previously audited.
- Imported the entire `Thunderspies/i24` tree at
  `d51533ec8e6a9cf726b9214968077a05fdcf19f3` under `upstream/i24`: 156,297 files,
  1,992,097,492 bytes, no exclusions. Local and hosted integrity/tree checks passed.
  Import commit: `1768775ab3608cdd852ec7119bbf0139a91248c6`.
- Added `content-lock.json`, data inventory and per-file manifest. The importer
  and verifier accept `--lock content-lock.json`; existing source defaults remain.
- Added the exact 72-archive upstream catalog and portable `content_assets.py`
  probe/fetch/record/verify tool. Receipt checks detect changed/missing bytes.
- Added `prepare_runtime.py`; full text-only staging passed. It keeps imports
  immutable, fixes `Game.exe` to `CityOfHeroes.exe` in staged launchers and uses
  source-pinned configs. It accepts extracted asset data and exact-pin build
  outputs separately; it does not execute programs or install SQL.

## External content result

The user's `small_i26_piggs.zip` has now been inspected: all **17 archives /
8,864 entries** passed size, decompression, MD5 and cached-header checks.
**549 compiled files use Parse7; the pinned source expects Parse6**, so these
caches cannot be reused unchanged. Staged **665 candidate binary assets**
(141 geometry, 445 textures, 79 audio files; 152,755,341 bytes) separately,
with runtime compatibility still unverified. No raw client binaries/assets were
published. The original ZIP plus the new portable inspector reproduce staging.
See [client content assessment](CLIENT_CONTENT_ASSESSMENT.md) and its
[per-archive hashes/counts](client-content-assessment.json). Eight inspector
regression tests passed in that initial pass.

The subsequent **`geomBC.pigg`** also passed: 1,232 entries, comprising 584
geometry files and 648 Parse6 caches. All geometry files use versions accepted
by the source and passed compressed-header/data-bounds checks; meshes/collision
and runtime loading are untested. Staged geometry separately under
`imports/base-geomBC-candidate-assets`. Cumulative result: **18 archives,
10,096 verified entries, 1,249 distinct candidate assets / 318,908,734 bytes**.
The inspector now records geometry header checks; eleven regression tests pass.
See [base geometry evidence](base-geometry-assessment.json).

The later `fonts.pigg`, `player.pigg`, `misc.pigg` and `geom.pigg` batch also
passed: **2,774 additional entries**. Cumulative result is now **22 archives /
12,870 entries / 2,487 distinct candidate asset paths**, with two conflicting
custom/base geometry variants kept separately. All 46 fonts are staged, including
TTC collections; every one of the 16 startup font filenames is present. All
1,277 new geometry headers passed. `misc.pigg` mostly duplicates the pinned text.
At that earlier stage there were **zero skeletal .anim tracks** in the supplied
set and none of seven requested basic renderer texture names. The subsequent
stage1 uploads below supply those candidates; runtime startup remains untested. See [asset coverage history](BASE_ASSET_COVERAGE.md)
and [machine-readable evidence](base-assets-assessment.json).

The subsequent **`coh-asset-index.json`** has now been received from Thor and
preserved as [thor-asset-index.json](thor-asset-index.json). It reports 73 base
archives and 22 custom-folder archives, with 96,379 entries across those tables
(not deduplicated). Base `stage1a.pigg` lists 5,878 animation tracks, including
MALE/THUMBSUP; `stage1b.pigg` and `stage1f.pigg` list all seven startup texture
names. This locates candidates on the device; it does not add to the 22
payload-verified archives or establish source-format/runtime compatibility.
The indexer previously matched full-inspection counts/extensions for all 22
available archives; thirteen regression tests passed in that earlier pass.

The three selected **stage1 archives** then passed integrity and offline format
checks. Cumulative payload-inspected count: **25 archives / 27,684 entries**.
New staging contains 14,814 distinct paths within the batch and 654,699,284 bytes;
its overlaps with earlier custom assets have not been recomputed. The 20 new
format/staging tests passed. All animation base references resolve, including
the fallback, and all seven startup textures pass structural checks. Native
ARM64 needs explicit decoding of 32-bit animation records; the renderer must
handle the observed DDS formats. Runtime compatibility remains untested. See
[stage1 evidence](stage1-assets-assessment.json) and the
[reproducible checks](STAGE1_ASSET_ASSESSMENT.md#reproduce-without-windows).


[Hosted import/probe run](https://github.com/Russianranger/coh-android/actions/runs/35940141238)
completed successfully. All 72 archive HEAD requests to `dists.thunderspy.org`
returned HTTP 403. Local sample GET and the current live manifest also returned
403. Binary assets were not downloaded from that host. `docs/asset-availability.json` contains
the complete observations.

[Content acquisition instructions](CONTENT_ACQUISITION.md) identify the canonical
recipe and OuroDev's base/binning-data archive listings as an unverified fallback.
The original fallback was an accessible compatible archive/mirror/magnet or
existing asset folder; the user has since supplied the targeted assets above.
No additional broad asset upload or Windows VM is required for this assessment. Do not silently substitute the current
customized Thunderspy/Homecoming live client or reuse unrelated generated bins.

## Next implementation priority and remaining scope

The accepted device build is [COH Server Test 0.2.0](ANDROID_SERVER_DEVICE_TEST.md),
installed alongside 0.1.5 as `io.github.russianranger.cohdiagnostic.m3`.
It packages the exact accepted M2 payloads and qualified loopback DbServer donor
`36460867428`, with a device policy enabling loopback for every DbServer process
and fixed inputs for both normal schema launches. The original Atlas donor is
not changed. Each real test has disposable state and each operation an immutable
support ZIP. The candidate workflow builds the APK and runs its exact packaged
guest/bundles on hosted ARM64 with the device policy. All three jobs and all 28
runtime stages passed in
[run 36483331900](https://github.com/Russianranger/coh-android/actions/runs/36483331900)
at `f7dbba42ec29a1c054d856d71810146f5b53bac6`. Tooling passed 233 checks with eight
Windows-only skips. The APK is 16,668,615 bytes, SHA-256
`cb5cf453af1b81cbaa02917a6d7cb55ab8b8f2a910a46b0a85f4ae399883188b`.
The [candidate receipt](android-evidence/accepted-device-candidate-hosted-36483331900.json)
binds the build, independently checked APK payloads and hosted reports.
The [physical Thor receipt](android-evidence/accepted-dbserver-thor-20260928.json)
records two full passes in 325.763 and 338.326 seconds, surrounding a clean Stop
during active Wine setup. Both passes verified 14 local endpoints, all 21 fixture
groups, both schema passes and all 111 closed process captures. The stopped run
closed all 22 captures and correctly reported cancellation. All three ended with
zero owned processes and inspection failures. App switching and screen locking
are user-attested; peak memory is unmeasured. The subsequent hosted Atlas loopback
integration passed in `36493722153`, preserving the earlier accepted default.
MapServer/client local bindings then passed Windows and hosted ARM64
qualification in `36510836956`. Verified asset import and separate Android
Atlas runtime/lifecycle integration are next; none of these hosted results
establish physical Atlas acceptance.

**The primary M2 device diagnostic, hosted M3 DbServer and hosted Atlas
create/save/restart/resume/second-save sequence are accepted.** The Atlas
[acceptance receipt](android-evidence/accepted-game-hosted-36460005201.json)
records the successful full workflow `36460005201`, including the final host
validator. Preserve the earlier `36454174481` workflow failure and its separate
post-correction acceptance.
The isolated Wine-compatible DbServer fixture
and normal schema startup/export/reload have passed; preserve their
[accepted evidence](android-evidence/accepted-dbserver-hosted-36369485666.json).
The current fixed-input DbServer successor is also
[qualified](android-evidence/accepted-dbserver-hosted-36451873322.json).
Keep default donor `36451873322` and retain both DbServer
activation acknowledgments and all four schema/configuration snapshots.
Enabled ARM64 dispatch publication was already verified in run `36428915900`.
The separate sibling DbServer failure remains unexplained despite the successful
byte-identical repeat; retain both receipts and the qualified donors.
The separate loopback listener package is
[hosted-qualified](android-evidence/accepted-dbserver-hosted-36460867428.json)
in run `36460867428` and accepted for the explicit Atlas loopback profile in
`36493722153`; the historical default donor is retained. Preserve its earlier
CRLF fixture-setup failure and correction. The 0.2.0 device results accept this
listener package and Stop/rerun handling on Thor. The separate
[hosted game listener receipt](android-evidence/accepted-game-listeners-hosted-36510836956.json)
accepts both MapServer starts and both TestClient sessions with actual local
UDP bindings and the complete persistence sequence. Its opt-in donor profile
preserves the historical defaults and accepted device APKs.
Keep the existing 0.1.5 and 0.2.0 APKs and runtimes. See the
[concrete next steps](THOR_DEVICE_ACCEPTANCE.md#next-work).
Peak memory remains unmeasured. The following items preserve
completed reference gates; no repeated Windows-only milestone is needed.

1. Preserve the accepted results from corrected manual [asset run 36176806895](https://github.com/Russianranger/coh-android/actions/runs/36176806895).
   It passed ordinary template comparison and Atlas Park readiness with schema
   run `36088012666`, reference run `36088012664`, asset `588984151` and
   `run_one_map=true`. No rerun is needed to establish those completed gates.
   Upload is complete: unpublished draft release
   `396839391` contains the accepted **615,541,018-byte** ZIP, SHA-256
   `28b4aa8f0b3a71287e9a596df23097722bd71db9ddb9a5a906b5af9d6152cc07`.
   Ignore incomplete asset `588979946`. No repeat PIGG or ZIP upload is needed.
   The initial manual [run 36174562963](https://github.com/Russianranger/coh-android/actions/runs/36174562963)
   failed during download before any game process, suspected to be the draft
   release's rejection of the read-only token. Its HTTP status was not logged.
   [Fix 5f37d7c](https://github.com/Russianranger/coh-android/commit/5f37d7c)
   scopes `contents: write` to the manual comparison job; global/tooling tokens
   stay read-only. It also adds safe numeric HTTP status and stage diagnostics;
   all 12 downloader tests and [tooling run 36175800522](https://github.com/Russianranger/coh-android/actions/runs/36175800522)
   passed. [Run 36175960917](https://github.com/Russianranger/coh-android/actions/runs/36175960917)
   then successfully downloaded and verified the exact ZIP, confirming hosted
   draft access. It failed `Manifest must use canonical JSON` before game
   execution: Windows checkout changed the manifest's LF bytes to CRLF.
   [Fix fe98dd5](https://github.com/Russianranger/coh-android/commit/fe98dd5a9761fb05d79b9b3f9f39a771eb9ea687)
   marks `assets/reference-inputs-*.json -text`; a temporary Git checkout with
   `core.autocrlf=true` reproduced the accepted canonical bytes, and
   [tooling run 36176404244](https://github.com/Russianranger/coh-android/actions/runs/36176404244)
   passed. The successful manual run used that fix. The release remains unpublished
   and raw assets are not uploaded as Actions artifacts. See the
   [concrete handoff](NEXT_SERVER_VALIDATION.md) and
   [transfer evidence](reference-runtime-evidence/asset-transfer-20260925.json).
   The matching reference package and coherent base assembly are ready. Preserve the accepted attribute-ID mappings; do not
   substitute the separate schema executable or its incidental caches for the
   reference runtime.
2. Preserve the accepted [character persistence result](CHARACTER_PERSISTENCE_VALIDATION.md#accepted-hosted-validation-36282414135).
   Fake-auth creation, live currency change, explicit logout, committed SQL,
   same-cluster/service restart and exact-name short resume have passed.
   The [sustained resume and second-save result](SUSTAINED_SESSION_VALIDATION.md#accepted-hosted-validation-36295176484)
   has also passed, including missing-name refusal without mutation. Preserve
   the separate diagnostic TestClient receipts alongside the stock reference.
   The [Atlas round trip](MAP_TRANSFER_VALIDATION.md) has also passed with
   independent destination identity, fresh player updates, current heartbeats,
   live currency and a final committed protocol save. New-zone assets, mission
   transfers and automatic Launcher startup remain unvalidated.
   Separate remaining server work includes player-session completion callbacks, game-level
   name uniqueness and auxiliary-service persistence. Generic-container network
   ACK ordering is now verified. Fake auth is only the minimal local diagnostic route; no SQL
   Server save migration has been attempted. Empty-database startup/export and
   controlled persistence fixtures do not establish these gameplay behaviors.
3. Generate further server/client caches with the bounded harness when the runtime
   has the required graphics. Resolve legacy animation hierarchy/DDS warnings
   through reference runtime use. Keep custom variants separate and request
   further archives only when runtime evidence identifies a concrete missing
   input. The older upstream v2i3 release is not the locked build; use the current
   reference artifact.
4. Keep the accepted 0.1.5 and [0.2.0 server](ANDROID_SERVER_DEVICE_TEST.md)
   installations. The real DbServer, Stop/rerun and requested background checks
   are complete within their documented evidence scope; do not request another
   run of these passed diagnostics. Peak memory remains unmeasured.

Do not run the unmodified upstream asset fetcher inside `upstream/i24`; it assumes
a standalone Git checkout. Never modify the preserved snapshot to fix a launcher.

The manual i25 discovery workflow and its prior TLS findings remain historical.
`odtoken` is not required for current work and must not be printed or sent to the
asset host. No background import is running. The current APK status is recorded
in [ANDROID_DIAGNOSTIC.md](ANDROID_DIAGNOSTIC.md); gameplay remains unvalidated.
