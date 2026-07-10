# JXP 0.23.3 Mission Renderer Geometry Hotfix

Date: 2026-07-09

## Player Report

The OTM/Otomo mission window loaded the intended JXP daimyo tree in slots 1-3,
with vanilla administrative and Asian generic missions in slots 4-5. Several
prerequisite arrows nevertheless appeared as disconnected horizontal stubs.

## Root Cause

The previous validator checked row span and column span independently. It
accepted an adjacent-column edge spanning two rows, although the pinned EU4
1.37.5 Japanese mission corpus contains no such edge. Measured vanilla geometry
is:

- same slot, one row: 32 edges;
- same slot, two rows: 14 edges;
- adjacent slot, one row: 26 edges;
- adjacent slot, two rows: 0 edges.

The screenshot matched three invalid `(slot 2,row N) -> (slot 1,row N+2)`
daimyo edges. A full profile audit found 14 unique invalid two-row diagonals
across daimyo, unified Japan, and overseas missions.

## Implemented Fix

- Removed all 14 two-row diagonals from `required_missions`.
- Preserved every progression gate as `mission_completed = ...` in the child
  trigger; mission requirements and rewards are unchanged.
- Added `effective.edge_diagonal_span`: cross-column visible edges must move
  exactly one row, while same-column edges may still span two clear rows.
- Added pinned generic mission inputs and effective fallback composition.
  Non-generic series occupy whole slots; generic series fill only completely
  unoccupied slots. The OTM profile is therefore validated as JXP slots 1-3,
  generic administrative slot 4, and generic Asian slot 5.
- Added pinned hashes for `00_Generic_missions.txt`,
  `01_Generic_European_Missions.txt`, and `Asian_Missions.txt`.
- Hardened all 23 replaced vanilla Japanese mission series with both
  `potential_on_load = { always = no }` and country-scope
  `potential = { always = no ... }` guards.
- Added hidden migration `jxp_migration_v023.3`; existing Japanese saves queue
  one delayed mission-tree rebuild and record
  `jxp_mission_renderer_migration_v0233`.
- Bumped both descriptors and release validation to `0.23.3`.

## Validation

- General EU4 validator: pass.
- JXP release checks: 11/11 pass.
- Clausewitz gameplay files: 167/167 parse.
- Missions: 187 ids, 28 custom series, 15 representative profiles.
- Effective topology: two pinned Japanese overrides, three pinned generic
  files, zero invalid edges or collisions.
- Unit tests: 28/28 pass, including two-row diagonal rejection and generic
  fallback slot suppression.
- EU4 was not launched, in accordance with the active user instruction.

## Player-Side Confirmation

On the next normal restart, load the affected save and advance one game day so
`jxp_migration_v023.3` can rebuild the mission tree. Reopen the mission window
and confirm that the former horizontal stubs are absent. Runtime confirmation
remains intentionally pending because no game launch was authorized.
