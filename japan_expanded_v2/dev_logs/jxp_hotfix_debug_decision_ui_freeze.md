# JXP Hotfix - Debug Decision UI Freeze

Date: 2026-07-09

## Problem

Clicking the JXP debug decision menu could make the EU4 decisions panel appear frozen and prevent further scrolling. The likely cause was a combination of:

- too many core debug decisions visible at once;
- debug route/value/cleanup decisions expanding large scripted effects into decision tooltips;
- old saves potentially reopening event trigger categories immediately after the debug event panel was opened.

## Fix

- Split the core debug menu into one-open-panel-at-a-time groups:
  - cleanup tools;
  - value presets;
  - route tools;
  - contact/pressure seeding tools.
- Kept the default debug menu compact: enable/disable, initialize, unify, grant resources, panel openers, and event panel opener.
- Added `jxp_debug_hide_core_panels` to collapse the current core tool group.
- Opening a core tool group now closes event trigger panels and clears event category flags.
- Opening the event trigger panel now clears core tool groups and stale event category flags.
- Wrapped heavy debug scripted effects with `custom_tooltip = jxp_debug_internal_effect_tt` plus `hidden_effect`, so the decisions UI no longer needs to render route cleanup, tag-change, mission refresh, province loops, or government-power sync internals.
- Regenerated active escaped localisation for `jxp_debug_l_english.yml`.

## Files Changed

- `decisions/jxp_debug_decisions.txt`
- `common/scripted_effects/jxp_debug_effects.txt`
- `localisation_source/jxp_debug_l_english_utf8_source.yml`
- `localisation/jxp_debug_l_english.yml`
- skill reference: `eu4-modding/references/modding-reference.md`

## Validation

- `check_jxp_ui_guardrails.py`: passed. Debug event decisions: `48/48` gated.
- `validate_eu4_mod.ps1`: passed.
- `check_mission_series_overlap.py`: passed before the final tooltip polish; no mission files were changed.
- `check_jxp_japan_coverage.py`: passed before the final tooltip polish; no coverage-sensitive gameplay files were changed.
- Active debug localisation has UTF-8 BOM and no raw CJK.
- Root residual check: no `jxp_*` files were written under the EU4 game root.

## In-Game Test Route

1. Start a Japan-region country and open decisions.
2. Click `调试：开启日轮诸道调试菜单`.
3. Confirm the list remains scrollable.
4. Open `展开数值档位`, `展开路线工具`, `展开接触播种`, and `展开清理工具` one at a time.
5. Confirm each panel replaces the previous core panel rather than stacking every debug button.
6. Open `调试：打开事件触发面板`; confirm it first shows only event category buttons, then one chosen event category.
