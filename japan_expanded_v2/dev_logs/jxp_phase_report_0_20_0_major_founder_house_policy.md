# JXP 0.20.0 - Major Founder House Policy Events

Date: 2026-07-09

## Summary

- Bumped `japan_expanded_v2` to `version="0.20.0"`.
- Added a new exact-house post-founder-reform pulse layer for the 14 representative major daimyo:
  `ODA`, `TKG`, `TKD`, `UES`, `HJO`, `MRI`, `SMZ`, `OTM`, `DTE`, `ASK`, `CSK`, `OUC`, `IMG`, `SOO`.
- Each event is gated by `jxp_is_unified_japan_state_trigger = yes`, the exact selected founder-house government reform, and a one-shot `jxp_52_*_major_founder_policy_seen` flag.
- Each event gives two policy choices, a small era-attribute adjustment, and a 10-year house-specific modifier.
- Added debug cleanup so repeated in-game testing can clear all new one-shot flags and remove all new temporary modifiers.

## Added Files

- `events/jxp_52_major_founder_house_policy_events.txt`
- `common/event_modifiers/jxp_52_major_founder_house_policy_modifiers.txt`
- `common/scripted_effects/jxp_52_major_founder_house_policy_effects.txt`
- `localisation_source/jxp_52_major_founder_house_policy_l_english_utf8_source.yml`
- `localisation/jxp_52_major_founder_house_policy_l_english.yml`

## Updated Files

- `common/scripted_effects/jxp_debug_effects.txt`
- `descriptor.mod`
- outer `japan_expanded_v2.mod`
- skill checker `check_jxp_japan_coverage.py`
- skill reference `references/modding-reference.md`

## Validation

- `validate_eu4_mod.ps1`: passed.
- `check_mission_series_overlap.py`: passed, no route-profile mission slot overlaps.
- `check_jxp_japan_coverage.py`: passed, including the new `Major founder house policy coverage` section.
- Active localisation file has UTF-8 BOM and no raw CJK characters after EU4SpecialEscape conversion.
- Root residual check found no accidental `jxp_*` files written under the EU4 game root.

## Remaining Scope

- This slice intentionally covers the 14 major representative daimyo first. The remaining 23 founder houses still need exact-house post-founder-reform events if the project wants full 37-house parity at this layer.
- Next recommended design focus from the user: add many route-specific, player-facing government reform choices for every Japan-building branch. These should be registered in `common/governments/00_governments.txt`, kept out of the auto-grant effect unless they are guaranteed carrier reforms, added to route-switch cleanup, localized in source files, and enforced by coverage tooling.
