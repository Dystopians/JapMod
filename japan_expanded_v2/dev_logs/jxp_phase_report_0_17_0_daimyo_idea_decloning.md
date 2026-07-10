# JXP Phase Report 0.17.0 - Daimyo Idea Decloning

## Scope
- Version bumped to `0.17.0`.
- Continued the daimyo national idea identity work from 0.16.0.
- Focused on removing repeated mechanical templates inside daimyo idea files.
- No vanilla game-root files were edited.
- No event, decision, mission, route, flag, or permanent legacy dispatch chain was structurally changed.

## Main Changes
- Removed the repeated five-stat legitimacy package from daimyo idea files:
  - `jxp_hjo_kamakura_legacy`
  - `jxp_ask_court_defenders`
  - `IMG_ideas` bonus
  - `jxp_hsk_kanrei`
  - `jxp_tti_nara_city`
  - `jxp_asa_keitai_legacy`
  - `jxp_sba_kanrei_consolidation`
  - `jxp_ymn_nitta_descent`
  - `jxp_stk_hitachi_genji`
  - `jxp_utn_fujiwara_descent`
- Split repeated one-line castle/defensive ideas into house-specific combinations:
  - Amago: mountain castle, attrition, and cheaper fort upkeep.
  - Hatakeyama: Wakae Castle with garrison emphasis.
  - Maeda: Kanazawa as defense plus prestige.
  - Yamana: San'in isolation as defense plus attrition.
  - Akamatsu: castle network plus counter-espionage.
  - Satake: Mito as defense plus state administration.
  - Toki: Inabayama as defense plus local intelligence.
  - Utsunomiya: Shirakawa barrier as defense plus movement control.
- Split several one-line unrest ideas into more specific local-order packages:
  - Ishiki, Nanbu, Asakura, Hatakeyama, Ikeda, Shiba, and Satake.

## Localisation
- Added human-readable source:
  - `localisation_source/jxp_49_daimyo_idea_decloning_l_english_utf8_source.yml`
- Generated active escaped localisation:
  - `localisation/jxp_49_daimyo_idea_decloning_l_english.yml`
- Text continues the EU4-style historical register and avoids direct mechanical prose.

## Tooling
- Extended `check_jxp_japan_coverage.py` daimyo idea revision coverage to 68 rows.
- Added residual-signature checks for:
  - the old five-stat legitimacy template;
  - single-line `defensiveness = 0.20` castle templates in daimyo idea files.
- Added a skill reference note: decloning passes should include negative/residual template checks, not only positive row checks.

## Validation
- `check_jxp_japan_coverage.py`: PASS
  - `0_13_1_to_0_17_identity_pass 68/68 68/68`
  - `decloning_signatures OK`
- `validate_eu4_mod.ps1`: PASS
- `check_mission_series_overlap.py`: PASS
- `jxp_49_daimyo_idea_decloning_l_english.yml`: UTF-8 BOM present and no raw CJK characters.
- Game root residual scan: PASS, no `jxp_*` files under the EU4 install directory.

## Next Suggested Slice
- The next high-value step is no longer another pure idea pass. Consider cleaning up the Decisions UI density around unified-Japan legacy buttons:
  - `jxp_decision_convene_founder_legacy_council`
  - `jxp_decision_compile_founder_idea_legacy`
  - `jxp_decision_recall_preunification_edicts`
  - `jxp_decision_integrate_house_diet_law`
  - `jxp_decision_convene_route_house_compromise`
- Do this carefully because it touches persistent flags, permanent modifiers, debug cleanup, and existing coverage expectations.
