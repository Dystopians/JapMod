# JXP 0.21.2 - UI Bugfix And Guardrail Pass

Date: 2026-07-09

## Scope

This slice fixes three user-reported blocking UI problems:

1. National-idea or reform-style UI crowding.
2. Broken-looking mission-tree arrows in daimyo-stage branches.
3. Debug decision list overload after opening the debug event panel.

It also records the guardrails added to prevent the same failures from returning.

## Fixes

### Idea And Government UI Crowding

- Confirmed all parsed national idea groups have exactly seven ideas.
- Fixed invalid v1.37.5 modifiers:
  - `accepted_culture_threshold` -> `num_accepted_cultures`
  - `missionary_strength` -> `global_missionary_strength`
- Reduced the visible custom route-government UI load:
  - kept `jxp_route_institution_foundations`;
  - kept `jxp_route_institution_administration`;
  - kept `jxp_route_institution_command`;
  - parked later `jxp_route_institution_*` definitions outside the visible government UI until they can be consolidated into vanilla monarchy tiers or converted into mission/event rewards.
- Kept founder-house constitution visible as its own current layer pending the broader 0.22 reform consolidation.

### Mission Tree Arrows

- Shifted daimyo house branch chains in `jxp_21_daimyo_house_missions.txt` from same-row cross-column layouts into downward row sequences at positions 15, 16, and 17.
- Converted route-entry dependencies that previously created upward/folded cross-column arrows from `required_missions = { jxp_mission_settle_the_realm }` into trigger-side `mission_completed = jxp_mission_settle_the_realm` gates where the mission had to remain visually above the parent row.
- Parked the standalone house-diet mission group with `always = no` because slot 6 is not a safe visible mission slot and moving it into occupied visible slots created route-profile overlap. The content is retained for a future merge into existing route trees or event/decision rewards.

### Debug Decision List

- Reworked bulk debug event triggers behind an explicit event panel and five category selectors.
- Kept 48 one-click event-fire decisions hidden unless both the event panel and one category are active.
- Clearing or disabling debug mode now clears the event panel and category flags so old saves do not reopen the full dense debug list by accident.
- Hid verbose flag-cleanup and panel-switching internals behind `hidden_effect` for the six heaviest debug decisions, so opening the decision list no longer expands long visible effect tooltips for those controls.

## New Guardrails

- Added `check_jxp_ui_guardrails.py`.
- Strengthened `check_jxp_ui_guardrails.py` to reject duplicate mission keys, duplicate idea-group definitions, malformed idea groups, and over-dense debug panels/categories.
- Strengthened `check_jxp_ui_guardrails.py` to reject debug decisions or debug scripted effects that expose too many internal effect operations in visible tooltips.
- Updated `check_jxp_japan_coverage.py` to treat parked route reform definitions as intentional and to reject visible route-level overload.
- Updated the `eu4-modding` skill reference with:
  - visible mission slots 1-5 only;
  - no same-row or upward cross-slot mission arrows;
  - debug event decisions must be panel/category gated;
  - route-government expansion should consolidate into vanilla monarchy tiers instead of appending long custom reform chains.

## Validation

- `validate_eu4_mod.ps1`: passed.
- `check_mission_series_overlap.py`: passed.
- `check_jxp_ui_guardrails.py`: passed.
  - 174 missions checked.
  - 44 idea groups checked, with duplicate definitions rejected.
  - 48 debug event-fire decisions checked; all 48 are panel/category-gated.
  - Largest event category: `reformed_kaikyo`, 14 fire decisions and 21 total visible controls.
  - Debug core visible count: 11.
  - Debug decisions with hidden heavy tooltip internals: 6.
  - Debug scripted effects with hidden internals: 25/25.
  - Visible route-government levels: 3.
- `check_jxp_japan_coverage.py`: passed.
- Visualizer regeneration: passed, with 30 mission groups, 174 missions, 182 decisions, 424 events, and 0 missing localisation keys.
- Game-root residual check: passed; no `jxp_*` files were found under the EU4 install directory.

## Remaining Manual Verification

Static validation proves the files are structurally safe and that the known bug patterns are removed. The next in-game smoke test should still verify:

1. Open the debug decision menu, open one event category, scroll the decision list, then close the panel.
2. Start as Otomo or another daimyo with house missions and inspect the daimyo mission tree arrows.
3. Form/select at least one route Japan and open the government reform UI to confirm there is no visual crowding or `modifiers_box_*` error spam in a fresh `error.log`.

## Follow-Up

The next design slice should be `0.22.0 - Reform Integration and Government Icon Pass`, focused on consolidating parked route reforms into the vanilla 11 monarchy reform tiers and replacing generic `shogunate` reform icons with verified Japan-specific art.
