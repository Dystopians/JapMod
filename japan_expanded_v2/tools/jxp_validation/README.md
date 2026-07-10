# Japan Expanded 0.24.0 Validation

This standard-library-only suite validates the staged mod without modifying it.

Run the one command entrypoint from the mod root:

```powershell
python tools\jxp_validation\run_validation.py
```

The entrypoint auto-detects
`D:\Steam\steamapps\common\Europa Universalis IV` when present. Otherwise pass
the install explicitly:

```powershell
python tools\jxp_validation\run_validation.py --game-root "D:\Steam\steamapps\common\Europa Universalis IV"
```

The command exits `0` when every check passes, `1` for content failures, and
`2` for invocation or validator errors. Use `--json` for CI output,
`--verbose` for separate vanilla/mod cell summaries, `--mod-root PATH` to
inspect another staged copy, and `--max-details 0` to print every diagnostic.

## Checks

- Parses Clausewitz script while preserving duplicate keys and source lines.
- Validates mission slots `1..5`, positive rows, unique mission ids, complete
  dependencies, an acyclic dependency graph, and dependency edges that point
  to larger rows. Broad `potential_on_load = { always = yes }` candidates are
  rejected; dynamic branches use narrow `potential` blocks and the guarded
  mission swap instead.
- Enforces one delayed `swap_non_generic_missions` execution point, verifies
  all route transitions use the guarded refresh helper, and requires an
  old-save topology migration.
- Validates all seven route end-tag idea groups, their tags, seven-idea shape,
  minimum strength structure, route signatures, and modifier keys against the
  vanilla idea and custom-idea catalogs.
- Evaluates exact `(slot, row)` occupancy for all 37 supported daimyo tags
  across the five house layouts,
  uncommitted and mutually exclusive JAP Shinto states, CJP Confucian with
  harmonized Shinto, KJP Christian, EJP Imperial, RFJ Reformed, SJP Kaikyo,
  IJP Ikko, and WAK Wokou. Two independently authored JXP series may not share
  an active slot even when their occupied rows are disjoint; EU4 can log
  `mission.cpp:353` and misdraw them.
- Requires every representative daimyo and unified-Japan profile to activate
  one custom non-generic series in each of slots `1..5`. Any vanilla generic
  fallback series is a release-blocking failure rather than an accepted filler.
- Builds an effective vanilla-plus-mod topology from the actual EU4 1.37.5
  Japanese mission potentials. It checks combined collisions, active and
  inactive prerequisites across sources, forward dependency edges, cycles,
  and the five-column limit. Visible edges must match the renderer geometry
  measured from the pinned Japanese trees: at most two rows, adjacent columns,
  no occupied cell in a vertical segment, no crossing diagonals, and no more
  than three visible parents.
- Verifies every transformed route tag has no active vanilla Japanese mission
  cells and activates all 13 foundation missions after those missions are
  consolidated into the shared state/court series. Daimyo profiles must not
  activate the unified foundation missions.
- Verifies every `jxp_*` trigger called from mission potentials and trigger
  blocks is actually defined under `common/scripted_triggers`.
- Treats the 27 `jxp_reform_*` definitions in
  `jxp_18_route_reforms_extra.txt` as visible route reforms and the 38 in
  `jxp_28_founder_house_reforms.txt` as founder reforms. Both sets must be
  registered exactly once in the vanilla monarchy levels `1..11`; all other
  `jxp_reform_*` definitions are parked and must remain unregistered.
- Rejects custom JXP reform-level keys and auto-grants of visible route reforms.
- Validates the Confucian-Shinto harmonization mutation, full religion copy,
  custom conversion definition, three-center cap, province `4359` exclusion,
  marker cleanup, and completion guard.
- Requires a UTF-8 BOM and no raw CJK characters in every active
  `localisation/**/*.yml` file.
- Resolves referenced JXP icon sprites and their textures. Reform DDS files
  must be uncompressed 32-bit RGBA at `57x57` with a nonblank alpha channel.

The release target defaults to `0.24.0`; override it only for an intentional
validation of another staged release with `--expected-version`.

Representative profiles assume the `Domination` and `Mandate of Heaven` DLCs
are enabled. The JAP open profile carries vanilla's
`jap_chose_kaikoku_flag`; the sakoku profile carries
`christianity_defeated_flag`; the uncommitted profile carries neither. These
states select actual mutually exclusive vanilla potential branches while the
validator continues to evaluate every condition from the parsed files.

## Vanilla Pin

The effective topology is pinned to `EU4 v1.37.5.0 Inca (491d)`. A manifest is
necessary because version metadata alone cannot prove that the mission files
are unmodified. The suite reads each listed file, verifies its SHA256, and then
evaluates its real group potentials:

- `missions/Japanese_Missions.txt`:
  `67b3f0abb6276fb11f2688c2f7269eb9086e0afd7a2d778e6bc4bf856c028fd5`
- `missions/DOM_Japanese_Missions.txt`:
  `55917ac903b47ba943ed8e0256bdd19af7bec65443e2f72a633e3d4cded98525`

The machine-readable source is
`tools/jxp_validation/vanilla_1_37_5_manifest.json`. A hash mismatch is a hard
failure so an EU4 update or locally edited vanilla file cannot silently change
the effective topology.
