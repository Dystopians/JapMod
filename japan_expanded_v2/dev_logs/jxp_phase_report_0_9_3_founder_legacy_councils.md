# JXP 0.9.3 Phase Report - Founder Legacy Councils

Date: 2026-07-09

## Scope

This slice adds a post-unification, origin-specific layer on top of the existing five house-ordinance archetypes. It targets major daimyo founders whose historical profile should still matter after forming Japan or a route Japan.

## Added Gameplay

- New unified-Japan decision: `jxp_decision_convene_founder_legacy_council`.
- The decision appears only for unified Japan states with one of these origin flags:
  - `jxp_origin_oda`
  - `jxp_origin_tkg`
  - `jxp_origin_tkd`
  - `jxp_origin_ues`
  - `jxp_origin_hjo`
  - `jxp_origin_mri`
  - `jxp_origin_smz`
  - `jxp_origin_otm`
- The decision triggers one matching founder event through an `if` / `else_if` dispatch chain so old debug saves with multiple origin flags cannot queue several events from one click.
- Each founder event has two policy choices and a 20-year modifier:
  - Oda: Azuchi edicts vs. Rakuichi market law.
  - Tokugawa: Fudai council vs. road/barrier network.
  - Takeda: Koshu muster vs. mountain law.
  - Uesugi: Kanto justice vs. Echigo muster.
  - Hojo: Odawara cadasters vs. Sogamae defense network.
  - Mori: Setouchi admiralty vs. kokujin compacts.
  - Shimazu: Satsuma firearm workshops vs. Satsunan learning.
  - Otomo: Funai foreign quarter vs. Kunikuzushi artillery bureau.

## Files Added

- `common/scripted_triggers/jxp_26_founder_legacy_triggers.txt`
- `decisions/jxp_26_founder_legacy_councils.txt`
- `events/jxp_26_founder_legacy_councils.txt`
- `common/event_modifiers/jxp_26_founder_legacy_council_modifiers.txt`
- `localisation_source/jxp_26_founder_legacy_councils_l_english_utf8_source.yml`
- `localisation/jxp_26_founder_legacy_councils_l_english.yml`

## Files Updated

- `common/scripted_effects/jxp_debug_effects.txt`
  - Added cleanup for the shared council flag, eight per-origin council flags, and all sixteen temporary modifiers.
- `descriptor.mod`
- `../japan_expanded_v2.mod`
- EU4 modding skill reference:
  - Added a reusable warning to use `if` / `else_if` or a dispatch guard when one decision dispatches mutually exclusive origin-specific events.

## Validation Notes

- New active localisation readback before full validation:
  - BOM: true
  - Header: `l_english:`
  - Raw CJK in active file: 0
  - Localisation keys: 66
- New event, decision, and modifier files have balanced braces.

## Remaining Work

- Extend the founder council layer to additional origins, especially `ASK`, `CSK`, `OUC`, `IMG`, `SOO`, and the post-0.8 minor houses.
- Add mission rewards that unlock or discount these founder councils instead of leaving them entirely decision-driven.
- Consider route-specific variants for Christian Otomo and open-trade Shimazu/Mori outcomes.
