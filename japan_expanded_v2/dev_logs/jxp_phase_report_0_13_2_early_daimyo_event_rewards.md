# JXP Phase Report 0.13.2 - Early Daimyo Event Reward Identity

Date: 2026-07-09

## Scope

Version `0.13.2` addresses a quality issue found during read-only audit: early major/minor daimyo events existed and were structurally valid, but `jxp_07` and `jxp_17` mostly rewarded players from the same small generic modifier pool. This made early play feel flatter than later founder-legacy systems.

## Implemented

- Replaced all generic `jxp_daimyo_*` reward modifiers in:
  - `events/jxp_07_major_daimyo_events.txt`
  - `events/jxp_17_minor_daimyo_events.txt`
- Added 42 new event-specific or group-specific temporary modifiers in:
  - `common/event_modifiers/jxp_42_early_daimyo_event_modifiers.txt`
- Added debug cleanup entries for all 42 modifiers in:
  - `common/scripted_effects/jxp_debug_effects.txt`
- Added Chinese localisation source and active escaped localisation:
  - `localisation_source/jxp_42_early_daimyo_event_modifiers_l_english_utf8_source.yml`
  - `localisation/jxp_42_early_daimyo_event_modifiers_l_english.yml`
- Extended `check_jxp_japan_coverage.py` with `early_daimyo_event_reward_report`.
- Updated descriptors to `version="0.13.2"`.

## Coverage Improvement

The checker now proves:

- `jxp_07_major`: 14/14 events have expected specific modifiers, 28/28 modifiers defined, localized, and debug-cleaned.
- `jxp_17_minor`: 7/7 grouped events have expected specific modifiers, 14/14 modifiers defined, localized, and debug-cleaned.
- Neither early event file still uses the old generic `jxp_daimyo_domain_accounts`, `jxp_daimyo_castle_town`, `jxp_daimyo_courtly_petition`, `jxp_daimyo_gun_foundries`, `jxp_daimyo_namban_letters`, or `jxp_daimyo_league_of_kin` reward pool.

## Validation

Passed:

- `check_jxp_japan_coverage.py`
- `validate_eu4_mod.ps1`
- `check_mission_series_overlap.py`
- UTF-8 BOM check for `jxp_42_early_daimyo_event_modifiers_l_english.yml`
- Vanilla `common` modifier-key lookup for all new event-modifier keys

No live in-game UI test was run in this pass.

## Context From Parallel Audit

The read-only audit noted that the broad "exists" coverage is strong, but quality gaps remain:

- early decisions often set one-time flags without later unified-Japan consumers;
- specific route-house events cover one representative route per origin, not multi-route variants;
- idea groups still use many repeated high-impact modifier types even after the 0.13.1 identity pass;
- quality-oriented checker reports are still worth expanding.

## Suggested Next Slice

The strongest next step is "early special decisions enter unified memory": select 5-8 distinctive early decisions such as Oda, Mori, Otomo, Date, Ashikaga, Asakura, Shimazu, and So, set persistent `jxp_selected_*` flags, then consume them in unified-Japan events or founder-legacy choices. Add coverage that requires set, consume, localisation, and debug cleanup for each flag.
