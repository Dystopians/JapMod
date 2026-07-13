# JXP Phase Report 0.13.0 - Route Government Reform Focus

Date: 2026-07-09

## Scope

Version `0.13.0` focuses on making every Japan-foundation route feel institutionally distinct through visible government reforms. It also finishes the immediately preceding founder-idea legacy slice so unified Japan can preserve the founding daimyo's national-idea identity after tag changes.

## Implemented

- Added `jxp_decision_compile_founder_idea_legacy`, a one-time unified-Japan decision that opens a founder-house event.
- Added 5 founder idea legacy events, one for each house archetype: warrior, court, maritime, frontier, and temple-market.
- Added 37 exact-origin permanent founder idea legacy modifiers, one for every expected daimyo origin tag.
- Added 5 generic archetype school permanent modifiers as alternate event choices.
- Added `jxp_add_founder_idea_legacy_modifier_effect` and `jxp_clear_founder_idea_legacy_effect`.
- Wired founder idea cleanup into the general debug reset effect.
- Added two new visible route government reform levels:
  - `jxp_route_institution_secretariats`
  - `jxp_route_institution_grand_design`
- Added 36 new route-specific visible reforms: 4 per route across 9 routes.
- Registered all 36 reforms in `common/governments/00_governments.txt`.
- Added every new route reform to `jxp_clear_route_reforms_effect` so route switching removes stale selections.
- Added Chinese localisation source and active escaped localisation for founder idea legacy and route government reforms.
- Bumped descriptors to `version="0.13.0"`.

## Route Reform Coverage

Each route now has 20 visible registered route reforms plus 3 hidden/auto route carrier reforms:

- Sakoku: inspection, coastal defense, ancestral-domain order, controlled foreign learning.
- Open trade: red-seal companies, naval contracts, Pacific exchange, transoceanic colonies.
- Kirishitan: sun-cross chancery, Nagasaki order fleet, martyr levies, Roman embassy cabinet.
- Confucian: Shinto-Confucian harmonizers, censorate granaries, ritual core commission, school network.
- Imperial: Jingikan cabinet, restoration planning board, sacred envoys, solar guard bureaus.
- Reformed: scripture printing, burgher synods, civic militia covenant, Dutch engineers.
- Kaikyo/Islamic: harbor qadi bureau, monsoon customs, pilgrim embassy network, cannon-foundry madrasas.
- Ikko: somon assemblies, monto watch bells, public granary leagues, equal-field compact.
- Wokou: black-current captains, island broker courts, tidewater admiralty charters, red-seal raiding law.

## Tooling Updates

- `check_jxp_japan_coverage.py` now checks founder idea legacy coverage per expected daimyo origin.
- Route reform coverage now requires at least 20 visible reforms per route.
- The checker now expects the two new government reform level keys.
- `eu4-modding` reference now records:
  - how to preserve daimyo national-idea identity as a founder idea legacy;
  - how to expand route government reform layers without missing government registration, cleanup, localisation, or coverage thresholds.

## Validation

Passed:

- `validate_eu4_mod.ps1`
- `check_mission_series_overlap.py`
- `check_jxp_japan_coverage.py`
- EU4-root residual `jxp_*` file scan

Skipped:

- `tools/quick_validate.py`, because this mod currently has no such script.

## In-Game Test Route

Suggested smoke test:

1. Enable only `日轮诸道：日本扩展风味包`.
2. Start as a major daimyo such as Oda or Otomo.
3. Use the existing debug route decisions if needed to form/force a route quickly.
4. Open the government reform list after choosing each route and confirm the new `国体枢机` and `国家大策` levels appear.
5. Switch route through debug and confirm old route reforms disappear from the country.
6. After unification, run the `编纂开府国策` decision and confirm the event gives either exact-origin legacy or archetype school rewards.

No live in-game UI test was run in this pass.
