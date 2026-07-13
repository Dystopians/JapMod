---
name: eu4-modding
description: Develop, extend, debug, and validate Europa Universalis IV (EU4) mods in local Windows installs. Use when Codex is asked to create or update EU4 mods, inspect EU4 game/mod directories, scaffold descriptor files, work with localisation, events, decisions, countries/tags, ideas, missions, flags, compatibility, Steam Workshop metadata, or preserve reusable EU4 modding knowledge as an evolving workflow.
---

# EU4 Modding

## Core Rules

- Treat the EU4 install directory as read-only unless the user explicitly asks otherwise. Use it for source lookup and examples.
- Put local mods under the user data path, normally `Documents/Paradox Interactive/Europa Universalis IV/mod`.
- Inspect the real environment first: read `launcher-settings.json`, confirm `rawVersion`, confirm the user mod path, and check whether the target mod already exists.
- For isolated runtime tests on EU4 1.37.5, use exactly one lower-case `-userdir=<absolute-path>` argument whose value is ASCII, unquoted, and contains no whitespace. Pin the executable, `launcher-settings.json`, and an empty game-root `userdir.txt`; prove the redirect with an independent visible probe before running gameplay scenarios. A path containing whitespace followed by option-like punctuation can be truncated by the game's command-line parser and silently fall back to the normal Documents tree. Reserve one canonical evidence directory outside mod/config/runtime surfaces, and authenticate its sealed session plus active nonce before any recovery cleanup.
- A release closure must not trust operator-authored static-gate receipts or a self-hashed historical execution. On first closure and every replay, run fixed non-shell validator argv against the exact candidate with OS-derived executable paths, a complete minimal environment, bounded streaming output, and before/after payload/process/toolchain guards. Bind repo inputs to one exact Git HEAD (including ignored/untracked rejection), installed skills to the Git-derived tree, and external Python/Windows/Git bytes to a reviewed Git-tracked baseline. Authenticate every batched Git blob response body against its object OID before accepting a stronger manifest hash; only an identified body-integrity mismatch may receive a small bounded reread. Run Python gates through an isolated/no-site/safe-path runner with standard library first and only exact copied dependency distributions afterward; when a Git-verified skill script must execute, allow only its exact canonical file and never add the skill directory as an import root. Seal the resulting raw output bytes and hashes. Replay must remain read-only but rerun the controlled gates as current authorization while separately verifying the old seal. Bind the canonical ledger through one uniquely headed, CommonMark-line/fence-aware structured journal object; control-character pseudo-lines, reserved-fence aliases, strings, or fake headings scattered across unrelated/fenced entries are not evidence.
- Prefer adding new files in the mod folder over copying and replacing large vanilla files.
- Use `replace_path` only for intentional full directory replacement, usually total conversions or map/history overhauls.
- Treat province-map work as version-pinned infrastructure. Prefer a separate companion map mod, preserve established province IDs/colors for scripted geographic anchors, require a new campaign, and document hard incompatibility with other map overhauls.
- For new visual assets, use image generation first, but inspect the same asset class in the pinned vanilla version before prompting or converting. Build a local reference contact sheet, match the visual grammar and exact file contract, and do not assume every DDS should be transparent: EU4 1.37.5 mission icons are opaque while many government-mechanic buttons use alpha.
- For Japanese daimyo flags, use vanilla Japanese flags as the direct style reference: one bold centered mon on a flat solid field, normally one ink color, with no gradients, fabric texture, scenery, text, European shield, or decorative border. Preserve the high-resolution generated source, then deterministically flatten the field and export a 128x128 24-bit RGB TGA.
- Preserve user changes in existing mods. Before editing an existing file, read it and make a scoped patch.
- For the local `japan_expanded_v2` project, treat `dev_logs/JXP_SHARED_DEVELOPMENT_LEDGER.md` in the main mod as the canonical cross-agent state. Read both mod-root `AGENTS.md` files and the ledger before editing, claim a stable ledger TODO for substantial work, and never create a competing current-status or TODO document. The lead agent owns ledger updates when subagents work in parallel.

## Workflow

