# JXP 0.9.4 Phase Report - Founder Legacy Extension

Date: 2026-07-09

## Scope

This slice extends the 0.9.3 founder-legacy council system from 8 origins to 14 early major daimyo origins. The goal is to make post-unification Japan retain more specific memory of the founding house, rather than collapsing every origin into the five broad house archetypes.

## Added Origins

The `jxp_decision_convene_founder_legacy_council` decision now also supports:

- `DTE`: Date
- `ASK`: Ashikaga
- `CSK`: Chosokabe
- `OUC`: Ouchi
- `IMG`: Imagawa
- `SOO`: So

Together with the previous Oda, Tokugawa, Takeda, Uesugi, Hojo, Mori, Shimazu, and Otomo support, this gives all 14 original major-daimyo flavor origins a concrete post-unification council event.

## Added Event Choices

- Date: Oshu cavalry rolls vs. Keicho envoy records.
- Ashikaga: Hokoshu order vs. Higashiyama culture.
- Chosokabe: Ichiryo-gusoku rolls vs. Tosa sea law.
- Ouchi: Yamaguchi mercantile court vs. Korean envoy rites.
- Imagawa: Tokaido lawbooks vs. triple-alliance model.
- So: Wakan trade office vs. Tsushima sea wardens.

Each choice gives a 20-year country modifier and nudges one of the three Japanese polity values through existing `jxp_add_*_5_effect` hooks.

## Files Updated

- `common/scripted_triggers/jxp_26_founder_legacy_triggers.txt`
- `decisions/jxp_26_founder_legacy_councils.txt`
- `events/jxp_26_founder_legacy_councils.txt`
- `common/event_modifiers/jxp_26_founder_legacy_council_modifiers.txt`
- `localisation_source/jxp_26_founder_legacy_councils_l_english_utf8_source.yml`
- `localisation/jxp_26_founder_legacy_councils_l_english.yml`
- `common/scripted_effects/jxp_debug_effects.txt`
- `descriptor.mod`
- `../japan_expanded_v2.mod`

## Validation Notes

- Active localisation readback:
  - BOM: true
  - Header: `l_english:`
  - Raw CJK: 0
  - Total keys: 114
  - Required keys found: 100 / 100
- Braces balanced in the edited event, decision, trigger, and modifier files.
- Dispatch chain readback: 14 origin-to-event mappings.
- New modifier names were checked against vanilla examples for key risk names such as `vassal_forcelimit_bonus`, `global_foreign_trade_power`, `privateer_efficiency`, `leader_land_shock`, and `ae_impact`.

## Remaining Work

- Extend a similar post-unification founder layer to the later-added minor/remaining houses.
- Add mission hooks that unlock, discount, or improve founder-legacy councils.
- Consider route-aware variants, especially Christian Otomo, maritime So/Ouchi, and imperial Ashikaga paths.
