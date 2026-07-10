# EU4 Modding Reference

## Environment Discovery

From an EU4 game root, `launcher-settings.json` contains:

- `rawVersion`, such as `v1.37.5.0`
- `version`, such as `EU4 v1.37.5.0 Inca (491d)`
- `gameDataPath`, usually `%USER_DOCUMENTS%/Paradox Interactive/Europa Universalis IV`

Default Windows paths:

```text
Game root: D:\Steam\steamapps\common\Europa Universalis IV
User data: %USERPROFILE%\Documents\Paradox Interactive\Europa Universalis IV
Mods:      %USERPROFILE%\Documents\Paradox Interactive\Europa Universalis IV\mod
Logs:      %USERPROFILE%\Documents\Paradox Interactive\Europa Universalis IV\logs
```

## Descriptor Files

Local mods need an outer descriptor in the user `mod` folder and an inner `descriptor.mod`:

```text
mod\my_mod.mod
mod\my_mod\descriptor.mod
```

Outer descriptor:

```txt
name="My Mod"
path="mod/my_mod"
supported_version="1.37.*"
tags={
	"Gameplay"
	"Events"
}
```

Inner `descriptor.mod` should omit `path`:

```txt
name="My Mod"
supported_version="1.37.*"
tags={
	"Gameplay"
	"Events"
}
```

Workshop descriptors may include:

- `path`: folder path for unpacked content
- `archive`: packed legacy/bin content
- `remote_file_id`: Steam Workshop ID, usually launcher-managed after upload
- `dependencies`: launcher-level dependency names
- `replace_path`: full replacement of a vanilla directory; avoid unless intentional

The Paradox launcher may rewrite a local outer `.mod` `path` from `mod/my_mod` to an absolute forward-slash path. Treat this as acceptable if it points to the same local mod folder.

## File Map

```text
common/country_tags       tag -> country file registry
common/countries          country colors, graphical culture, unit list, names
common/event_modifiers    country/province modifiers used by events and missions
common/ideas              national/group ideas
decisions                 country decisions
events                    country/province events
gfx/flags                 TGA flags named TAG.tga
history/countries         country history, government, culture, religion, capital
localisation              text keys, UTF-8 BOM, language header
missions                  mission trees
interface                 vanilla UI, mission icon, and event picture lookup
map                       high-risk map files; avoid for first-pass mods
```

Keep EU4 script `.txt` files in UTF-8 without BOM. A UTF-8 BOM at the start of
files such as `common/governments/00_governments.txt` can corrupt the first
top-level token and produce cascading `persistent.cpp` parsing errors even when
brace balance and visible text look correct. Localisation `.yml` files are the
opposite and should retain a UTF-8 BOM. Unicode descriptor names may also need a
BOM, so the general validator applies the no-BOM rule specifically to script
`.txt` files.

For each custom country file, provide at least ten entries in both
`leader_names` and `ship_names`. EU4 otherwise writes `countrydatabase.cpp`
errors such as `has less than 10 random leader names` or `has less than 10
random ship names` during startup. The general validator checks these lists.

## Province Map Expansion

Treat a province expansion as a version-pinned map product, not an ordinary additive content slice. A regional expansion is usually safest as a separate companion mod that depends on the gameplay mod, requires a new campaign, and declares incompatibility with other mods that override `provinces.bmp`, areas, trade nodes, or the same province histories.

Preserve existing province IDs and RGB colors wherever scripts use them as geographic anchors. Keep the old ID on the same city, shrine, port, island, or regional core and carve new IDs around it. Allocate new IDs above the supported version's highest defined ID, keep them contiguous, and set `max_provinces` to one past the highest ID. Re-scan the effective VFS before assigning country tags or province IDs; a mnemonic code that looks free may already belong to an unrelated vanilla country.

When the requested detail can fit inside the existing coastline, do not edit `heightmap.bmp`, `rivers.bmp`, `terrain.bmp`, `trees.bmp`, or `world_normal.bmp`. Clip new province colors to the old land mask and require a pixel diff against vanilla to be zero outside an explicit target-region mask. Existing islands that are already painted as part of a larger province can be separated without changing the coastline; an island absent from the land mask is a separate coastline project.

Nonzero is not a useful clickability standard. Measure every land province in the pinned vanilla map and adopt a documented floor no smaller than its minimum ordinary land province unless runtime evidence justifies an exception. For undersized mainland provinces, transfer only four-neighbour-connected pixels from explicitly listed historical neighbours; after each transfer, prove that the recipient remains connected and the donor neither disconnects nor falls below the floor. For isolated islands, prefer merging at map scale, but when the design requires a separate province, permit a minimal cartographic exaggeration only when the plan names the target province, allowed sea IDs, target size, and growth radius. Record every added coordinate in the manifest.

If an island expansion changes the land mask, generate matching full-size support maps from the pinned vanilla inputs. Preserve the indexed palettes of `terrain.bmp` and `rivers.bmp`, keep `heightmap.bmp` as 8-bit grayscale, keep `world_normal.bmp` as half-size RGB, and reject support-map changes outside the island/support masks. Copy or interpolate from the island's original pixels rather than inventing unrelated terrain. This is still a runtime-sensitive coastline edit: static closure cannot prove its final 3D appearance.

Enumerate the connected components of every source province before assigning island children. EU4 often compresses or relocates small island chains, so historically accurate GIS polygons can project entirely onto vanilla ocean. Under a preserve-coastline contract, use a documented semantic split of the existing island components or remove that planned province; never silently paint new land merely to make the GIS overlap. Store the fallback and component sizes in the generated manifest so later maintainers know it was deliberate.

Regional province expansion normally requires version-pinned full copies of:

- `map/provinces.bmp`, `definition.csv`, `default.map`, and `positions.txt`;
- `map/area.txt`, `region.txt`, `climate.txt`, and `continent.txt`;
- `map/adjacencies.csv` when straits change;
- the file that owns the affected trade node;
- affected province histories and regional diplomacy history.

Do not use `replace_path = "history/provinces"` for a regional companion mod unless it also supplies every province history in the world. Override only the affected vanilla filenames and add the new ID files. Record hashes for every full-file vanilla override so a game update cannot silently mix map versions.

Build the map validator before large-scale raster editing. It should reject:

- bitmap colors missing from `definition.csv`, definitions with no pixels, new or changed duplicate RGB values, wrong image dimensions/mode, or a bad `max_provinces`;
- disconnected land provinces except an explicit multi-island whitelist, one-pixel corridors, isolated speckles, holes, and diagonal-only contacts;
- city, unit, text, trade, or port positions outside the province, and ports that do not touch their assigned sea zone;
- land provinces missing or duplicated across area, region, continent, climate, and trade-node membership;
- any changed pixel outside the allowed regional mask and explicitly enumerated cartographic expansion;
- a province below the pinned pixel floor, a donor disconnected by rebalancing, an island grown from an unapproved sea province, or support-map pixels changed outside their planned masks.

Do not assume the vanilla `definition.csv` itself is perfectly unique. EU4 1.37.5 contains ten inherited duplicate RGB reservations across IDs 3600-3619. Pin the supported vanilla definition as a baseline, allow only those exact inherited pairs, and fail on any duplicate introduced or altered by the mod. A validator that blindly rejects every duplicate will report a false failure; one that ignores all duplicates can hide a map-breaking collision.

Historical alignment is continuous, not a set of bookmark screenshots. Parse every affected `history/provinces` and `history/countries` file into a dated state model. For strongest assurance, walk every selectable day from campaign start to the exclusive end; because EU4 province history is piecewise constant, validating a complete, gap-free partition of every interval is mathematically equivalent, but a daily sweep is cheap for a regional map and easier to explain. At each date require every land province to have a valid owner/controller, every active country to own its capital, every subject to own land and have exactly one overlord, and extinct tags not to survive as ghost subjects.

Split the ownership proof into two sources. Provinces without an intentional override must have the exact root owner and dated owner/controller sequence from the pinned vanilla file. Every new province and each deliberate old-province divergence must have one explicit, sorted, unique, in-campaign, non-no-op timeline. Export a CSV of `province_id, source, parent, start_inclusive, end_exclusive, owner` and verify that it reconstructs the generated histories exactly. When replacing ownership in a copied vanilla history, scrub only `owner` and `controller`; deleting `add_core` or `remove_core` while changing owners silently destroys unrelated historical state.

Adding provinces must not automatically multiply regional power, but exact no-growth conservation is also a design choice rather than a law. Record the original region's tax, production, manpower, centers of trade, gold provinces, and trade-good distribution; then choose an explicit total and cap. If finer provinces represent towns and population omitted by the coarse vanilla map, a documented moderate uplift can be more credible than splitting the old total into dozens of 1/1/1 provinces.

For deterministic allocation, give every province a total floor, allow lower named floors only for genuine frontier or remote islands, and set explicit floors for major urban/economic centers. Complete those floors across tax, production, and manpower using the inherited parent profile and remaining category capacity, then distribute the remainder by overlap weights and largest remainders. Validate the exact category totals, minimums, distribution histogram, and uplift over vanilla. Re-audit fixed province-count missions and disasters after expansion. Whole-region scopes often scale naturally, while conditions such as "own 15 provinces" may need a development, area, or strategic-anchor replacement.

New historical countries need registration, country/history files, flags, localisation, ideas or an intentional generic idea path, capitals, rulers, and dated subject relationships. Give every country at least ten random leader names and ten ship names to avoid `countrydatabase.cpp` startup errors. First route them through generic culture/government/region gates; add bespoke missions only after the map and timeline are stable. When several bespoke series share a slot, place explicit mutually exclusive tag sets in each `potential`; many static topology tools do not expand arbitrary scripted triggers and otherwise cannot prove exclusivity. Update canonical tag/origin coverage, unified-country legacy effects, debug cleanup, and visualizer/catalog inputs in the same slice.

For a companion map that extends a gameplay mod, prefer additive ownership of integration state. Record origins through companion on-actions, call a small public initialization effect if the parent exposes one, and keep companion missions, legacy dispatch, debug reset, and visualizer inputs in companion files. Avoid replacing the parent mod's central scripted triggers or effects merely to add new tags; that creates a fragile load-order fork and makes concurrent development unsafe.

### Parent-Companion Compatibility Contract

Treat a maintained gameplay mod and its companion map as one effective VFS during validation, while keeping either mod's ownership boundaries explicit. A parent that must still load alone cannot safely name an optional tag, new province ID, companion-only area, or companion-only mission in executable script. Use free flags as the ABI: the companion records origin country flags, stamps semantic province flags for split macro-regions, and sets a versioned global initialization flag. The parent may test those flags because an unset flag is harmless when the companion is absent.

Do not make one mission fingerprint guess another mod's optional column. The parent should validate only its shared columns and reject its own foreign house anchors. A companion-origin branch may mark the parent's portion valid, while the companion separately requires exactly one of its own anchors and forbids every sibling and parent house anchor. Run the companion check during initialization, after a versioned one-time migration, and through a low-frequency repair event that calls the parent's canonical two-phase mission refresh helper.

Expanded areas need semantic preservation, not direct optional references. If a map splits western Kyushu, the Seto Inland Sea, Ise-Kii, or Ryukyu out of old vanilla areas, stamp the new provinces with purpose-specific flags such as `shimabara_belt`, `ikko_heartland`, or `wokou_waters`. Extend the parent's event, disaster, decision, or mission scope with those flags. A combined validator must prove the exact mapping from each semantic flag to companion areas and prove that every flag has at least one parent consumer.

For new country history, validate `primary_culture` against the inner object keys actually defined under `common/cultures/*.txt`. A comment such as `# Saigoku / Western Japanese` does not make `saigoku` a valid culture key; the executable key may be `japanese`. Perform this catalog-closure check before simulating culture-group mission gates.

The combined release gate should enumerate every companion tag across every relevant DLC state. Require one non-generic series per slot `1..5`, no generic fallback, unique mission/series/event/decision/modifier/callable IDs, active visible and `mission_completed` prerequisites, canonical row parity, and zero renderer topology errors. Also verify preserved strategic province names, complete expanded-region closure, descriptor dependency identity, origin-group partition, idea-group uniqueness, and a valid founder-reform fallback. Report fixed `num_of_cities` or province-count gates as map-scale risks until their historical intent is redesigned; do not silently multiply them by the province-count ratio.

Static topology can prove closure and timeline consistency but cannot prove that the EU4 engine accepts the map. Launch only after static checks pass and the active user permission boundary allows it. Runtime validation should cover a cold map load, all unique bookmark dates, one-day starts for key transitions, ports/navies/unit placement, and a newly written `error.log`; close every test process afterward.

## Visual Assets

For project-specific EU4 mod art, prefer generated bitmap assets rather than hand-drawn placeholder SVGs or generic flat icons. Generate the source image, then process it into the target EU4 asset format.

Default art direction:

