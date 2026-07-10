# JXP Phase Report 0.13.1 - Daimyo Idea Identity Pass

Date: 2026-07-09

## Scope

Version `0.13.1` continues the long-term goal of making each daimyo tag feel less generic. This pass focuses on national ideas that had drifted toward broad conquest or discipline bonuses and retunes them toward the actual house identity, geography, institutions, or historical memory of the tag.

## Implemented

- Updated descriptors to `version="0.13.1"`.
- Adjusted 19 idea/group entries across the three daimyo idea files:
  - `jxp_15_daimyo_ideas.txt`
  - `jxp_17_minor_daimyo_ideas.txt`
  - `jxp_18_remaining_daimyo_ideas.txt`
- Added a later-sorting localisation override file:
  - `localisation_source/jxp_41_daimyo_idea_revision_l_english_utf8_source.yml`
  - `localisation/jxp_41_daimyo_idea_revision_l_english.yml`
- Added `daimyo_idea_revision_report` to `check_jxp_japan_coverage.py`.
- Updated the `eu4-modding` reference with the localisation-overlay pattern for safely editing older double-byte-patch localisation.

## Balance/Flavor Changes

- Tokugawa start no longer uses generic aggressive expansion reduction; it now emphasizes Mikawa/Fudai internal order.
- Takeda Kurokawa gold now supports fiscal/inflation control instead of generic diplomacy.
- Uesugi Agakita-shu now represents local manpower and unruly northern retainers rather than generic discipline.
- Hojo Odawara administration now focuses on state maintenance/governing reach instead of generic idea-cost reduction.
- Shimazu Tsurinobuse now emphasizes shock tactics and morale instead of plain discipline.
- Otomo retainers now grant army tradition/morale rather than another discipline source.
- Date expansion was split into northern governance, marriage diplomacy, and cultural patronage instead of stacking core creation, AE, and idea-cost reduction.
- Chosokabe's Hundred Article Code now provides order and state administration rather than discipline.
- Imagawa start and Kyoto march now emphasize prestige/diplomacy and campaign reach instead of discipline/core creation.
- Amago, Akita, Asakura, Maeda, Yamana, Satake, and Utsunomiya were similarly nudged toward castles, northern mobilization, courtly administration, rich-domain management, shugo prestige, family military memory, or Kanto absorption.

## Validation

Passed:

- `check_jxp_japan_coverage.py`
- `validate_eu4_mod.ps1`
- `check_mission_series_overlap.py`
- UTF-8 BOM check for `jxp_41_daimyo_idea_revision_l_english.yml`
- Vanilla `common` modifier-key lookup for revised modifier keys

No live in-game UI test was run in this pass.

## Follow-Up Candidates

- Continue idea retuning with the remaining tags that still use broad tax/manpower/development packages where a more local historical hook exists.
- Add a softer balance checker that flags repeated use of high-impact modifiers such as `discipline`, `core_creation`, `idea_cost`, and `development_cost` across daimyo idea groups for manual review.
- Revisit older mojibake-like localisation source files only if a full source-normalization pass is planned; otherwise keep using later-sorting override source files for surgical text fixes.
