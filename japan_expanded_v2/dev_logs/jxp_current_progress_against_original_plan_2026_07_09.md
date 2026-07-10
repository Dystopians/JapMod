# JXP Current Progress Against Original Plan

Date: 2026-07-10

## Required Companion-Map Compatibility Addendum

- `japan_expanded_v2_map` is now a mandatory compatibility target for every
  subsequent gameplay change in this project.
- Fixed 13 invalid `saigoku` country cultures, the companion daimyo mission
  refresh loop, the undefined maritime-house trigger, disconnected map-origin
  house systems, slot-3 row parity, split-area losses in Shimabara/Ikko/Wokou/
  Setouchi content, and multi-origin legacy stacking.
- The parent consumes only free origin/global/province flags and never names
  optional map tags, areas, provinces, or missions. The companion owns its
  exact slot-3 fingerprint and versioned migration.
- Combined validation covers 30 map tags across four DLC states (120 profiles),
  88/88 Japan provinces, culture/tag/idea/founder-fallback closure, and all
  cross-mod mission/event/decision/modifier/callable IDs.
- Added 34 canonical `_title` aliases for the 0.25 final-tag missions; all 287
  combined missions now resolve `_title` and `_desc`, and the validator enforces
  this convention for future additions.
- Remaining map-scale review: 19 active `num_of_cities = 25/30` gates must be
  redesigned by historical purpose, not multiplied mechanically.
- Both full validators pass with zero errors/warnings; EU4 was not launched.
- Current main release gate remains 11/11, with 37/37 unit tests after adding
  the canonical mission-localisation regression test.
- Detailed report: `jxp_main_map_compatibility_audit_2026_07_10.md`.

## 0.25.0 Final-Tag Mission Identity And Reform Visibility Addendum

- Current descriptor version is `0.25.0`.
- Unified Japan's shared state/court spines were compacted from rows `1..27`
  to dense rows `1..14`, following the pinned vanilla Japanese allowance for
  one-row same-column edges.
- Six new route-owned series and 34 missions bring the active inventory to 40
  custom series and 272 mission IDs. CJP, EJP, RFJ, and WAK no longer borrow
  route columns from another final identity; uncommitted JAP also has five
  missions in each short route column.
- Every unified profile now has five non-generic owners, at least five missions
  per slot, route terminals at row 10 or later, a maximum terminal spread of
  five rows, and a unique five-series signature. CJP terminals are
  `14/14/10/11/14`; EJP terminals are `14/14/10/11/12`.
- WAK's five obsolete hidden prerequisites were rebound from the inactive
  shared Shinto branch to its new Black Current branch, including the reflow
  generator's preserved logical snapshot.
- Government validation now simulates all ten unified route states and rejects
  missing or foreign reforms. The canonical route-reform sync regenerates
  government mechanics immediately; 27 route reforms and 38 founder reforms
  remain semantically registered inside vanilla monarchy tiers 1-11.
- Existing saves receive hidden migration `jxp_migration_v025.1`, which repairs
  missing final-tag route flags when necessary, synchronizes ideas/reforms, and
  runs the canonical immediate-plus-next-day mission refresh.
- The companion map event typo `year = 1543` was corrected to the
  vanilla-confirmed trigger `is_year = 1543`.
- Main validation is 11/11 across 179 gameplay scripts and 188 effective
  profiles; unit tests are 36/36. Companion map/history/content/assets also
  pass with zero errors and warnings. EU4 was not launched, so this release is
  static-safe rather than runtime-confirmed.
- Detailed report:
  `jxp_phase_report_0_25_0_final_tag_missions_and_reforms.md`.

## 0.24.2 Mission Runtime And Spacing Addendum

- Current descriptor version is `0.24.2`.
- The 23 pinned vanilla Japanese series now retain their exact original keys as
  inactive tombstones, allowing old-save mission swaps to evict serialized DOM
  and base-game series instead of stranding them under missing keys.
- Route changes use one immediate swap plus one guarded next-day reconciliation.
  A generated `has_mission` fingerprint repairs stale pending flags, missing
  route columns, foreign-route residues, and legacy vanilla anchors.
