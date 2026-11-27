# Thor test: COH Atlas Gameplay 0.13.85 (ARM64 client): unlocked content, the Primalist archetype, a second hero slot

0.13.85 follows 0.13.84 (missions) by a day; 0.13.84 and 0.13.83 have not
been on the Thor. With the new options unticked, 0.13.85 plays as 0.13.84, so
this sheet starts with the 0.13.84 test and adds two launches.

## What is new in 0.13.85 (your request of 2026-11-25)

- **Test option "Unlock all content"**, off by default. The one local account
  owns every store product and every veteran reward, is a VIP, and has every
  pack and archetype access bit. That unlocks:
  - 28 locked power sets: Beam Rifle, Beast Mastery, Bio Armor, Brawling
    (Street Justice), Dark Assault, Darkness Affinity, Darkness Control, Demon
    Summoning, Dual Pistols, Electric Control, Experimentation, Force of Will,
    Gadgetry, Kinetic Melee, Martial Assault, Martial Manipulation (Martial
    Combat), Nature Affinity, Psionic Melee, Radiation Armor, Radiation Melee,
    Savage Melee, Sorcery, Staff Fighting, Time Manipulation, Titan Weapons,
    Utility Belt, Water Blast, Wind Control;
  - Peacebringer, Warshade, Arachnos Soldier and Arachnos Widow;
  - costume sets and pieces, auras, extra costume slots, the invention and
    auction licences, store and veteran badges and the powers they give.
  Counts of consumable items (respecs, tokens) are not changed. Thirteen
  developer test powers stay locked (list at the end).
- **Test option "Primalist archetype"**, off by default: the unfinished
  shapeshifting melee archetype, from the files you sent. **It changes the
  saved game once:** the first launch with it adds the class name to that
  saved game's database (at the end of the list; no existing name changes).
  From then on the archetype stays on for that saved game whatever the box
  says, and **app versions before 0.13.85 will not open that saved game**.
- **A second hero slot** (Setup tab, "Switch hero slot"). The app keeps one
  saved hero; a new archetype needs a new hero. The button sets the saved hero
  aside (nothing is deleted) so **Create fresh character** appears, and swaps
  the two heroes later.

What CI showed, and what it could not:

- **Shown in CI with both options on, the fast server, the spare server and
  the database server the app ships** (run 45720659785, at the release commit):
  - The zone server compiled its class list with the Primalist in it; the 39
    content files were in place; the database took the new class name (number
    56412) and the next session found it there.
  - "Unlock all content" reached the game and the zone servers (65 account
    bits; store, veteran and VIP checks answer yes). The new hero had 24 or
    more reward tokens at once: holiday, mutant, science, cyborg, magic,
    valkyrie, martial arts, animal and wedding packs, Going Rogue set,
    collector's capes and emblems, preorder helmets.
  - A Blaster was created, played, travelled to a second zone through the
    spare server (ready 9.3 s after the request) and was saved; the saved hero
    was reopened with the saved zone data taken again (no file compiled a
    second time, zone server ready in 23.4 s; 23.8 s without the options).
- **Found and fixed on the way** (five builds): with the Primalist on, every
  launch prepared the zone data from scratch (zone server 167-206 s in CI
  instead of 23 s). Two causes, both fixed and covered by a test now.
- **Not shown in CI:** CI's creation clicks a Blaster, so **no Primalist has
  been created or played anywhere yet**: its powers, forms, animations and
  the Primal Energy bar are untested. The unlocked menus were not looked at
  (only that the creator still works with them). The checkboxes and the hero
  slot were compiled and unit-tested, not run on Android. On the Thor the
  first start with the Primalist rebuilds two compiled files per zone data
  set (Atlas, then the shared zone data on the first trip): how long that
  takes there is not known.
- **Known gaps:** the Primalist has no icon or preview pictures and no
  ancillary power pools; its balance is whatever the unfinished files hold.

## Steps (update in place: no uninstall; assets and the navigation map pack stay imported)

