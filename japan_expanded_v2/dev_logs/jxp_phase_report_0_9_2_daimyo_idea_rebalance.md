# JXP 0.9.2 Phase Report - Daimyo Idea Rebalance

Date: 2026-07-09

## Scope

This slice continues the broader 0.7+ goal of making each daimyo origin and Japan-founding path feel distinct. It does not add new mission branches or events; it focuses on national-idea differentiation for later-added daimyo tags and keeps all existing mission/event coverage intact.

## Changed Daimyo Idea Profiles

- `OGS`: shifted Suwa shrine and Shinano unification toward durable prestige, mountain administration, and state upkeep.
- `KTB`: strengthened Southern Court memory and Kuki naval identity with prestige retention and sailor support.
- `AKT`: made northern trade and Ainu frontier content less purely conquest-oriented by adding sailor and heathen-tolerance flavor.
- `KNO`: made Iyo/Murakami sea power more ship-roll and sailor based instead of only cheaper galleys.
- `RFR`: changed famine relief from generic production into northern granary/state-maintenance flavor.
- `HTK`: gave Hatakeyama retainer and Saika content mercenary/arquebus flavor.
- `IKE`: made Setouchi accounts and Tokugawa ties more administrative and diplomatic.
- `MAE`: made tea/noh and outer-daimyo balance less generic prestige/AE and more courtly endurance/diplomacy.
- `SBA`: made the military office and northern access more military-tradition/trade-route focused.
- `KKC`: made Kyushu religious coexistence also support national religious unity.
- `TKI`: made Ranjatai prestige and Saito-house intelligence flavor more explicit.

## Files Changed

- `common/ideas/jxp_17_minor_daimyo_ideas.txt`
- `common/ideas/jxp_18_remaining_daimyo_ideas.txt`
- `localisation_source/jxp_17_minor_daimyo_ideas_l_english_utf8_source.yml`
- `localisation_source/jxp_18_remaining_daimyo_ideas_l_english_utf8_source.yml`
- `localisation/jxp_17_minor_daimyo_ideas_l_english.yml`
- `localisation/jxp_18_remaining_daimyo_ideas_l_english.yml`
- `descriptor.mod`
- `../japan_expanded_v2.mod`

## Validation

- `validate_eu4_mod.ps1`: OK, no issues found.
- `check_mission_series_overlap.py`: OK, no route-profile mission slot overlaps found.
- `check_jxp_japan_coverage.py`: OK, all daimyo coverage rows OK; all route reform packs remain `hidden_auto = 3`, `visible_registered = 9`, `unregistered = 0`.
- Active localisation readback: both regenerated idea localisation files have BOM, `l_english:` headers, and `raw_cjk = 0`.
- Idea structure readback: `jxp_17_minor_daimyo_ideas.txt` has 12 groups / 84 idea blocks; `jxp_18_remaining_daimyo_ideas.txt` has 11 groups / 77 idea blocks.
- Root residual check: no `jxp_*` files were found under the EU4 install outside the local mod.

## Remaining Work

- Continue the same idea-pass for the earlier major daimyo file if balance testing shows Oda/Tokugawa/Takeda/etc. still feel too strong or too generic.
- Add more founder-origin missions and post-unification legacy events so the idea differences have mission/event hooks.
- In-game spot test recommended tags for this slice: `HTK`, `KTB`, `AKT`, `KNO`, `MAE`, `KKC`.
