# EU4 Modding Skill Update: Dynamic Missions and Idea Validation

Verified against local EU4 `v1.37.5.0 Inca (491d)` and JXP 0.23.0.

## Dynamic mission candidates

- A mission branch that can become eligible after game start should be kept in
  the candidate pool with a broad, static `potential_on_load`. Use dynamic tag,
  religion and route conditions in `potential`, not in the preload filter.
- Treat `swap_non_generic_missions` as a state-commit operation. After changing
  tag, religion, harmonization, route flags or government, schedule one hidden
  country event for the following game day and execute the swap there.
- Route every caller through one scripted refresh helper. A pending flag avoids
  duplicate event queues and must be cleared by the delayed event.
- Add a new one-time migration flag whenever saved countries need a refresh.
  Reusing an older migration flag leaves already-migrated saves untouched.
- A misleading engine tooltip can be suppressed by keeping the scheduling
  helper in `hidden_effect`; the actual swap remains in the hidden event.

## Mission topology

- Preserve mission IDs during a layout rewrite so completed-mission state can
  survive old-save migration.
- Validate every representative effective profile, not each file in isolation.
  A prerequisite is legal only when its defining series is active in that same
  profile.
- Never make a shared mission depend on one of several mutually exclusive
  house or route missions. Exclusive branches may depend on shared nodes; the
  reverse direction would make other profiles impossible.
- Five columns can still look linear when each series is a straight chain.
  Measure cross-column edges, multi-parent merge nodes and multi-child fork
  nodes, then enforce a minimum in validation.
- A useful vanilla-like pattern is: five-column foundation diamond, two-column
  state ladder, three-column route braid, and late shared side branch.
- Every dependency edge must point to a strictly larger row. Sparse rows are
  valid and are often necessary to weave branches without collisions.
- Retire checks that reject every pair of active series sharing a `slot` or
  every cross-column arrow. Same-slot series are legal when their active row
  sets are disjoint, and cross-column prerequisites are the basis of vanilla
  forks and merges. Validate active `(slot, row)` cells instead.
- After consolidating reforms into vanilla levels 1-11, retire coverage rules
  that still require the old `jxp_route_institution_*` government levels.
  Coverage must inspect actual registrations in vanilla levels.

## National idea audits

- Validate route idea modifiers against keys actually present in the pinned
  game's `common/ideas` and `common/custom_ideas` catalogs.
- EU4 1.37.5 uses `global_trade_goods_size_modifier` for national goods output
  and `navy_tradition` for yearly naval tradition. Similar-looking aliases may
  parse as script yet do nothing.
- Religion-specific modifiers must match the route religion. Reformed countries
  use `monthly_fervor_increase`; `church_power_modifier` is Protestant-specific.
- For upgraded formable/end tags, enforce seven ideas, correct tag triggers, a
  minimum modifier count, several dual-modifier ideas, and route-signature
  effects. Compare strength against the actual vanilla formable benchmark.

## Runtime test sequence

1. Change route/tag and leave the mission panel.
2. Unpause for at least one game day so the hidden refresh event executes.
3. Reopen missions and verify the expected groups, completed-state retention,
   and no generic fallback.
4. Save, reload, and verify the migration flag prevents repeated rebuilding.
5. Inspect `error.log` for unknown modifiers and mission candidate failures.

The installed global skill path was read-only in this sandbox. This file is the
patch-ready handoff for the next writable skill update.
