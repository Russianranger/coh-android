# Solo Experience handoff

The *Solo Experience* changes rework City of Heroes for one player. Buffs and
rezzes that needed a teammate now work on yourself; task forces, strike forces
and trials can be run solo; and purchasable teammate bots fill out a team.

This is a reorganized version of the patch notes the user supplied on
2026-11-25 ("Patchnotes issue 1", Pages 1–9 plus 5v2). The
[original notes](#original-patch-notes) are kept word for word at the end. If
this summary and the original disagree, the original wins.

**Status in this repo (checked 2026-11-25):** the pinned `upstream/i24` data
does not appear to contain these changes. A search of its `data/defs` and
`data/texts` for names the notes introduce (Last Ditch, Calculated Risk,
Teammate Bot, SES-Store, P2W) found only unrelated text. Two things the notes
build on are partly there already:

- All four new origin pools have definition files:
  `upstream/i24/data/defs/powers/pool_experimentation.powers`,
  `pool_force_of_will.powers`, `pool_gadgetry.powers` and
  `pool_utility_belt.powers`.
- The Primalist has 17 `primalist_misc*` power-definition files in the same
  folder, but no class file: `upstream/i24/data/defs/classes.def` has the
  include commented out (`//include defs/classes/PC_Primalist.def`), and
  `PC_Primalist.def` is not in the data.

These haven't been compared with the Solo Experience versions. Read everything
below as a description of the Solo Experience, not of what this repo does today.

## Contents

- [How to read this](#how-to-read-this)
- [Patterns behind the changes](#patterns-behind-the-changes)
- [Watch out for](#watch-out-for)
- [Solo play support](#solo-play-support)
- [Archetypes and inherents](#archetypes-and-inherents)
- [Temp, affinity and travel powers](#temp-affinity-and-travel-powers)
- [Power pools](#power-pools)
- [Support sets](#support-sets)
- [Melee and armor sets](#melee-and-armor-sets)
- [Control and Mastermind sets](#control-and-mastermind-sets)
- [Epic and patron pools](#epic-and-patron-pools)
- [Incarnates and enhancement sets](#incarnates-and-enhancement-sets)
- [Incarnate trials](#incarnate-trials)
- [Client additions](#client-additions)
- [Bug fixes](#bug-fixes)
- [Patch index](#patch-index)
- [Original patch notes](#original-patch-notes)

## How to read this

- The notes shipped as sequential **pages**: 1, 2, 3, 4, 5, 5v2, 6, 7, 8, 9.
  Later pages override earlier ones. Tags such as **(P3)** give the page.
- The sections below give the state after Page 9. Where a power changed more
  than once, its entries are in page order and the last one wins.
- The [patch index](#patch-index) lists what each page touched.
- Terms:
  - **Self PBAoE**: a buff centered on the caster that covers the caster and
    anyone nearby, replacing a teammate-targeted buff.
  - **Self-rez**: a rez the caster uses on themself.
  - **Crash**: the penalty when a power such as Unstoppable or Rage ends.
  - **SES-Store**: the in-game store, called the **P2W vendor** before P9.
  - **Bots**: purchasable AI teammates.
  - **SE treatment**: the notes' phrase for converting a whole power set for
    solo play (used for Empathy in P9).
  - **Cooldown**: the notes use it to mean recharge time.

## Patterns behind the changes

These patterns repeat across the notes. Follow them when applying the same
approach to powers the notes don't cover.

1. **Teammate-targeted buffs become Self PBAoE**, or start including the caster
   (Shield Defense/Grant Cover). The notes give the reason: the PBAoE keeps
   team powers working if you still play multiplayer over LAN.
2. **Ally rezzes become self-rezzes**: Medicine/Resuscitate, Poison/Elixir of
   Life, Radiation Emission/Mutation, Thermal Radiation/Power of the Phoenix,
   Empathy/Resurrect. Pain Domination/Conduit of Pain became a self-buff
   instead, and Radiation Emission/Fallout became a PBAoE attack.
3. **Ally heals become PBAoE absorption buffs**: Empathy/Heal Other, Thermal
   Radiation/Cauterize, Pain Domination/Soothe.
4. **Mez-protection buffs become Self PBAoE with a 60 s cooldown and 5× the
   potency**: Empathy/Clear Mind, Sonic Resonance/Clarity, Pain
   Domination/Enforced Morale (all P9).
5. **Crashes are softened, usually by 50%, or removed.**
6. **Team-dependent bonuses apply solo**: the Kheldian inherent works without a
   team, and Phalanx Fighting acts as if 3 players are present.
7. **Group content is scaled for one player plus bots, not removed.** For the
   incarnate trials the author says they are meant to be played *with bots*:
   some archetypes can solo them, but that wasn't the balancing target.
8. **Long timers are cut**: temp-power and Kheldian cooldowns, Giant Monster
   spawn timers, travel-power restrictions.

## Watch out for

- **Power changes may need to reach the client.** P4 fixed a bug where the
  client ignored power changes; the notes cite the Brute Rage crash and target
  buffs. When changing a power, check that the client side picks it up too.
- **Places where the notes are ambiguous.** Check the data rather than guess:
  - *Invulnerability/Unstoppable*: P1 changed the crash from 100/90 to 75/50;
    P2 lists it again under "crash softened by 50%". The notes don't say
    whether P2 stacks on P1.
  - *Super Strength/Rage*: P6 set the crash to −45% endurance and −20% defense
    for 10 s and gave Scrappers only 50% of the damage bonus. P9 says Rage
    "got adjusted and its crash removed", without saying whether the Scrapper
    rule still applies.
  - *Force of Nature*: P2 softened its crash by 50% in Power Mastery and Field
    Mastery; P9 cut the Force Mastery version's crash from 100 to 50
    (recovery/endurance drop). It isn't stated whether these overlap.
  - *Prices*: P8 gives store prices as "10f" and "100f" without defining "f".
    P2 had priced Long Range Teleport at 1000 Inf.
  - *Elemental Control* (P4): "new Elemental Control Power for Controllers and
    Dominators", with no further detail.
  - *TPNC* (P9): "Reduced PO" is not explained.
- **Known issues** listed in P9: some power descriptions are wrong, some icon
  codings are wrong, and the Flashback TF has scaling issues.

## Solo play support

### Teammate bots

- Bought at the store (P3): Tank, Melee, Ranged, Support and Backup bots.
- More than one bot can be out at once (P4 fix).
- Controllable (P5v2).
- Summoning is a permanent power once bought; price cut to 100f (P8).
- Backup Bot Summon calls 3 bots (P9).
- Dismiss with `/releasepets`; bots zone with you until dismissed (P9).
- Team Teleport also moves bots (P9).
- Bots use the correct voice lines (P9 fix).

### SES-Store (formerly the P2W vendor)

- Revamped and renamed in P9. It can grant permanent buffs as auto powers:
  2 categories, 1 choice per category (P9).
- Long Range Teleport: added at 1000 Inf (P2), cut to 10f (P8), more
  destinations such as Ouroboros and Nova Praetoria (P9).
- Ouroboros Portal: 10f (P8).
- Teammate bots: see above.
- Envenomed Dagger: the store's version of the pool daggers. P8 buffed
  Experimentation/Toxic Dart and Utility Belt/Poisoned Dagger to compete with it.

### Group content

- All task forces and strike forces can be done solo (P3).
- Archvillains, heroes and Giant Monsters are scaled down "to a more
  reasonable level" (P3).
- Trials can be done solo (P5).
- Incarnate trials: level shift removed (54 → 50), some archvillains scaled
  from 54 to 50, plus per-trial changes (P9). See
  [Incarnate trials](#incarnate-trials).
- Forced level removed from Sewer and Bloody Bay, listed under Trials (P9).

### Contacts, missions and trainers

- All contacts give you their phone number on introduction (P6).
- All contacts scale up to level 50, so you can't outlevel them (P6).
- Indoor missions scale to your level: about 75% in P6 (Hero side further
  along than Villain), completed for Hero, Villain and Praetoria in P7.
- Ms. Liberty and Arbiter Richards train you remotely by phone (P9).

### Giant Monsters

Babbage, Eochai, Jack in Irons, Jurassik, Kraken, Lusca and Sally were on
6 h/36 h timers. They are now regular spawns; you just have to find them on
the map (P3).

## Archetypes and inherents

### Controller

- Pet at level 1; all other abilities move one level up (P1). P4 fixed
  Controllers not getting their powers when the pet was the level-1 pick.
- Second pet at level 26 (P9). Mind Control gets no second pet; Mass
  Confusion's cooldown is halved instead.
- New Elemental Control power, shared with Dominators (P4).

### Dominator

- Illusion Control proliferated to Dominators (P9).
- New Elemental Control power (P4).

### Tanker

- New inherent **Last Ditch** (P1): below 10% health, a large bonus to damage
  and to-hit.
- New inherent **Calculated Risk** (P9): sacrifice 85% of your health to
  trigger Last Ditch; you can't be healed for a while afterwards.
- All taunts add a 7% defense debuff (P9).
- All tier-2 powers gain Bruising (P9).
- Regeneration and Energy Aura proliferated to Tankers (P9).

### Scrapper

- Super Strength proliferated (P6), with Confront (a single-target ranged
  taunt) instead of Taunt. Scrappers get 50% of Rage's damage bonus (P6; see
  [Watch out for](#watch-out-for)).
- Energy Melee proliferated, with Confront instead of Taunt (P8).
- All Confront powers add a 3.5% to-hit debuff (P9).

### Defender

- Endurance discount that grows as health drops (P9).

### Mastermind

- Pet upgrade powers are all AoE (P9).
- Pets get a level bonus while standing close to the Mastermind (P9).
- Inherent gains a +5% defense bonus (P9).
- Pet-set power changes: see
  [Control and Mastermind sets](#control-and-mastermind-sets).

### Sentinel

- Opportunity: tier-1 damage bonus raised to 10%; the tier-2 buff gains 50%
  endurance recovery (P8).
- Ice Armor/Moisture Absorption range 10 → 50 (P9).

### Kheldians (Peacebringer and Warshade)

- Inherent bonus without needing a team (P1).
- Can take the opposite Kheldian's powers, making "WarBringers" and
  "PeaceShades" (P5). P6 fixed cross-power characters being unable to slot IOs.
- Powers reworked so a human-only build is viable while the shapeshifting
  playstyle still works (P8):

| Set | Power | Change (P8) |
|---|---|---|
| Luminous Blast | Inner Light | Cooldown 1.5 min → 1 min |
| Luminous Blast | Incandescent Strike | Cooldown 20 s → 10 s |
| Luminous Blast | Pulsar | Cooldown 45 s → 30 s |
| Luminous Blast | Glowing Touch | Now a PBAoE heal |
| Luminous Blast | Photon Seekers | Cooldown 3 min → 1 min |
| Luminous Blast | Dawn Strike | Cooldown 2 min → 1 min |
| Luminous Aura | Essence Boost | Cooldown 6 min → 3 min |
| Luminous Aura | Conserve Energy | Cooldown 10 min → 3 min |
| Luminous Aura | Quantum Flight | Cooldown down to 30 s; stealth raised |
| Luminous Aura | Light Form | Crash halved; cooldown reduced to 5 min |
| Umbral Blast | Sunless Mire | Cooldown 2 min → 45 s |
| Umbral Blast | Gravity Well | Now ranged (40 ft); cooldown 20 s → 10 s |
| Umbral Blast | Essence Drain | Now ranged (40 ft) |
| Umbral Blast | Dark Extraction | Cooldown 5 min → 2 min |
| Umbral Blast | Quasar | Cooldown 2 min → 1 min |
| Umbral Aura | Orbiting Death | Endurance cost −30% |
| Umbral Aura | Eclipse | Cooldown 6 min → 3 min |

### Primalist (new archetype, P5)

A melee archetype that shapeshifts into a Hunter or a Prowler. In primal form
it deals good damage and heals nearby allies; in Hunter form it attacks with
tooth and claw and weakens nearby foes; in Prowler form it shreds enemies and
stuns them.

P5v2 changes:

- Own archetype icon.
- Rage-meter bar added for managing Primal Energy.
- Primal Energy gain and loss rebalanced.
- Hunter form is now a Direwolf.
- Call of the Wild: permanent, controllable, accepts pet IOs.
- Hunter's Howl cooldown reduced to 2 min; Pack Frenzy to 1 min.
- Upheaval radius doubled.
- Rejuvenate builds Primal Energy, as its description says.

P8 fixed the Primalist stopping resource generation. The partial Primalist
files in the pinned data are described in the status note at the top.

## Temp, affinity and travel powers

- Mission, base and Pocket D transporters: cooldown 30 s (P1).
- Return to Battle and Renewal of Light: cooldown 5 min (P1); both can be
  owned at the same time (P5).
- Recovery Serum and Inner Inspiration: cooldown 5 min (P5).
- Temp powers work in restricted missions such as incarnate trials (P9).
- Affinity powers: granted the moment you switch sides, all with a 1-min
  cooldown (P1).
- Travel: exclusivity removed from the Fly, Jump and Speed travel powers (P6);
  30-second timer removed from the prestige jump (P6); Sprint costs no
  endurance (P9).
- Long Range Teleport and the Ouroboros Portal: see
  [SES-Store](#ses-store-formerly-the-p2w-vendor).

## Power pools

### Existing pools

- Leadership/Vengeance targets a foe instead of a teammate; the same goes for
  the VEAT version (P1).
- Medicine/Aid Self can be taken without another power first (P1).
- Medicine/Resuscitate is a self-rez (P1).
- Sorcery/Spirit Ward targets self instead of a teammate (P1), then became a
  self toggle (P6).
- All pools: prerequisite-power requirements removed; level requirements still
  apply (P6).

### New origin pools (P1)

Experimentation, Force of Will, Gadgetry and Utility Belt were added in P1.
The effect column is as listed in P1; the last column gives later changes.

#### Experimentation

| Power | Effect | Later changes |
|---|---|---|
| Experimental Injection | Ranged (close), ally +Regen, +Recovery, +Res(Status) | Recharge extended to 3 min (P3) |
| Toxic Dart | Ranged, minor Lethal and high Toxic damage | Adds −Regen (P2); −Regen and its duration doubled (P8) |
| Speed of Sound | Toggle: self +Speed, special | — |
| Jaunt | Click: self teleport | — |
| Corrosive Vial | Ranged (targeted AoE), high Toxic DoT, foe −Def | Now location-targeted, "as originally intended" (P9) |
| Adrenal Booster | Self +ToHit, +Recharge, +Damage, special | Recharge extended to 5 min (P3); alternative FX for players who dislike the injection animation (P8) |

#### Force of Will

| Power | Effect | Later changes |
|---|---|---|
| Weaken Resolve | Ranged, foe −Res, −Def, −ToHit | Effect amplified (P9) |
| Project Will | Ranged, moderate Psi/Smashing damage, foe knockdown | — |
| Mighty Leap | Toggle: self long jump, special | — |
| Stomp | PBAoE, foe knockdown | — |
| Wall of Force | Ranged cone, moderate Psi/Smashing damage, foe knockdown | — |
| Unleash Potential | Self +Regen, +Recovery, +Def | — |

#### Gadgetry

| Power | Effect | Later changes |
|---|---|---|
| Nano Web | Ranged, foe −Speed, −Recharge, −Fly, −Regen | — |
| Energy Blast | Ranged, moderate Energy damage, foe −Regen | — |
| Jetpack | Toggle: self Fly (special) | — |
| Turbo Boost | Click: self +Fly speed | — |
| Nano Energy Barrage | Ranged cone, moderate Energy damage, foe −Regen | — |
| Force Barrier | Self +Absorb | — |

#### Utility Belt

| Power | Effect | Later changes |
|---|---|---|
| Bolas | Ranged, foe Immobilize, knockdown | — |
| Poisoned Dagger | Ranged, moderate Lethal damage, foe light Toxic DoT, −Damage | Adds −Regen (P2); −Regen and its duration doubled (P8) |
| Freerunning | Toggle: self +Jump, +Run speed, special | — |
| Athletics | Click: self +Run speed, +Jump | — |
| Toxic Oil | Ranged cone, moderate Lethal damage, foe light Toxic DoT, −Damage | — |
| Life Support System | Self +HP, heal over time, special | — |

The P8 dagger buffs were meant to make the pool powers competitive with the
store's Envenomed Dagger.

## Support sets

### Converted to Self PBAoE buffs (P1 unless noted)

| Set | Powers |
|---|---|
| Kinetics | Increase Density, Speed Boost |
| Time Manipulation | Temporal Selection |
| Cold Domination | Ice Shield, Glacial Shield; Frostwork became a PBAoE buff in P4 |
| Force Field | Deflection Shield, Insulation Shield |
| Poison | Alkaloid, Antidote |
| Sonic Resonance | Sonic Barrier, Sonic Haven, Clarity |
| Storm Summoning | O2 Boost |
| Thermal Radiation | Fire Shield, Plasma Shield, Thaw, Forge |

### Converted to self-rez (P1)

Poison/Elixir of Life, Radiation Emission/Mutation, Thermal Radiation/Power of
the Phoenix.

### Set-by-set changes

- **Radiation Emission**: Fallout is a PBAoE attack (P1).
- **Sonic Resonance**: Disruption Field and Sonic Repulsion target self instead
  of a teammate (P1). Clarity gets a 60 s cooldown and is 5× more potent (P9).
- **Empathy** (P9, "the SE treatment"):
  - Heal Other → PBAoE absorption buff.
  - Absorb Pain → a "Self Moderate Damage (Special) Buff".
  - Resurrect → Resurrect Self.
  - Clear Mind → Self PBAoE, 60 s cooldown, 5× more potent.
  - Fortitude → PBAoE.
  - Recovery Aura and Regeneration Aura → recharge reduced to 2 min.
  - Adrenalin Boost → self-targeted PBAoE, recharge reduced to 2 min.
- **Force Field** (P9): Personal Force Field loses its "self only" limit, and
  its bonus is lowered by 33%. Force Bolt does a bit more damage.
- **Thermal Radiation** (P9): Cauterize → PBAoE absorption buff.
- **Pain Domination**:
  - Share Pain → PBAoE buff without the healing (P8).
  - Conduit of Pain → no longer a rez; extracts power from defeated enemies
    to buff the user (P8). Crash reduced by 50% (P9).
  - Enforced Morale → PBAoE instead of ally-targeted (P8), then Self PBAoE
    with a 60 s cooldown and 5× potency (P9).
  - Painbringer → PBAoE instead of ally-targeted (P8).
  - Soothe → PBAoE absorption buff (P9).

## Melee and armor sets

- **Super Strength**
  - Rage: damage handicap removed and crash softened (P1); P4 fixed the client
    ignoring the Brute Rage crash; crash set to −45% endurance and −20%
    defense for 10 s, with Scrappers getting 50% of the damage bonus (P6);
    "adjusted" and crash removed (P9).
  - Hand Clap does minor Smashing damage (P9).
  - The Scrapper version uses Confront instead of Taunt (P6).
- **Energy Melee**: the Scrapper version uses Confront instead of Taunt (P8).
- **Titan Weapons**: Momentum reworked to compensate for early loss (P3).
- **Invulnerability**: Unstoppable's crash changed from 100/90 to 75/50 (P1),
  and listed again in P2's 50% crash softening (see
  [Watch out for](#watch-out-for)).
- **Regeneration**: Instant Healing is a toggle again (P1); animation loops in
  Regeneration toggles fixed (P8); proliferated to Tankers (P9).
- **Shield Defense**: Grant Cover includes the caster (P1); One with the
  Shield's crash softened by 50% (P2); Phalanx Fighting applies its bonus as
  if 3 players are present (P9).
- **Energy Aura**: Overload's crash softened by 50% (P2); proliferated to
  Tankers (P9).
- **Crash softened by 50% (P2)** also for Ninjitsu/Kuji-In Retsu, Super
  Reflexes/Elude, Willpower/Strength of Will, Electric Armor/Power Surge and
  Widow Teamwork/Elude.
- **Ice Armor (Sentinel)**: Moisture Absorption range 10 → 50 (P9).

## Control and Mastermind sets

- **Electric Control**: Jolting Chain accepts AT and Immobilize enhancements
  (P9).
- **Illusion Control**: proliferated to Dominators (P9).
- **Mind Control**: Mass Confusion's cooldown halved, in place of the second
  Controller pet (P9).
- **Elemental Control**: new power for Controllers and Dominators (P4).
- **Mastermind primaries**, now PBAoE (P9): Ninja Summoning/Smoke Flash,
  Mercenaries/Serum, Necromancy/Soul Extraction, Demon Summoning/Hell on Earth.

## Epic and patron pools

- Surge of Power (Electrical Mastery, Charge Mastery, Mu Mastery): crash
  softened by 50% (P2).
- Force of Nature (Power Mastery, Field Mastery): crash softened by 50% (P2).
- Force Mastery/Personal Force Field: "self only" limit removed, bonus lowered
  by 33% (P9).
- Force Mastery/Force of Nature: crash cut from 100 to 50 recovery/endurance
  drop (P9).

## Incarnates and enhancement sets

- Hybrid incarnate powers (Assault, Control, Melee, Support) are full toggles
  but cost endurance (P8).
- Celerity enhancement set: Translucency FX removed (P9).

## Incarnate trials

All changes are from P9. Across all trials, the level shift is removed (54 →
50) and some archvillains are scaled from 54 to 50. The trials are meant to be
played with bots; add or remove bots to set the difficulty.

| Trial | Changes |
|---|---|
| BAF | Riot phase: kills 40 → 20. Suppression and Siege phases: fewer guard towers, doing less damage. Escape phase: survive for 3 min; fail state moved from 20 to 50. Siege and Nightstar phase: kill time limit removed. |
| Lambda | Phase 1: defeat 30 IDF instead of 60. Marauder: reinforcement waves reduced to 3. |
| Keyes Island | Power cells hold 3 charges, so 6 are needed per core instead of 18. Anti-Matter arrives after 4–6 min depending on phase (was 1 min), no longer uses Disintegration, has more solo-friendly ability timers, and has one heal phase at 50% instead of three (one every 33%). Time limit 12 → 30 min. |
| Underground | No changes: an endurance trial, not particularly hard. |
| TPNC | "Reduced PO": done right, you only have to get into the building once. |
| Minds of Mayhem | Mother Mayhem's Psionic_Suffering disabled. Penelope Yin always takes damage, not only inside the vortex. Final encounter: 1 phase instead of 3. |
| Dilemma Diabolique | No changes: an endurance trial, not particularly hard. |
| Magisterium | IDF count 250 → 50. |

## Client additions

Added in P6:

- Vidiotmaps (by AboveTheChemist)
- Better inspiration icons (by rcarmin)
- Power Icon Pack (by Vanden)
- Higher-visibility mouse cursor (by Koopak)

## Bug fixes

- **P4**: Controllers not getting their powers when the pet was the level-1
  pick; the client ignoring power changes (Brute Rage crash, target buffs);
  only one teammate bot callable at a time; the mapserver freezing when maps
  loaded after creating a new character.
- **P6**: Kheldians with cross powers couldn't slot IOs.
- **P8**: animation loops in Regeneration toggles; taunts that did nothing;
  endurance regen that could be doubled indefinitely; sound loops in several
  powers; the Primalist stopping resource generation.
- **P9**: 50+ icons; bots' voice lines.

## Patch index

| Page | What it touched |
|---|---|
| 1 | Controller pets at level 1; Kheldian inherent without a team; Tanker Last Ditch; temp and affinity cooldowns; four new origin pools; teammate buffs → Self PBAoE; ally rezzes → self-rez; Rage, Unstoppable, Instant Healing, Grant Cover |
| 2 | Long Range Teleport in the store; −Regen on Toxic Dart and Poisoned Dagger; 50% crash softening for armor and epic powers |
| 3 | Solo task and strike forces; archvillain, hero and Giant Monster scaling; teammate bots; Giant Monster timers removed; Experimentation recharges; Titan Weapons Momentum |
| 4 | Frostwork; Elemental Control power; fixes for Controller pets, client power changes, multiple bots and the mapserver freeze |
| 5 | Kheldian cross powers; Primalist archetype; temp-power cooldowns; solo trials |
| 5v2 | Primalist rework; controllable bots |
| 6 | Client additions; pool prerequisites and travel exclusivity removed; contacts; mission scaling (about 75%); Scrapper Super Strength; Rage crash; Kheldian IO fix |
| 7 | Mission scaling completed for Hero, Villain and Praetoria |
| 8 | Store prices and Ouroboros Portal; permanent bot summon; Sentinel Opportunity; dagger buffs; Hybrid toggles; Pain Domination; Scrapper Energy Melee; Kheldian rework; bug fixes |
| 9 | Bot quality of life; SES-Store; Tanker Calculated Risk; Defender, Controller, Scrapper and Mastermind changes; proliferation; Empathy and other set changes; incarnate trial rebalance; known issues |

## Original patch notes

As supplied by the user, word for word.

<details>
<summary>Show the original notes</summary>

```text
Patchnotes issue 1

____________________Page 1:

AT Changes
-Controllers get their Pets at Lvl1, all other abilities move one lvl up.

Inherent Powers
-Peacebringer and Warshades get their Inherent Bonus without the need of a Group
-Tankers got a new inherent power called "LastDitch", if the Tanker is about to die (less than 10% health) he gets an immense bonus to dmg and toHit as a last ditch effort to win the battle

Temp Powers
-Transporter for Missions, Base and Pocket D got their cooldowns reduced to 30sec
-Return to Battle and Renewal of Light got their cooldowns reduced to 5min

Affinity Powers
-All affinity powers are now granted the moment you switch sides and all have now a cooldowns of 1min

Pool Powers
-Leadership/Vengence has now target Foe instead of Teammate (same goes for the VEAT Power)
-Medicine/Aid Self can now be selected without taking another power first
-Medicine/Resucitate is now a selfrez
-Sorcery/Spirit Ward is now target self instead of Teammate
-Pools "Experimentation", "Force of Will", "Gadgetry" and "Utility Belt" added

Experimentation                         Effect
Experimental Injection       Ranged (Close), Ally +Regen, +Rec, +Res(Status)
Toxic Dart                            Ranged, Minor DMG(Lethal), High DMG(Toxic)
Speed of Sound                  Toggle: Self +Speed, Special
Jaunt                                    Click, Self Teleport
Corrosive Vial                      Ranged (Targeted AoE), High DoT(Toxic), Foe -Def
Adrenal Booster                  Self +To Hit, +Rech, +DMG, +Special

Force_of_Will                              Effect
Weaken Resolve                 Ranged, Foe -Res, -Def, -To Hit
Project Will                          Ranged, Moderate DMG(Psi/Smash), Foe Knockdown
Mighty Leap                        Toggle: Self Long Jump, Special
Stomp                                  PBAoE, Foe Knockdown
Wall of Force                       Ranged (Cone), Moderate DMG(Psi/Smash), Foe Knockdown
Unleash Potential               Self +Regen, +Rec, +Def

Gadgetry                                      Effect
Nano Web                            Ranged, Foe -Speed, -Recharge, -Fly, -Regen
Energy Blast        Ranged, Moderate DMG(Energy), Foe -Regen
Jetpack                                Toggle: Self Fly, (Special)
Turbo Boost                        Click, Self +Fly Speed
Nano Energy Barrage         Ranged Cone, Moderate DMG(Energy), Foe -Regen
Force Barrier                       Self, +Absorb

Utility_Belt                                    Effect
Bolas                                    Ranged, Foe Immobilize, Knockdown
Poisoned Dagger                Ranged, Moderate DMG(Lethal), Foe Light DoT(Toxic), -DMG
Freerunning                         Toggle: Self, +Jump, +Run Speed, +Special
Athletics                               Click, Self +Run Speed, +Jump
Toxic Oil                               Ranged(Cone), Moderate DMG(Lethal), Foe Light DoT(Toxic), -DMG
Life Support System           Self, +HP, +Heal Over Time, +Special

Buff/DeBuff Powers
following skills are now Self PBAoE buffs instead of Teammate buffs. (the PBAoE effect is so you could still play MP in LAN if you wanted without loosing teamskills)
-Kinetic/Increase Density
-Kinetic/Speed Boost
-Time Manipulation/Temporal Selection
-Cold Domination/Ice Shield
-Cold Domination/Glacial Shield
-Force Field/Deflection Shield
-Force Field/Insulation Shield
-Poison/Alkaloid
-Poison/Antidote
-Sonic Resonance/Sonic Barrier
-Sonic Resonance/Sonic Haven
-Sonic Resonance/Clarity
-Storm Summoning/O2 Boost
-Thermal Radiation/Fire Shield
-Thermal Radiation/Plasma Shield
-Thermal Radiation/Thaw
-Thermal Radiation/Forge

following skills are now selfrez
-Poison/Elixir of Life
-Radiation Emission/Mutation
-Thermal Radiation/Power of the Phoenix

other changes to buff/debuff
-Radiation Emission/Fallout is now a PBAoE attack
-Sonic Resonance/Disruption Field is now target self instead of Teammate
-Sonic Resonance/Sonic Repulsion is now target self instead of Teammate

Melee Pools
-Super Strength/Rage removed the dmg handicap and softened crash

Defense Powers
-Invulnerability/Unstoppable softened crash from 100/90 to 75/50
-Regeneration/Instant Healing is is a toggle again
-Shield Defense/Grant Cover includes now self

____________________Page 2:

Pool Powers
-Long Range Teleport is now available at the P2W vendor for 1000 Inf
-Experimentation/Toxic Dart does now -Reg
-Utility Belt/Poisoned Dagger does now -Reg

Epic and Patron Powers
-Electrical Mastery/Charge Mastery/Mu Mastery/Surge of Power have their crash softened by 50%
-Power Mastery/Field Mastery/Force of Nature have their crash softened by 50%

Defense Powers
Following Powers have their crash softened by 50%
Invulnerability/Unstoppable
Shield Defense/One with the Shield
Ninjitsu/Kuji-In Retsu
Energy Aura/Overload
Super Reflexes/Elude
Willpower/Strenght of Will
Electric Armor/Power Surge
Widow Teamwork/Elude

____________________Page 3

Mechanics
All Task Forces/Strike Forces can now be done solo
Archvillains/Heroes and Giant Monsters are scaled down to a more reasonable level

Addition for SoloPlay
You can buy Teammate Bots at the P2W vendor (Tank/Melee/Ranged/Support/Backup)

Spawns
Giant Monsters who where on a 6h/36h timer (Babbage/Eochai/Jack in Irons/Jurrasik/Kraken/Lusca/Sally) are now regular spawns, you just have to find them on the map ;-)

Pool Powers
-Experimentation/Experimental Injection got its Recharge timer extended to 3m
-Experimentation/Aderal Booster got its Recharge timer extended to 5m

Melee Sets
-Titan Weapons / reworked momentum to compensate for early loss

____________________Page 4

-Changed Cold Domination/Frostwork to PBAoE buff
-fixed bug where Controller AT would not get their powers when the Pet is selected as lvl1 skill
-fixed bug where skill changes would be ignored by the client (Brute Rage crash/Target Buffs)
-fixed bug where only one TeammateBot could be called at a time
-fixes bug where loading maps after creating a new character would freeze the mapserver
-new Elemental Control Power for Controllers and Dominators

____________________Page 5

Archetypes

-Kheldians can now select the opposite powers, make WarBringers and PeaceShades
-new AT, the Primalist
Primalists are competent melee combatants, this is enhanced by their ability to shapeshift into a Hunter or a Prowler. While in primal form, the Primalist will deal good damage and heal nearby allies. In Hunter form you can attack foes with tooth and claw and weaken nearby foes and in Prowler form you can shred enemies and stun them.

Temp Powers

-"Renewal of Light" and "Return to Battle" can now be acquired at the same time
-Recovery Serum has its cooldown reduced to 5m
-Inner Inspiration has its cooldown reduced to 5m

Mechanics

-Trials can now be done Solo

____________________Page 5v2

Primalist

Primalist has now his own icon
added Ragemeter Bar to better manage your Primal Energy
balanced Primal energy gain/loss
Hunterform is now a Direwolf
Call of the Wild is now permanent, controllable and accepts Pet IOs
Hunters Howl cooldown reduced to 2min
Pack Frenzy cooldown reduced to 1min
Upheaval radius doubled
Rejuvenate now builds Primal Energy (as stated in the description)

Temp Powers

Teammember bots are now controllable

____________________Page 6

Client
added vidiotmaps (by AboveTheChemist)
added better Icons for Inspirations (by rcarmin)
added Power Icon Pack (by Vanden)
added higher visibility mouse cursor (by Koopak)

Pool Powers
removed precursor buy requires for pool powers, level requires are still in place
removed exclusivity toggle from travel powers (fly, jump, speed)
removed 30sec timer on prestige jump
Sorcery/Spirit Ward is now a Self/Toggle

Mechanics
all contacts are now more trusting and give your their phone number on introduction
all contacts scale up to lvl50, you won't outlevel them anymore
around 75% of all indoor missions scale now to your level. (Hero side is more complete than Villain / rest will follow in future updates)

Archetypes
Scrapper now have access to Super Strength 

Powers
Super Strength/Rage got further tweaked (-45% end and -20% def for 10sec on crash/ Scrappers only get 50% of the dmg bonus)
Super Strength/Confront Scrappers get Confront instead of Taunt, which is a single target ranged taunt

Bug Fixes
Fixes a bug where Kheldians with CrossPowers can't slot IO's

____________________Page 7

completed indoor mission scaling for Hero, Villain and Pretoria

____________________Page 8

QoL
Ouroboros Portal was added to the P2W-Vendor for 10f
Long Range Teleporter got its Price down to 10f
Summoning Bots is now a Permanent Skill once bought (price also reduced to 100f)

Inherent Powers
Sentinals Opportunity got buffed: Tier1 dmg Bonus went up to 10%; The Tier 2 buff got a 50% EndRecovery

PoolPowers
Experimental/Toxic Dart doubled his -reg DeBuff and duration to make it more usable in regards to the P2W version (Envenomed Dagger)
Experimental/Adrenal Booster got an alternative FX (for those who dislike the injection animation)
Utility Belt/Poisoned Dagger doubled his -reg DeBuff and duration to make it more usable in regards to the P2W version (Envenomed Dagger)

Incarnate Powers
Hybrid Incarnates (Assault/Control/Melee/Support) Are now full Toggles, but cost Endurance

Archetype Powers
Pain Domination/Share Pain - Is now a PBAoE Buff without the Healing
Pain Domination/Conduit of Pain - Now Extracts Power from defeated Enemies to Buff the User (no longer a Rez) 
Pain Domination/Enforce Morale - Is now a PBAoE instead of TargetAlly
Pain Domination/Painbringer -  Is now a PBAoE instead of TargetAlly

Power proliferation
Scrappers can now learn Energy Melee, Taunt was exchanged for Confront

Kheldians
Kheldians got there Powerpools reworked. HumanOnly Form is now viable while also keeping the Shapeshifter playstyle.
Luminous Blast/Inner Light - cooldown down from 1.5m to 1m
Luminous Blast/Incandescent Strike -  cooldown down from 20s to 10s
Luminous Blast/Pulsar -  cooldown down from 45s to 30s
Luminous Blast/Glowing Touch is now a PBAoE Heal
Luminous Blast/Photon Seekers -  cooldown down from 3m to 1m
Luminous Blast/Dawn Strike -  cooldown down from 2m to 1m
Luminous Aura/Essence Boost - cooldown down from 6m to 3m
Luminous Aura/Conserve Energy - cooldown down from 10m to 3m
Luminous Aura/Quantum Flight - cooldown down to 30s; raised stealth
Luminous Aura/Light Form - crash after use is halved and the cooldown was reduced to 5m
Umbral Blast/Sunless Mire -  cooldown down from 2m to 45s
Umbral Blast/Gravity Well -  this is now a Ranged skill with 40ft; cooldown down from 20s to 10s
Umbral Blast/Essence Drain -  this is now a Ranged skill with 40ft
Umbral Blast/Dark Extraction -  cooldown down from 5m to 2m
Umbral Blast/Quasar -  cooldown down from 2m to 1m
Umbral Aura/Orbiting Death - endurance cost reduced by 30%
Umbral Aura/Eclipse -  cooldown down from 6m to 3m

Bugfixes
Fixed Animation loops in Regeneration toggles
Fixed Bug where a Taunt would do nothing
Fixed Bug that lets you double you eng reggen indefinitely
Fixed Soundloops in several Skills
Fixed Bug where the Primalist would stop resource generation

____________________Page 9

QoL
Backup Bot Summon now summons 3 Bots
Bots can now be dismissed - /releasepets
Bots will now zone with you till dismissed
Ms Liberty and Arbiter Richards got a new Phone an are willing to train you remotely
TempPowers are now usable in restricted Missions like Incarnate Trials
The P2W-Vendor got a Revamp and is now the SES-Store
The SES-Store can now provide permanent Buffs as autopowers, there are 2 categories and you can choose 1 per category
Long-Range-Teleport now has more destinations like Ouroboros or Nova Pretoria
Team-Teleport now also teleports Bots
Sprint does no longer cost endurance

Archetypes
Tanker got a new Inherent ability called "Calculated Risk", with this power the Tanker sacrifices 85% of his health to trigger his Last Ditch inherent, but he can't be healed for a while after using it.
All Tanker Taunts got an 7% Defence deBuff
All Tanker Tier 2 powers got access to bruising
All Scrapper Confront powers got a 3.5% toHit deBuff
Defender gets an endurance discount depending on his health (less health, more discount)
All Controllers get a second Pet at lvl 26, except for Mind Control here is the cooldown for Mass Confusion cut in half
Masterminds Pet Upgrade powers are all AoE effects now
Mastermind Pets gain a level bonus as long as they are standing close to him.
Mastermind Inherent got a 5% +def bonus added

Powersets-Proliferation
Regeneration is now available for Tankers
Energy Aura is now available for Tankers
Illusion Control is now available for Dominators

Powersets
Empathy got the SE-Treatment
Heal Other got converted to a PBAoE Absorption Buff
Absorb Pain is now a Self Moderate Damage (Special) Buff
Resurrect Ally is now Resurrect Self
Clear Mind changed to Self PBAoE whith a 60sec cooldown, but also is 5x more potent
Fortitude is now a PBAoE
Recovery Aura got reduced recharge to 2m
Regeneration Aura got reduced recharge to 2m
Adrenaline Boost is now SelfTarget PBAoE with reduced recharge to 2m

Force Field
Personal Force Field got its "self only limit" removed and it's bonus lowerd by 33%
Force Bolt does a bit more DMG

Sonic Resonance
Clarity changed to Self PBAoE whith a 60sec cooldown, but also is 5x more potent

Thermal Radiation
Cauterize got converted to a PBAoE Absorption Buff

Pain Domination
Soothe got converted to a PBAoE Absorption Buff
Conduit of Pain got it's crash down by 50%
Enforced Morale changed to Self PBAoE whith a 60sec cooldown, but also is 5x more potent

Super Strength
Hand Clap got minor Smashing Damage
Rage got adjusted and its crash removed

Shield Defense
Phalanx Fighting now automatically applies Bonus as if 3 Players are present

Ice Armor / Sentinels
Moisture Absorption got it's Range increased from 10 to 50

Electric Control
Jolting Chain now accepts AT- and Immo-enhancements boosts

Ninja Summoning
Smoke Flash is a PBAoE power now

Mercenaries
Serum is a PBAoE power now

Necromancy
Soul Extraction is a PBAoE power now

Demon Summoning
Hell on Earth is a PBAoE power now

PoolPowers
Force of Will/Weaken Resolve has its effect amplified
Experimentation/Corrosive Vial is now a location target, as originally intended

Epic Powers
Force Mastery/Personal Force Field - removed self only limit, bonus lowerd by 33%
Force Mastery/Force of Nature - Crash down from 100 to 50 rec/end down

Boostsets
Celerity - Removed Translucency fx (i just hate it)

Trials
Removed ForcedLevel from Sewer and BloodyBay

Incarnate Trials
All Trials: Removes Level Shift from 54 to 50; Scaled down some ArchVillains from 54 to 50.
keep in mind that these trials are supposed to be played with bots.
Depending on your archetype, some can be done completely solo, but this was not my intent for balancing. 
Add or Remove Bots till you archive the difficulty you desire.

BAF 
Riot-Phase: Kills down from 40 to 20
Supression-Phase: Guard Towers reduced Damage and count
Escape-Phase: Time to survive down to 3Min, Failstate moved up from 20 to 50
Siege-Phase: Guard Towers reduced Damage and count
SiegeAndNightstar-Phase: Removed Kill-Time-Limit

Lambda
Phase 1: Defeat IDF Down from 60 to 30
Marauder Reduced Reinforcement Waves to 3

Keyes Island 
PowerCell now has 3 charges so only 6 instead of 18 are needed per core
Anti-Matter arrive time up from 1 to 4-6m depending on phase
Anti-Matter no longer uses Disintegration
Time-Limit up from 12 to 30Min
Adjusted Anti-Matters ability timers to be more solo friendly
Anti-Matter only has 1 healphase at 50% instead of three every 33%

The Underground
No changes, this is an endurance trial and not particularly hard

TPNC 
Reduced PO, if done right you only have to get into the building once

Minds of Mayhem
Disabled Psionic_Suffering from Mother Mayhem
Penelope Yin is always takes damage, not only inside the vortex
reduced phases in the final encounter from 3 to 1

Dilemma Diabolique
Phase no changes, this is an endurance trial and not particularly hard

Magistarium
IDF count from 250 to 50

Bug Fixes
About 50+ Icons
Bots now have the correct voicelines

Known Issues
Some Skill descriptions are wrong
Some Iconscodings are wrong
Scaling issues in Flashback TF
```

</details>
