# Japan Expanded 0.9.0 Phase Report: Route Government Reform Expansion

## Scope

0.9.0 makes route-specific government reforms the main focus. The earlier 0.8.1 implementation exposed three route reform levels, but each route effectively had one option per level. This version adds three later reform levels with two route-specific choices per route and per level.

## New Government Reform Levels

- `jxp_route_institution_society`: social order, registration, education, civic and religious institutions.
- `jxp_route_institution_arms`: army, navy, coastal defense, arsenals and route-specific military organization.
- `jxp_route_institution_horizon`: diplomacy, overseas direction, ideological world order and long-range state identity.

Each level contains two choices for each of the nine route identities:

- Sakoku Japan
- Open Trade Japan
- Kirishitan Japan
- Confucian Japan
- Imperial Restoration Japan
- Reformed Japan
- Kaikyo / Muslim Japan
- Ikko Commonwealth Japan
- Wokou Admiralty Japan

## Implementation Notes

- Added `common/government_reforms/jxp_24_route_reforms_deep.txt` with 54 new visible route reforms.
- Registered the three new levels in the modded `common/governments/00_governments.txt` under monarchy reform levels.
- Added every new reform to `jxp_clear_route_reforms_effect` so route switching and debug cleanup remove stale selections.
- Deliberately did not add the new reforms to `jxp_grant_route_reforms_effect`; these are meant to be player choices, not automatically granted old-save carrier reforms.
- Added human-readable localisation source and generated active localisation in the normal escaped-localisation workflow.

## Test Route

1. Enter or debug-force each Japan route.
2. Open government reforms and confirm the three new `日轮国制` levels appear after the earlier route reform levels.
3. Confirm each route sees only its own two choices in each new level.
4. Switch route through debug and confirm previously selected new route reforms are cleared.