1. Discover paths and version.
   - From the game root, read `launcher-settings.json`.
   - Resolve the user data path from `gameDataPath` or default to `%USERPROFILE%/Documents/Paradox Interactive/Europa Universalis IV`.
   - Before an isolated runtime test, read the **Isolated Runtime Userdir Contract** in `references/modding-reference.md`; do not treat a prepared folder or copied `dlc_load.json` as proof that the running process used it.
   - Check `mod/`, existing `.mod` descriptors, and any target mod folder before writing.
2. Scaffold or inspect the mod.
   - For new local mods, run `scripts/scaffold_eu4_mod.ps1`.
   - For existing mods, inspect `descriptor.mod`, outer `.mod`, and the relevant content directories first.
   - For local JXP work, also read the shared ledger, its active TODO and risks, the relevant historical report, and the companion compatibility contract before touching gameplay or map files.
3. Implement in small feature slices.
   - Localisation before or alongside gameplay keys.
   - Events and modifiers before decisions that trigger them.
   - Tags, country files, history, and flags before ideas/missions that depend on the tag.
   - Missions after icons and localisation keys are known.
4. Validate after every meaningful slice.
   - Run `scripts/validate_eu4_mod.ps1`.
   - For the local Japan Expanded `jxp_` framework at 0.22.0 or later, run `scripts/validate_jxp_mod.ps1`; it combines the general validator, the mod-owned pinned vanilla-plus-mod topology suite, and unit tests.
   - Before creating, extending, or reflowing a mission tree, read and follow the **Renderer-Safe Mission Tree Standard (RSMTS-1.37.5)** in `references/modding-reference.md`. For a newly authored full five-column tree, use its canonical parity grid unless reproducing an exact pinned topology or a documented pinned compact-Japan exception: slots `1/3/5` use odd rows, slots `2/4` use even rows, vertical visible edges advance two rows, and diagonal visible edges move one adjacent slot and one row. A compact exception may use one-row same-column steps only when pinned vanilla examples, the effective-profile geometry solver, source monotonicity, and final-profile density checks all pass.
   - Use `scripts/check_mission_series_overlap.py` as a mod-only fallback when a project lacks an effective-topology validator. For independently authored custom trees, it rejects two simultaneously active series in one slot even when their row ranges are disjoint, and also checks active `(slot, row)` collisions.
   - Treat `scripts/check_jxp_japan_coverage.py` as a legacy pre-consolidation audit until its project-specific expectations are updated; it still expects removed custom government levels.
   - Also use targeted `rg`/`Select-String` lookups in vanilla files for unfamiliar triggers, effects, icons, event pictures, government reforms, and units.
   - When validating mission icons or event pictures, resolve sprite names against both the mod's recursive `interface/**/*.gfx` registry and vanilla `interface/*.gfx`; a custom sprite is not missing merely because its name is absent from vanilla. Separately validate each registered `texturefile` path and binary image contract.
   - Require canonical mission localisation for every authored mission: `<mission_id>_title` and `<mission_id>_desc`. A bare `<mission_id>` key does not replace the `_title` key; keep it only as a compatibility alias when older content already used it. Regenerate escaped active localisation before rerunning visualizers and release gates.
   - Mission syntax and abstract DAG validity do not prove that EU4 can draw the tree. Validate the effective tree EU4 assembles for every concrete tag/route/religion/DLC/transient profile, including vanilla overrides and generic fallback. For a promised full national tree, require exactly one active custom non-generic owner in every visible slot `1..5`, unique cells, active prerequisites, and zero generic fallback.
   - When mission potentials enumerate tags, test every enumerated tag rather than one representative per archetype. A single omitted daimyo can silently lose its house column and receive a generic replacement while all representative profiles pass.
   - After adding, removing, or reclassifying mission series, give existing saves a one-time hidden migration that calls the canonical two-phase mission refresh. Reconstruct new progression flags from stable completed mission IDs; new effects added to an already-completed mission do not run retroactively.
   - A disabled `potential`/`potential_on_load` does not necessarily evict a non-generic mission series already serialized in an old save. For a pinned full replacement, retain every replaced top-level series under its exact original key as an unconditionally inactive same-path tombstone. Do not rename the key: a renamed definition cannot reconcile the key stored in the save. Route latent vanilla swaps through the canonical helper and treat a fresh `mission.cpp:353` overlap as proof that the saved series still needs migration.
   - Keep mission blocks inside each series in strictly increasing `position` order in the source file. EU4 assembles a column in declaration order; numerically valid positions do not repair a physically scrambled series. For compact Japanese-style trees, permit at most one empty row between consecutive declarations and no whole-profile vertical void wider than one row unless a pinned vanilla exception is documented.
   - Validate final-tree density, not only legality. For JXP unified profiles, every slot must contain at least five missions, route slots `3..5` must reach row 10, the five terminal rows may differ by at most five, and every named final tag/route must have a unique five-series signature. A five-slot tree can be collision-free yet still render as isolated stems if three columns end halfway down the shared spines.
   - When a final tag stops sharing a mission series, rebind both visible `required_missions` and hidden `mission_completed` gates to the replacement series. If a reflow generator preserves an older logical-graph snapshot, override that snapshot too; otherwise regeneration can silently restore inactive prerequisites. Effective-topology validation must reject every active mission that depends on an inactive mission in the same profile.
   - For dynamic route trees, use one canonical two-phase refresh helper: run `swap_non_generic_missions = yes` immediately so the open UI updates, guard and schedule a second swap one day later after tag/religion state settles, and run a `has_mission` fingerprint repair on startup with a low-frequency fallback for stale pending flags or interrupted old-save queues.
   - Gameplay `.txt` files normally must remain UTF-8 without BOM. If an older release already serialized BOM-prefixed mission-series keys, repair only those exact keys with byte-locked, `always = no` compatibility aliases plus a one-time delayed refresh. Put the exceptional files behind an explicit validator allowlist and a project check that compares their complete bytes; never permit arbitrary BOM gameplay files.
   - After changing to a tag whose national ideas are selected by a tag-triggered free idea group, call one canonical `swap_free_idea_group = yes` sync when `has_custom_ideas = no`. Do not rely on the optional `ideagroups.1` prompt when the route requires an exact idea set. Give old saves a one-time forced sync; a mixed group title/tooltip or `Missing Icon 'national_idea8'` is a stacked free-idea-group signature.
   - Do not set every dynamic candidate to `potential_on_load = { always = yes }`. Proven mission overhauls use normal narrow `potential` blocks and `swap_non_generic_missions = yes`; broad preload candidates can make mutually exclusive series compete during load.
   - Treat `potential_on_load` as a global preload gate, not a country-scoped mission `potential`. A tag, country flag, or country scripted trigger placed there cannot reliably exclude a vanilla series because no country scope exists yet. When a pinned full-tree override owns every affected country profile, use `potential_on_load = { always = no }` and `potential = { always = no ... }` on each replaced vanilla series; retain the shared country exclusion in `potential` as a documented second guard.
   - For player-selectable government reforms, treat `potential` as stable tree membership and `trigger` as the dynamic unlock gate. Put enduring identity such as Japanese polity in `potential`; put route flags, mission unlocks, and later choices in `trigger`. A reform can be defined and registered correctly yet never appear if a flag gained after campaign initialization is used only in `potential`.
   - Simulate government-reform visibility for every concrete final tag/route profile. Require the exact expected route set and reject missing or foreign-route options; definition count and first-11 registration alone do not prove what the government UI exposes. The canonical route sync should call `regenerate_government_mechanics = yes` after changing trigger-gating flags.
   - Register each visible reform in the existing first-11 level whose institutional theme matches its name, description, icon, and modifiers. Founder identity is not itself a level theme: artillery belongs in `military_doctrines`, port brokerage in `economical_matters`, shrine compacts in `state_and_religion`, and councils in `deliberative_assembly`. Enforce a complete reform-to-level matrix in validation.
   - Never auto-grant a parked, unregistered, or later-tier optional reform. Auto-granting an origin reform after moving it out of tier 2 can bypass normal progression or displace a player's choice. Use an origin-filtered `potential` so only one relevant founder option appears, and let the player select it when that tier unlocks. For old saves, remove the misplaced selected reform, restore a valid vacated-tier fallback, refund reform progress, and regenerate government mechanics.
   - `basic_reform = yes` is appropriate for an invisible mechanic carrier, not for an option promised inside the normal reform tiers. Validate definition, semantic first-11 registration, stable potential, dynamic trigger, migration, and an actual cold-start UI state as one chain.
   - Before runtime-testing a province expansion, validate bitmap/definition closure, province connectivity, positions and ports, area/region/climate/continent/trade membership, continuous dated history across the full selectable campaign, and a zero-difference mask outside the intended edit region plus any explicitly bounded cartographic expansion. Reposition every affected old and new province after a split.
   - Set a project-wide minimum province polygon from the pinned vanilla map instead of accepting any nonzero pixel count. Grow undersized mainland provinces only from explicit adjacent donors while preserving donor connectivity and size; for an isolated island that must remain separate, use a tightly bounded, documented cartographic exaggeration into named sea zones and synchronize `heightmap.bmp`, `terrain.bmp`, `rivers.bmp`, and `world_normal.bmp`.
   - Compare duplicate province RGBs against a pinned vanilla baseline: allow only exact inherited reservations and reject every new or changed duplicate. Inspect source-province connected components before allocating islands; if real GIS falls outside a stylized vanilla coastline, either split documented existing land components, omit the province, or explicitly change the coastline with support-map validation. Never paint ocean silently.
   - Do not treat exact preservation of pre-split development as automatically balanced. Record the vanilla baseline, choose and justify an explicit regional uplift cap when added granularity represents omitted population or towns, enforce per-province total floors plus named urban floors, preserve the parent region's tax/production/manpower profile, and close each category deterministically.
   - A date-slider map must validate every selectable day or an equivalent proven partition of all piecewise-constant intervals. Require unmodified old provinces to match the pinned vanilla owner/controller chronology exactly, require every new or intentionally changed province to match one explicit timeline, export continuous ownership intervals, and prove landed-country capital and subject invariants for the whole campaign. When rewriting ownership, remove only `owner` and `controller`; preserve vanilla `add_core` and `remove_core` history unless a separately audited design explicitly changes cores.
   - Keep companion-map integration additive where possible. Own the new tags, origin flags, on-actions, missions, legacy dispatch, debug cleanup, and validators in the companion instead of overriding the gameplay mod's core triggers/effects. Use explicit tag sets in mission `potential` when static tools must prove mutually exclusive same-slot series.
   - Treat a maintained parent-plus-companion pair as one release surface. The parent must not directly reference optional country tags, province IDs, area names, or mission IDs supplied only by the companion; consume free country/global/province flags instead. Let the companion initialize those flags and own exact checks for its optional mission column.
   - Split runtime mission fingerprints by ownership. The parent validates its shared columns and accepts a companion-origin marker without requiring the parent's house-column anchor; the companion validates its own exact anchor and invokes the parent's canonical refresh helper when stale. Add a one-time migration whenever companion mission positions or series ownership change.
   - When a companion splits vanilla areas, expose semantic macro-scopes through invisible province flags such as a historical belt, maritime circuit, or old macro-area. This preserves standalone parent loading while restoring event/disaster/mission coverage on the expanded map. Validate the exact `flag -> companion area set -> parent consumers` matrix.
   - Validate every generated country `primary_culture` against actual culture object keys in `common/cultures`; comments and display labels are not script keys. For combined daimyo missions, enumerate every companion tag across all relevant DLC states, require exactly one custom owner in slots `1..5`, no generic fallback, canonical odd/even row parity, active prerequisite closure, and no ID/cell collision.
   - For the local `japan_expanded_v2` + `japan_expanded_v2_map` pair, every gameplay change must pass both `validate_jxp_mod.ps1` and the companion's `tools/validate_all.ps1` without `-SkipMainModValidation`. The combined gate must continue to report map-sensitive fixed province/city thresholds until each is redesigned by historical purpose rather than mechanically scaled.
   - Keep the JXP shared ledger inside the release gate. It must agree with all four inner/outer descriptor versions, preserve stable unique TODO IDs and allowed statuses, point both `AGENTS.md` entry files to one canonical ledger, and index every historical report. A new phase report is incomplete until the ledger index and update journal are updated in the same slice.
   - A Clausewitz parser cannot prove that a scripted trigger exists. After any in-game load, inspect `logs/error.log` for `Parsing Errors`, `Unknown trigger type`, mission-series errors, and event namespace errors.
   - A Clausewitz parser also cannot validate hardcoded effect names. Before shipping a newly used effect, search the pinned vanilla files for its exact spelling. In EU4 1.37.5 government reform progress changes use `change_government_reform_progress`, not the plausible but invalid `add_government_reform_progress`.