1. Install 0.13.85 over the installed version.
2. **Setup** tab: tap **Set up / update runtime**, wait for **Runtime ready**.
3. **Options** tab: tap **Restore recommended options**. The options then are:

   Checked - Recommended (19):
   - Use performance graphics
   - Fast mode (PRoot seccomp, experimental)
   - Share server data between zones (faster zone preparation)
   - Skip server-only folders in the client's file scan (faster client start)
   - Reuse the client's saved file list while the data is unchanged (faster client start)
   - Game audio (sound and music through Android)
   - Game's own zone travel (doors, tunnels, monorail; any zone)
   - Start my saved zone while the game starts (Reopen)
   - Keep a spare zone server loaded for travel (needs Fast server)
   - Fast server (untick for the 0.13.36 server)
   - Raise the frame cap to 60 FPS in the world
   - Lighter system-call monitor (untick for the 0.13.36 one)
   - Do not monitor ordinary socket traffic (needs Lighter system-call monitor)
   - Find files in any letter case in one step (needs Lighter system-call monitor)
   - Load zone server animations when first used (faster zone start)
   - Remember folder locations in the Wine server (faster file opening)
   - Reuse prepared collision meshes (faster zone start, needs Fast server)
   - Faster number emulation in zone servers (64-bit x87; faster zone start and travel)
   - Finish zone loading while the game loads the zone (needs Fast server)

   Your choice - Optional (1):
   - Keep the zone you just left loaded (about 1.2 GB more memory; needs the spare zone server)

   Unchecked - Test (3), each ticked only for the launch that names it:
   - Start mission maps (test; needs the game's own zone travel and the imported zone assets)
   - Unlock all content (test; store, veteran and pack rewards, locked power sets and archetypes; needs Fast server)
   - Primalist archetype (test; adds its name to the saved game once and stays on; older app versions will not open that saved game; needs Fast server)

   Unchecked - Experimental (5):
   - Start King's Row in the background (zoning)
   - Lower the waiting zone server's priority (zoning, experimental)
   - Shared server memory (experiment: zone servers share game data)
   - Draw on the game's own thread (frame rate experiment)
   - Keep prepared zone object files (experimental, ARM64 client; faster zone loading)

4. **Launches A and B: the 0.13.84 test** (menu and FPS buttons; a mission
   with **Start mission maps**), exactly as in `THOR-TEST-0.13.84.md` steps 4
   and 5. Do these first, with your existing hero and the two new options
   unticked: they show that nothing changed for ordinary play.
5. **Launch C: unlocks on your existing hero.** Tick **Unlock all content**
   only. **Reopen saved character**, log in, Enter Game. Note:
   - Is the hero in the world as usual? Expect a burst of "badge earned"
     messages and new powers at first (the game hands out store and veteran
     rewards); note anything that looks wrong or any error box.
   - Open the costume editor (a tailor) if one is near: are locked pieces now
     selectable?
   - Play a few minutes, **Save character / log out**, **Finish and save
     report**, export.
6. **Launch D: a Primalist.** This needs a new hero.
   - **Setup** tab: **Switch hero slot**, confirm. Your hero is set aside.
   - **Options** tab: tick **Primalist archetype** and **Unlock all content**.
   - **Play** tab: **Create fresh character**. The first start takes several
     minutes longer once: the server data is prepared again and two compiled
     files are rebuilt. The first trip to another zone does the same once for
     the shared zone data. Later launches should be as fast as before; say so
     if they are not.
   - In character creation: is **Primalist** in the archetype list (melee or
     support playstyle)? It has no icon or preview pictures; that is expected.
     Are other locked sets and archetypes selectable?
   - Create a Primalist: Feral Might and Primal Gifts. Enter the game.
   - Try the first attacks, then at level 6 or with a trainer the Hunter
     form: do powers animate, does the form change the model, does the Primal
     Energy bar appear above the tray?
   - **Save character / log out**, **Finish and save report**, export.
   - Then **Reopen saved character** once more: does the Primalist come back?
     Save and export again.
7. To go back to your first hero: **Setup** tab, **Switch hero slot**. The
   Primalist goes to the other slot; switch again any time. Leave **Primalist
   archetype** as it is (the first hero's saved game is not changed unless you
   launch it with the box ticked).
8. **Options** tab: **Restore recommended options** when done.

If the game does not start with a new option ticked: untick it, **Restore
recommended options**, try once more, and export the failed launch's report
(Setup, **Recover interrupted reports** if needed). A Primalist hero that
exists can only be opened with 0.13.85 or later.

If an error box appears in the game, tap **Ignore** (not Stop Program), note
what it says and keep going.

## Report

The exports of each launch and what you saw. Fields I will read:

- `primalist` (`requested`, `in_database`, `active`, `attribute_id` 56412)
  and `single_player_content` (39 files).
- `character_creation.single_player_stale_bins` (which compiled files were
  rebuilt) and `map_startup_observation.*.single_player_class_compiled`.
- `private_map_data.server_data_cache` and `zone_tree_preparation.
  server_data_cache` (`reused` true and no `reuse_refused` from the second
  launch on) and the zone server's start time in each launch.
- `character_creation.account_unlock` and `client_account_unlock` (which
  switches reached the server and the client), `unlock_all`
  (`auth_bits_granted` 65).
- `character_reopen.unlock_all_changes` (which saved tables the unlock
  changed; recorded, not judged) and `gameplay_progress`.
- Launch D's first zone start time and `server_preparation_phase_seconds`.
- The zone server console for missing files or power errors.

## What stays locked

The game data marks 13 temporary powers for developer accounts only (access
level above 9; this build's account has 9, which already opens every other
access-level check in the data). They are art and damage test powers, not
content, and no power set or archetype depends on them:

- Art Test: Melee, Melee PBAoE, Ranged, Ranged AoE, Ranged Snipe, Melee
  Snipe, Self Toggle, PBAoE Toggle.
- Temporary Powers: OBSOLETE Temporal Disruption, Damage Power, Vince is
  Evil, Vince is Sneaky, The I Win Button.

Say so if you want them opened too; it is a one-line setting.

Details: `HANDOFF-X86.md`, section "0.13.85 (100)".

CI: build 45701470085 at `6bb8db37e`; trusted 45715767338 (zone server 387.0 s new, 23.8 s reopened); both new options with the spare server 45720659785 (172.8 s new, 23.4 s reopened, trip's zone ready 9.3 s); APK 45724776095 (93,934,082 bytes, sha256 `b2dae94d0502a65087481ed4991120989ec537252dd410e9009dde1e038524af`, same signer, 53 runtime modules equal the commit). With the options off, one commit earlier (`6bbb472c3`; only the app's file inventory limit changed since): zone change 45683248678, spare 45694752114.
