# JXP 0.24.0 Daimyo And Final-Tag Mission Expansion

Date: 2026-07-09

## Player Report

The daimyo-stage tree had only eleven JXP missions in slots 1-3 and relied on
seven vanilla generic missions to fill slots 4-5. Its five house identities
were represented by only three missions each. Formed Japan also retained
generic fallback columns in the uncommitted state, the Sakoku route, and the
Ikko end tag.

## Root Cause

EU4 selects non-generic mission series by whole slot. It then inserts eligible
`generic = yes` series only into slots left completely unoccupied. Disabling
the original Japanese trees did not disable generic administrative or Asian
missions. Any JXP profile that owned fewer than all five slots therefore
received a mixed custom/generic tree even though its custom potentials were
otherwise correct.

## Daimyo Reconstruction

- All 37 supported daimyo tags now activate exactly five custom series.
- Each active daimyo tree contains 30 missions across a staggered five-column
  layout:
  - slot 1: domain law, survey, castle town, household government;
  - slot 2: roads, merchants, artisan guilds, firearms, foreign learning;
  - slot 3: one of five six-mission house traditions;
  - slot 4: village compacts, irrigation, magistrates, schools, reserves;
  - slot 5: banner raising, regional command, Kyoto, unification strategy.
- The visible grid alternates odd and even rows. Every diagonal joins adjacent
  columns on the immediately following row; vertical edges span no more than
  two rows. The effective renderer check reports ten cross-column edges, six
  merges, and ten forks for every daimyo profile.
- Landlocked daimyo are no longer blocked by a mandatory port at the opening
  of the tree. Maritime requirements are reserved for genuinely maritime
  house and late contact missions.

## House Identity And Choice

The five house families now have six missions each:

- warrior: muster rolls, war council, castle roads, firearm drill, commander
  oaths, banner law;
- court: genealogies, rank petitions, mediator networks, Kinri escort, Kanrei
  legacy;
- maritime: port registers, harbor council, shipwrights, atakebune, tide
  brokers, strait law;
- frontier: passes, border council, markets, guides, hostages, border oaths;
- temple-market: ledgers, temple-town council, free markets, debt arbitration,
  public law.

The existing low-frequency house-agenda events are also called from the first
house mission when they have not already occurred. Each option records a
persistent choice flag, and later missions react to that choice. The final
daimyo mission opens `jxp_daimyo.5`, a three-way decision between military
conquest, an imperial edict, and a league of lords. The selected founding
method leaves a modest permanent legacy after unified Japan completes
`jxp_mission_route_inherited_realm`.

## Final-Tag Completion

- Uncommitted `JAP` receives temporary council and horizon series in slots 3
  and 5 while it prepares the route choice.
- Sakoku `JAP` receives a seven-mission controlled-frontier series covering
  coastal magistrates, Matsumae, Tsushima, Ryukyu, beacon stations, and the
  permitted Dutch-learning window.
- `IJP` receives a seven-mission communal-economy series covering temple
  granaries, debt relief, pilgrim roads, commoner schools, guild councils,
  communal shipyards, and the fellowship state.
- Every validated daimyo and unified profile now has zero active generic
  fallback cells.

## Save Migration

Hidden event `jxp_migration_v023.5` runs once for Japanese polities that lack
`jxp_mission_expansion_migration_v024`.

- It schedules the standard delayed mission refresh.
- It reconstructs the new house-completion flag from old completed mission
  IDs.
- It supplies deterministic agenda-choice defaults for old saves that had
  already seen an agenda before option flags existed.
- It schedules the appropriate agenda for a daimyo whose earlier mission was
  already complete but whose agenda had not fired.

## Validation Hardening

- `missions.py` now requires every one of 47 profile states to occupy custom
  slots 1-5.
- `effective_topology.py` treats any active vanilla generic fallback series as
  a release-blocking error.
- Profile coverage expanded from five representative daimyo to all 37
  supported tags plus ten formed-Japan states.
- Mission-refresh validation requires the 0.24.0 migration flag.
- Original effect names were checked against EU4 1.37.5; the valid reform
  progress effect is `change_government_reform_progress`.

## Validation

- Descriptor version: `0.24.0`.
- General EU4 validator: pass.
- JXP release checks: 11/11 pass.
- Clausewitz gameplay files: 169/169 parse.
- Missions: 238 IDs in 34 custom series.
- Profiles: 47/47 have five custom slots and zero generic fallback.
- Active localisation: 56 UTF-8-BOM files, zero raw CJK.
- Unit tests: 31/31 pass.
- EU4 was not launched, in accordance with the active user instruction.

## Player-Side Test

On the next normal launch, test one tag from each house family: ODA, ASK, OTM,
DTE, and IMG. An old save should be advanced one day before opening missions.
Then verify formed `JAP` before route selection, Sakoku `JAP`, and `IJP`; none
should display the vanilla generic administrative or Asian columns.
