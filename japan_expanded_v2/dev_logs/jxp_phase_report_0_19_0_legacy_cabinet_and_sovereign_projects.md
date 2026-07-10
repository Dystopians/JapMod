# JXP Phase Report 0.19.0 - Legacy Cabinet and Sovereign Projects

Date: 2026-07-09

## Summary

- Bumped `japan_expanded_v2` to `version="0.19.0"`.
- Completed the 0.18 UI consolidation slice by replacing five exposed unified-Japan legacy decisions with one visible decision/event menu: `jxp_decision_convene_legacy_cabinet`.
- Kept the five older detailed decisions intact for save/debug compatibility, but hid them by default behind `jxp_50_show_legacy_detail_decisions`.
- Completed the 0.19 government-reform focus by adding one new visible route reform level: `jxp_route_institution_sovereign_projects`.
- Added 36 new route-specific optional reforms, 4 for each of the 9 Japan founding routes:
  - Sakoku
  - Open Trade
  - Kirishitan
  - Confucian
  - Imperial
  - Reformed
  - Kaikyo / Islamic
  - Ikko
  - Wokou

## Key Files

- Added:
  - `decisions/jxp_50_legacy_cabinet_decisions.txt`
  - `events/jxp_50_legacy_cabinet_events.txt`
  - `common/scripted_effects/jxp_50_legacy_cabinet_effects.txt`
  - `common/government_reforms/jxp_51_route_sovereign_project_reforms.txt`
  - `localisation_source/jxp_50_legacy_cabinet_l_english_utf8_source.yml`
  - `localisation_source/jxp_51_route_sovereign_project_reforms_l_english_utf8_source.yml`
  - escaped active localisation files under `localisation/`
- Updated:
  - `common/governments/00_governments.txt`
  - `common/scripted_effects/jxp_scripted_effects.txt`
  - five older legacy decision files to require `jxp_50_show_legacy_detail_decisions`
  - descriptors to `version="0.19.0"`
  - `check_jxp_japan_coverage.py`
  - `references/modding-reference.md`

## Implementation Notes

- The legacy cabinet menu dispatches to the original founder legacy, founder idea, pre-unification memory, house diet legacy, and route-house compromise chains through `jxp_50_execute_*` scripted effects.
- New sovereign-project reforms are registered in `common/governments/00_governments.txt`, not auto-granted. They are intended as player-facing mutually exclusive choices in the government reform list.
- All new optional route reforms are added to `jxp_clear_route_reforms_effect` so route switching and debug route changes do not preserve stale route choices.
- All new reforms include `custom_attributes = { cannot_become_dictatorship = yes }` to avoid vanilla republic dictatorship events when compatibility states temporarily expose republic reform behavior.
- Active Chinese localisation was regenerated through `escape_eu4_special_localisation.py`.

## Validation

- `check_jxp_japan_coverage.py`: OK.
  - Route reform coverage now reports every route as `hidden_auto=3`, `visible_registered=31`, `unregistered=0`.
  - New `legacy_cabinet_report` checks central decision, triggers, effects, event menu, hidden old decisions, and localisation.
- `validate_eu4_mod.ps1`: OK, no issues found.
- `check_mission_series_overlap.py`: OK, no route-profile mission slot overlaps found.
- Active localisation readback: OK, all active `.yml` files have UTF-8 BOM and no raw CJK.
- Root residual scan: OK, no `jxp_*` files found under the EU4 game root outside the local Documents mod.
- Active descriptors: OK, no `replace_path`; outer descriptor keeps launcher-managed absolute `path`.

## Follow-Up

- In-game test route:
  - Load only `日轮诸道：日本扩展风味包`.
  - Form Japan through any daimyo, then check Decisions: normal UI should show `召集遗绪议定` rather than five separate legacy consolidation decisions.
  - Pick any route, open the government reform UI, and confirm the new `诸道建国纲领` level shows 4 options for the current route.
  - Use route debug decisions or event paths to switch route, then confirm stale sovereign-project reforms are removed.
- Future content can safely add another route reform layer by repeating the same pattern: definitions, government registration, route-switch cleanup, localisation, coverage threshold bump.
