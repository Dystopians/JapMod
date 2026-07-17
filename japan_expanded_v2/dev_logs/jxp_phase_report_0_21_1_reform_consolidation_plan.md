# JXP 0.21.1 - Government Reform Consolidation Plan

Date: 2026-07-09

Status: planning and handoff only. No gameplay implementation was intentionally changed in this slice.

## Why This Pause Exists

The current route-government design drifted too far toward adding new visible monarchy reform levels after the vanilla 11 levels. That is not the desired direction. Future work should preserve the EU4 government reform rhythm: route-specific Japan reforms must be folded into the first 11 monarchy reform levels and should respect each level's vanilla design theme.

The next implementation pass should therefore be a consolidation pass, not another expansion pass.

## Current Snapshot

- Active descriptor version is still `version="0.21.0"`.
- The latest completed gameplay slice is `0.21.0`, which added `jxp_route_institution_high_offices`.
- `common/governments/00_governments.txt` currently keeps the vanilla monarchy levels through `separation_of_power`, then appends many `jxp_route_institution_*` levels and `jxp_founder_house_constitution`.
- Many custom government reforms still use `icon = "shogunate"`, which is functional but visually unfinished.
- Vanilla government reform icons are 57x57 RGBA DDS files under `gfx/interface/government_reform_icons/`, registered through `interface/governmentreformicons.gfx` with sprite names like `government_reform_shogunate`.
- There appears to be partial unfinished work for a broader `jxp_52_major_founder_house_policy` expansion: source/event files include additional entries, while descriptors and active localisation were not finalized for a new version. The next implementer must either finish and validate that slice or deliberately defer it before changing related cleanup/coverage logic.

## Binding Design Decision

Do not add any more normal player-facing reform levels after the vanilla 11 monarchy levels.

All route, religion, founder-house, and branch government reforms that are meant to be visible should be registered inside these existing monarchy levels:

1. `feudalism_vs_autocracy`
2. `hereditary_vs_nobility`
3. `bureaucracy`
4. `state_and_religion`
5. `military_doctrines`
6. `deliberative_assembly`
7. `growth_of_administration`
8. `economical_matters`
9. `legitimation_of_power`
10. `absolute_rule_vs_constitutional`
11. `separation_of_power`

Existing `jxp_reform_*` definitions may be kept where possible, but their registration should move into the relevant vanilla-level bucket. Route switching cleanup should continue to remove stale route reforms. Optional visible route reforms should not be auto-granted unless a specific design note says they are carrier/invisible reforms.

## Proposed 0.22.0 Focus

Working title: `0.22.0 - Reform Integration and Government Icon Pass`.

Primary objective:

- Consolidate Japan route government reforms into the first 11 monarchy reform levels.
- Remove the extra post-11 custom route levels from `common/governments/00_governments.txt`.
- Add generated EU4-style government reform icons for the Japan branch reforms.
- Harden coverage tooling so future agents cannot reintroduce the same mistake.

## Reform Level Mapping

Use this as the first implementation map:

| Vanilla level | Design role | JXP content that belongs here |
| --- | --- | --- |
| `feudalism_vs_autocracy` | Basic state form and ruling constitution | Route foundation reforms: bakuhan state, maritime monarchy, Kirishitan crown, Confucian rite-state, imperial restoration, Reformed civic monarchy, Kaikyo sultanate/diwan, Ikko commonwealth, Wokou sea-lord domain |
| `hereditary_vs_nobility` | House, nobility, daimyo, and aristocratic settlement | Founder-house reforms and house-memory reforms; route-specific noble/retainer settlements |
| `bureaucracy` | Ministries, laws, records, exams, censors | Cadaster bureaus, examination ministries, qadi courts, synods, curia offices, land/revenue boards |
| `state_and_religion` | Religion-state relationship and cultural synthesis | Shinbutsu/Confucian harmony, Kirishitan seminaries, Ikko temple law, Islamic qadi and waqf systems, Reformed consistories, Sakoku temple registration |
| `military_doctrines` | Army and navy organization | Gunfoundries, foreign drill yards, guard banners, ashigaru leagues, privateer or blue-water naval boards |
| `deliberative_assembly` | Councils, diets, parliaments, privy bodies | Privy councils, domain assemblies, somon diets, port-guild diets, court councils |
| `growth_of_administration` | Provincial administration and domain integration | Domain surveys, prefectures, governors, steward networks, barriers, local registration systems |
| `economical_matters` | Trade, money, ports, production | Silver exchanges, Nagasaki/foreign factories, customs houses, red-seal companies, port waqf/endowments, island brokerage courts |
| `legitimation_of_power` | Ideology, mandate, public law, imperial/theological legitimacy | Imperial envoys, divine kingship, civic oaths, East Asian ritual mandate, `八纮一宇`-style mandate reforms if unlocked through missions |
| `absolute_rule_vs_constitutional` | Centralization versus chartered restraints | Bakufu absolutism, restoration command, constitutional charters, treaty-port high courts, crown patronage |
| `separation_of_power` | High offices, cabinet/court separation, late institutional form | High offices, cabinets, courts, state councils, admiralty boards, censorial separation |

## Concrete Implementation Steps

1. Freeze and inventory:
   - Parse all `jxp_reform_*` definitions under `common/government_reforms`.
   - Classify each visible reform as route, founder-house, route/founder hybrid, or generic Japan.
   - List every reform currently registered in a `jxp_route_institution_*` level.

