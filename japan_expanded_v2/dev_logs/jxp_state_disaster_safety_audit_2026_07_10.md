# JXP State Lifecycle And Disaster Safety Audit

Date: 2026-07-10
Main Mod: `0.26.0` working tree
Companion Map: `0.1.1-alpha`
Evidence: `STATIC_AUDIT_FAIL; PENDING_RUNTIME`

This is a historical audit artifact for `JXP-007` and `JXP-015`, not a second
current-status or TODO document. The canonical status remains
`JXP_SHARED_DEVELOPMENT_LEDGER.md`. The lead agent must index this report there;
the parallel audit agent did not edit the ledger.

## Scope And Method

The audit traverses all Clausewitz gameplay scripts in the maintained main and
companion release surface. It inventories every mod-owned country, province,
and global flag; every dynamically added/read/removed event modifier; all
event-modifier definitions; the transitive scripted-effect graph reachable
from the canonical main and map debug reset roots; and every JXP disaster.

The new standalone checker is
`tools/jxp_validation/state_safety.py`. It hard-fails:

- a flag written but never read, or read but never written across the combined
  release surface;
- a gameplay state with no lifecycle cleanup, with finite-duration modifiers
  correctly treated as self-expiring;
- any event/mission/decision modifier or flag not reachable from the owning
  mod's debug reset graph;
- undefined, duplicate, or unused dynamic modifier definitions;
- a disaster outside the required count of 4-5, missing structural blocks,
  exact identity/chronology/geography/pressure gates, balanced progress,
  resolution/end cleanup, or enter/resolve/cleanup debug tools;
- a disaster whose start event resolves every available choice immediately;
- regression of the sword-hunt decision's Japanese identity gate or any of
  its three explicit vanilla-overlap exclusions.

The only cleanup exemptions are the companion's persistent geography contract:
`jxp_map_geography_contract_v011` and the four
`jxp_map_compat_{shimabara_belt,ikko_heartland,setouchi,wokou_waters}` province
flags. Clearing those without rebuilding the map contract would break the
parent/companion interface.

## Inventory Snapshot

| Inventory | Count |
| --- | ---: |
| Country flags created | 598 |
| Province flags created | 6 |
| Global flags created | 1 |
| Dynamic country modifiers created | 813 |
| Dynamic province modifiers created | 23 |
| Event-modifier definitions | 840 |
| JXP disasters | 2 |
| Exact disaster contracts present | 2 |
| Sword-hunt contract clauses present | 4/4 |

The standalone audit returned `246` hard failures:

| Failure class | Count |
| --- | ---: |
| Flags written but never read | 76 |
| Flags read but never written | 1 |
| Persistent state without any lifecycle cleanup | 40 |
| Content state absent from debug reset closure | 120 |
| Modifier definitions never added/read | 4 |
| Disaster count shortfall | 1 |
| Disaster start events resolving immediately | 2 |
| Missing disaster debug seed | 1 |
| Missing disaster debug end-cleanup parity | 1 |

## State Findings

### Orphan And Dangling Flags

The 76 write-only flags comprise five `jxp_22_*_taken` markers, all 37
`jxp_26_*_legacy_council_seen` markers, all nine
`jxp_29_*_house_compromise_seen` markers, and these 25 residual keys:

```text
jxp_24_horizon_question_recorded
jxp_24_realm_council_convened
jxp_china_coast_entrepots_done
jxp_cjp_rites_without_severance
jxp_confucian_shinto_synthesis_granted
jxp_daimyo_port_letters_seen
jxp_daimyo_ready_for_unification
jxp_debug_japan_unified
jxp_eastern_sea_lords_seen
jxp_ejp_imperial_constitution
jxp_ejp_rites_of_restoration
jxp_ejp_sun_over_eastern_seas
jxp_ikko_covenant_seen
jxp_kaikyo_conversion_active
jxp_kirishitan_conversion_active
jxp_mandate_claim_unified_celestial
jxp_north_pacific_charts_done
jxp_reformed_conversion_active
jxp_reviewed_translations_flag
jxp_rfj_free_seas_commonwealth
jxp_shimabara_mitigated
jxp_uncommitted_all_courses_open
jxp_uncommitted_realm_program_drafted
jxp_wak_black_tide_code
jxp_wokou_admiralty_seen
```

`jxp_50_show_legacy_detail_decisions` is the inverse defect: five decision
families read it, but no main or companion script ever creates it.

### Missing Lifecycle Cleanup

The 40 persistent states with no clear/remove path are:

