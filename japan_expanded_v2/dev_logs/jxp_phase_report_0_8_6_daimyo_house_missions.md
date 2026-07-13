# Japan Expanded 0.8.6 Phase Report: Daimyo House Mission Branches

## Scope

0.8.6 adds a third visible daimyo-stage mission column. It is meant to make different daimyo starts feel less identical before unification, while avoiding a 37-column UI flood.

## New Content

- Added `missions/jxp_21_daimyo_house_missions.txt`.
- Added `common/event_modifiers/jxp_21_daimyo_house_mission_modifiers.txt`.
- Added localisation source and generated active localisation:
  - `localisation_source/jxp_21_daimyo_house_missions_l_english_utf8_source.yml`
  - `localisation/jxp_21_daimyo_house_missions_l_english.yml`
- Bumped descriptors to version `0.8.6`.

## Mission Design

The new mission groups all use:

- `slot = 3`;
- `position = 14/15/16`;
- `jxp_is_daimyo_stage_trigger = yes`;
- mutually exclusive tag lists;
- no `replace_path` and no vanilla mission override.

The five archetypes are:

- Warrior houses: `ODA/TKG/TKD/UES/HJO/CSK/STK/CBA`.
- Court and old-order houses: `ASK/HSK/HTK/SBA/YMN/KTB/TTI/AKM`.
- Maritime houses: `MRI/SMZ/OTM/OUC/SOO/SHN/ISK/KNO`.
- Frontier houses: `DTE/RFR/AKT/UTN/OGS/ITO`.
- Temple, market, and ledger houses: `IMG/AMA/ASA/IKE/MAE/KKC/TKI`.

Each archetype has three missions. Rewards are temporary, moderate modifiers and small axis changes, designed as pre-unification identity rather than late-game power stacking.

## Debug / Testing

- Added all `jxp_21_*` temporary modifiers to `jxp_debug_clear_event_state_effect`.
- Future tests:
  - start as one tag from each archetype;
  - confirm the third mission column appears only for that archetype;
  - complete the branch and then use debug cleanup to verify the modifiers clear.

## Remaining Risk

This was statically validated, but not launched in-game. The main thing to watch in UI is whether the new slot-3 column visually coexists with vanilla/Domination Japan missions on every DLC combination.
