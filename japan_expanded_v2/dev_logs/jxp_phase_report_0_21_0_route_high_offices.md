# JXP 0.21.0 - Route High Office Reforms

Date: 2026-07-09

## Summary

- Bumped `japan_expanded_v2` to `version="0.21.0"`.
- Added a new visible government reform level: `jxp_route_institution_high_offices`.
- Added 27 player-selectable route reforms: 3 for each of the 9 Japan-building routes.
- The reforms are deliberately not auto-granted by `jxp_grant_route_reforms_effect`; they are normal government reform choices.
- Route-switch cleanup now calls `jxp_clear_route_high_office_reforms_effect`, so stale high-office choices are removed when a save changes route through events, debug force-route tools, or old-save sanitation.

## Route Coverage

- Sakoku:寺请穿凿役所, 参勤国役金藏, 内许兰学天文寮.
- Open Trade: 太平洋商社局, 通商口岸巡回裁判, 远洋炮术学寮.
- Kirishitan: 宗徒地籍簿, 慈悲院国役, 日轮十字海外修会.
- Confucian: 经学取士省, 神儒礼讼院, 东亚礼藩府.
- Imperial: 神祇官国中网络, 复古军制学馆, 朝廷地租局.
- Reformed: 活字公法局, 町人市民军委员会, 荷兰交换技师团.
- Kaikyo: 港市卡迪高等院, 季风朝觐护航队, 学塾铸炮城.
- Ikko: 惣村均田评定, 寺内町相济法, 门徒守备盟约.
- Wokou: 黑潮朱札奉行, 岛屿中介联邦, 朱印袭掠海军府.

## Added Files

- `common/government_reforms/jxp_53_route_high_office_reforms.txt`
- `common/scripted_effects/jxp_53_route_high_office_effects.txt`
- `localisation_source/jxp_53_route_high_office_reforms_l_english_utf8_source.yml`
- `localisation/jxp_53_route_high_office_reforms_l_english.yml`

## Updated Files

- `common/governments/00_governments.txt`
- `common/scripted_effects/jxp_scripted_effects.txt`
- `descriptor.mod`
- outer `japan_expanded_v2.mod`
- skill checker `check_jxp_japan_coverage.py`
- skill reference `references/modding-reference.md`

## Validation

- `validate_eu4_mod.ps1`: passed.
- `check_mission_series_overlap.py`: passed, no route-profile mission slot overlaps.
- `check_jxp_japan_coverage.py`: passed. Route reform visible counts are now `34` for every route.
- Active localisation file has UTF-8 BOM and no raw CJK characters after EU4SpecialEscape conversion.

## Notes For Continuation

- The next logical government-reform pass can either add route-specific capstone events that react to these new high-office reforms, or add founder-house variants to make selected route and founding family interact.
- When adding more reforms, verify vanilla modifier names first. This slice corrected a candidate `global_spy_offence` to the actual EU4 modifier `spy_offence`.