- 25 country flags: `jxp_24_horizon_question_recorded`,
  `jxp_24_house_path_completed`, `jxp_24_realm_council_convened`,
  `jxp_cjp_rites_without_severance`, `jxp_daimyo_port_letters_seen`,
  `jxp_daimyo_ready_for_unification`, the three `jxp_ejp_*` identity flags,
  `jxp_hirado_consistory_done`, `jxp_kaikyo_port_law_codified`,
  `jxp_kaikyo_qadi_courts_seen`, `jxp_map_runtime_migration_v011`,
  `jxp_mission_runtime_repair_v0242`, `jxp_nagasaki_church_council_done`,
  `jxp_polity_initialized`, `jxp_polity_mechanic_registered`,
  `jxp_reformed_oranda_schools_seen`, `jxp_reviewed_translations_flag`,
  `jxp_rfj_free_seas_commonwealth`, `jxp_sakoku_edicts_seen`,
  `jxp_shimabara_mitigated`, both `jxp_uncommitted_*` completion flags, and
  `jxp_wak_black_tide_code`;
- eight permanent country modifiers: `jxp_24_foundation_{blade,edict,league}`,
  `jxp_24_ikko_realm_of_fellowship`, `jxp_24_sakoku_four_seas_watch`,
  `jxp_kirishitan_shimabara_compact`, `jxp_mission_court_order`, and
  `jxp_reformed_commonwealth`;
- seven permanent province modifiers: `jxp_hirado_congregation`,
  `jxp_kaikyo_reform_center`, `jxp_kirishitan_reform_center`,
  `jxp_kyoto_renewed`, `jxp_muslim_port_quarter`, `jxp_nagasaki_factory`, and
  `jxp_reformed_reform_center`.

### Missing Debug Reset Coverage

The transitive main/map reset closures miss 45 country flags, 59 country
modifiers, and 16 province modifiers. The largest families are 16 `jxp_24_*`
flags, six `jxp_synced_*_sword_hunt/sankin_kotai/expel_ronin` flags, and 54
`jxp_24_*` modifiers. The remaining country modifiers are
`jxp_kirishitan_shimabara_compact`, `jxp_mission_court_order`,
`jxp_mission_oceanic_ports`, `jxp_mission_tenka_state`, and
`jxp_reformed_commonwealth`.

The 16 missing province-modifier cleanups are:

```text
jxp_domain_school_city
jxp_hirado_congregation
jxp_kaikyo_newly_ordered
jxp_kaikyo_reform_center
jxp_kirishitan_newly_baptized
jxp_kirishitan_reform_center
jxp_kyoto_renewed
jxp_muslim_port_quarter
jxp_nagasaki_factory
jxp_northern_sea_port_office
jxp_osaka_ledger_city
jxp_reformed_newly_ordered
jxp_reformed_reform_center
jxp_sakai_merchant_quarter
jxp_south_sea_brokerage_port
jxp_translation_port_quarter
```

Four definitions are currently inert:
`jxp_black_tide_vanguard`, `jxp_confucian_newly_ordered`,
`jxp_ikko_disaster_modifier`, and `jxp_shimabara_disaster_modifier`. The last
two are removed by disaster end paths, but are never added or read.

## Disaster Findings

The current two definitions pass their exact static false-positive gates:

- Shimabara is limited to eligible Japanese polities, excludes resolved and
  Kirishitan/Reformed route states, requires 1620, no other active disaster,
  multiple pressure dimensions, Christian exposure, and the vanilla plus
  semantic-map Shimabara geography;
- Ikko is limited to eligible uncommitted Japanese polities, excludes IJP and
  resolved states, requires 1470, eight cities, low Tenka order, multiple
  pressure dimensions, and the vanilla plus semantic-map Ikko heartland.

They are not yet complete disasters. `jxp_kirishitan.4` sets
`jxp_shimabara_resolved` in both start choices, and `jxp_ikko.6` sets
`jxp_ikko_rising_resolved` in all three start choices. Consequently both
disasters resolve at their start event instead of sustaining an active crisis.
Ikko also has no dedicated `jxp_debug_seed_*` entry, and its end path removes
`jxp_ikko_disaster_modifier` while the debug reset does not.

The target remains 4-5 full disasters, so 2-3 additional systems are still
required. Each new system must receive an explicit checker contract and a
dedicated enter/resolve/cleanup debug route. Existing Shimabara and Ikko must
first be changed so the start event opens the crisis, later choices/events set
the resolved flag, and the end/debug paths clean the same state.

## Sword-Hunt Collision Gate

`jxp_decision_issue_sword_hunt` currently passes all four required clauses:
positive `jxp_is_japanese_polity_trigger = yes`, plus explicit negative gates
for `is_subject_of_type = daimyo_vassal`, `subject_sword_hunt`, and
`overlord_sword_hunt`. The mutation test removes each clause independently and
confirms the validator hard-fails every regression.

## Commands And Evidence

```powershell
$env:PYTHONPATH = '<repo>/japan_expanded_v2/tools'
python -m unittest japan_expanded_v2.tools.jxp_validation.tests.test_state_safety -v
# 9/9 tests passed

python -m jxp_validation.state_safety `
  --mod-root '<repo>/japan_expanded_v2' `
  --companion-root '<repo>/japan_expanded_v2_map'
# exit 1: 246 intentional audit failures listed above
```

No EU4 or launcher process was started. The checker is deliberately not yet
registered in `run_validation.py`; registration should occur only after the
lead agent fixes or explicitly contracts the reported gameplay state.
