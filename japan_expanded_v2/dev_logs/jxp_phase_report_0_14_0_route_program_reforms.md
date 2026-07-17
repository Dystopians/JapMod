# Japan Expanded v2 0.14.0 Phase Report - Route Program Government Reforms

Date: 2026-07-09

## Summary

- Bumped the local descriptor version to `0.14.0`.
- Added a new visible route reform level, `jxp_route_institution_branch_programs` / "诸道国策".
- Added 36 new player-selectable government reforms: 4 options for each of the 9 Japan-building routes.
- These reforms are deliberately optional and are not auto-granted by `jxp_grant_route_reforms_effect`.

## Covered Routes

- `sakoku`: guarded internal order, temple-neighborhood control, coastal cordon, licensed private learning.
- `open`: red-seal companies, translator colleges, ocean arsenals, Pacific settlement.
- `kirishitan`: court patronage, confraternity charity, missionary admiralty, sun-cross war council.
- `confucian`: rite-law ministry, Shinto-Confucian harmonization, examination routes, East Asian mandate policy.
- `imperial`: Daijokan ministries, shrine constellation, restoration general staff, subject rank order.
- `reformed`: Hirado synod court, printed catechism bureau, Dutch drill admiralty, covenant militias.
- `kaikyo`: maritime shura council, port waqf endowments, monsoon ship registers, madrasa navigation corps.
- `ikko`: somon public council, temple-town market law, monto defense leagues, equal-oath commons.
- `wokou`: black-current letters, island trade courts, privateering admiralty, sea-lord compacts.

## Files Added Or Changed

- Added `common/government_reforms/jxp_44_route_program_reforms.txt`.
- Registered the new level in `common/governments/00_governments.txt`.
- Added route-switch cleanup for every new reform in `common/scripted_effects/jxp_scripted_effects.txt`.
- Added source localisation in `localisation_source/jxp_44_route_program_reforms_l_english_utf8_source.yml`.
- Generated active escaped localisation in `localisation/jxp_44_route_program_reforms_l_english.yml`.
- Updated `check_jxp_japan_coverage.py`:
  - route visible reform minimum raised from 20 to 24;
  - new level key required in `common/governments`;
  - new level localisation required.
- Updated `eu4-modding` reference notes for full-table daimyo checks and optional route reform cleanup.

## Validation

- `validate_eu4_mod.ps1`: OK
- `check_mission_series_overlap.py`: OK
- `check_jxp_japan_coverage.py`: OK
  - route reform coverage now reports `hidden_auto=3`, `visible_registered=24`, `unregistered=0` for every route.
- Active `jxp_44_route_program_reforms_l_english.yml`: UTF-8 BOM present, no raw CJK.
- Root residual scan for accidental `jxp_*` files under the EU4 install root: no results.

## Remaining Risk

- Static validation passed, but this slice was not live-tested in the EU4 government reform UI.
- Recommended in-game check:
  - enable only `日轮诸道：日本扩展风味包`;
  - use debug route decisions or route events to enter each route;
  - open Government Reforms and confirm the "诸道国策" level shows exactly the 4 route-appropriate options.