2. Consolidate government registration:
   - Remove the custom post-11 route levels from `common/governments/00_governments.txt`.
   - Move each visible reform key into one of the 11 vanilla monarchy levels using the mapping above.
   - Move `jxp_founder_house_constitution` content into `hereditary_vs_nobility` unless testing proves the founder-house choice works better under `legitimation_of_power`.
   - Keep route-specific `potential` gates narrow so each country only sees its own branch choices.
   - Avoid broad culture-only visibility gates; use route flags/tags and unified-Japan triggers.

3. Preserve route switching safety:
   - Keep `jxp_clear_route_reforms_effect` and its child cleanup effects.
   - Confirm every visible route reform is removed by route-switch cleanup.
   - Confirm founder-house reforms are not removed by ordinary route switching unless the founder origin itself is reset.
   - Keep optional reforms out of `jxp_grant_route_reforms_effect`; only carrier or guaranteed route institutions may be auto-granted.

4. Rebalance density:
   - Each route should normally see 1-3 special choices in a given vanilla tier, not a wall of every route's reforms.
   - Strong route reforms may be slightly stronger than vanilla, but should not stack multiple discipline, administrative efficiency, core-creation cost, or global tax bonuses without tradeoffs.
   - Prefer route identity over raw power: Sakoku control, Open Trade commerce/navy, Kirishitan conversion/diplomacy, Confucian administration/harmonization, Imperial legitimacy/mandate, Reformed printing/civic law, Kaikyo maritime Islam, Ikko commune/levy, Wokou raiding/sea law.

5. Generate and register icons:
   - Use image generation for source art. Do not hand-draw placeholder icons.
   - Match vanilla government reform icon style: small painted vignette, parchment/sepia base, subdued metal/wood/cloth, readable silhouette, no modern flat vector look.
   - Final files should be 57x57 RGBA DDS, placed under `gfx/interface/government_reform_icons/`.
   - Keep source sheets and cropped PNG previews under `gfx/interface/government_reform_icons/source/`.
   - Register sprites in a mod-owned interface file such as `interface/jxp_governmentreformicons.gfx`.
   - Reform definitions should use `icon = "jxp_<theme>"`, matching sprite `government_reform_jxp_<theme>`.
   - Verify every icon reference has a registered sprite and every DDS is 57x57 RGBA.

6. Suggested icon families:
   - Sakoku: closed gate, temple register, coastal watchtower, hostage procession.
   - Open Trade: red-seal ship, silver scales, telescope, treaty-port customs house.
   - Kirishitan: sun cross, seminary book, hospital bell, ocean mission banner.
   - Confucian: classics tablet, brush and seal, shrine-tablet harmony, censor's desk.
   - Imperial: chrysanthemum seal, Daijokan hall, shrine envoy, restoration guard banner.
   - Reformed: printed oath, burgher council table, Dutch instruments, covenant press.
   - Kaikyo: crescent harbor, qadi scroll, monsoon dhow, madrasa foundry.
   - Ikko: temple bell, village oath tablet, granary, fortified temple town.
   - Wokou: black-current wave, island court, red-seal privateer, tidewater arsenal.

7. Localisation:
   - Edit human-readable `localisation_source/*_utf8_source.yml` first.
   - Regenerate active localisation with `escape_eu4_special_localisation.py`.
   - Keep reform descriptions immersive; do not repeat raw effects or monarch-point costs in prose.

8. Tooling and validation:
   - Update `check_jxp_japan_coverage.py` so it rejects `jxp_route_institution_*` levels in `00_governments.txt`.
   - Replace the old "minimum 34 visible route reforms" assumption with:
     - every non-basic visible `jxp_reform_*` is registered in one of the 11 vanilla monarchy levels;
     - every route has a minimum agreed visible count across the 11 tiers;
     - every route-switch cleanup effect removes all route reforms;
     - every custom icon key resolves to a registered sprite and DDS.
   - Run `validate_eu4_mod.ps1`.
   - Run `check_mission_series_overlap.py`.
   - Run `check_jxp_japan_coverage.py`.
   - Run a root residual check to ensure no `jxp_*` files were written into the EU4 game root.

9. In-game test script:
   - Start as a normal daimyo such as Oda or Otomo and confirm pre-unification reforms are not polluted by post-route choices.
   - Form/select each Japan route through debug or normal route events.
   - Open the government reform UI and confirm there are only the normal 11 monarchy levels.
   - Confirm route-specific reforms appear in appropriate existing tiers and use distinct icons.
   - Switch route through debug tools and confirm stale route reforms disappear.
   - Confirm founder-house identity remains available after route switching.

## Do Not Do

- Do not add more `jxp_route_institution_*` levels after `separation_of_power`.
- Do not use `basic_reform = yes` for reforms that are meant to be chosen in the government UI.
- Do not leave every reform on `icon = "shogunate"`.
- Do not rely on descriptor/version bump as proof of completion; run the coverage scripts.
- Do not regenerate active localisation in parallel with the readback verifier.

## Open Questions For Execution

- Whether to finish the unfinished `jxp_52_major_founder_house_policy` expansion before or after the reform consolidation. The safer path is to finish/validate it first if those edits are already present, then proceed to government reform cleanup.
- Whether founder-house reforms should live in `hereditary_vs_nobility` or `legitimation_of_power`. Design preference is `hereditary_vs_nobility`; if in-game unlocking feels awkward, move them to `legitimation_of_power`.
- How many unique icons to ship in the first icon pass. Minimum acceptable: route-by-tier icon families with no `shogunate` fallback on new route reforms. Ideal: one icon per major visible reform.
