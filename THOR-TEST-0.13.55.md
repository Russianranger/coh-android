# Thor test: COH Atlas Gameplay 0.13.55 (ARM64 client): the game's own zone travel

0.13.55 replaces the station wait with the game's own zone travel, opens every
zone the game allows your hero, and moves the launcher options into a floating
button. Evidence: [HANDOFF-X86.md](HANDOFF-X86.md), "0.13.55";
design: [armport/notes/ON-DEMAND-ZONES.md](armport/notes/ON-DEMAND-ZONES.md).

## What changed since 0.13.54

| Change | Default | Expected effect |
|---|---|---|
| `Game's own zone travel (doors, tunnels, monorail; any zone)` | on | Taking a zone tunnel, a zone door or the monorail shows the loading screen at once; your hero leaves the world (frozen, untargetable, invincible) and appears in the new zone when it is ready. No more "Stay near the station". Untick to get 0.13.54's station travel back |
| Every zone | with the option | Any zone the game itself lets your hero enter: monorail stops, tunnels (Atlas Park ↔ Galaxy City, King's Row ↔ Skyway City, …) and zone doors. Missions and instanced maps are not yet served (the game says the map failed; you stay where you are) |
| Two zone servers | always | The zone you are in plus one more stay loaded (about 1.8 GB each). Going to a third zone stops the one you left before it |
| First start of a zone | once per zone server start | About 3–4 minutes on the loading screen (King's Row took 191 s in 0.13.54). The very first zone other than Atlas Park and King's Row also prepares the shared zone files once (about a minute more). The pre-loaded spare that brings this to about 1 minute is the next step |
| NPCs outside Atlas Park and King's Row | — | They spawn but stand still (no pathing data yet). Generating it for every zone is a later step |
| Floating options button | always | CONTROLS_SUMMARY |

CI: CI_SUMMARY

## Steps

1. Install 0.13.55 over 0.13.54, then tap **Set up / update runtime** once.
2. Reopen the hero in Atlas Park with `Game's own zone travel` ticked (default).
3. Take the monorail to King's Row: the loading screen should appear right
   after you pick the stop. Note how long it shows.
4. In King's Row, walk through the tunnel to Skyway City (or take the monorail
   to Steel Canyon): loading screen again, then the new zone (NPCs will not
   move there). Note the time.
5. Return to Atlas Park by monorail. Save/logout, Finish, **export**.
6. Optional: reopen once more. You start in the zone you saved in.

## Report

The export, the loading-screen times you noticed, and anything odd: a
loading screen that never ends (wait at least 6 minutes, then export), "map
failed" messages, a zone that looked wrong. Fields I will read:
`character_zoning.stock_travel` (requests, starts, stops, arrivals), the
supervisor's requests and decisions, `zone_tree_preparation`, and
`rss_kib`/`pss_kib` per server.