- Match vanilla EU4's painted, late-medieval/early-modern look: parchment texture, subdued contrast, hand-painted metal/cloth/wood, heraldic clarity, and slightly aged edges.
- Avoid modern flat vector UI, neon colors, photorealistic stock imagery, or clean mobile-app icon style.
- Keep a high-resolution generated source beside any downscaled final asset when useful, but reference only the final game asset from descriptors or interface files.

Transparency workflow:

- For icons, mission art, interface ornaments, and other overlay assets, remove the background and export as a transparent PNG/TGA/DDS as appropriate for the target UI path.
- For launcher thumbnails and large event images, transparency is usually not useful; still generate the art, then crop/downscale to a conventional opaque PNG/JPG matching the descriptor or interface expectation.
- For country flags under `gfx/flags`, EU4 expects `TAG.tga`; use the flag's full square canvas unless a specific interface requires an alpha cutout.
- Vanilla country flags in the inspected EU4 v1.37.5 install are 128x128, 24-bit RGB TGA files with no color map and no alpha. Both image type 2 (uncompressed true-color, often 49196 bytes with the Truevision footer) and image type 10 (RLE true-color, smaller files) appear in vanilla, so either is compatible.
- For generated country or route flags, keep the high-resolution imagegen source under `gfx/flags/source/`, create a 128x128 preview PNG for quick inspection, and export only the final `TAG.tga` under `gfx/flags/`. Verify final flags with PIL or another image tool: `size=(128,128)`, `mode=RGB`, and nonzero/normal file size.

When adding generated art, verify:

- filename and extension match the script or descriptor reference exactly;
- dimensions match the vanilla pattern for that asset class;
- alpha channel is present when the asset is meant to be transparent;
- the image is not blank after conversion;
- launcher thumbnails use `picture="thumbnail.png"` in both descriptors when applicable.

## Localisation

Use UTF-8 BOM. Structure:

```yml
l_english:
 MY_KEY:0 "Visible text"
 MY_KEY_desc:0 "Description text"
```

Common key conventions:

- Event: `namespace.1.t`, `namespace.1.d`, `namespace.1.a`
- Decision: `decision_key_title`, `decision_key_desc`
- Country: `TAG`, `TAG_ADJ`
- Idea group: `TAG_ideas`, `TAG_ideas_start`, `TAG_ideas_bonus`, `idea_key`, `idea_key_desc`
- Mission: `mission_key_title`, `mission_key_desc`

EU4 mission titles resolve through `<mission_id>_title`; a bare `<mission_id>`
localisation entry is not a substitute. If a prior release shipped bare keys,
retain them and add canonical `_title` aliases, then validate every mission ID
against both `_title` and `_desc`. A visualizer that reports only newly authored
mission titles missing is often exposing this exact coverage gap.

When overriding a vanilla national idea group such as `ODA_ideas` or `ASA_ideas`, write the whole group in the mod file: `start`, `bonus`, `trigger`, `free = yes`, and all seven ideas. Do not add only a few idea entries under the same key; EU4 treats the top-level idea group as a complete definition, and partial overrides can create missing ideas, bare localisation keys, or duplicate/confusing load-order behavior. Keep the matching localisation keys in the same version slice and regenerate active localisation immediately.

Tag changes need a separate free-idea-group transition. A country can retain its old free national ideas while the new tag's group is also selected, producing a new group title over old idea tooltips, overlapping icons, and `Missing Icon 'national_idea8'` in `error.log`. Put one guarded `swap_free_idea_group = yes` in the canonical tag/route synchronization effect, call it only when `has_custom_ideas = no`, and call it again from a one-time old-save migration. When route identity requires the new ideas, do not use the optional `ideagroups.1` prompt: declining it preserves the stale group by design. Validate exactly seven ideas per group, exactly one executable swap helper, every route tag's expected `has_idea_group`, and zero route calls to `ideagroups.1`.

When adding one-time decisions, MTTH flavor events, or hidden legacy dispatchers, update the mod's debug cleanup effect in the same slice. Clear every new `*_taken`, `*_seen`, `*_dispatching`, and `*_granted` flag, and remove every temporary or permanent modifier introduced by the feature. Otherwise repeated in-game testing can look broken because old state silently suppresses decisions or events.

For broad tag-coverage features, maintain an explicit coverage audit by tag and content type before declaring a slice done. In Japan daimyo work, check at least: idea group, MTTH flavor event, one-time decision, origin recording, unified-Japan legacy event, legacy modifier, localisation, and debug cleanup. Group-level coverage is useful but does not prove one-house flavor coverage.

For daimyo national idea passes, do not treat a matched `<TAG>_ideas` block as sufficient coverage. Validate that each overridden group has `start`, `bonus`, `trigger = { tag = <TAG> }`, `free = yes`, exactly seven top-level idea blocks, and localisation for the group, start, bonus, every idea key, and every `<idea>_desc` key. A brace-depth-aware parser is safer than regex alone here, because `trigger`, `start`, and inner modifier blocks can otherwise be mistaken for ideas or cause false missing reports.

For the local `japan_expanded_v2`/`jxp_` framework, run the dedicated coverage checker after broad daimyo or route-reform work:

```powershell
$py = "$env:USERPROFILE\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
& $py "$env:USERPROFILE\.codex\skills\eu4-modding\scripts\check_jxp_japan_coverage.py" "$mod"
```

This checker treats Ashikaga-style pre-route content as valid when it is gated by Japanese polity, no route selected, shogunate/daimyo reforms, and a call to the daimyo polity initialization effect. Do not require every such feature to use only `jxp_is_daimyo_stage_trigger`, because the shogunate can legitimately share some daimyo-family flavor.

For JXP 0.22.0 and later, the custom government levels audited by that legacy
coverage script have been removed. Use the current release gate instead:

```powershell
& "$env:USERPROFILE\.codex\skills\eu4-modding\scripts\validate_jxp_mod.ps1" `
  -ModPath $mod `
  -GameRoot "D:\Steam\steamapps\common\Europa Universalis IV"
```

For repeatable in-game testing, cleanup coverage must include more than origin and legacy state. If a daimyo decision or event sets `*_taken` or `*_seen`, or adds a temporary country modifier, `jxp_debug_clear_event_state_effect` should clear that flag or remove that modifier. Otherwise the next test run can falsely look like the decision, event, or house flavor is missing.

If the game shows `$KEY$`, check spelling, language header, BOM, and whether the mod is enabled.

When testing with community Chinese language mods that rely on the EU4 double-byte patch, ordinary UTF-8 Chinese text can load as question marks and produce `Couldn't find Latin1 character` in `logs/error.log`. Those mods use EU4SpecialEscape-style triplets such as `0x10 <low byte> <high byte>` plus custom `zh-hans-*.fnt` fonts. Keep a human-readable UTF-8 source copy outside the active `localisation/` folder, then generate the active `.yml` with:

```powershell
$py = "$env:USERPROFILE\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
& $py "$env:USERPROFILE\.codex\skills\eu4-modding\scripts\escape_eu4_special_localisation.py" `
  "path\to\source_l_english.yml" `
  "path\to\mod\localisation\source_l_english.yml" `
  --backup "path\to\mod\localisation_source\source_l_english_utf8_source.yml"
