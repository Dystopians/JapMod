# JXP Original-Machine R5 Recovery And Portability Baseline

Date: `2026-07-13` (America/Los_Angeles)
Evidence class: `STATIC_FORENSIC_EVIDENCE`
Runtime claim: `NONE`

This report records the original-development-machine recovery that unblocked the missing R5 migration fixture. It is immutable historical evidence, not a second current-status page. Current TODO state, blockers, and execution order remain owned by `JXP_SHARED_DEVELOPMENT_LEDGER.md`.

## Recovery Boundary

- Repository checkout: `C:\Users\Fiber Memory\Documents\GitHub\JapMod`
- Reviewed Git baseline: `1b68bb3559edb3377c7c72b1956c2f27e20b67b0`
- Game root: `D:\Steam\steamapps\common\Europa Universalis IV` (read-only)
- Daily EU4 user-data root: `C:\Users\Fiber Memory\Documents\Paradox Interactive\Europa Universalis IV`
- External escrow root: `C:\JXP_R5_Escrow\20260713_original_machine`
- No EU4, Launcher, dowser, bootstrapper, or observer process was started.
- No source save or backup was loaded, renamed, decompressed, resaved, edited, or overwritten.

## Recovered Files

| Role | Original path/name | Size (bytes) | SHA-256 |
| --- | --- | ---: | --- |
| Authentic pre-0.24.2 engine save | `save games\autosave.eu4` | 36,371,037 | `9F6DD96A60C7B9F583C22F87E7DA2F5C659E2EDC14723483A077B7AFD73A8BEF` |
| Named backup 1 | `japan_expanded_v2_before_mission_layout_hotfix_20260709_154614.zip` | 47,308,072 | `64F11ACE4F049B799B1C9D5CF0FA64D0A75ABF485D90C0DBC0814FC71107485D` |
| Named backup 2 | `japan_expanded_v2_before_series_consolidation_20260709_161217.zip` | 47,373,265 | `C05C1B9EE8D1AAB31E02B472AE2C8F897CDFA08E07B33B75367EAC1B3984AE3D` |
| Named backup 3 | `japan_expanded_v2_before_reform_visibility_hotfix_20260709_164900.zip` | 48,071,664 | `CDBCFD3A7ABE5653BC8C44A377912511C6EC864587D0A504AEC21C949F6B6AE4` |

The ZIP descriptors identify the three backups as `0.23.0`, `0.23.1`, and `0.23.1` respectively. Source and escrow size/hash pairs were re-read after copying and matched exactly.

## Save Content Identity

The helper's strict EU4 text-save parser accepted the recovered save as `EU4txt`, with 1,794,479 parsed lines and maximum brace depth 7. The save header records:

- date `1445.1.1`;
- player `JAP`;
- EU4 `1.37.5.0 Inca`;
- the two Chinese localisation mods and `日轮诸道：日本扩展风味包` enabled;
- player flag `jxp_path_open_trade=1444.12.18`.

The player has these exact 13 completed JXP missions:

1. `jxp_mission_daimyo_domain_accounts`
2. `jxp_mission_harbor_mosque_registers`
3. `jxp_mission_land_survey_state`
4. `jxp_mission_matsumae_treaties`
5. `jxp_mission_nanban_factory`
6. `jxp_mission_northern_sea_office`
7. `jxp_mission_open_nagasaki`
8. `jxp_mission_osaka_rice_ledger`
9. `jxp_mission_road_to_kyoto`
10. `jxp_mission_secure_home_domain`
11. `jxp_mission_settle_the_realm`
12. `jxp_mission_south_sea_brokers`
13. `jxp_mission_unite_the_isles`

The serialized player mission ownership simultaneously contains DOM and JXP series in all five slots. Raw BOM-prefixed JXP series occur with these exact whole-save counts:

| Series | Count |
| --- | ---: |
| `jxp_daimyo_domain_missions` | 35 |
| `jxp_ikko_route_missions` | 1 |
| `jxp_japan_eastasia_missions` | 9 |
| `jxp_japan_state_missions` | 8 |
| `jxp_kirishitan_deep_missions` | 1 |
| `jxp_shinto_branch_missions` | 3 |

These facts match the pre-0.24.2 failure described by the 0.24.1 phase report and establish that this is the authentic R5 input rather than a later save relabelled as an old fixture.

## Chain Of Custody

The escrow directory was created outside the repository, game root, daily user-data root, and future acceptance root. Its ancestor chain was checked for reparse points before copying. The following sidecars were written in escrow:

- `r5_external_input_provenance.json`
- `r5_external_input_hash_manifest.txt`
- `r5_content_identity.json`

The source bytes remain at their original paths. The escrow copy is the only candidate that may be offered to the acceptance helper. The save and backups must not be committed, pushed, uploaded, or shared outside the machine without separate user authorization.

## Current-Host Portability Baseline

The acceptance helper was authored on a profile rooted at `C:\Users\meizhanxuan`. On this original machine the Windows profile is `C:\Users\Fiber Memory`, whose Documents path contains whitespace. The inherited default `C:\Users\Fiber Memory\Documents\JXP_Acceptance` is therefore invalid for the pinned EU4 1.37.5 `-userdir` parser.

The pre-change helper suite ran 52 tests and produced 1 failure plus 15 errors. Every failure traces to host portability: the old acceptance root, the old trusted Git path, or the old external-toolchain baseline. This is a baseline result, not a product regression.

Reviewed current-host candidates are:

- canonical isolated acceptance root: `C:\JXP_Acceptance`;
- Git executable: `C:\Program Files\Git\mingw64\bin\git.exe`;
- Git SHA-256: `C39B1B4F7A57935BBEADF246DC2466316619453A6A9DA77C4A9C6BD6D8FB21D3`;
- validation Python: `C:\Users\Fiber Memory\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe`;
- Python: `3.12.13`;
- NumPy/Pillow/PyYAML: `2.3.5` / `12.2.0` / `6.0.3`.

These values are candidates until the reviewed portability patch, tests, and controlled gates pass. No acceptance root or session was created as part of this report.

## Required Follow-Up

1. Port the helper, README, matrix PROBE argv, trusted Git pin, and external-toolchain baseline to the reviewed current-host values.
2. Extend the external-input contract to pin the recovered save's filename, size, SHA-256, header identity, 13 completed missions, five player mission slots, and six BOM-prefixed series counts.
3. Add positive and adversarial tests for authentic-source acceptance and wrong/tampered-save rejection.
4. Strictly validate all escrow sidecars, then remove the R5 and dependent R13 blockers through a reviewed matrix change.
5. Re-run helper tests, both static release gates, runtime oracle check, skill validation, and `git diff --check`.
6. Only after those steps, prepare `C:\JXP_Acceptance` without launching the game.
7. Request explicit user permission before PROBE or any R1-R12 EU4 session.

Until the reviewed matrix and all static gates pass, the recovered save status is `FOUND_ESCROWED_NOT_ADMITTED`; it is not yet runtime evidence and closes no TODO by itself.
