# jxp 0.13.4 Minor-House Policy Memory Expansion

## Scope

- Version advanced to `0.13.4`.
- Builds directly on `0.13.3` by extending the pre-unification policy memory chain beyond the first 14 major daimyo branches.
- Main focus: make selected remaining/minor daimyo early decisions survive into unified Japan as institutional memories with two-option events.

## Implemented

- Added persistent memory flags to 6 additional early decisions:
  - `ASA`: `jxp_decision_asa_ichijodani_council`
  - `AMA`: `jxp_decision_ama_gassan_toda_registers`
  - `HSK`: `jxp_decision_hsk_sakai_kanrei_council`
  - `KTB`: `jxp_decision_ktb_ise_court_petition`
  - `AKT`: `jxp_decision_akt_ezochi_trade_brokers`
  - `RFR`: `jxp_decision_rfr_mutsu_nine_gates`
- Expanded `jxp_decision_recall_preunification_edicts` to dispatch to events `jxp_preunification_memory.15` through `.20`.
- Added 6 new triggered events with two options each:
  - Ichijodani council versus Echizen paper/document office.
  - Gassan-Toda mountain castle law versus Izumo mine registers.
  - Sakai kanrei council versus merchant arbitration.
  - Ise shrine court rites versus Kuki pilots.
  - Ezochi trade office versus northern wardens.
  - Mutsu gate wardens versus Morioka granary law.
- Added 12 new permanent, moderate reward modifiers.
- Extended Chinese source and escaped active localisation.
- Extended debug cleanup for all added flags and modifiers.
- Extended `preunification_memory_report` so the checker now requires 20/20 complete rows.

## Validation

- `validate_eu4_mod.ps1`: passed.
- `check_mission_series_overlap.py`: passed.
- `check_jxp_japan_coverage.py`: passed.
  - `Pre-unification policy memory coverage`: `20/20` early flags, dispatches, events, modifiers, localisation, and cleanup.
- New modifier keys were checked against vanilla `common/*.txt`; missing keys: none.
- Active `jxp_43_preunification_memory_l_english.yml` has UTF-8 BOM and no raw CJK.

## Remaining Work Toward 0.7

- The memory chain now covers 20 representative branches. Remaining single-house decisions in `jxp_19`/`jxp_20` can be added in a later broadening pass if the design goal becomes full 37-house early-policy memory coverage.
- Continue expanding route-plus-founder combinations where the current coverage is structurally complete but some routes still have fewer tailored narrative events than others.
- Add mission objectives that explicitly reward having integrated these early policy memories, using stable mission potential and placing the memory flag in mission triggers.