- All 34 JXP series are physically declared in strictly increasing row order.
  The shared state and court columns now both occupy compact rows `1..27`.
- Static checks are 11/11, all 188 effective profiles pass, unit tests are
  36/36, and all three mission generators are idempotent. EU4 was not launched.
- Detailed report:
  `jxp_phase_report_0_24_2_mission_runtime_and_spacing_hotfix.md`.

## 0.24.0 Daimyo And Final-Tag Mission Addendum

- Current descriptor version is `0.24.0`.
- All 37 supported daimyo tags now receive a 30-mission, five-slot custom tree
  instead of eleven JXP missions plus seven vanilla generic fillers.
- Five house traditions now contain six missions each and use mission-driven
  agenda choices with persistent consequences.
- The final daimyo mission offers three unification strategies whose founding
  legacy survives into unified Japan.
- Uncommitted JAP, Sakoku JAP, and IJP now own their previously empty slots;
  all 47 validated profiles have zero generic fallback cells.
- Version 0.24.0 includes a one-day old-save migration and delayed tree refresh.
- Static checks are 11/11 and unit tests are 31/31. EU4 was not launched.
- Detailed report:
  `jxp_phase_report_0_24_0_daimyo_and_final_tag_mission_expansion.md`.

## 0.23.4 Government Reform Semantic Addendum

- Current descriptor version is `0.23.4`.
- Thirty-eight founder reforms are distributed across vanilla monarchy tiers
  2-11 by institution type instead of being grouped under noble privileges.
- `府内国崩炮所`, the Satsuma gunnery office, naval commands, musters, and fort
  networks now belong to tier 5 military doctrines.
- Founder reforms are origin-filtered optional choices and are no longer
  auto-granted. This preserves normal eleven-tier progression.
- Existing saves receive `jxp_migration_v023.4`: a previously selected tier-2
  founder reform is removed, a normal tier-2 fallback is installed, and 100
  reform progress is refunded.
- A 65-reform semantic matrix now makes a wrong-tier registration fail release
  validation. Static checks are 11/11 and unit tests are 30/30.
- Detailed report: `jxp_phase_report_0_23_4_reform_semantic_reclassification.md`.

## 0.23.3 Mission Renderer Geometry Addendum

- Current descriptor version is `0.23.3`.
- The OTM/Otomo screenshot exposed the missing joint geometry invariant:
  same-slot edges may span two rows, but adjacent-slot edges must move exactly
  one row. All 14 unique two-row diagonals were removed from the visible graph
  and retained as `mission_completed` trigger gates.
- Effective topology now includes vanilla generic fallback series after whole
  non-generic slots are claimed. Daimyo profiles are validated with JXP slots
  1-3 plus vanilla administrative slot 4 and Asian slot 5.
- All 23 replaced vanilla Japanese series are disabled in both
  `potential_on_load` and country `potential`.
- Existing saves receive one delayed mission refresh through
  `jxp_migration_v023.3` after a normal restart and one game day.
- Static release validation is 11/11 and unit validation is 28/28. EU4 was not
  launched; player-side visual confirmation remains pending.
- Detailed report: `jxp_phase_report_0_23_3_mission_renderer_geometry_hotfix.md`.

## 0.23.2 Government Reform Visibility Addendum

- Current descriptor version is `0.23.2`.
- Twenty-seven selectable route reforms now use stable Japanese-polity
  `potential` blocks and dynamic route `trigger` blocks, with exactly three
  choices per route registered inside the vanilla monarchy tiers 3 through 11.
- Superseded by 0.23.4: founder reforms were temporarily grouped in tier 2 and
  auto-assigned by canonical origin.
- The legacy auto-granted, unregistered route pack is removed by a one-day
  old-save migration; parked reforms can no longer be auto-granted without
  failing validation.
- Static release validation is 11/11 and unit validation is 26/26. Final UI
  confirmation awaits the player's next normal restart and one in-game day.
- Detailed report: `jxp_phase_report_0_23_2_government_reform_visibility_hotfix.md`.

