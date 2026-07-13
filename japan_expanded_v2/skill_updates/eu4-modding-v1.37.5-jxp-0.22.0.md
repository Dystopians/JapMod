# EU4 Modding Skill Update: JXP 0.22.0

This patch-ready reference records rules verified against the local EU4
`v1.37.5.0 Inca` data. These rules supersede older broad heuristics in the
current `eu4-modding` reference.

## Mission topology

- EU4 exposes exactly five mission columns (`slot = 1..5`). `position` is the
  row inside that column.
- Two active mission series may reuse the same slot when their occupied row
  sets are disjoint. The illegal state is a duplicate active `(slot, row)`, not
  merely two group declarations with the same slot.
- Validate the effective tree, including vanilla and mod groups. Raw maximum
  positions in a vanilla file are not enough because mutually exclusive
  `potential` blocks do not coexist.
- Pin the inspected vanilla mission files by SHA256. Recompute the effective
  cells for representative tags and route flags whenever the supported game
  version changes.
- Every `required_missions` target must exist in the effective active catalog,
  the dependency graph must be acyclic, and every edge must point to a larger
  row. Cross-column prerequisites are legal when they still point downward.
- Route tags such as `CJP` do not inherit vanilla groups whose potential is
  strictly `tag = JAP`. Give transformed tags a legal five-column foundation
  band, then place route content below it.
- Call `swap_non_generic_missions = yes` only after tag, religion,
  harmonization and mutually exclusive route flags have reached their final
  state. Add a one-time hidden migration event for existing saves.

The reusable validator for this project is
`tools/jxp_validation/run_validation.py`. It combines the pinned vanilla
Japanese mission topology with the mod topology and permits disjoint row reuse.

## Confucian and Shinto state

- Treat `add_harmonized_religion = shinto` as one engine-owned transaction.
  Guard it with `NOT = { has_harmonized_with = shinto }` and keep exactly one
  scripted mutation site.
- Do not manually add or remove `harmonized_shinto`. Vanilla
  `on_harmonized_shinto` owns that modifier. Debug cleanup cannot undo engine
  harmony and must not fake an inverse by removing the modifier.
- Shinto incidents are religion-locked. After conversion to Confucianism, use
  mod-owned low-frequency bridge chains for the eight incident themes:
  Neo-Confucianism, urbanization, Nanban trade, firearms, Christianity,
  shogunate authority, Ikko leagues and Wokou.
- A bridge must not replay an incident that is active or already happened. It
  may set the vanilla completion flags that downstream vanilla missions use,
  but should store its own `started` and `done` flags as well.
- Before leaving Shinto, import the isolationism stance into the persistent
  opening variable as a floor, never as a destructive overwrite. Existing JXP
  investments must not be reduced.

## Native non-Christian reform centers

- `add_reform_center` is not restricted to Christianity. The destination
  religion must declare the source in `allowed_center_conversion`; for this
  project the version-pinned full religion copy adds `shinto` under
  `confucianism`.
- Define `confucianism_center_of_reformation` under
  `common/religious_conversions`. Restrict targets to Shinto provinces in
  `japan_region`, reject empty provinces, missionaries, existing centers,
  religious centers and religious zeal.
- Enforce a scripted cap of three centers and mark every JXP-owned center with
  a province flag. Cleanup removes only marked centers.
- Place deterministic centers in separated regions before using capital or
  random fallbacks. This prevents three centers clustering around one capital.
- Exclude Ise (`4359`) both in conversion weights and scripted spawning. Track
  JXP-owned zeal with a province flag so debug cleanup never removes unrelated
  religious zeal.
- Retire direct annual province-conversion effects after native centers are
  enabled. A hidden monitor may detect completion, but must not perform the
  conversions itself.

## Government reform consolidation

- Player-selectable route reforms belong in the existing vanilla monarchy
  levels 1-11. Do not append a long custom tier chain after level 11.
- Register visible route reforms in exactly one suitable vanilla level and do
  not auto-grant them. Auto-grant only hidden/basic route carriers.
- Founder-house reforms may share one vanilla level because narrow origin
  potentials make only the matching house choice visible. Preserve founder
  reforms when changing religious or diplomatic route.
- A version migration should remove obsolete route choices, restore current
  hidden carriers, regenerate government mechanics, then refresh missions.
- Government reform icons use the vanilla asset contract: `57x57` uncompressed
  RGBA DDS, sprite name `government_reform_<icon_key>`, and reform field
  `icon = "<icon_key>"`. Vanilla reform art is a framed opaque vignette; do not
  force transparency when that would violate the reference asset format.

## Validation order

1. Regenerate double-byte active localisation from UTF-8 source.
2. Run the general EU4 mod validator.
3. Run `tools/jxp_validation/run_validation.py --game-root <EU4 root>`.
4. Run its unit tests from the parent `tools` directory.
5. Inspect a contact sheet and DDS metadata for generated reform icons.
6. Launch a fresh game and inspect `error.log`; static checks cannot prove that
   a harmonized source religion will accept every native center conversion at
   runtime.

The active global skill path was read-only in the implementation sandbox, so
this file is the handoff source for the next writable skill-maintenance pass.