5. Explain the in-game test route.
   - Tell the user which playset/mods to enable, what console command to run, and which decisions/events/missions should prove the change works.

## Useful Commands

PowerShell examples, assuming the current directory is the EU4 game root:

```powershell
$mod = "$env:USERPROFILE\Documents\Paradox Interactive\Europa Universalis IV\mod\my_mod"
.\path\to\eu4-modding\scripts\scaffold_eu4_mod.ps1 -ModId "my_mod" -DisplayName "My Mod" -GameRoot (Get-Location)
.\path\to\eu4-modding\scripts\validate_eu4_mod.ps1 -ModPath $mod -GameRoot (Get-Location)
.\path\to\eu4-modding\scripts\validate_jxp_mod.ps1 -ModPath $mod -GameRoot (Get-Location)
Select-String -Path decisions\*.txt -Pattern "change_tag =","swap_non_generic_missions = yes"
Select-String -Path interface\countrymissionsview.gfx -Pattern 'name = "mission_high_income"'
```

If local PowerShell execution policy blocks the scripts, run the same script through:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File ".\path\to\eu4-modding\scripts\validate_eu4_mod.ps1" -ModPath $mod -GameRoot (Get-Location)
```

## Resource Routing

- Read `references/modding-reference.md` for file layout, descriptor rules, localisation requirements, common snippets, known EU4 v1.37.5 patterns, and the mandatory **RSMTS-1.37.5** mission-tree design and acceptance standard.
- Run `scripts/scaffold_eu4_mod.ps1` to create a safe local mod skeleton with descriptors and common folders.
- Run `scripts/validate_eu4_mod.ps1` to check descriptors, brace balance, localisation BOM/header, country tags, flags, unit names, mission icons, and event pictures.
- Run `scripts/validate_jxp_mod.ps1` for current Japan Expanded work. It is the release gate for dynamic mission preload, two-phase refresh and runtime fingerprints, national ideas, government reform registration, Confucian bridges, assets, and effective EU4 1.37.5 mission topology.
- Run `scripts/check_mission_series_overlap.py` as a lightweight mod-only fallback; it catches active custom same-slot series overlap and cell collisions but cannot prove compatibility with vanilla/DLC trees.
- Run `scripts/check_jxp_ui_guardrails.py` for decision density, idea shape, hidden slots, and accidental custom post-11 reform levels. For current JXP mission geometry, rely on the mod-owned effective-topology suite: merely pointing to a larger row is not enough for a stable rendered arrow.
- Run `scripts/escape_eu4_special_localisation.py` when a Chinese EU4 double-byte-patch setup needs ordinary UTF-8 Chinese localisation converted into EU4SpecialEscape-compatible text.
- Run `scripts/patch_launcher_thumbnail.py` only after explicit user approval to back up `launcher-v2.sqlite` and set `mods.thumbnailPath` for a local mod thumbnail.

## Continuous Skill Improvement

When EU4 mod work reveals a reusable fact, bug pattern, command, or validation rule, update this skill during the same task:

- Put core procedure changes in `SKILL.md`.
- Put detailed domain knowledge and examples in `references/modding-reference.md`.
- Put repeatable deterministic checks or scaffolding in `scripts/`.
- After updates, run the skill validator and any changed scripts on a representative mod.
- In the final response, briefly mention what was added to the skill.
- For local JXP changes, also update the canonical shared ledger in the same slice: version/stat snapshot, TODO owner/status/evidence, new risks, report index, and newest-first update journal. Never turn a static pass into a runtime claim, and never launch EU4 without explicit user permission.

Do not add README, changelog, or unrelated docs inside the skill. Keep the skill lean and action-oriented.