## 0.23.1 Mission Renderer Addendum

- Current descriptor version is `0.23.1`.
- The active tree contains 187 mission ids in 28 custom series plus two pinned
  vanilla mission overrides, and is evaluated in 15 effective profiles,
  including five separate daimyo house layouts.
- Visible mission edges followed the then-known separate row/column limits;
  0.23.3 supersedes this with the stricter joint diagonal rule.
- Distant progression gates remain in mission triggers as
  `mission_completed = ...`; mutually exclusive Mandate outcomes are no
  longer both mandatory for one continuation.
- Static release validation is 11/11 and unit validation is 24/24. A complete
  cold start after the final preload fix produced zero mission-series,
  unknown-trigger, parsing, or JXP runtime errors.
- Detailed report: `jxp_phase_report_0_23_1_mission_renderer_hotfix.md`.

## Snapshot

- Descriptor version: `0.25.0`.
- Effective content state: beyond the original 0.4 scope in raw volume, but still short of the 1.0 release discipline and polish target.
- Mission count: 40 custom series, 272 missions, two pinned 1.37.5 Japanese mission overrides, 0 missing mission-localisation keys.
- Implemented route tags: `KJP`, `CJP`, `EJP`, `RFJ`, `SJP`, `IJP`, `WAK`.
- Implemented disaster files: `jxp_shimabara_fire`; other planned disasters remain incomplete or not yet represented as full disaster systems.
- Government reform UI state: route reforms are now UI-safe by guardrail, with 3 visible route-institution levels plus founder-house constitution. Many later route reform definitions are parked outside the visible government UI.
- Government reform art state: 35 custom reform sprites resolve to 35 verified 57x57 RGBA DDS files.

## Validation Run

- `validate_jxp_mod.ps1`: passed, 11/11 release checks.
- JXP unit validation: passed, 36/36 tests.
- Effective topology: passed across 188 tag/route/religion/DLC profiles.
- Fresh EU4 `error.log`: all 23 pinned vanilla Japanese series are disabled at
  the global `potential_on_load` gate; zero JXP mission parse, unknown-trigger,
  or series-overlap errors after a complete cold start.

These checks prove structural health, localisation coverage, mission-slot safety, debug-decision gating, daimyo idea coverage, and broad route/founder coverage. They do not replace in-game route-transition, government-UI, or event-flow tests.

## Original Roadmap Distance

### 0.1 MVP

Status: mostly complete, with release-polish gaps.

Done:
- Three long-term Japan mechanic values exist.
- Core Japan decisions/government interaction framework exists.
- General Japan, daimyo-stage, and route mission content exceeds the original 35-45 mission target.
- Route choice exists.
- Sakoku, Open Trade, Kirishitan, and Confucian branches exist.
- `KJP`, `CJP`, and `EJP` exist.
- Shimabara disaster exists.
- Honnoji/Nanban/Rangaku-style base event content exists.
- Chinese localisation workflow and active localisation coverage exist.

Remaining distance:
- In-game proof pass is still needed for every route from a fresh daimyo save.
- Descriptors are not bumped after the latest fixes.
- Some UI-safe compromises are temporary, especially parked reform definitions and parked house-diet mission content.

### 0.2 Religious Alternate Expansion

Status: implemented in structure, still uneven in depth.

Done:
- Reformed Japan and Islamic/Kaikyo Japan exist.
- `RFJ` is used instead of occupied vanilla `RJP`; `SJP` exists.
- Hirado, Malay, Islamic port/legal, and pilgrimage-flavored content exists in event/mission layers.
- Religious-route reform definitions exist, but many are parked or still visually generic.

Remaining distance:
- Religious routes need parity passes: events, decisions, missions, and government reforms should feel equally deep across Kirishitan, Confucian, Reformed, Kaikyo, Ikko, Wokou, Sakoku, Open Trade, and Imperial routes.
- Government reform placement should be consolidated into vanilla monarchy tiers instead of bespoke post-11 layers.
- Reform icons are not complete.

### 0.3 Overseas And East Asia Expansion

