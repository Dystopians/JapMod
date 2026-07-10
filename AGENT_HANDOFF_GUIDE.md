# JapMod Agent Handoff Guide

This repository is the portable development source for **Japan Expanded V2 / 日轮诸道** and its
**Japan 88-province companion map**. It intentionally excludes the proprietary EU4 installation,
Steam Workshop content, saves, launcher databases, runtime logs, and local backups.

This guide explains how to enter and leave the project safely. It is not a second status page:
always read `japan_expanded_v2/dev_logs/JXP_SHARED_DEVELOPMENT_LEDGER.md` for the current versions,
open TODOs, risks, validation evidence, and newest update journal.

## Repository Layout

| Path | Purpose |
| --- | --- |
| `japan_expanded_v2/` | Main gameplay mod and canonical shared ledger |
| `japan_expanded_v2_map/` | Mandatory 88-province companion map and executable compatibility contract |
| `japan_expanded_v2.mod` | Portable launcher descriptor for the main mod |
| `japan_expanded_v2_map.mod` | Portable launcher descriptor for the companion map |
| `skills/eu4-modding/` | Repository-pinned Codex skill, references, and validation scripts |
| `AGENTS.md` | Repository-wide agent entry point |

The two top-level `.mod` files use `path="mod/..."` so they can be copied into the EU4 user-data
`mod` directory. If the repository is kept elsewhere, generate local descriptor copies with absolute
paths to the two repository subdirectories; do not commit host-specific paths.

## First Ten Minutes

1. Read, in order:
   - `skills/eu4-modding/SKILL.md`
   - root `AGENTS.md`
   - `japan_expanded_v2/AGENTS.md`
   - `japan_expanded_v2/dev_logs/JXP_SHARED_DEVELOPMENT_LEDGER.md`
   - the phase report named by the relevant ledger entry
2. For map or cross-mod work, additionally read:
   - `japan_expanded_v2_map/AGENTS.md`
   - `japan_expanded_v2_map/dev_logs/BASELINE_LOCK.txt`
   - `japan_expanded_v2_map/tools/jxp_map_validation/main_compatibility_contract.json`
3. Confirm the installed game is the pinned EU4 version recorded by the ledger and keep the game root read-only.
4. Run the smallest relevant static baseline before editing.
5. Claim an existing ledger TODO, set one owner, and add a `STARTED` journal entry. Add a new stable TODO ID only when no existing item covers the work.

## Local Setup

Keep the Git checkout outside the Steam installation. A typical checkout is:

```text
<Documents>/GitHub/JapMod/
```

For launcher use, either copy the two mod directories into:

```text
<Documents>/Paradox Interactive/Europa Universalis IV/mod/
```

or keep the Git checkout in place and create local, uncommitted launcher descriptors whose `path`
values point to the checkout subdirectories. Never commit a username-specific absolute path.

The companion map requires the main mod, a new campaign, and the compatibility boundaries recorded
in `BASELINE_LOCK.txt`. Do not combine it with another overhaul of Japanese map bitmaps, areas,
province history, or the Nippon trade node.

## Development Rules

- Preserve user changes and edit generator sources when a generated file has an established owner.
- Main gameplay changes must remain compatible with the companion map in the same development slice.
- Do not hard-reference optional companion tags, province IDs, areas, or missions from the main mod.
- Mission, route, idea, reform, tag, and map changes require migration analysis or an explicit new-campaign boundary.
- Active Chinese localisation follows the existing UTF-8 BOM and EU4SpecialEscape pipeline; Markdown remains ordinary UTF-8.
- Do not describe static validation as an in-game result.
- Do not launch EU4, the launcher, or an observer game without explicit user permission.

## Required Static Gates

From the repository root, set the host-specific game path and run:

```powershell
$repo = (Get-Location).Path
$game = 'D:\Steam\steamapps\common\Europa Universalis IV'

powershell.exe -NoProfile -ExecutionPolicy Bypass -File `
  "$repo\skills\eu4-modding\scripts\validate_jxp_mod.ps1" `
  -ModPath "$repo\japan_expanded_v2" `
  -GameRoot $game

powershell.exe -NoProfile -ExecutionPolicy Bypass -File `
  "$repo\japan_expanded_v2_map\tools\validate_all.ps1" `
  -GameRoot $game `
  -MainMod "$repo\japan_expanded_v2"
```

If the embedded skill changes, also run the Codex skill validator available on the host. Record the
exact command and result in the shared ledger. Runtime acceptance remains pending until the user
explicitly authorizes a current-version game run.

## Git Workflow

1. Work on a focused branch or worktree; do not develop directly on `main`.
2. Keep unrelated changes out of the commit.
3. Run both static gates before publishing.
4. Update the shared ledger in the same slice with files touched, evidence class, remaining risks, and next TODO.
5. Review `git diff --check`, the staged diff, and large-file limits before pushing.
6. Open a draft pull request unless the user explicitly requests otherwise.

## Handoff Checklist

Before giving the project to another agent, state:

- branch, commit, and pull-request link;
- exact files and systems changed;
- what was deliberately not changed;
- main, combined, and skill validation results;
- whether evidence is `STATIC_PASS`, `RUNTIME_PASS`, `USER_OBSERVED`, or `PENDING_RUNTIME`;
- the stable ledger TODO that should be taken next;
- any required new-campaign, migration, DLC, or compatibility constraints.

The repository was first imported to GitHub on 2026-07-10. The authoritative import record and all
subsequent project history belong in the ledger's newest-first Update Journal.
