# Japan Expanded v2 0.13.5 Phase Report - Full Pre-Unification Policy Memory

Date: 2026-07-09

## Summary

- Completed the pre-unification policy memory chain for all 37 tracked Japanese daimyo tags.
- The chain now covers every tag from `jxp_is_major_daimyo_tag_trigger`, not only the earlier 20-house subset.
- This slice was later folded into the visible descriptor version `0.14.0`, because the same working session added a major route government reform layer.

## Implemented

- Added persistent early-choice flags for the remaining 17 daimyo decisions:
  - `HTK`, `IKE`, `MAE`, `SBA`, `YMN`, `AKM`, `KKC`, `STK`, `TKI`, `UTN`, `SHN`, `OGS`, `CBA`, `ISK`, `ITO`, `KNO`, `TTI`.
- Expanded `jxp_decision_recall_preunification_edicts` to dispatch through `jxp_preunification_memory.37`.
- Added 17 triggered unified-Japan memory events and 34 permanent but moderate choice modifiers.
- Added source localisation and regenerated active escaped localisation for the Chinese double-byte setup.
- Extended debug cleanup to clear every new memory flag and remove every new permanent reward modifier.

## Tooling

- Updated `check_jxp_japan_coverage.py` so `preunification_memory_report` compares its expected-row table against the canonical daimyo tag trigger.
- Current checker result:
  - `early_flag=37/37`
  - `dispatch=37/37`
  - `event=37/37`
  - `modifiers=37/37`
  - `loc=37/37`
  - `cleanup=37/37`
  - decision gate/localisation OK

## Validation

- `validate_eu4_mod.ps1`: OK
- `check_mission_series_overlap.py`: OK
- `check_jxp_japan_coverage.py`: OK
- Active `jxp_43_preunification_memory_l_english.yml`: UTF-8 BOM present, no raw CJK.

## Notes For Next Agent

- Keep using persistent `jxp_43_selected_*` flags when an early daimyo decision should matter after unification.
- Do not add new rows to the checker without also comparing against the canonical tag set.
- If a new daimyo is added to `jxp_is_major_daimyo_tag_trigger`, this chain should fail coverage until its memory row is implemented.
