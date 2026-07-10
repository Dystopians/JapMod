# jxp 0.13.3 Pre-Unification Policy Memory

## Scope

- Version advanced to `0.13.3`.
- Main focus: make major-daimyo early special decisions matter after Japanese unification through persistent policy-memory flags and a unified-Japan follow-up decision.
- This is a continuation slice toward the broader 0.7 goal: more distinctive daimyo decisions, founder-specific events, special family memories, and better long-term variety.

## Implemented

- Added persistent memory flags to all 14 major daimyo early decisions in `decisions/jxp_15_daimyo_flavor_decisions.txt`.
- Added unified-Japan decision `jxp_decision_recall_preunification_edicts` in `decisions/jxp_43_preunification_memory_decisions.txt`.
- Added 14 triggered policy-memory events in `events/jxp_43_preunification_memory_events.txt`.
  - Each event is tied to one early decision memory flag.
  - Each event has two player options: preserve the founder-house old law or adapt it into a broader realm institution.
  - Each event sets the shared consumed flag `jxp_43_preunification_memory_integrated`.
- Added 28 permanent but moderate country modifiers in `common/event_modifiers/jxp_43_preunification_memory_modifiers.txt`.
- Added Chinese source localisation in `localisation_source/jxp_43_preunification_memory_l_english_utf8_source.yml`.
- Generated escaped active localisation in `localisation/jxp_43_preunification_memory_l_english.yml` for the existing double-byte Chinese setup.
- Added debug cleanup for all new memory flags and reward modifiers in `common/scripted_effects/jxp_debug_effects.txt`.
- Extended `check_jxp_japan_coverage.py` with `preunification_memory_report`.
- Updated the `eu4-modding` skill reference with the reusable pre-unification memory-chain pattern.

## Validation

- `validate_eu4_mod.ps1`: passed.
- `check_mission_series_overlap.py`: passed.
- `check_jxp_japan_coverage.py`: passed, including new `Pre-unification policy memory coverage`.
- New modifier keys were checked against vanilla `common/*.txt`; missing keys: none.
- New active localisation has UTF-8 BOM and no raw CJK characters.
- Root residual scan found no `jxp_*` files accidentally written under the EU4 game root.

## Remaining Work Toward 0.7

- Extend the same early-choice memory pattern to selected `jxp_19` and `jxp_20` single-house decisions, especially ASA, HSK, AKT, AMA, KTB, and RFR.
- Add a second wave of route-plus-founder combo events for high-value pairings that are still represented only once.
- Continue tuning daimyo idea text and modifiers for minor houses, now that major-house early policy memory is covered.
- Add more mission hooks that consume stable memory flags through mission triggers rather than mission-group potential.
