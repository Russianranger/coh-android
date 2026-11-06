# Thor test: COH Atlas Gameplay 0.13.57 (ARM64 client): King's Row arrival fix

In 0.13.56 the monorail took the hero to King's Row (loading screen at once,
King's Row ready in about 3½ minutes), then the session stopped about a minute
later. The app's own safety check still had a rule from the station-monorail
days: King's Row only counted as a supported zone with the station monorail
on. With the game's own travel it is off, so the check rejected the hero and
stopped everything (export 20261106-152038: "Reopen phase budget lacks the
current validated graphical character").

0.13.57:

- King's Row and every other zone the game's travel reaches count as
  supported zones, for the arrival, for saving there, and for the next login
  starting there;
- "Map loading, please wait..." no longer stays on screen after you arrive
  (the server's loading notice came after the loading screen had started, and
  nothing turned it off);
- when a third zone is asked for soon after a trip, the app first asks the
  database server where the hero is, so it never stops the zone server the hero
  is standing in (the game's log of an arrival reaches the app up to a minute
  late).

Everything else is 0.13.56: [THOR-TEST-0.13.56.md](THOR-TEST-0.13.56.md).
Evidence: [HANDOFF-X86.md](HANDOFF-X86.md), "0.13.57".

CI: build 42246645668, zone-trip runtime 42263546136, default runtime
42270379862 and trusted runtime 42276008129 passed at 8050afca8; APK
42281556221 published it. The zone-trip run took the game's own trip on CI
(instance 2 ready 182 s after the DbServer asked for it, hero in the new zone
352 s after the request, back to Atlas, save passed). CI's trip goes to a
second Atlas Park, not King's Row, and does not ask for a third zone, so **your
test is the first run of the King's Row and third-zone fixes**.

## Steps

1. Install 0.13.57 over 0.13.56, then tap **Set up / update runtime** once.
2. Reopen the hero with `Game's own zone travel` ticked. The hero may come
   back **in King's Row** (the 0.13.56 stop can have left them there): that is
   fine now; note where they start and how long it takes.
3. If you start in Atlas Park: take the monorail to King's Row (about 3–4
   minutes of loading screen the first time). Once there, check that no
   "Map loading" text remains and stay **at least 2 minutes** (the old crash
   came about a minute after arriving).
4. From King's Row take the monorail (or walk the tunnel) to a third zone, for
   example Steel Canyon or Skyway City: loading screen again, then the new
   zone (NPCs there will not move yet). Note the time.
5. Return to Atlas Park by monorail, or save/logout where you are (saving in
   King's Row or another zone is supported now). Finish and **export**.

If an error box appears, tap **Ignore** (not Stop Program), note what it says
and keep going; export at the end. If the game says a map failed, note which
one and try again after a minute.

## Report

The export, the loading-screen times, where the hero started, and anything
odd. Fields I will read: `character_zoning.stock_travel` (starts, arrivals,
`occupied_probes`, evictions), the zoning events, `character_session_budgets`
and the DbServer console.
