# JXP Master TODO From Original Plan

Date: 2026-07-09

## Required Companion-Map Compatibility Status

- Done: every future main-Mod gameplay slice must pass the full
  `japan_expanded_v2_map/tools/validate_all.ps1` gate with main validation
  enabled.
- Done: all 30 companion tags have valid cultures, one idea-group owner, one
  origin class, five custom mission slots across four DLC states, and no
  cross-mod ID collision or generic mission fallback.
- Done: parent/companion runtime fingerprints have separate ownership and a
  versioned map mission migration; the previous 30-day repair loop is closed.
- Done: companion area splits are bridged through four semantic province-flag
  contracts consumed by Shimabara, Ikko, Wokou, and Setouchi content.
- Done: strategic vanilla province anchors remain stable and `japan_region`
  closes at 88/88 provinces.
- Done: all 287 combined missions have canonical `_title` and `_desc`
  localisation; a bare mission-ID key no longer passes the release gate.
- TODO: redesign the 19 active `num_of_cities = 25/30` gates by historical
  intent. Do not mechanically scale them by `88/48`.
- Needs Review: user-approved cold-start/new-campaign runtime acceptance with
  both mods enabled. Codex did not launch EU4.

## 0.25.0 Status Override

- Done: descriptor version is `0.25.0`.
- Done: all ten unified Japan states own a distinct five-series mission
  signature with no generic fallback; CJP, EJP, RFJ, and WAK no longer borrow
  another final tag's route column.
- Done: final-tree density is a release invariant: at least five missions per
  slot, route terminals at row 10 or later, and no more than five rows between
  the shallowest and deepest column terminal.
- Done: 272 mission IDs in 40 custom series pass 188 effective
  tag/route/religion/DLC profiles, including hidden prerequisites.
- Done: all 27 selectable route reforms are profile-simulated for the ten
  unified states, registered in the vanilla first 11 monarchy tiers, and
  refreshed immediately by the canonical route sync.
- Done: `jxp_migration_v025.1` refreshes missions, ideas, and reforms for old
  saves; missing final-tag route flags are repaired conservatively.
- Needs Review: permission-gated runtime confirmation for a migrated save and
  every final-tag family. Codex did not launch EU4.

## 0.24.0 Status Override

- Done: descriptor version is `0.24.0`.
- Done: all 37 supported daimyo tags activate five custom mission slots and a
  30-mission tree; no vanilla generic administrative or Asian filler remains.
- Done: warrior, court, maritime, frontier, and temple-market house traditions
  each contain six missions and a mission-driven agenda choice.
- Done: the final daimyo mission offers three different unification methods,
  and unified Japan inherits the selected founding tradition.
- Done: uncommitted JAP, Sakoku JAP, and IJP receive bespoke missing-slot
  series, so every validated formed-Japan state has zero generic fallback.
- Done: old saves receive the 0.24.0 mission expansion migration and one
  delayed mission refresh.
- Done: release validation covers all 37 daimyo tags and ten formed-Japan
  states, requires slots 1-5, and rejects any generic fallback series.
- Needs Review: visual and pacing confirmation in a normal player-started game.
  Codex did not launch EU4.

## 0.23.4 Status Override

- Done: descriptor version is `0.23.4`.
- Done: all 38 founder reforms are placed in semantically matching vanilla
  monarchy tiers without adding levels beyond the original eleven.
- Done: `府内国崩炮所` and all other artillery/naval/muster institutions are in
  tier 5 military doctrines rather than noble privileges.
- Done: founder reforms are optional origin-filtered choices, not automatic
  grants that bypass normal tier progression.
- Done: ambiguous founder and route descriptions were rewritten to state their
  military, administrative, religious, economic, legal, or council function.
- Done: old saves receive a tier-2 fallback and 100 reform progress before the
  origin reform becomes available in its new tier.
- Done: release validation enforces the complete 65-reform semantic matrix.
- Needs Review: player-side government-window confirmation after a normal
  restart and one game day. Codex did not launch EU4.

## 0.23.3 Status Override

- Done: descriptor version is `0.23.3`.
- Done: all 14 cross-column/two-row prerequisite edges were converted to
  hidden `mission_completed` gates without weakening progression.
- Done: the effective topology model now composes active generic fallback
  series only after non-generic whole-slot occupancy is known.
- Done: the OTM/Otomo profile is validated as custom slots 1-3 plus vanilla
  administrative and Asian fallback slots 4-5.
- Done: pinned vanilla Japanese mission series are unconditionally disabled in
  both load and country potential gates.
- Done: old saves receive a one-time 0.23.3 delayed mission refresh.
- Needs Review: player-side mission-window confirmation after a normal restart
  and one game day. Codex did not launch EU4 and will not do so without explicit
  permission.