```

After conversion, the active localisation file should still be UTF-8 with BOM but should contain no raw CJK characters. Old `error.log` entries remain until the next launch rewrites logs.

EU4 treats square-bracket text in localisation as dynamic text, for example `[Root.GetName]`. Do not use ordinary labels such as `[DEBUG]` in visible localisation; the parser can log `Unknown text property` spam and treat the label as a broken dynamic tag. Use plain prefixes such as `Debug:` or localized text without brackets.

For flavor localisation copy passes, edit the human-readable `localisation_source/*_utf8_source.yml` first, then regenerate the active `localisation/*.yml`. Keep visible decision, mission, event, reform, and government-interaction descriptions in an EU4-like historical register:

- Prefer institutional and historical framing over mechanical instructions. The game tooltip already shows costs, requirements, and effects; do not repeat phrases such as "spend ADM", "gain modifier", "increase value", or "at least 50" in prose descriptions.
- Keep titles compact and period-flavored; use descriptions for context, stakes, and atmosphere.
- For scripted trigger localisation that appears in tooltips, replace raw numeric labels with qualitative thresholds, such as "Sea Gate Opened" or "Realm Ordered", when the user wants immersive copy.
- In Chinese localisation for Japan content, occasional short public-domain classical or early-modern references can add texture, but use them sparingly and keep the surrounding prose clear.

When generating escaped active localisation, run the generator and only then run readback checks. Do not put the generator and the BOM/raw-CJK verification in the same parallel tool batch; the verifier can race the file write and report a false missing file.

## Common Snippets

Triggered event:

```txt
namespace = my_mod

country_event = {
	id = my_mod.1
	title = "my_mod.1.t"
	desc = "my_mod.1.d"
	picture = COURT_eventPicture
	is_triggered_only = yes
	option = {
		name = "my_mod.1.a"
		add_prestige = 10
	}
}
```

One-time player decision:

```txt
country_decisions = {
	my_decision = {
		major = yes
		potential = {
			ai = no
			NOT = { has_country_flag = my_decision_done }
		}
		allow = {
			adm_power = 50
		}
		effect = {
			add_adm_power = -50
			set_country_flag = my_decision_done
		}
		ai_will_do = { factor = 0 }
	}
}
```

For debug or QA decision suites, do not put dozens of one-click event dispatch
decisions behind one global `debug_enabled` flag. EU4's decision UI can become
sluggish or appear frozen when it has to rebuild a very dense list with long
tooltips. Keep core debug operations visible, then hide bulk event triggers
behind explicit panel/category flags. Clear those panel/category flags when the
debug menu is disabled so old test saves do not reopen a large decision list by
accident.

For very large debug suites, split core tools as well as event triggers into
one-open-panel-at-a-time groups such as cleanup, value presets, route forcing,
and contact seeding. Debug scripted effects that call route cleanup, tag-change
helpers, mission refresh, reform grants, province loops, or government-power sync
ladders should expose only a short `custom_tooltip`, with the actual operations
inside `hidden_effect`. Otherwise merely opening or clicking the debug menu can
make the EU4 decision panel appear stuck because the UI is expanding hundreds of
internal effect lines.

Do not leave the root debug actions visible while a core or event subpanel is
open. Gate root-only decisions through one shared scripted trigger that requires
all panel flags to be absent, keep one persistent disable action, and provide a
single back/close action in each subpanel. Count the persistent action, panel
controls, and category contents together when enforcing visible-decision limits;
counting only the category contents understates the actual UI load.

Validate semantic panel ownership as well as density: route chooser and
`force_*_route` decisions belong in the route panel, `seed_*` decisions in the
contact-seed panel, value presets in the values panel, and cooldown/event-state
cleanup in the cleanup panel. A misplaced decision can pass simple count checks
while making the intended tool appear missing.

Bulk event preview buttons must not accumulate every option reward on one debug
country. Before preparing the next debug action, remove non-route country
modifiers that can be added by the event-preview set; keep route-state modifiers
under the route cleanup effect. Derive the expected preview cleanup set from the
actual event ids dispatched by debug decisions so a newly added event modifier
cannot silently push `countrygovernmentview` past its available
`modifiers_box_*` rows.

The `countrygovernmentview` loader probes sequential `modifiers_box_*` names and
logs the first missing number as it discovers the list terminator. If adding rows
changes `modifiers_box_5` into `modifiers_box_9` or `modifiers_box_17`, the message
is a sentinel probe, not proof that more rows are required. Do not chase it by
copying the full GUI and adding unbounded boxes; judge actual crowding in game and
reduce accumulated modifier sources or debug-preview residue instead.

For the local Japan Expanded `jxp_` framework, run `scripts/check_jxp_ui_guardrails.py`
after changing missions, ideas, debug decisions, or route reforms. It catches
UI failures that ordinary syntax validation misses: mission groups in hidden
slots, same-row or upward mission prerequisites, duplicate mission keys, idea
groups with more or fewer than seven ideas,
duplicate idea-group definitions, bulk debug event decisions that are not
panel/category-gated, over-dense debug panels, debug decisions or scripted
effects that expose too many internal effect lines in tooltips, and route reform
levels that overload the government UI.

Form/test tag pattern:

```txt
change_tag = TAG
on_change_tag_effect = yes
restore_country_name_effect = yes
if = {
	limit = { has_custom_ideas = no }
	country_event = { id = ideagroups.1 }
}
my_schedule_mission_refresh_effect = yes
```

Mission group:

```txt
my_tag_missions = {
	slot = 1
	generic = no
	potential = { tag = TAG }
	has_country_shield = yes
	my_first_mission = {
		icon = mission_high_income
		position = 1
		required_missions = { }
		trigger = { adm_power = 100 }
		effect = { add_prestige = 10 }
	}
}
```

For additive national mission groups that should not replace vanilla mission files, keep `potential` narrow. A safe pattern is to define a core tag trigger plus a route/flag gate, then require the country to still be in the intended modded scope:

```txt
my_core_tag_trigger = {
	OR = {
		tag = JAP
		tag = KJP
		tag = CJP
	}
}

my_additive_mission_scope_trigger = {
	my_japanese_polity_trigger = yes
	OR = {
		my_core_tag_trigger = yes
		has_country_flag = my_route_selected
	}
}

my_extra_missions = {
	slot = 4
	generic = no
	potential = {
		NOT = { map_setup = map_setup_random }
		my_additive_mission_scope_trigger = yes
	}
}
```

Avoid letting a broad culture, capital-region, or route flag trigger decide mission visibility by itself; additive mission trees can otherwise leak into unintended countries or overlap vanilla/DLC mission grids.

For Japan content that should appear before unification, use the government reform rather than the final Japan tag as the primary gate. In the inspected v1.37.5 install, ordinary and independent daimyo are checked with `has_reform = daimyo` and `has_reform = indep_daimyo`. Keep pre-unification mission groups mutually exclusive with later route tags/flags:

```txt
my_daimyo_stage_trigger = {
	my_japanese_polity_trigger = yes
	OR = {
		has_reform = daimyo
		has_reform = indep_daimyo
	}
	NOT = { tag = JAP }
	NOT = { my_has_any_route_trigger = yes }
}
```

Good daimyo-stage content is local and preparatory: domain surveys, castle towns, clan leagues, court petitions, early port merchants, and firearms rumors. Keep rewards modest and avoid setting late-route state too early. For example, an early Sakai/Hakata merchant event should not set a later Kirishitan-contact flag or a "Nanban ship seen" flag if that would suppress the dedicated post-contact event chain.

For archetype-specific daimyo content, a single short identity column often feels like filler beside generic administration. A stronger full-tree pattern is four shared institutional columns plus one mutually exclusive house column, with all five visible slots owned by custom non-generic series. Stagger odd/even rows so adjacent-column links always descend exactly one row, and use common milestones to merge the house line back into unification. Do not gate these branches only on origin flags or Japanese culture, because origin flags survive tag changes and can leak pre-unification missions into `JAP` or route tags. Gate the whole family on a daimyo-stage trigger, then enumerate and validate every supported tag. Good archetype labels are institutional rather than mechanical, such as house military rolls, Kyoto court offices, port registries, northern border passes, and shrine-temple market law.

For EU4 mission arrows, vanilla usually links a parent to a child on the next
lower row. Measurements from the pinned 1.37.5 Japanese trees give a joint
geometry rule: a same-slot edge may span one or two rows, while a cross-slot
edge may move only one adjacent column and exactly one row. A cross-column edge
that spans two rows renders as disconnected horizontal stubs. Keep the logical
dependency by removing that parent from `required_missions` and adding
`mission_completed = parent_mission_key` to the child `trigger`. Do not ban all
cross-slot edges: adjacent-column, next-row diagonals are used by vanilla and
are useful for readable forks and merges.

For Japan-style additive mission groups, visible slots are 1 through 5. Do not
park real player-facing content in `slot = 6` to avoid overlap; it may parse but
risks being invisible or confusing. If all visible route profiles already use
slots 1 through 5, either merge the content into an existing route group, turn it
into a decision/event reward, or temporarily gate the standalone group with
`potential = { always = no }` until it is integrated. Re-run both
`check_mission_series_overlap.py` and `check_jxp_ui_guardrails.py`.

For post-unification content based on the daimyo that founded Japan, centralize origin groups in scripted triggers rather than repeating long `has_country_flag = jxp_origin_*` lists in decisions, missions, and events. If several alternatives are meant to be mutually exclusive, add one shared consumed flag such as `my_house_policy_taken` in addition to any specific `*_taken` flags; this protects debug saves or migrated campaigns that accidentally have multiple origin flags. Add both the shared flag and specific flags to debug cleanup, and run a small coverage check to confirm every intended tag appears exactly once across the origin groups.

When a decision dispatches one of several origin-specific events, use an `if` / `else_if` chain or set a dispatch guard before firing the event. Do not use a flat list of independent `if` blocks for mutually exclusive origin content, because old debug saves or migrated campaigns can retain multiple `jxp_origin_*` flags and queue several events from one click.

## Validation Lookups

Use vanilla examples before inventing syntax:

```powershell
rg -n "change_tag =|swap_non_generic_missions = yes|on_change_tag_effect = yes" decisions
rg -n "namespace =|country_event =|province_event =" events
rg -n "potential =|required_missions|icon =" missions
Select-String -Path interface\countrymissionsview.gfx -Pattern 'name = "mission_high_income"'
Select-String -Path interface\*.gfx -Pattern 'COURT_eventPicture'
Test-Path common\units\western_medieval_infantry.txt
```

Known good EU4 v1.37.5 names used in prior work:

- Event pictures: `COURT_eventPicture`, `DIPLOMACY_eventPicture`, `MERCHANTS_TALKING_eventPicture`, `TRADEGOODS_eventPicture`, `COLONIZATION_eventPicture`, `NAVAL_MILITARY_eventPicture`
- Mission icons: `mission_high_income`, `mission_early_modern_university`, `mission_monarch_in_throne_room`
- Monarchy reform: `feudalism_reform`
- Western units: `western_medieval_infantry`, `western_medieval_knights`, `western_men_at_arms`, `swiss_landsknechten`, `dutch_maurician`, `austrian_tercio`, `austrian_grenzer`, `austrian_hussar`, `austrian_white_coat`, `prussian_uhlan`, `austrian_jaeger`, `mixed_order_infantry`, `open_order_cavalry`, `napoleonic_square`, `napoleonic_lancers`
- Invalid in the inspected v1.37.5 install: `open_order_infantry`
- Invalid in the inspected v1.37.5 install: `NAVAL_BATTLE_eventPicture`
- Occupied vanilla tags in the inspected v1.37.5 install include `RJP = "countries/Rajputana.txt"`. Do not reuse `RJP` for "Reformed Japan"; pick an unused alternative such as `RFJ`.
- Invalid modifier names seen in v1.37.5 `error.log`: `missionary_strength` and `accepted_culture_threshold`. Use vanilla-confirmed modifiers such as `global_missionary_strength`, `global_heretic_missionary_strength`, `global_heathen_missionary_strength`, or `num_accepted_cultures` after checking the intended effect against vanilla files.

Additional v1.37.5 script notes:

- Province port checks use `has_port = yes` in province scope. Do not use `is_port = yes`; it was not found in the inspected vanilla scripts.
- `check_variable = { which = my_var value = 50 }` means the variable is at least 50. Wrap it in `NOT = { ... }` for below 50.
- `set_variable` and `change_variable` operate on the current scope; wrap them in `ROOT = { ... }` when inside another country or province scope.
- Script variables referenced by `check_variable`, `set_variable`, or `change_variable` can surface in generated tooltips. Add localisation keys matching the variable IDs, for example `my_var:0 "Readable Name"` and optionally `my_var_desc:0 "..."`, so decisions and missions do not show raw internal names.
- To display a variable's current value in event, decision, or tooltip localisation, use the vanilla pattern `[Root.my_var.GetValue]` or the appropriate scope in place of `Root`.
- If a visible effect keeps a hidden variable in sync with a government power or other UI field, hide the storage-layer `change_variable`, clamp logic, and any ladder of `set_government_power` values inside `hidden_effect`. Expose only the player-facing `add_government_power` or a `custom_tooltip`; otherwise EU4 can expand every branch of a sync ladder into tooltips, producing long lists such as "set power to 0/5/10/.../100".
- Conditional `country_event` dispatch inside a visible scripted effect can render as `Trigger [] event` because the tooltip builder cannot resolve an event ID until the `if`/`else_if` branch runs. Keep visible costs and one stable `custom_tooltip` at the top level, and put the route/origin-dependent event dispatch inside `hidden_effect`. Apply this to every option in the same menu, not only the first reported blank tooltip.
- For overseas and colonial mission checks, the inspected v1.37.5 install uses `has_discovered = ROOT`, `has_port = yes`, `owns_or_non_sovereign_subject_of = <province>`, `num_of_provinces_owned_or_owned_by_non_sovereign_subjects_with = { ... }`, and `colonial_region = colonial_alaska/colonial_california`. These are safer than inventing province predicates such as `is_port`.
- When event and localisation work is split across workers, establish the canonical `namespace.N` event order before writing. If content arrives out of order, reorder or renumber events to match localisation keys before validation; otherwise the game can show valid text on the wrong event.
- Celestial Empire reforms live in `common/imperial_reforms` with `empire = celestial_empire`. The inspected `01_china.txt` uses `trigger`, `member`, `emperor`, `on_effect`, `off_effect`, `disabled_by`, and `empire_of_china_reform_passed = <reform_key>`. Generic reform `potential = { ... }` is supported in the same file type by HRE reforms and can hide modded reforms behind mission flags.
- For a mission-unlocked Celestial reform, use `potential` only for stable identity filters such as the intended country family. Put the mission/unlock requirement in `trigger` so the reform remains visible but locked. If the mission can be completed before becoming Emperor of China, persist the unlock regardless of current emperor status and add a hidden old-save catch-up that recognizes `mission_completed = <mission_key>`.
- For mission-only unlocks, do not put unlock flags inside a shared reward effect that is also called by decisions or events. Add a dedicated scripted effect and call it only from the mission `effect`.
- A conquest CB is split between `common/cb_types` and `common/wargoal_types`: the CB key sets `prerequisites_self`, target `prerequisites`, and `war_goal`; the wargoal key sets `type`, `peace_options`, `badboy_factor`, `peace_cost_factor`, `allowed_provinces`, and `war_name`.
- To reduce aggressive expansion only for a region, put `badboy_factor = 0.5` under the attacker block and constrain `allowed_provinces`. EU4 v1.37.5's "sunrise invasion" pattern uses both `superregion = china_superregion` and `superregion = far_east_superregion` for East Asia.
- Vanilla Emperor-of-China pressure for non-Confucian religion and non-East-Asian primary culture is handled by `events/ChineseEmpire.txt` events `celestial_empire_events.2` and `.3`, gated by country flags `reacted_to_confucianism_event` and `had_sinicization_event`. A compatibility-friendly exemption can set these flags in a modded reform `on_effect` rather than replacing the vanilla event file.

## Government Mechanics

Custom government powers live in `common/government_mechanics/<file>.txt` and are attached to countries through a government reform's `government_abilities = { <mechanic_id> }`.

Reusable pattern for adding a UI-visible country mechanic without replacing vanilla government files:

```txt
my_mechanic = {
	alert_icon_gfx = GFX_alerticons_government_mechanics
	alert_icon_index = 16
	powers = {
		my_power = {
			show_before_interactions = yes
			min = 0
			max = 100
			default = 25
			reset_on_new_ruler = no
			base_monthly_growth = 0
			development_scaled_monthly_growth = 0
			is_good = yes
		}
	}
	interactions = {
		my_interaction = {
			icon = GFX_russian_rule_adm_button
			trigger = { adm_power = 50 }
			effect = { add_adm_power = -50 }
			cooldown_years = 10
			ai_chance = { factor = 1 }
		}
	}
}
```

Attach it with an invisible `basic_reform = yes` reform:

```txt
my_hidden_mechanic_reform = {
	icon = "shogunate"
	monarchy = yes
	republic = yes
	basic_reform = yes # invisible/does not take a reform slot
	valid_for_nation_designer = no
	potential = { my_country_trigger = yes }
	government_abilities = { my_mechanic }
}
```

In the inspected EU4 v1.37.5 install, `theocracy = yes` is not a valid top-level government reform attribute and logs as an unexpected token when placed after `republic = yes`. Theocracy reforms are ordinary reform entries in `common/government_reforms/03_government_reforms_theocracies.txt`, typically using attributes such as `has_devotion = yes`, `religion = yes`, `heir = yes`, `monastic = yes`, or `papacy = yes` as needed. Do not add `theocracy = yes` to custom reforms.

When adding the carrier reform by event or scripted effect, call:

```txt
add_government_reform = my_hidden_mechanic_reform
regenerate_government_mechanics = yes
```

Use:

```txt
add_government_power = { mechanic_type = my_mechanic power_type = my_power value = 5 }
set_government_power = { mechanic_type = my_mechanic power_type = my_power value = 50 }
has_government_power = { mechanic_type = my_mechanic power_type = my_power value = 50 }
has_government_mechanic = my_mechanic
```

Long-running investments can be modeled without replacing `common/on_actions`: make a government interaction start the project, set hidden flags/variables, add a visible temporary country modifier, and schedule a hidden self-rescheduling country event. This avoids depending on global pulse merge behavior and keeps the state local to countries that actually started the project.

Useful pattern:

```txt
my_start_investment_effect = {
	add_adm_power = -75
	add_treasury = -75
	add_country_modifier = { name = my_investment_modifier duration = 1095 }
	hidden_effect = {
		set_country_flag = my_investment_active
		set_variable = { which = my_investment_years value = 0 }
		country_event = { id = my_investment.1 days = 365 }
	}
}

my_progress_investment_effect = {
	add_government_power = { mechanic_type = my_mechanic power_type = my_power value = 5 }
	change_variable = { which = my_investment_years value = 1 }
	if = {
		limit = { check_variable = { which = my_investment_years value = 3 } }
		clr_country_flag = my_investment_active
		set_variable = { which = my_investment_years value = 0 }
		remove_country_modifier = my_investment_modifier
		country_event = { id = my_investment.2 days = 1 }
	}
	else = {
		country_event = { id = my_investment.1 days = 365 }
	}
}
```

For player-facing government interactions, add `custom_tooltip = my_long_investment_tt` so the future annual progress is understandable, and wrap internal flags, variables, and scheduling in `hidden_effect` so tooltips do not expose implementation details. If only one long investment should run at a time, use a shared flag such as `my_investment_active` plus `custom_trigger_tooltip = { tooltip = my_no_active_investment_tt NOT = { has_country_flag = my_investment_active } }`.

For low-frequency balancing or "inertia" around custom government powers, prefer visible MTTH country events with per-direction cooldown flags rather than hidden yearly pulses. Gate each event behind the extreme threshold, set a cooldown flag in the option, and schedule a hidden event to clear it after 10-20 years. Keep corrections small and call the same scripted effects used by buttons or missions so hidden storage variables and UI-visible powers remain synchronized:

```txt
country_event = {
	id = my_balance.1
	title = "my_balance.1.t"
	desc = "my_balance.1.d"
	picture = COURT_eventPicture
	trigger = {
		my_country_scope_trigger = yes
		has_country_flag = my_mechanic_initialized
		my_power_high_trigger = yes
		NOT = { has_country_flag = my_power_high_cooldown }
	}
	mean_time_to_happen = { months = 240 }
	option = {
		name = "my_balance.1.a"
		set_country_flag = my_power_high_cooldown
		my_subtract_power_5_effect = yes
		country_event = { id = my_balance.101 days = 7300 }
	}
}
```

This pattern gives the system texture and gentle self-correction without overriding player strategy or creating noisy event spam. Add the cooldown flags to any debug "clear event state" effect.

For visible balancing events, consider adding a second policy option when the state plausibly has agency. A good pattern is: option A accepts the inertia/correction, while option B preserves or intensifies the current extreme in exchange for a short-term reward or a small political cost. Put cooldown flags and hidden reset events inside `hidden_effect` so the player sees only meaningful policy outcomes in the tooltip.

For event testing, keep a clear distinction between normal gameplay access and debug access. Low-frequency flavor events with `mean_time_to_happen` are not expected to have ordinary player decisions; they should happen naturally when their trigger is true. If direct testing is useful, add debug-only decisions behind a flag such as `my_debug_enabled`, plus one localized "enable debug menu" decision. Keep those decisions `ai = no`, hidden from normal gameplay, and name them plainly as debug/test tools.

When a debug decision fires a strict or one-shot event, prepare the test state explicitly. Either call a helper such as `my_debug_prepare_polity_effect`, clear blocking seen/cooldown flags in a debug cleanup effect, or trigger a wrapper event that sets up the required route, date, religion, government, or province state before calling the target event. Document the enable-debug step in test notes so "the event cannot be triggered by decision" is not mistaken for a broken content path.

When integrating custom mechanics with vanilla government interactions, prefer listening for the vanilla modifier or flag created by the interaction instead of replacing the vanilla government mechanic file. For example, EU4 v1.37.5's Shogunate mechanic lives in `common/government_mechanics/17_shogunate.txt` and its interactions add these modifiers:

- `expel_ronin` adds `overlord_expel_ronin` to the Shogun and `subject_expel_ronin` to Daimyo subjects.
- `sankin_kotai` adds `overlord_sankin_kotai` and `subject_sankin_kotai`.
- `sword_hunt` adds `overlord_sword_hunt` and `subject_sword_hunt`.

A non-invasive bridge is a hidden MTTH event with a once-per-duration sync flag:

```txt
country_event = {
	id = my_bridge.1
	title = none
	desc = none
	hidden = yes
	trigger = {
		has_reform = shogunate
		has_country_modifier = overlord_sword_hunt
		NOT = { has_country_flag = my_synced_sword_hunt }
	}
	mean_time_to_happen = { days = 1 }
	immediate = {
		set_country_flag = my_synced_sword_hunt
		my_custom_power_effect = yes
		country_event = { id = my_bridge.101 days = 3650 }
	}
}
```

If a custom government interaction duplicates a vanilla one, do not merely add a false `trigger`; government interactions have no `potential`, so the duplicate button will usually still be visible but disabled. Prefer removing the custom interaction from the government mechanic and, if needed, keeping a non-vanilla decision version gated away from the vanilla reform.

Localise at least:

- `ability_<mechanic_id>`
- `<mechanic_id>`
- each power id
- `monthly_<power_id>`
- `<power_id>_gain_modifier`
- each interaction id and `<interaction_id>_desc`
- the carrier reform id and `<reform_id>_desc`

Custom interaction icons:

- Put final button textures under `gfx/interface/government_mechanics/<mechanic_id>/`.
- EU4 v1.37.5 government mechanic buttons commonly use transparent RGBA DDS; 82x82 matches newer vanilla buttons such as Japan Crusader State, while some older Shogunate icons are 72x72.
- Register every custom button in a mod-owned `interface/*.gfx` file:

```txt
spriteTypes = {
	spriteType = {
		name = "GFX_my_mechanic_interaction"
		texturefile = "gfx/interface/government_mechanics/my_mechanic/my_mechanic_interaction.dds"
		loadType = "INGAME"
		transparencecheck = yes
	}
}
```

- Reference the registered name from the mechanic interaction with `icon = GFX_my_mechanic_interaction`.
- Keep imagegen sources, alpha sheets, crop PNGs, and previews in a non-referenced `source/` subfolder; only point `.gfx` at final game-ready assets.
- For generated transparent buttons, a reliable workflow is: generate a chroma-key sprite sheet, remove the key to alpha, crop each cell by alpha bounding box, pad to square, resize to 82x82, save RGBA DDS, then verify every `icon = GFX_*` has a matching `spriteType` and that every `texturefile` exists.

## Generated Flags, Mission Icons, and Event Pictures

Treat generated art as source material and make the EU4-ready conversion deterministic. Before generating anything, assemble a contact sheet from the same vanilla asset class in the pinned game version. This is especially important for Japanese daimyo flags: the vanilla grammar is a flat solid field with one bold centered mon, usually in one ink color. Do not prompt for waving cloth, painted scenery, gradients, paper texture, European escutcheons, text, or ornamental borders. Keep each high-resolution ImageGen PNG in a non-referenced `source/` folder, flatten the final field to a planned color, extract the mon cleanly, and export a 128x128 24-bit RGB TGA with no alpha or color map.

For EU4 1.37.5 mission and event art:

- vanilla mission icons are 59x63 opaque RGBA DDS images; do not cut them to transparent silhouettes merely because other interface sprites use alpha;
- event pictures are 512x132 DDS and commonly use DXT1 compression. Prompt for the important action inside a central ultra-wide band because the final crop is extremely shallow;
- launcher cover art can use a 512x512 RGB PNG referenced as `picture="thumbnail.png"` from both descriptors;
- register mod-owned mission and event sprite names in `interface/*.gfx`, and validate names against both mod and vanilla registries;
- validate source existence and minimum size, final DDS/TGA magic and headers, exact dimensions, compression, alpha expectations, nonblank pixels, duplicate source/final hashes, script references, sprite registrations, and registered texture paths;
- ensure country/history builders verify generated flags instead of redrawing them. A hash-stability check around the full build is a useful guard against obsolete procedural asset writers;
- if the image service rejects a historically accurate symbol, do not evade the safety policy. Record the limitation and use a restrained, period-appropriate heraldic allusion rather than an unrelated decorative emblem.

## Testing

Suggested route:

1. Enable only the target mod in a fresh playset.
2. Start a new game.
3. Trigger test events with `event namespace.id`.
4. Check decisions, country name/adjective, flag, ideas, and missions.
5. Inspect `logs/error.log` after a game launch.
6. If testing with Chinese localisation mods, use a separate playset and verify load order.

Treat launching EU4 as a disruptive runtime validation step. Start with static parsing, targeted invariant checks, localisation coverage, event-chain graph checks, mission-series checks, and visualizer regeneration. If the user has established a no-launch boundary, do not infer permission from an earlier launch or an earlier turn: launch only after an explicit active instruction. If runtime evidence is indispensable, first explain exactly what static checks cannot prove and request explicit approval; close every test game process when the run is complete.

## Japan and Shinto Incidents

In EU4 v1.37.5, Shinto isolation incidents live in `common/incidents/00_isolationism.txt`, while event chains live in `events/Shinto.txt`. The incident `potential` blocks are locked to `religion = shinto`, and the Shinto religion itself is the one with `uses_isolationism = yes`; Confucianism uses `uses_harmony = yes` instead.

If a Japan-route tag converts to Confucianism but should retain Japan-flavored Shinto incident themes, avoid replacing the whole vanilla incidents file unless that compatibility risk is intentional. Safer patterns are:

- convert the country with `change_religion = confucianism` and immediately synchronize Shinto through one canonical effect. Guard its sole `add_harmonized_religion = shinto` mutation with `NOT = { has_harmonized_with = shinto }`; never add or remove the generated `harmonized_shinto` modifier manually;
- create mod-owned bridge events for Nanban trade, urbanization, Neo-Confucianism, and similar themes;
- preserve Ise as the Shinto exception when needed. In the inspected map, Ise is province `4359`, and vanilla localisation identifies it as the Ise Grand Shrine/Jingu province;
- for gradual religious settlement, use mod-owned province modifiers plus a hidden self-rescheduling event that converts eligible Japanese provinces over time, excluding `province_id = 4359`.

When the user reports that a Confucian Japan route "did not harmonize Shinto" after a previous one-shot route effect, add an idempotent sync layer instead of relying only on the tag-change effect. A robust pattern is:

- a canonical scripted effect that, whenever `religion = confucianism`, adds Shinto only when it is not already harmonized, then sets a mod-owned syncretism flag, adds a visible/fallback synthesis modifier, and protects Ise;
- a hidden catch-up MTTH event in its own namespace/file that retries the sync for old saves, debug transitions, and compatibility paths;
- route mission and event `potential` blocks that accept either `has_harmonized_with = shinto` or the mod-owned syncretism flag/fallback modifier;
- debug force-route decisions that call the same sync effect before firing route-specific events.

Do not expect vanilla Shinto incidents to keep starting after `change_religion = confucianism`; their incident `potential` blocks are religion-locked. Bridge the themes with mod-owned event chains and ordinary modifiers rather than trying to drive `add_incident_variable_value` without an active Shinto incident.

Treat a full Confucian-Shinto inheritance layer as a state-compatibility contract, not only a collection of similar stories:

- cover all eight v1.37.5 themes when the design promises full inheritance: Wokou, Urbanization, Ikko-Ikki, Neo-Confucianism, Nanban, Firearms, Christianity, and Shogunate Authority;
- stop a bridge only when the corresponding vanilla completion flag is present. Do not reject it merely because `is_incident_happened` is true: that can mean the Shinto incident began before conversion and is precisely the interrupted state that needs continuation;
- on bridge completion, set the exact vanilla end flag (`end_of_wokou_chain`, `end_of_urbanisation_chain`, `end_of_ikko_chain`, `end_of_neo_confucianism_chain`, `end_of_nanban_chain`, `end_of_incident_firearms_chain`, `end_of_incident_spread_of_christianity_chain`, or `end_of_incident_shogunate_authority_chain`);
- also write outcome flags consumed by downstream DLC missions: one of `jap_chose_kaikoku_flag` / `jap_chose_trade_with_west_flag` / `jap_chose_sakoku_flag`, one of `perfecting_the_musket_flag` / `proliferation_firearms_flag` / `example_of_bushido_flag`, and one of `significant_christian_presence_flag` / `christianity_defeated_flag`;
- add an idempotent hidden migration that maps already-completed mod bridge flags to missing vanilla completion/outcome flags for existing saves;
- preserve natural MTTH access, but provide either a paced player decision for the next eligible chain or category-gated debug decisions for every start event. Use a shared cooldown to prevent several newly eligible bridges from firing together.

Treat a decision that fires a chain's first event as an entry point, not proof that the chain works. Record each chain as an ordered graph and validate every edge: every selectable option in every nonterminal event must schedule the expected successor with the intended delay, each start must mark its `*_started` state, and each successor must be `is_triggered_only = yes`. Start-only cooldowns and temporary dispatch flags must not appear in successor triggers; a short cleanup event may clear only the temporary dispatch gate. Report chain, node, and delayed-edge counts so one missing option edge cannot hide behind a successful first event.

Choose the interruption policy explicitly. If a delayed successor requires a route, religion, or syncretism state that can change before it is due, decide whether the chain should abort or reach a coherent conclusion. An intentional abort needs started-state cleanup or a recovery path; intentional continuation needs a follow-up trigger that remains valid. Encode that policy in the checker rather than leaving a permanently half-finished chain by accident.

For alternate-religion Japan route tags, keep the route self-contained after `change_tag`:

- set `change_religion`, `set_ruler_religion`, and `set_heir_religion` inside the tag-change scripted effect, not only in the route-selection event. This prevents missions, debug decisions, or compatibility hooks from producing a route tag with the old state religion;
- route every tag change through one guarded two-phase mission refresh, then fire a route-establishment event that creates province "reform center" modifiers and starts hidden yearly conversion events;
- put post-route mission groups in visible slots `1..5`, using higher row positions where needed, with narrow `potential` such as `tag = KJP` or `has_country_flag = my_path_kirishitan`. Avoid broad Japanese culture gates for these late trees, or they can leak into ordinary daimyo and vanilla Japan;
- for gradual conversion outside vanilla Centers of Reformation, use a visible setup event plus a hidden `is_triggered_only` self-rescheduling event. Convert one eligible Japanese province per year, clear the route conversion flag when complete, then fire a completion event. This is compatible-friendly and does not require replacing vanilla religion or incident files.

For Japan social or maritime routes that do not map cleanly to a vanilla religion, prefer route flags, country/province modifiers, events, reforms, and missions over adding a fake religion. Keeping `religion = shinto` can preserve vanilla Shinto incident compatibility while still representing sectarian or popular movements through mod-owned content. Localise the distinction clearly so the route feels intentional rather than mechanically invisible.

For Japan route events, protect immersion by gating the narrative assumption, not just the numeric requirement:

- events about private overseas trade, merchant petitions, colonial charters, or open sea lanes should use a shared "not sakoku locked" / "private overseas trade allowed" scripted trigger instead of ad hoc `NOT` blocks;
- events that can still happen under sakoku must name an official controlled channel in both trigger and text, such as Dejima, a translation house, or a reviewed-translation modifier;
- colonial and New World events should fail if the country has the sakoku route flag or route modifier, even if debug tools or compatibility hooks have granted colonists or oceanic-opening variables;
- when event text names concrete development institutions, add concrete owned-province rewards as well as country modifiers. Useful Japan province anchors in the inspected map are Kyoto/Yamashiro `1020`, Osaka/Settsu `1021`, Edo/Musashi `1028`, and Nagasaki/Hizen `4182`;
- for mission-triggered events, still keep the event effect defensive with `if = { limit = { owns = <province> } ... }`; mission requirements can change during parallel work, debug firing, or future refactors.

When adding new route tags to an existing EU4 mod framework, update every shared gateway, not just `country_tags`:

- confirm the tag is unused in vanilla with `rg -n "\bTAG\b" common/country_tags`;
- add `common/countries`, `history/countries`, `gfx/flags/TAG.tga`, ideas, and country/adjective localisation;
- include the tag in shared "is this a modded polity" triggers and any core tag triggers used by additive missions;
- add its route flag to the "has any route" trigger and the shared route-clear effect;
- add route-aware initialization for custom variables or government mechanics;
- add one canonical `change_to_tag_effect` that calls `change_tag`, `on_change_tag_effect`, `restore_country_name_effect`, the guarded free-national-idea sync, government mechanic registration, special reform setup, and the canonical two-phase mission-refresh helper;
- add debug cleanup/force-route hooks if the mod already has a debug menu.

For additive route mission trees, use higher row positions inside visible slots `1..5` and narrow `potential` blocks such as `OR = { tag = TAG has_country_flag = my_path }`. If the route should be reachable before unification, add modest pre-route decisions or daimyo-stage missions that set contact/preparation flags, but keep the final tag-changing mission tree gated behind the route tag/flag.

## Official Achievements Boundary

EU4 official achievements are script-defined in `common/achievements.txt`; in v1.37.5 the visible achievement conditions commonly include `ironman = yes` inside each achievement's `possible` block. A tested content-mod attempt copied `common/achievements.txt` into a mod and removed all 373 `ironman = yes` lines while preserving IDs, localisation keys, `possible`, and `happened` blocks. That approach did not enable official non-Ironman achievements, so do not repeat it as a solution.

Treat official Steam achievement eligibility as outside normal EU4 content modding. Feasible content-mod alternatives are:

- an in-mod achievement tracker using events, decisions, country flags, and localisation;
- tutorial/testing decisions that simulate achievement goals;
- UI/localisation changes explaining that official achievements still require the launcher/game eligibility rules.

## Launcher Visibility Troubleshooting

If a local mod does not appear where the user expects, distinguish three states:

1. Descriptor missing or invalid: the mod is absent from `launcher-v2.sqlite`.
2. Installed but not in playset: the mod exists in the `mods` table with `source = local` and `status = ready_to_play`, but has no row in `playsets_mods`.
3. In playset but disabled: the mod has a `playsets_mods` row but `enabled = 0`.

For non-ASCII local mod names, write both the outer `.mod` and inner `descriptor.mod` as UTF-8 with BOM. A UTF-8-without-BOM outer descriptor can display as mojibake in Windows PowerShell and has caused launcher indexing confusion in local testing. If the launcher rewrites `path` to an absolute path, that is acceptable; for manual repair, `path="mod/my_mod"` is the safest local descriptor form.

Useful read-only SQLite inspection, using any available Python with sqlite3:

```powershell
@'
import sqlite3, pathlib
db = pathlib.Path(r"%USERPROFILE%\Documents\Paradox Interactive\Europa Universalis IV\launcher-v2.sqlite").expanduser()
con = sqlite3.connect(db)
cur = con.cursor()
for row in cur.execute("""
    select id, displayName, dirPath, source, status
    from mods
    where lower(coalesce(displayName,'')) like '%fiber%'
       or lower(coalesce(dirPath,'')) like '%fiber%'
"""):
    print(row)
for row in cur.execute("""
    select p.name, pm.enabled, pm.position, m.displayName
    from playsets p
    join playsets_mods pm on pm.playsetId=p.id
    join mods m on m.id=pm.modId
    where p.isActive=1
    order by pm.position
"""):
    print(row)
'@ | python -
```

Do not edit `launcher-v2.sqlite` without explicit user approval. Prefer the launcher UI:

- Open the launcher.
- Go to the active playset.
- Use `Add more mods` / `All installed mods`.
- Add the local mod, then enable it.
- Restart the launcher if the installed-mods list was open before the descriptor was created.

## Thumbnail / Cover Images

Use `picture="thumbnail.png"` in both the outer `.mod` and inner `descriptor.mod` when adding a launcher or Workshop cover. Put the image at the root of the mod folder. Square PNGs work well for launcher thumbnails; keep a backup generated source if available, but reference only the project-local `thumbnail.png` from descriptors.

In Paradox Launcher v2 local testing, Steam Workshop mods had `mods.thumbnailPath` populated with a file under `.launcher-cache/steam-mod-thumbnail-*`, while local mods with valid `picture="thumbnail.png"` descriptors still had `thumbnailPath` and `thumbnailUrl` set to `NULL`. If a local mod appears and works but has no thumbnail, confirm this with the SQLite query before changing the asset repeatedly. Make the asset small and conventional anyway, for example 512x512 PNG under 1 MB, but expect the launcher UI to show thumbnails reliably only for Workshop/PDX-cached mods unless the launcher database/cache is manually patched or the mod is uploaded.

Other-mod comparison pattern:

- Workshop `.mod` descriptors may or may not include `picture=...`.
- The launcher UI displays `mods.thumbnailPath`, normally a downloaded image under `.launcher-cache/steam-mod-thumbnail-<workshop_id>/...`.
- Local mods can have a valid `picture=...` and a valid project-local image while still having `mods.thumbnailPath = NULL`, which makes the launcher show no thumbnail.

With explicit user approval only, patch a local thumbnail by closing the launcher, backing up `launcher-v2.sqlite`, copying the thumbnail into `.launcher-cache`, and setting `mods.thumbnailPath` with:

```powershell
$py = "$env:USERPROFILE\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
& $py "$env:USERPROFILE\.codex\skills\eu4-modding\scripts\patch_launcher_thumbnail.py" `
  --db "$env:USERPROFILE\Documents\Paradox Interactive\Europa Universalis IV\launcher-v2.sqlite" `
  --mod-dir "$env:USERPROFILE\Documents\Paradox Interactive\Europa Universalis IV\mod\my_mod" `
  --image "$env:USERPROFILE\Documents\Paradox Interactive\Europa Universalis IV\mod\my_mod\thumbnail.png" `
  --display-name "My Mod"
```

## Branching Mission Trees

### Renderer-Safe Mission Tree Standard (RSMTS-1.37.5)

Use this standard for every newly authored, extended, replaced, or reflowed EU4 1.37.5 mission tree. It deliberately defines a conservative subset of layouts that the renderer can draw reliably. A parser-clean file or valid abstract DAG is not sufficient evidence.

Use two evidence labels and do not blur them:

- **Static-safe**: every design, profile, parser, topology, localisation, and migration gate below passes without launching EU4.
- **Runtime-confirmed**: the tree is static-safe and the approved cold-start game test passes for the explicitly tested profile matrix, with screenshots and a fresh `error.log`.

Never report a tree as "fully fixed", "proven in game", or equivalent from static checks alone. Runtime confirmation requires the user's permission before launching EU4.

#### 1. Freeze the profile matrix before placing missions

Define every supported country state as a concrete profile tuple:

```text
(tag, route flags, religion/religion group, relevant DLC state, transient/migration state)
```

- Enumerate every literal tag named by mission potentials; do not substitute one representative per family.
- Include pre-route formed countries, post-tag-change countries, mutually exclusive religious routes, relevant DLC combinations, and old-save migration states.
- For each profile, reproduce EU4's effective selection: activate matching non-generic series first and reserve each entire occupied slot, then add matching generic series only to wholly unoccupied slots.
- A full national tree must have exactly one independently authored active non-generic series owning each visible slot `1..5`. Missing slots, same-slot competitors, or any generic fallback are release failures.
- Every active mission must occupy a unique `(slot, position)` cell, and every visible prerequisite must also be active in that same profile.
- Potentials for mutually exclusive series must be provably disjoint for every profile. Disjoint row ranges do not make simultaneous same-slot series safe.

Write the matrix before mission code. If a state is absent from the matrix, it is outside the claim of correctness.

#### 2. Use the canonical five-column parity grid

EU4 1.37.5 exposes only five horizontal mission slots. New full custom trees must use `slot = 1` through `slot = 5`; `slot > 5` is invisible even when it parses.

Within every mission series, physically declare mission blocks in strictly increasing `position` order. EU4's mission view preserves declaration sequence while assembling a column; it does not reliably sort a scrambled source series back into numeric order. The pinned 1.37.5 `Japanese_Missions.txt` and `DOM_Japanese_Missions.txt` contain 23 Japanese series and all 23 are source-monotonic. A JXP failure with rows such as `13, 19, 25, 17, 23, 27, 15, 21` rendered the late missions out of narrative order and produced large empty connector runs even though every position was unique. Reject non-increasing source rows, and for compact Japanese-style authored columns reject a gap greater than two positions between consecutive declarations or a whole-profile vertical void wider than one row unless an exact pinned vanilla exception is recorded.

Unless an exact vanilla topology is copied from the pinned supported version and separately validated, place new or reflowed trees on this canonical grid:

| Slot | Allowed mission rows | Same-column child | Adjacent-column child |
| --- | --- | --- | --- |
| `1` | odd: `1, 3, 5, ...` | same slot, `+2` rows | slot `2`, `+1` row |
| `2` | even: `2, 4, 6, ...` | same slot, `+2` rows | slot `1` or `3`, `+1` row |
| `3` | odd: `1, 3, 5, ...` | same slot, `+2` rows | slot `2` or `4`, `+1` row |
| `4` | even: `2, 4, 6, ...` | same slot, `+2` rows | slot `3` or `5`, `+1` row |
| `5` | odd: `1, 3, 5, ...` | same slot, `+2` rows | slot `4`, `+1` row |

This alternating lattice provides legal short vertical and diagonal edges while preventing the common two-row diagonal stub. Apply all of these hard geometry rules:

- Dependencies always point downward: `child_position > parent_position`.
- A visible same-column edge advances exactly two rows on the canonical grid.
- A visible cross-column edge moves exactly one slot and one row: `abs(child_slot - parent_slot) = 1` and `child_position - parent_position = 1`.
- Never draw a same-row, backward, two-row diagonal, or two-or-more-column edge.
- No mission cell may lie inside a vertical edge's open segment.
- Diagonals in the same row interval may not cross, and no edge may pass through another mission cell.
- A mission may have at most three visible parents; prefer one or two.
- The visible `required_missions` graph must be acyclic and all parents must exist in the same effective profile.

Existing vanilla-compatible trees may use one-row vertical edges because EU4 can render them, but do not introduce them into a new canonical layout. Exceptions must identify the exact pinned vanilla source and pass the same profile-level geometry checker.

The pinned compact-Japan exception applies when a full replacement deliberately follows the dense spines found in EU4 1.37.5 `Japanese_Missions.txt` or `DOM_Japanese_Missions.txt`. It may use one-row same-column steps to keep long common columns aligned with shorter route columns, but it must retain one-row diagonals, monotonic source order, unobstructed edges, and complete effective-profile validation. Record the source/version and enforce density limits in the project validator; “vanilla also does it” without those fixtures is not an exception.

#### 2a. Validate final-profile density and identity

Legal cells and arrows do not guarantee a coherent full tree. A common failure has two long shared columns extending to row 27 while three route columns stop near row 10; the renderer is technically correct, but the lower half becomes isolated stems and empty space.

- Establish per-slot mission-count and terminal-row floors before release. For the JXP unified-tree contract, each slot has at least five missions, route slots `3..5` end at row 10 or later, and the largest difference among all five terminal rows is at most five.
- Require a unique active-series signature for every promised final tag/route state. Shared national backbones are acceptable, but two distinct final identities must not resolve to the same complete five-series set.
- Measure every concrete DLC and religion profile. Whole-tree occupied-row continuity can pass even when one individual column ends far too early.
- When splitting a formerly shared series, rewrite visible prerequisites, trigger-only `mission_completed` gates, runtime fingerprints, old-save migration, and any generated logical-graph snapshot in the same change. Reject active-to-inactive dependencies in effective topology.

#### 3. Separate visible topology from logical gating

Use `required_missions` only for nearby relationships that satisfy the grid. Put distant, cross-route, or otherwise cluttering prerequisites in `trigger`:

```txt
trigger = {
  mission_completed = my_distant_prerequisite
  stability = 1
}
```

- Do not add a long visible edge merely to express chronology.
- Do not require a mission that can be inactive under the child's own potential.
- Mutually exclusive outcomes must converge through a shared flag or `OR = { mission_completed = ... }`, never by listing every outcome as a mandatory visible parent.
- Audit `mission_completed` checks inside triggers as well as `required_missions`; trigger-only dependencies can still create impossible progression even though they draw no line.
- Build forks and merges only from legal adjacent cells. Use flags, events, or decisions for long-distance convergence.

#### 4. Make dynamic selection deterministic

- Keep country-scoped series `potential` narrow and stable. Do not use `potential_on_load` as though it had country scope.
- When a pinned full replacement owns an affected vanilla profile, disable every replaced vanilla series in both the global preload gate and its country `potential`.
- For existing saves, those two false gates are not sufficient if the save already serialized the old non-generic series key. Keep each replaced top-level series under that exact original key as a deterministic same-path tombstone with both gates false. Never rename it to a new quarantine key: `swap_non_generic_missions` cannot reconcile a serialized key that no longer resolves in the current registry. Keep the pinned source hash and rewrite dormant direct mission swaps inside the tombstoned content to the canonical helper. A runtime `mission.cpp:353` naming both custom and supposedly disabled vanilla series is the decisive failure signal.
- If a historical release wrote mission files with UTF-8 BOM, inspect an uncompressed save for raw `EF BB BF` immediately before `jxp_*` series names. EU4 1.37.5 can serialize that prefix as part of the first top-level key, so merely removing the BOM from the current file creates a second, clean key while the corrupted key survives in old saves. The narrow repair is one generated BOM-prefixed alias file per observed key, containing only the same series name, correct slot metadata, and `potential_on_load = { always = no }` plus `potential = { always = no }`; then run the one-time delayed refresh. Sort these aliases before the real definitions, validate their exact bytes, exclude them from authored-series topology counts, and allow them through the generic no-BOM check only via an explicit project wrapper. Ordinary gameplay scripts must remain BOM-free.
- Route, religion, government, or tag changes must call one canonical two-phase helper. It performs one immediate `swap_non_generic_missions = yes`, schedules one guarded next-day reconciliation, and clears the pending flag in the delayed event. Do not scatter competing swaps across events and decisions.
- For a heavily branched old-save-compatible tree, define a hidden reconciliation event using `has_mission` anchors. Invoke it from `on_startup` so a loaded campaign is repaired before the player opens the mission panel, and retain a low-frequency MTTH fallback. Its fingerprint should require the exact common and route anchors, forbid foreign-route and replaced-vanilla anchors, clear a stale pending flag, and call the same canonical helper. Generate and byte-check large fingerprints instead of maintaining them by hand.
- Mission layout changes are tested after a cold process restart, not by hot reload.
- Existing saves need a one-time hidden migration that clears stale pending state and calls the two-phase refresh.
- Preserve stable mission IDs during reflow. Reconstruct new progression flags from `mission_completed = <old_id>` because completed missions do not rerun newly added effects.

#### 5. Pass the mandatory static release gate

A mission-tree change is **static-safe** only when all checks pass for the frozen profile matrix:

1. Clausewitz parsing and brace balance pass for every gameplay file.
2. Mission IDs are globally unique; icons and all `_title` / `_desc` keys resolve.
3. Every active profile has the promised slot coverage, with no same-slot series overlap, cell collision, missing parent, or inactive parent.
4. The visible graph is acyclic, forward-only, and compliant with the canonical geometry rules, including occluded verticals, crossing diagonals, and parent-count limits.
5. Every series is physically declared in strictly increasing row order, with no undocumented source gap wider than the project limit.
6. Full national trees have exactly five custom non-generic slot owners and zero generic fallback in every profile.
7. Pinned vanilla overrides match the supported version/hash and retain exact inactive tombstone keys.
8. Every route/tag/religion transition uses the canonical two-phase refresh, and old-save migration plus fingerprint repair coverage exists where needed.
9. Project unit tests and regression fixtures pass, and the validator emits a machine-readable per-profile report.
10. Full final-tag profiles pass the project's slot-density, terminal-balance, and unique-series-signature contract.

`scripts/check_mission_series_overlap.py` is only a lightweight fallback. It cannot prove vanilla/DLC assembly, route coverage, edge geometry, or migration behavior. A mature full-tree project must maintain an effective-topology solver that models those inputs.

#### 6. Pass the permission-gated runtime release gate

Only after explicit permission to launch EU4:

1. Start a fresh game process with the target mod alone unless compatibility testing is requested.
2. Open at least one country from every distinct profile family plus every transient pre-route/post-route state promised by the release.
3. Scroll the full tree from top to bottom and capture evidence of all five columns, branch joins, bottom rows, and absence of generic filler.
4. Exercise route/religion/tag transitions, wait one day for the canonical refresh, and re-open the tree.
5. Load a migrated save, wait one day, and verify preserved completions and newly reconstructed flags.
6. Inspect the newly written `error.log` for parse failures, unknown triggers/effects, missing localisation, `mission.cpp:353`, inactive prerequisites, and mission-series errors.

Passing this gate permits the claim **runtime-confirmed for the tested profiles**. It is still not universal proof for untested mod combinations or unsupported game versions.

#### 7. Keep the tree readable after it is safe

- Give each column a stable institutional or narrative purpose and use legal local forks/merges instead of five unrelated vertical ladders.
- Do not add filler solely to occupy a slot. Every mission should advance a branch, expose a meaningful choice, or bridge two arcs.
- Do not block a landlocked start behind mandatory ports or fleets unless the profile explicitly selects a maritime branch.
- Keep mandatory prerequisites achievable in the same campaign state and audit hidden trigger dependencies for circular design.
- Treat missing localisation, wrong icons, unreadable branch order, or stale generic missions as release failures even when topology passes.

For large flavor mods that branch by religion, route, or government path without replacing vanilla mission files, use higher mission `position` values inside visible slots `1..5` and mutually exclusive `potential` blocks.

EU4's vanilla mission view is horizontally capped. In v1.37.5, `interface/countrymissionsview.gui` contains `max_slots_horizontal = 5`; mission groups with `slot > 5` can parse successfully and still be functionally invisible in-game. Prefer `slot = 1` through `slot = 5`, then place additive content below vanilla rows with higher `position` values.

Do not treat a forward, acyclic dependency graph as proof that the mission UI can draw it. Measurements from the active vanilla EU4 1.37.5 Japanese and Domination Japanese trees show these renderer-safe limits:

- same-column `required_missions` edges span one or two `position` rows;
- cross-column edges connect an adjacent slot on the immediately following row (`abs(child_slot - parent_slot) = 1` and `child_row - parent_row = 1`);
- a two-row vertical edge must not pass through another active mission cell;
- diagonal edges between the same pair of columns must not cross;
- vanilla Japanese nodes draw at most three visible parent lines.

Use `required_missions` for this short visible graph. Preserve a distant or otherwise cluttering prerequisite as a logical gate inside the mission trigger:

```txt
trigger = {
  mission_completed = my_distant_prerequisite
  stability = 1
}
```

Do not optimize for a high count of cross-column arrows; that metric directly encourages unreadable or broken trees. Model every mutually exclusive branch state, including representative tags for each daimyo house family, and reject cell collisions, inactive prerequisites, overlong edges, occluded verticals, and diagonal crossings per active profile. Mutually exclusive outcome missions must never both be listed as mandatory prerequisites of one continuation; gate the continuation on their shared result flag or an `OR` trigger instead.

Model vanilla generic fallback series when validating the effective tree. EU4 first selects active non-generic series; any such series occupies its entire slot and suppresses the generic series for that slot, even where the custom column has empty rows. Only then add active `generic = yes` series to wholly unoccupied slots. A Japanese daimyo tree using custom slots 1-3 therefore still displays the vanilla administrative series in slot 4 and the Asian trade series in slot 5. Run cell, dependency, and renderer checks on this assembled tree.

If the design promises a complete national tree, do not accept that fallback as harmless. Occupy all five visible slots with narrow custom series for every concrete daimyo tag, every final route tag, and transient states such as formed Japan before route selection. Treat any active generic series as a release error. When a new series is added to an existing campaign, call the project's canonical two-phase helper and add an old-save migration; a parser-clean mission file does not force an already-running save to rebuild its mission selection.

Mission IDs are useful migration anchors. Preserve old IDs when reflowing or expanding a tree, then reconstruct newly introduced flags with `mission_completed = old_id` in a one-time hidden event. Adding a flag-setting effect to an old mission is not enough because an already-completed mission never executes its new effect. Likewise, verify hardcoded effect names against the pinned vanilla version: EU4 1.37.5 uses `change_government_reform_progress = 25`, while `add_government_reform_progress` merely parses as an unknown assignment and fails at runtime.

Mission files are not safely hot-reloaded into an already running campaign. After changing positions, prerequisites, or mission potentials, restart EU4, allow any one-day migration/refresh event to run, and inspect a newly written `error.log`. A clean custom parser can still miss an engine-level `Unknown trigger type` that causes an entire mission file to be rejected.

Avoid same-route, same-slot non-generic mission series overlaps. EU4 can log `mission.cpp:353 Non-generic mission series ... overlapping ...` and then swallow or misdraw a column even when the two groups use different `position` ranges. For Japan route trees, run:

```powershell
$py = "$env:USERPROFILE\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
& $py "$env:USERPROFILE\.codex\skills\eu4-modding\scripts\check_mission_series_overlap.py" "$mod"
```

This is a series-level rule, not merely a cell-collision rule, for independently added custom series. Vanilla sometimes coordinates several segmented series in one slot inside the same mission package, but that does not make arbitrary additive groups safe. For each actual country state, keep at most one independently authored custom series active in each slot. If common, foundation, religious, and late-game groups need the same column, physically merge their mission blocks into one series whose `potential` matches that state, or move optional content into decisions/events. Do not assume disjoint row ranges alone make two custom series safe.

When a full custom tree must replace a vanilla tree, follow the pattern used by mature mission overhauls such as the locally inspected Europa Expanded installation:

- copy the exact supported-version vanilla mission files into the mod under the same `missions/` filenames;
- make a minimal change to every affected vanilla series `potential`, adding a shared exclusion trigger for countries using the custom tree;
- if the custom tree owns every country profile served by those files, add both `potential_on_load = { always = no }` and a country-scope `potential = { always = no ... }` guard to every replaced vanilla series so it cannot enter either candidate path;
- keep the original game directory untouched and pin the source file hashes in validation;
- validate the effective virtual filesystem so the mod override is used instead of counting both the original and override;
- keep one coherent custom series per needed slot/profile, then call `swap_non_generic_missions = yes` after route or tag changes;
- declare incompatibility or a required load order with other mods that override the same mission files.

Treat pinned vanilla mission overrides as compatibility infrastructure, not authored mod content. Enforce the unconditional disable in both the country-scoped `potential` and `potential_on_load`, retain the shared country exclusion for intent, and make the generator/validator check all three. Exclude these compatibility-only copies from custom-content visualizers, catalog counts, and custom-localisation completeness scans; otherwise vanilla missions can appear duplicated and create false missing-localisation reports.

`potential_on_load` is evaluated before a country scope exists. Do not put tags, country flags, or country-scoped scripted triggers there and expect them to make vanilla and custom trees mutually exclusive; the guard can appear syntactically valid while the original series still enters the candidate pool. Do not add `potential_on_load = { always = yes }` to every route candidate either. Use narrow country `potential` blocks for custom candidates, and use unconditional `always = no` only in pinned vanilla overrides when the custom mod fully owns all affected profiles. After changing this architecture, only a fresh game-process `error.log` can prove the `mission.cpp:353` warnings are gone.

Use a route-column matrix before adding groups. A tested safe Japan layout is:

- slot 1: shared state spine or daimyo domain spine;
- slot 2: shared court/economy spine or daimyo contact spine;
- slot 3: one active route main branch;
- slot 4: one active route support branch, such as Shinto, Christian deep, Confucian domestic, Muslim, or popular;
- slot 5: one active route continuation, such as Pacific for open trade, Christian/commonwealth support, Confucian/imperial rites, Kaikyo deep, or Wokou frontier.

Recommended pattern:

- keep the shared/unification spine in lower slots;
- keep branch columns inside visible slots `1` through `5`, using higher `position` ranges to avoid vanilla overlap;
- if several alternatives share the same visual column, give every group the same `slot` but make `potential` blocks strictly mutually exclusive with route flags, tags, religion, and `NOT = { OR = { ... } }` exclusions;
- connect the first branch mission to a shared route/settlement mission only when the two cells satisfy the renderer-safe row and slot limits; otherwise use `mission_completed` in the branch mission's trigger;
- use religion as an explicit branch gate when it matters, for example `religion = shinto`, `religion = confucianism`, `religion_group = christian`, or `religion_group = muslim`;
- for social routes that intentionally keep a vanilla religion for compatibility, gate the branch on route tags/flags instead of religion alone;
- reuse known-valid vanilla mission icons from the game root or existing mod files, then validate with the EU4 mod validator;
- when mission effects call events, localise both mission keys and event keys in the source localisation file, then generate active escaped localisation for Chinese setups;
- add new permanent or long-duration modifiers to debug cleanup effects so repeated test runs can reset the country cleanly.

This pattern is compatible with `swap_non_generic_missions = yes` after tag or route changes because it does not require `replace_path` or mission-file overrides. It also keeps religion branches from leaking into ordinary daimyo or unrelated Japanese-culture countries when the `potential` block includes both a Japanese polity trigger and narrow route/tag/religion conditions.

When a mission appears as completed/required in tooltips but cannot be found in the tree, check for invisible high slots first:

```powershell
rg -n "slot = ([6-9]|1[0-9]|20)" "$mod\missions"
Select-String -Path "$gameRoot\interface\countrymissionsview.gui" -Pattern "max_slots_horizontal"
```

For additive Japanese trees that keep vanilla missions, a safe layout is to keep vanilla in rows 1-8, put daimyo or shared mod missions around positions 9-15, deeper route missions around 17-30, and large overseas/economy/frontier continuations farther down the same visible columns.

If a mission group is intentionally parked with `potential = { always = no ... }`, mission-overlap tooling should ignore it as inactive. Do not move or rebalance disabled groups just to satisfy a checker; fix the checker to understand `always = no`, then separately decide whether the disabled content should be restored in a real visible slot.

If the Domination Japan mission tree is active, vanilla/DLC Japanese groups can use rows beyond 8. In the inspected v1.37.5 install, `missions/DOM_Japanese_Missions.txt` uses positions up to about 13 in the first five visible slots. For additive Japan mods that should coexist with the vanilla tree, start mod-owned visible branches around `position = 14` or later. Before choosing positions, inspect the real base tree with:

```powershell
rg -n "DOM_japanse_missions|slot =|position =" "$gameRoot\missions\DOM_Japanese_Missions.txt"
```

When a route should preserve another religious branch, do not put both branches in the same slot and position range. For example, a Confucian Japan that harmonizes Shinto can show a Shinto-syncretic branch in one visible slot and the Confucian branch in another. Keep the `potential` blocks explicit and add a route sync effect plus a hidden catch-up event for existing saves if a one-time conversion effect may have been missed.

Route changes must also clean old route state, not only set the new route flag. If an existing save has both `jxp_path_confucian` and `jxp_path_open_trade`, EU4 can activate the wrong mission columns even after `swap_non_generic_missions = yes`; the visible symptom is a route country showing another route's missions, such as Confucian Japan displaying open-trade Pacific missions. Put route sanitation in a reusable scripted effect:

- clear every mutually exclusive `jxp_path_*` flag;
- clear every stale route country modifier in the same effect or through the route-flag clearing helper;
- remove stale route country modifiers such as `jxp_route_open_trade`;
- prioritize the current route tag over stale route flags when sanitizing migrated saves. For example, `tag = KJP` with an accidental old `jxp_path_confucian` flag should remain Kirishitan Japan and have the Confucian flag cleared, not be converted into `CJP`;
- set exactly one route flag and route modifier;
- force the intended government type for route tags if vanilla events can see them as republics;
- run religion/harmonization sync effects;
- call `swap_non_generic_missions = yes`;
- add a hidden MTTH catch-up event for existing saves and old-version transitions.

For government-mechanic carrier reforms that are allowed for republics only for compatibility, add `custom_attributes = { cannot_become_dictatorship = yes }` unless the design intentionally wants vanilla low-republican-tradition dictatorship events. Otherwise an accidental republic state can fire vanilla `republics.3` ("Rise of a Dictator") and derail route flavor.

For route countries that should be monarchies, do not rely only on a hidden daily catch-up event to prevent `republics.3`. Call the route's monarchy-forcing cleanup from every route reform grant or tag-change helper, before or alongside `add_government_reform`, so the country is corrected during the same scripted action that creates the route.

When a Confucian route is meant to preserve Shinto flavor through harmonization, do not gate the Shinto-flavor mission branch on `religion = shinto` only. Add an alternate potential branch for the route tag/flag plus `has_harmonized_with = shinto`, a route-owned syncretism flag, or the route-owned harmonization modifier, while keeping other route flags excluded to avoid mission leakage.

## Route Government Reform Packs

When a flavor mod needs special government reforms for many route tags but should not replace vanilla `common/governments/00_governments.txt`, prefer auto-granted route reform packs:

- define route reforms in a separate `common/government_reforms/*.txt` file with `basic_reform = yes`;
- keep `monarchy = yes` and, if needed for old-save compatibility, `republic = yes` plus `custom_attributes = { cannot_become_dictatorship = yes }`;
- gate `potential` narrowly on route flags and/or route tags, but do not rely on player selection UI if the reform is meant as a route institution;
- create one scripted effect to remove all mutually exclusive route reforms before a route switch;
- create one scripted effect to grant the correct reforms for the current route/tag;
- call the grant effect from every route entry point, including route events, tag-change scripted effects, debug force-route effects, and sanitation/catch-up effects. Avoid hand-adding a single reform in one event while other entry points call the unified grant effect;
- add a hidden MTTH catch-up event that checks for a representative missing reform per route, then grants the pack once for existing saves. When expanding an existing pack, update this catch-up trigger to check both an old representative reform and a new representative reform, or old saves that already have the old reform will never receive the new additions;
- localise reform keys and `_desc` keys in `localisation_source`, then regenerate active localisation.

This pattern gives route countries visible government modifiers and durable institutional identity while avoiding a broad overwrite of vanilla government reform levels. If the user specifically wants reforms to appear as manual selectable entries in the normal government reform tiers, treat that as a separate compatibility-sensitive task: inspect the exact v1.37.5 `00_governments.txt`, merge rather than blindly replace, and run an in-game government UI test.

For route reforms that must actually appear in the normal government reform list, defining entries under `common/government_reforms` is not enough. The reform keys also need to be present in a government type's `reform_levels` under `common/governments/00_governments.txt` or a correctly merged equivalent. A practical pattern for a local version-locked flavor mod is:

- copy the inspected vanilla `common/governments/00_governments.txt` into the mod and make the smallest possible insertion;
- insert player-facing reform keys into the semantically matching existing vanilla levels; do not append project-specific levels after the normal progression unless the design explicitly requires a new tier;
- remove `basic_reform = yes` from reforms intended to be visible, because basic reforms are invisible/no-slot carrier reforms;
- use a stable `potential` such as the owning country family or Japanese-polity trigger, and move route flags, mission flags, and other later unlocks into `trigger`; EU4 can build/cache the reform tree before those dynamic flags exist, leaving a correctly defined and registered reform permanently absent from the UI;
- include `allow_normal_conversion = yes` on normal selectable reforms, matching the v1.37.5 vanilla tier style;
- keep route-clear scripted effects so route switching cleans old selections, but do not auto-grant reforms that are meant to be manual tier choices;
- for later optional two-choice or multi-choice route levels, register the reform keys in `common/governments` and add them to the route-clear effect, but do not add them to the auto-grant effect. Otherwise the country receives every option in the level and the government UI loses the intended player choice;
- when expanding mature route reform trees with a new optional level, validate the full chain: reform definition, stable family `potential`, dynamic route/tag `trigger`, government-level registration, level localisation, reform localisation, and route-switch cleanup. Optional route levels should raise the visible reform count in coverage tooling; a green registration check alone is not enough if the reform was removed from the tree before its route flag existed;
- when a new route reform slice is meant to be a player-facing design focus, give each route several mutually exclusive choices in one visible level, keep strengths route-specific rather than generic, and deliberately omit those reforms from `jxp_grant_route_reforms_effect`. The grant effect is for carrier or guaranteed institutions; optional levels should be chosen through the government UI and only cleared by route-switch sanitation.
- when expanding every route with one or more new visible levels, update all three guardrails in the same slice: add the reform-level keys to `common/governments`, add those level keys to coverage tooling, and raise the minimum visible reform count per route. This prevents a broad "government reform expansion" from silently covering only the routes that happened to be tested.
- for all-route optional reform layers, every route-specific reform still needs route-switch cleanup even though it is not auto-granted. Otherwise a player who changes route or a debug save that flips flags can keep a stale selected reform from another Japan.
- for mature all-route optional layers, prefer one visible level with several route-narrow mutually exclusive reforms per route. Do not add these to the auto-grant effect; register them in `common/governments`, add every key to route-switch cleanup, localise the level and all reforms, and raise the route-visible minimum in the checker by the exact number of new per-route choices.
- if a route-government system starts adding many custom visible levels after the vanilla monarchy reform tiers, consolidate before expanding further. For EU4-style compatibility and pacing, visible Japan reforms should normally be registered inside the existing 11 monarchy level keys by theme: government foundations in `feudalism_vs_autocracy`, hereditary retainers and noble settlements in `hereditary_vs_nobility`, offices and lawbooks in `bureaucracy`, religious synthesis in `state_and_religion`, armies/navies/arsenals in `military_doctrines`, councils in `deliberative_assembly`, provincial administration in `growth_of_administration`, trade/finance/ports in `economical_matters`, legitimacy/mandate in `legitimation_of_power`, centralization/charters in `absolute_rule_vs_constitutional`, and cabinets/courts/high offices in `separation_of_power`. A reform's founder-house identity does not make it a noble-privilege reform: classify the institution it actually represents. If the project already has overloaded bespoke `jxp_route_institution_*` levels, keep only a small UI-safe core visible and park the later reform definitions until they can be converted into events, missions, or vanilla-tier choices. Update coverage tooling to reject ever-longer custom tier chains instead of rewarding high visible reform counts.
- custom government reform icons should follow the vanilla pattern: final DDS files under `gfx/interface/government_reform_icons/` are 57x57 RGBA, sprites are registered as `government_reform_<icon_key>` in an interface `.gfx` file, and reform definitions use `icon = "<icon_key>"`. When the user asks for generated EU4-style reform art, create imagegen source sheets, crop/alpha-process them, export verified DDS files, and add a checker for icon references, sprite registrations, texture existence, dimensions, alpha, and nonblank pixels.
- when consolidating several mature decision chains into one UI entry, add a central decision that opens a triggered menu event and dispatches to scripted effects for the original chains. Keep the old detailed decisions in place but hide them behind a deliberately named debug/detail flag, then add coverage for the central decision, menu options, old dispatch events/costs, hidden old potentials, and localisation. This reduces UI clutter without losing save/debug compatibility.
- localise both the reform keys and the new reform-level keys, then validate. Recheck this merge whenever the supported EU4 minor version changes.

For Japan founder-house reforms, keep the founding house as a separate identity layer from religious or diplomatic routes, but do not create one catch-all founder tier. The route answers what kind of Japan the state becomes; the founder option records which household supplied an institution. A robust pattern is:

- define one narrow reform per origin flag and preserve already selected reforms with `potential = { OR = { has_reform = <self> AND = { jxp_is_unified_japan_state_trigger = yes has_country_flag = jxp_origin_<tag> } } }`;
- register every founder reform in the existing vanilla level matching its actual institution. A gunfoundry is military doctrine, a port brokerage is economic, a shrine compact is state-and-religion, a cadaster is administrative growth, and a council is deliberative;
- rely on the origin-filtered potential to expose only one founder option per country. Do not auto-grant it, especially when its semantic tier may not be unlocked yet;
- when migrating from an old catch-all tier, detect a selected founder reform, remove it, restore a valid fallback in the vacated lower tier, refund reform progress, and regenerate government mechanics. Leave the origin-specific reform available in its new tier;
- keep founder choices across ordinary route switching, because house identity should survive a later Kirishitan, Confucian, imperial, or maritime route choice; clear them only when origin state itself is reset;
- extend coverage tooling with a complete reform-to-level semantic matrix plus checks for definition, one registration, origin-specific potential, localisation, zero auto-grants, migration flags, and debug cleanup.
- for low-frequency events that should fire only after a founder-house reform is actually selected, gate the event on `has_reform = jxp_reform_founder_*` rather than only the persistent `jxp_origin_*` flag. Origin flags prove who founded Japan; `has_reform` proves the government UI choice exists in the current state. If events are grouped by founder-house archetype, make coverage tooling derive the expected reform keys from the reform definitions and compare them against the archetype trigger instead of maintaining a second hand-written tag list.
- for exact-house follow-up events covering a named subset such as the major daimyo, maintain a concrete checker table with the tag, event id, exact founder reform key, one-shot flag, and both reward modifiers. Also compare the table against the promised subset order. Otherwise every written event can pass while one intended house was never implemented, or an event can accidentally trigger from an origin flag instead of the selected government reform.

For one-time founder legacy council decisions, validate the concrete decision chain rather than a broad "unified legacy event exists" signal. In `japan_expanded_v2`, the `jxp_decision_convene_founder_legacy_council` chain should be checked per expected daimyo origin for:

- inclusion in the scripted trigger that makes the decision visible;
- inclusion in the decision's `if` / `else_if` dispatch chain, pointing at the matching event id;
- one triggered event gated by `jxp_is_unified_japan_state_trigger`, the matching `jxp_origin_<tag>` flag, and the shared `jxp_26_founder_legacy_council_taken` guard;
- exactly two options if the design promises a meaningful choice;
- every added temporary modifier defined, localized, and removed by debug cleanup;
- every per-origin seen flag cleared by debug cleanup.

Do not let older grouped legacy systems such as archetype events, permanent family modifiers, or founder-house government reforms substitute for this check. They are complementary layers, not proof that a specific player-facing decision works for every origin.

When unified Japan should keep the mechanical memory of the daimyo's original national ideas, convert that identity into a one-time founder idea legacy instead of trying to keep multiple national idea groups active. A reliable pattern is:

- gate the decision on unified-Japan state, a canonical founder-origin trigger, and a one-time compiled flag;
- dispatch by founder-house archetype so the event text and broad choice style stay readable;
- use a single `if` / `else_if` scripted effect over every expected `jxp_origin_<tag>` flag to add exactly one exact-origin permanent modifier;
- offer a generic archetype school as the second event option, so migrated saves or players who prefer a broader institution still receive a coherent reward;
- clear the compiled flag, all exact-origin modifiers, and all generic school modifiers in debug cleanup;
- extend coverage tooling from the canonical daimyo tag list so each origin flag, modifier definition, localisation pair, add effect, and cleanup line is checked.

When tuning existing idea groups in a Chinese double-byte-patch mod, check whether older `localisation_source` files are still human-readable UTF-8 or already contain escaped/mojibake-like output. If the old source is not safely editable, prefer a new later-sorting localisation source file such as `jxp_41_*_utf8_source.yml` with only the revised keys, then regenerate the active escaped `localisation` file. Also add a targeted coverage section that checks each revised idea block for the new modifier snippets and the override localisation keys. This avoids corrupting older text while still making the current balance pass auditable.

When early flavor events share a small generic modifier pool, they may pass coverage while still feeling repetitive. For major/representative daimyo event chains, prefer event-specific or small-group-specific modifiers that preserve the same trigger and option structure but give each house a distinct mechanical memory. Add coverage that checks:

- every expected event id uses the new specific modifier keys;
- the old generic reward pool no longer appears in that event series;
- every new modifier has a definition, localisation key and `_desc`, and debug cleanup;
- the modifier keys are validated against vanilla `common` before delivery.

For full-daimyo event reward passes, do not treat grouped MTTH events as proof of single-house flavor. In `japan_expanded_v2`, dedicated single-tag namespaces such as `jxp_major_daimyo`, `jxp_remaining_daimyo`, and `jxp_minor_house` should be checked separately from grouped archetype events such as `jxp_minor_daimyo`. Coverage should scan every dedicated namespace, reject old shared `jxp_daimyo_*` reward pools across all early event series, and verify modifier definitions/localisation/debug cleanup per event.

For cross-system route/founder content, validate the whole player-facing chain rather than only the final event file. A robust one-time compromise layer should have: one decision with narrow unified-Japan, route, and founder-origin gates; an `if` / `else_if` route dispatch so stale multi-route debug saves do not fire several events; one event per route with exactly the intended choice count; a centralized founder-house effect for archetype-specific rewards; route and house modifiers defined and localized; and one debug cleanup effect called by the general event-state reset. This prevents route flavor, founder flavor, and debug testing state from drifting apart as the mod grows.

For low-frequency route/founder MTTH events, keep them separate from one-time decision chains. Gate them by unified Japan, a selected route or route tag, one founder-house archetype trigger, and a per-event `*_seen` flag. Give every event a real `mean_time_to_happen`, two meaningful options, one route-pressure effect and one house-accommodation effect, and temporary modifiers with localisation. Add the flags and modifiers to debug cleanup, then extend coverage tooling so frequency, options, modifiers, localisation, and cleanup are all checked together. This keeps flavor variety from becoming hidden event spam or stale-save clutter.

For a single decision that branches by daimyo founder-house archetype, validate the branch matrix rather than only the decision key. The decision should record origin state before firing the event, and the checker should verify each archetype's visible option pair, reward modifiers, localisation keys, and debug cleanup. Add a narrow fallback option only for missing-origin debug or migrated saves; do not let it appear alongside normal archetype choices.

When an early-game choice is meant to matter after unification, do not rely on a timed modifier as the only memory of that choice. Set a specific persistent `selected_*` country flag for each option, clear those flags in debug cleanup, and make the later unification or route event read the flag while optionally removing the old timed modifier. Extend coverage tooling to verify the early option sets the flag and the later event consumes or rewards that exact flag.

For a multi-house pre-unification policy memory chain, validate the whole path per row: the early decision sets the persistent memory flag, the unified-Japan decision is gated by the shared unconsumed flag and dispatches with an `if` / `else_if` chain, the target event checks the same memory flag and sets one shared consumed flag, both policy options add localized modifiers, and debug cleanup clears every memory flag plus every permanent reward modifier. This prevents a feature from looking complete because the final event exists while the early decision never records the state that unlocks it.

For full-daimyo variants of that chain, make the checker compare its explicit expected-row table against the canonical tag list from the project trigger, not only against rows that were already written. A report where all listed rows pass can still be incomplete if one intended house never appears in the table.

When adding missions that consume a flag set by a recent event or decision, keep the mission group's `potential` stable unless the same effect calls `swap_non_generic_missions = yes`. A safe pattern is to gate the group on stable tags or route state, then put the new flag in the first mission's `trigger`. This avoids a newly unlocked mission branch staying invisible because the mission tree was not refreshed.

For concrete founder-tag and route combination events, maintain an explicit expected-combo table in tooling. Each row should name the origin flag, route flag/tag condition, event id, seen flag, and exactly two reward modifiers. This is preferable to ad hoc searches because representative combinations grow irregularly over time, and a broad "specific event file exists" check will not catch one missing route gate, stale flag, localisation pair, or debug cleanup entry.

When a development slice promises coverage for a named subset such as the major daimyo, compare the expected-combo table against that subset's tag list as well as validating each row. It is easy for every written event to pass while one intended major house was never assigned a representative route combo.

When expanding a representative route/founder system to all expected origins, make the checker assert full origin coverage from the canonical tag source, not only the older major-house subset. Keep event frequency bands aligned between implementation and tooling: if the checker accepts a deliberate low-frequency MTTH band such as 300/310/320 months, adding 330-month events is a design drift unless the checker and phase report explicitly widen the band.

When doing national-idea identity passes for many daimyo, avoid replacing one generic strong modifier with another generic strong modifier. Prefer small combinations that match the house's geography, status, institutions, and historical memory: court-facing houses can use diplomacy, relations, advisor, or legitimacy-adjacent bonuses; mountain or frontier houses can use attrition, movement, garrison, or state-maintenance bonuses; maritime brokers can use trade steering, sailors, envoys, and institution spread. Add each revised idea to a checker table with exact modifier snippets and localisation keys so later balance work does not silently revert the pass.

For decloning passes, add at least one residual-signature check for the old template pattern, not only positive checks for new rows. Examples from `japan_expanded_v2`: reject the repeated five-stat legitimacy package `legitimacy/devotion/republican_tradition/meritocracy/horde_unity` in daimyo idea files, and reject one-line `defensiveness = 0.20` castle ideas after they have been split into castle-specific combinations. This catches unedited remnants that a row-based coverage table would never see.

EU4 1.37.5 country and national-idea fort defense uses the modifier key `defensiveness`; the plausible key `fort_defense` is absent from the pinned game catalog. Because an ordinary Clausewitz parser accepts either spelling, keep a residual negative check for `fort_defense` in generated ideas, modifier definitions, and their source plans.

In EU4 v1.37.5, `sailor_maintenance_modifer` is a vanilla-valid misspelling used by the game data. Do not correct it to `sailor_maintenance_modifier` unless a validator or vanilla data proves the engine added a new spelling in a later version. Treat this as a known-good EU4 typo when reviewing idea files and government reforms.

In EU4 v1.37.5, the offensive spy network modifier is `spy_offence`; do not invent `global_spy_offence` by analogy with `global_spy_defence`. Check vanilla modifier names with `rg` before adding a new government reform or event modifier.

## Parallel Agent Integration Checks

When multiple agents work on the same EU4 mod, run an integration pass before final validation:

- confirm every newly created `jxp_*` or mod-owned file lives under the local mod path, not the EU4 game root;
- check for duplicate implementations of the same feature, especially hidden catch-up events, once-only country flags, permanent modifiers, and namespace ranges;
- pick one canonical implementation and delete or merge the duplicate before testing, otherwise a country can receive two events or stacked permanent modifiers;
- regenerate active localisation for every new `localisation_source/*_utf8_source.yml`, even if a subagent only changed source files;
- if multiple agents write the same localisation source file, merge the keys manually before regenerating active localisation and `rg` for representative event, decision, mission, and modifier keys afterward. A later worker can otherwise overwrite earlier event keys while validation still passes structurally;
- re-run debug cleanup coverage for any new permanent country modifier, province modifier, or once-only flag;
- after integration, run the normal validator and mission overlap checker.

Useful root-residual check from the EU4 game root:

```powershell
Get-ChildItem -Path "$gameRoot" -Recurse -File -Filter "jxp_*" |
  Where-Object { $_.FullName -notlike "*\Documents\Paradox Interactive\Europa Universalis IV\mod\japan_expanded_v2\*" }
```

If the mod id differs, replace the hard-coded mod segment or compare paths against the resolved `$mod` variable.

### Shared Development Ledger Pattern

For a long-lived mod maintained across agents and conversation windows, keep one canonical ledger in the required parent mod and make every companion point to it from a root `AGENTS.md`. Do not duplicate current state into separate main/companion TODO files. Historical phase reports stay immutable; the ledger owns only the current version snapshot, active TODO, known risks, validation evidence, handoff protocol, newest-first journal, and a complete report index.

Give TODOs stable IDs, a bounded status vocabulary, an owner, scope, task, and acceptance evidence. Never delete an ID after completion. During parallel work, let the lead agent claim and update the ledger; subagents return touched-file lists and evidence so two workers do not overwrite the same coordination file.

Put ledger integrity in the normal static release gate. At minimum, validate:

- main and companion inner/outer descriptor versions against the ledger snapshot;
- unique TODO IDs, valid statuses, and an owner for every in-progress item;
- one exact ledger pointer in each mod-root `AGENTS.md`;
- presence of runtime-permission and parent/companion compatibility rules;
- indexing of every file in each `dev_logs` directory;
- an update-journal entry and current validation evidence for the completed slice.

Use explicit evidence classes such as `STATIC_PASS`, `RUNTIME_PASS`, `USER_OBSERVED`, and `PENDING_RUNTIME`. Static parsers, topology solvers, and asset checks never justify a runtime claim. If the user has prohibited unsolicited launches, preserve that rule in the ledger, every agent entry point, and the validator.
