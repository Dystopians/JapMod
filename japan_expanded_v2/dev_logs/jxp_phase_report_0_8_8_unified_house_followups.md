# Japan Expanded 0.8.8 Phase Report: Unified House Follow-up Events

## Scope

0.8.8 expands the 0.8.7 unified-house ordinances with low-frequency follow-up events. The goal is to make founding-house identity remain active after unification instead of ending as a single permanent modifier.

## New Content

- Added `events/jxp_23_unified_house_followup_events.txt`.
- Added `common/event_modifiers/jxp_23_unified_house_followup_modifiers.txt`.
- Added localisation source and generated active localisation:
  - `localisation_source/jxp_23_unified_house_followup_l_english_utf8_source.yml`
  - `localisation/jxp_23_unified_house_followup_l_english.yml`
- Bumped descriptors to version `0.8.8`.

## Event Design

Each event is gated by one of the 0.8.7 ordinance modifiers:

- `jxp_22_warrior_house_codes` -> flagbook and retainer muster review.
- `jxp_22_court_office_order` -> Kyoto rank and service-office dispute.
- `jxp_22_maritime_house_routes` -> vermilion-seal ships and private merchants.
- `jxp_22_frontier_house_wards` -> frontier wardens and market brokers.
- `jxp_22_temple_market_law` -> shrine-temple privileges and public registries.

The events use long MTTH values around 170-190 months and set once-only `jxp_23_*_seen` flags. Each event has two player options so the state can steer the founding-house legacy toward order, sanction, or maritime opening.

## Debug / Testing

`jxp_debug_clear_event_state_effect` clears all new event flags and removes all new temporary modifiers.

Suggested test route:

1. Start as one daimyo from each 0.8.6 archetype, or use debug origin setup in a save.
2. Unify Japan and enact the matching 0.8.7 ordinance.
3. Console-fire `event jxp_house_ordinance.1` through `.5` as appropriate to verify text, options, and effects.
4. Use debug cleanup and confirm the event can be tested again.