This TODO restates the earliest `日轮诸道：日本扩展风味包` plan as a durable handoff list. Statuses are based on the current `0.25.0` mod snapshot and the known development history in `dev_logs`.

## 0.23.2 Status Override

- Done: 27 route reforms are registered inside the original first 11 monarchy
  tiers with stable tree membership and dynamic route unlock conditions.
- Done: nine routes have exactly three player-selectable reforms each.
- Done: legacy unregistered route reforms are no longer auto-granted and are
  removed from migrated saves.
- Superseded by 0.23.4: exactly one founder-house reform was formerly assigned
  automatically by canonical origin.
- Needs Review: player-side visual confirmation after a normal restart and one
  in-game day; automated/static checks are green and Codex will not launch the
  game again without prior approval.

## 0.23.1 Status Override

- Done: descriptor version is `0.23.1`.
- Done: mission renderer architecture now uses 28 consolidated custom series,
  two pinned minimal vanilla-Japan overrides, narrow potentials, and one
  effective custom tree per profile.
- Superseded: 0.23.1 used separate two-row/adjacent-column limits. Version
  0.23.3 now enforces the measured joint rule for diagonals.
- Done: all 23 pinned vanilla Japanese series are unconditionally disabled in
  `potential_on_load`; a complete cold start reports zero `mission.cpp:353`,
  unknown-trigger, parsing, or JXP errors.
- Done: all five daimyo house layouts are validated, including OTM/大友 as the
  maritime representative.
- Needs Review: complete a human visual pass in the in-game mission window for
  all route tags after one game day; static, generated visual, and runtime-load
  checks are already green.

## Legend

- Done: implemented and previously validated at least structurally.
- Needs Review: implemented, but should be rechecked because later systems touched it or the user reported related issues.
- TODO: not complete or explicitly requested as next work.

## Original 0.1 Foundation

- Done: local mod `japan_expanded_v2` exists under the user EU4 mod directory.
- Done: descriptors exist and launcher recognizes the mod.
- Done: descriptor `version` is `0.25.0` and matches the release validator.
- Done: no intentional edits to the EU4 game root should be required.
- Needs Review: run root residual check after every multi-agent or image-processing pass.
- Done: no `replace_path` should be used.

## Core Japan Mechanic Values

- Done: `jxp_tenka_order`, `jxp_imperial_sanction`, and `jxp_oceanic_opening` exist as the three long-term Japan mechanic values.
- Needs Review: government UI display should remain compact and avoid tooltip spam from hidden sync ladders.
- Needs Review: balancing events that pull extreme values back toward the center exist, but more events with meaningful alternative options are still desirable.
- TODO: ensure every new route reform interacts with at least one of the three values where thematically appropriate.

## Decisions And Investments

- Done: original ten mechanism decisions were implemented and later integrated with government interaction art.
- Needs Review: old detailed decisions may now be hidden behind consolidated UI paths; confirm no duplicate sword-hunt/shogunate action conflict returns.
- Done: long-term investment alternatives beyond decisions have been explored.
- TODO: add or audit non-decision ways to change the three attributes through missions, events, reforms, estates, and government interactions.

## Route Selection And Tags

- Done: route selection expanded beyond the original five routes.
- Done: `KJP`, `CJP`, and `EJP` were created for Kirishitan, Confucian, and Imperial Japan.
- Done: Reformed, Kaikyo/Islam, Ikko, Wokou, Confucian, Imperial and Kirishitan tag/flag mission gating is covered by the 188-profile topology matrix.
- Done: every route change is routed through the canonical two-phase mission refresh and reform synchronization.
- TODO: in-game test every route transition from a normal daimyo and from a formed Japan save.

## Religion And Culture Branches

- Needs Review: Confucian Japan must harmonize/fuse Shinto and preserve Shinto-style Japanese event chains such as Nanban trade. This has been reported as still fragile.
- Done: every final religious/cultural route has three active route-owned mission columns and a five-slot national tree; final-tag mission parity is enforced structurally.
- Needs Review: event, disaster, and decision volume still differs by route even though mission-tree parity is complete.
- TODO: ensure religious conversion centers and protected sacred provinces behave as designed.

## Countries, Ideas, Flags, And Art

- Done: route countries and flags exist.
- Done: daimyo idea identity passes and decloning passes were performed for many tags.
- Needs Review: run idea coverage checker after any further daimyo balance work.
- Done: active government reform icons are generated, cropped, processed to 57x57 RGBA DDS, registered in `.gfx`, and verified.
- Done: future icon additions remain subject to the same deterministic asset gate.

## Missions

- Done: route and daimyo mission branches exist and are assembled through one
  guarded delayed refresh path.
- Done: all 37 supported daimyo tags receive a full five-column, 30-mission
  pre-unification tree with five conditional house identities.
- Done: formed-Japan profiles do not fall back to generic missions; this is now
  a hard release check rather than a manual expectation.
