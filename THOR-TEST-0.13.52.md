# Thor test: COH Atlas Gameplay 0.13.52 (ARM64 client) — draft, staged

Staged while the 0.13.51 test runs; it is published after those results, and
items from them may be added first. Evidence: [HANDOFF-X86.md](HANDOFF-X86.md),
"0.13.52".

## What changed since 0.13.51

| Change | Default | Expected effect |
|---|---|---|
| Saved client file list | on (`Reuse the client's saved file list`) | The first start after installing scans as before (about 110 s) and saves the list. Later starts with unchanged game data rebuild it in about a second. Any change to the data, or a failed check, runs the full scan again |
| Zone servers find their private files first | always | Each zone load (Atlas and King's Row) should be a few seconds shorter |
| Fast server start (test server) | **off** | Ticking it runs a second, instrumented MapServer with trusted prepared bins (in CI: Atlas start 130 s → 94 s). It has never run on a device; untick it if a zone fails to start |

## Steps

1. Install 0.13.52 over 0.13.51, then tap **Set up / update runtime** once.
2. Options as in 0.13.51; `Reuse the client's saved file list` is on and
   `Fast server start (test server)` is off.
3. **Session 1:** reopen the hero; time tap → login screen. The client scans
   in full this time. Save/logout, Finish, **export**.
4. **Session 2:** reopen again and time tap → login screen; it should be
   about 100 s shorter than session 1. Take the monorail to King's Row and back.
   Save/logout, Finish, **export**.
5. **Session 3 (test server):** tick `Fast server start (test server)`. Reopen;
   time tap → login screen and note anything wrong in Atlas (missing NPCs,
   contacts, doors). Save/logout, Finish, **export**. Untick it afterwards
   unless it worked well.

## Report

Times per session, anything that looked wrong, and the three exports. Fields I
will read: client log `ARMPORT_FOLDER_CACHE_V1 phase=index`, `client_folder_index`,
`shared_server_data.first_lookup_private_folders`, `server_option`, `trusted_bins`
and the Atlas console's `loading map` time.
