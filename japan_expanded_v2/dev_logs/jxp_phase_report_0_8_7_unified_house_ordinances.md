# Japan Expanded 0.8.7 Phase Report: Unified House Ordinances

## Scope

0.8.7 adds a post-unification policy layer based on the daimyo house that unified Japan. Earlier slices already gave each daimyo stage events, decisions, ideas, and legacy modifiers; this slice adds one active decision after unification so the founding house can deliberately write its institutional memory into the new state.

## New Content

- Added reusable origin archetype triggers:
  - `common/scripted_triggers/jxp_22_house_ordinance_triggers.txt`
- Added five one-time unified-Japan decisions:
  - `jxp_decision_codify_warrior_house_law`
  - `jxp_decision_restore_court_office_order`
  - `jxp_decision_charter_maritime_house_routes`
  - `jxp_decision_settle_frontier_house_wards`
  - `jxp_decision_register_temple_market_law`
- Added five permanent ordinance modifiers:
  - `jxp_22_warrior_house_codes`
  - `jxp_22_court_office_order`
  - `jxp_22_maritime_house_routes`
  - `jxp_22_frontier_house_wards`
  - `jxp_22_temple_market_law`
- Added localisation source and generated active localisation:
  - `localisation_source/jxp_22_unified_house_ordinances_l_english_utf8_source.yml`
  - `localisation/jxp_22_unified_house_ordinances_l_english.yml`
- Bumped descriptors to version `0.8.7`.

## Design Notes

Only one ordinance can be enacted per country, controlled by `jxp_22_house_ordinance_taken`. The five visible decisions are mutually exclusive in normal play because a country should only have one founding daimyo origin, but the shared flag also protects debug or migrated saves that may contain multiple origin flags.

The archetypes follow the 0.8.6 daimyo mission groupings:

- Warrior houses: `ODA/TKG/TKD/UES/HJO/CSK/STK/CBA`.
- Court houses: `ASK/HSK/HTK/SBA/YMN/KTB/TTI/AKM`.
- Maritime houses: `MRI/SMZ/OTM/OUC/SOO/SHN/ISK/KNO`.
- Frontier houses: `DTE/RFR/AKT/UTN/OGS/ITO`.
- Temple and market houses: `IMG/AMA/ASA/IKE/MAE/KKC/TKI`.

## Debug / Testing

`jxp_debug_clear_event_state_effect` now clears all new ordinance flags and removes all five new ordinance modifiers.

Suggested in-game checks:

- Use a debug or normal unification path from one tag in each archetype.
- Confirm only the matching ordinance decision appears after unification.
- Enact it and confirm all other ordinance decisions disappear.
- Run the debug event-state cleanup and confirm the flag/modifier state resets.