- Done: early daimyo series and unified-Japan series are mutually exclusive by
  polity stage and tag/route potential.
- Done: renderer geometry, slot coverage, profile collisions, and effective
  vanilla-plus-mod topology are checked for every supported daimyo tag.
- Needs Review: player-side visual and pacing pass for one tag from each house
  family, plus uncommitted JAP, Sakoku JAP, and IJP.
- Done: final-tag route columns meet the 0.25.0 depth and terminal-balance
  contract; generic filler is a release error.

## Events And Disasters

- Done: many daimyo, route, founder-house, and low-frequency events exist.
- Needs Review: the user reported strange event behavior and display issues; event ordering and localisation should be rechecked.
- TODO: add more player-choice options to events where the state plausibly has agency.
- TODO: continue polishing event prose to EU4 style and remove direct mechanical prose from descriptions.
- TODO: ensure every event flag and modifier is included in debug cleanup.
- TODO: keep Shimabara and other disaster conditions narrow enough to avoid false positives.

## Government Reforms

- Done: many Japan route and founder-house reforms exist.
- Done: visible route and founder reforms use only the first 11 vanilla monarchy levels.
- Done: post-11 `jxp_route_institution_*` level registrations are absent.
- Done: founder-house reforms are distributed by institution type across tiers 2-11.
- Done: route reform cleanup and semantic-level coverage tooling are current.
- Done: concrete reform visibility is simulated for all ten unified route
  states, and canonical sync regenerates government mechanics immediately.
- Needs Review: complete player-side route-switch and old-save migration checks.
- Done: vanilla-style government reform icons are generated, registered, and validated.

## Celestial Empire And East Asia

- Needs Review: the special Celestial Empire reform `八纮一宇` was requested and should be checked for:
  - mission-only unlock by Japan that has obtained the Mandate;
  - core-creation cost reduction;
  - removal of non-Confucian/non-Chinese Mandate penalties as scripted;
  - a 50% AE conquest CB over East Asian provinces;
  - correct localisation and visibility.
- TODO: integrate `八纮一宇` into the government reform consolidation if it is represented as a Japan-specific legitimacy/mandate reform.

## Localisation And Writing

- Done: localisation source/active split exists.
- Done: EU4SpecialEscape workflow exists for the Chinese double-byte patch setup.
- Needs Review: some development logs show mojibake when read through PowerShell; logs should remain ordinary UTF-8 Markdown and not be run through localisation conversion.
- Done: source localisation edits are regenerated into active localisation and the release gate verifies BOM plus no raw CJK.
- Done: 0.25.0 final-tag mission descriptions are historical/atmospheric and leave direct mechanics to tooltips; continue this standard for new prose.

## Validation And Release Discipline

- Done: before every version bump, run `validate_jxp_mod.ps1`; for the map
  companion also run `tools/validate_all.ps1`. The mature validator now covers
  general validation, effective topology, reforms, ideas, localisation, assets,
  migrations, and unit tests.
- Done: icon work has deterministic checks for:
  - every `icon = "jxp_*"` has a `government_reform_jxp_*` sprite;
  - every sprite texture exists;
  - every final DDS is 57x57 RGBA and nonblank.
- TODO: after government reform consolidation, in-game test the government UI for at least Oda -> JAP, Otomo -> KJP, a Confucian CJP path, an Imperial EJP path, and one Kaikyo/Islam path.

## Immediate Next Slice

Recommended next work after `0.25.0`:

1. With explicit permission, runtime-test a migrated save across CJP, EJP,
   RFJ, WAK, KJP, SJP, IJP and the three JAP states; inspect the fresh log.
2. Continue route parity for disasters, low-frequency events, and meaningful
   player choices without changing the validated mission-series contract.
3. Revisit the original-plan disaster backlog and keep Shimabara conditions
   narrow enough to avoid false positives.

## 0.23.0 Checkpoint

- Done: all visible route/founder reforms are consolidated into vanilla levels
  1-11 and their icon pass is complete.
- Done: mission refresh now uses preloaded candidates plus one guarded next-day
  swap; old saves have a dedicated 0.23.0 migration.
- Done: all 187 mission IDs were retained while the tree was reorganized into
  five-column foundations, state ladders and route-specific forks/merges.
- Done: route tags are statically proven not to fall back to generic or inactive
  Japanese mission prerequisites in 11 representative profiles.
- Done: seven custom Japanese end-tag idea groups were positively rebalanced and
  validated against original modifier keys.
- Needs Review: run fresh-game and migrated-save UI tests after the staging copy
  can be deployed to Documents.
- Needs Review: runtime propagation of CJP Confucian reform centers and the
  Shinto bridge chains still requires a new `error.log` and observation game.
- TODO: continue route-parity work on disasters, low-frequency events and
  non-decision interactions after 0.23.0 runtime proof.
