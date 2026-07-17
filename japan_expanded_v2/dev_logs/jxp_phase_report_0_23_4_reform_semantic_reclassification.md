# JXP 0.23.4 Government Reform Semantic Reclassification

Date: 2026-07-09

## Player Report

Founder-house reforms were visible, but every one of them had been registered
inside monarchy tier 2, `hereditary_vs_nobility`. This made institutions such
as the Otomo `府内国崩炮所` appear under the noble-privilege heading even though
their names, modifiers, icons, and descriptions represented artillery, naval,
religious, commercial, or administrative systems.

## Root Cause

Version 0.23.2 deliberately placed all 38 founder reforms in one early tier so
the migration effect could auto-select exactly one without producing a 38-icon
wall. The origin potentials already limited each country to one relevant
founder reform, so the common tier and automatic assignment were no longer
necessary. They also made later-tier reforms unsafe to reclassify because an
automatic grant could bypass the normal eleven-tier progression.

## Semantic Matrix

- Tier 2, hereditary and nobility: 3 retainer, kokujin, and hereditary-house laws.
- Tier 3, bureaucracy: 1 founder lawbook plus 3 route bureaucracies.
- Tier 4, state and religion: 4 shrine/temple compacts plus 3 route institutions.
- Tier 5, military doctrines: 13 founder military systems plus 6 route systems.
- Tier 6, deliberative assembly: 2 founder councils plus 2 route councils.
- Tier 7, administrative growth: 4 cadastral/local offices plus 3 route systems.
- Tier 8, economic matters: 6 trade/port institutions plus 5 route systems.
- Tier 9, legitimation: 1 founder justice tradition plus 3 route systems.
- Tier 10, absolutism and constitutionalism: 2 founder constitutions plus 2 routes.
- Tier 11, separation of power: 2 founder court-office systems.

The original eleven monarchy level keys and their order remain unchanged. No
twelfth or later custom level was added.

## Behavioral Change

- Founder reforms are no longer auto-granted.
- A unified Japanese country sees only the reform associated with its recorded
  founder origin, in the thematically correct tier, and may choose it normally.
- Existing saves run hidden migration `jxp_migration_v023.4` after one day.
- If a founder reform was previously selected in tier 2, it is removed, tier 2
  receives `quash_noble_power_reform`, and 100 government reform progress is
  refunded. The founder reform then remains available in its new tier.
- `府内国崩炮所` and `长崎护教水军` now belong to tier 5 military doctrines.

## Copy Pass

Ambiguous reform names and descriptions were rewritten to match their new
institutional roles. The Otomo arsenal now describes gunfounders, powder
officers, siege command, garrison supply, and military registration. Tsushima,
Yamaguchi, Kaga, and Tango entries now read as economic/port institutions;
Muromachi and Buei offices now describe division of central responsibilities.

## Validation

- Descriptor version: `0.23.4`.
- General EU4 validator: pass.
- JXP release checks: 11/11 pass.
- Clausewitz gameplay files: 167/167 parse.
- Government reform matrix: 27 route + 38 founder reforms, each registered
  exactly once in its expected vanilla tier.
- Founder auto-grants: zero.
- Unit tests: 30/30 pass.
- Reform rewrite utility is idempotent across consecutive runs.
- EU4 was not launched, in accordance with the active user instruction.

## Player-Side Confirmation

After the next normal restart, load a unified-Japan save and advance one day.
The old tier-2 founder reform should be replaced by a normal tier-2 reform. The
origin-specific founder institution should appear as an available choice in its
new semantic tier; an Otomo-founded state should find `府内国崩炮所` under tier 5.