Status: partially complete.

Done:
- East Asia, tribute/mandate, and route/founder combo content exists in broad structure.
- Pacific and maritime content exists in missions/events.
- Mandate-related design has partial representation.

Remaining distance:
- East Asia conquest/tribute/Mandate tasks need a focused audit against the original design, especially the special Japan-with-Mandate reform and any AE/CB/fallback behavior.
- Pacific colonial tasks need a route-by-route gameplay pass for Alaska, California, Manila-Nagasaki, and oceanic Japan identity.
- Mandate DLC fallback needs explicit in-game testing with and without Mandate functionality.

### 0.4 Popular And Pirate Expansion

Status: structurally present, still content-thin compared with mature routes.

Done:
- `IJP` and `WAK` exist.
- Ikko and Wokou route framework exists.
- Ikko/Wokou decisions, events, and route/founder combinations exist.

Remaining distance:
- Ikko disaster is not yet a full parallel to Shimabara.
- Wokou league/privateer/naval state content needs a full gameplay loop.
- Tsushima, Setouchi, and Ryukyu specialty mission content needs an explicit mission and event pass.

### 1.0 Complete Version

Status: raw content volume exceeds the 1.0 numeric target, but the project is not yet 1.0-ready.

Raw numbers:
- Missions: 174, above the planned 100-130.
- Events: 424, above the planned 80-120.
- Route tags: 7, matching the target.
- Disasters: 1 full disaster visible in files, below the planned 4-5.
- Government reforms: far above the numeric target as definitions, but not 1.0-ready because many are parked, overloaded, or visually unfinished.

Why not 1.0 yet:
- The mod now has enough content, but not enough consolidation.
- Government reform UI and icon polish remain major blockers.
- Disaster systems are underbuilt.
- Several route branches exist but need parity, gating, and in-game validation.
- Compatibility and fallback behavior need deliberate testing rather than structural checks only.

## Priority TODO

### P0 - Release Safety

1. Bump descriptors only after the current bugfix slice is finalized and documented.
2. Run a fresh in-game smoke test for:
   - Oda or Otomo daimyo start;
   - normal Japan formation;
   - Kirishitan Japan;
   - Confucian Japan;
   - Imperial Japan;
   - one Kaikyo/Islam path;
   - one Ikko path;
   - one Wokou path.
3. Verify the decision UI after enabling debug mode and event categories.
4. Verify the mission tree visually in-game for daimyo-stage Otomo and at least one unified route.
5. Verify the government reform UI no longer crowds or produces missing `modifiers_box_*` log spam.

### P1 - Government Reform Consolidation

1. Move player-facing route and founder reforms into the existing 11 vanilla monarchy levels.
2. Keep only UI-safe core route institutions visible until that consolidation is complete.
3. Decide final placement for founder-house reforms, probably under `hereditary_vs_nobility`.
4. Ensure route-switch cleanup removes stale route reforms but preserves founder identity.
5. Update coverage tooling so new post-11 custom reform levels cannot return.

### P1 - Reform Icon Pass

1. Generate vanilla-style government reform icon source sheets.
2. Crop/process final 57x57 RGBA DDS icons.
3. Register sprites in a mod-owned `.gfx` file.
4. Replace generic `icon = "shogunate"` fallbacks on Japan-specific reforms.
5. Add a deterministic icon checker for sprite registration, texture path, dimensions, alpha, and nonblank pixels.

### P1 - Route Parity Pass

1. Audit each route for a comparable set of missions, decisions, events, reforms, and debug tools.
2. Strengthen route gates so Sakoku-only, open-trade-only, overseas-trade, religious, and piracy content cannot fire in contradictory states.
3. Add development-focused events where they clearly fit: owned-province development, local prosperity, institution spread, and temporary development-cost reductions.
4. Continue prose polish so event descriptions sound historical rather than mechanical.

### P2 - Overseas, East Asia, And Mandate

1. Audit East Asia conquest, tribute, and Mandate mission chains against the original 0.3 plan.
2. Finish or validate the special Mandate reform behavior.
3. Add/verify Mandate DLC fallback paths.
4. Expand Pacific/colonial events for Alaska, California, Manila-Nagasaki, and oceanic Japan identity.

### P2 - Popular And Pirate Expansion

1. Build a full Ikko disaster or equivalent pressure system.
2. Expand Wokou league/privateer mechanics into a coherent loop.
3. Add Tsushima, Setouchi, and Ryukyu specialty missions.
4. Test `IJP` and `WAK` route transitions from real campaign states.

### P2 - Disasters And Long-Term Pressure

1. Add or finish 4-5 planned disaster systems rather than relying mostly on events.
2. Keep every disaster narrowly gated to prevent immersion-breaking false positives.
3. Add debug decisions for entering, resolving, and cleaning each disaster state.

### P3 - Documentation And Review Tools

1. Keep the visualizer regenerated after every mission/event/decision localisation pass.
2. Add a report view for route parity: per-route missions, decisions, events, reforms, tags, disasters, and debug coverage.
3. Keep `jxp_master_todo_from_original_plan.md` updated after each versioned slice.
4. Preserve the current skill guardrails: validator, overlap checker, UI guardrails, coverage checker, and root residual check.

## Bottom Line

The mod is no longer a small MVP. It has enough mission/event volume to resemble a late alpha or early beta, and the latest structural checks are green. The distance to 1.0 is now less about adding raw content and more about consolidation, route parity, UI polish, disaster completion, icon work, and in-game proof.

## 0.22.0 Update

Completed from the priority TODO:

- P1 Government Reform Consolidation: complete for the current 65 player-facing
  reforms. The 27 route choices and 38 founder choices now live inside vanilla
  monarchy levels 1-11. The post-11 JXP levels are removed, stale selections
  migrate once, route cleanup preserves founder identity, and tooling rejects a
  return to custom late tiers.
- P1 Reform Icon Pass: complete. Thirty-five imagegen-derived, vanilla-format
  DDS icons are registered and validated; all 27 route reforms and all 38
  founder reforms resolve to the intended icon family.
- P0 mission-tree structural proof: complete statically. The validator now
  combines pinned vanilla 1.37.5 Japanese missions with all mod series and
  checks 11 effective profiles. The route-tag foundation gap is filled by 13
  new missions in legal rows 1-8.
- P0 Confucian route repair: complete statically. Shinto is harmonized through
  one guarded engine mutation, all eight Shinto incident themes have Confucian
  bridges, and three native Confucian reform centers replace scripted annual
  conversion while protecting Ise.

Updated raw numbers:

- Missions: 187 in 35 mod series.
- Effective vanilla mission series included in topology proof: 23.
- Visible route reforms: 27.
- Visible founder reforms: 38.
- Parked dormant reform definitions: 306.
- New government reform icon assets: 35.
- Validator regression tests: 14.

Still open from P0:

- Deploy 0.22.0 to the launcher-loaded Documents directory.
- Run fresh and migrated-save in-game tests for mission rendering, reform UI,
  native Confucian center propagation and a new `error.log`.

## 0.23.0 Update

Completed:

- Dynamic mission refresh architecture: all 35 candidates preload, all 28
  route refresh calls converge on one guarded hidden next-day swap, and old
  saves receive a one-time 0.23.0 topology migration.
- Full 187-mission topology reflow without changing mission IDs. All 11
  representative effective profiles now contain audited cross-column forks and
  merges instead of parallel vertical chains.
- EJP now receives the central ritual-administration branch, eliminating its
  empty middle mission column.
- All seven custom end-tag idea groups were strengthened against vanilla JAP,
  with 121 validated modifier entries and route-specific identities.
- Validation expanded to 10 checks, including delayed refresh policy, layout
  linearity metrics, and original-game idea modifier keys.

Still requires runtime proof after deployment:

- Unpause one day after a route transition and verify the mission panel rebuilds.
- Load a pre-0.23.0 save and verify completed mission state is preserved.
- Inspect the five representative trees and seven idea groups in the game UI.
- Check a freshly generated `error.log`.
