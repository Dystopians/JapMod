"""Guard semantic replacements for map-scale-sensitive progression gates."""

from __future__ import annotations

from pathlib import Path
import re

from .clausewitz import Object, Scalar, parse_text
from .core import CheckResult, ValidationContext


SEMANTIC_TRIGGER_FILE = Path("common/scripted_triggers/jxp_70_map_scale_triggers.txt")
LEGACY_CITY_THRESHOLDS = ("25", "30")

# Each former 25/30-city gate has one named semantic contract at its original
# gameplay site.  Keeping the mapping executable prevents a later bulk edit
# from silently restoring a province-count proxy.
EXPECTED_CALLS = {
    "jxp_has_shrine_castle_town_network_trigger": ((
        "missions/jxp_11_branching_missions.txt",
        "jxp_mission_kami_castle_towns",
    ),),
    "jxp_has_halal_granary_network_trigger": ((
        "missions/jxp_11_branching_missions.txt",
        "jxp_mission_halal_granary_law",
    ),),
    "jxp_can_settle_preunification_realm_trigger": ((
        "decisions/jxp_polity_decisions.txt",
        "jxp_decision_settle_the_realm",
    ),),
    "jxp_has_osaka_rice_ledger_network_trigger": (
        ("missions/jxp_japan_missions.txt", "jxp_mission_osaka_rice_ledger"),
        ("decisions/jxp_a_104_economy_decisions.txt", "jxp_a_charter_company_rice_credit"),
    ),
    "jxp_has_castle_town_market_network_trigger": ((
        "missions/jxp_japan_missions.txt",
        "jxp_mission_castle_town_markets",
    ),),
    "jxp_has_border_port_coverage_trigger": ((
        "missions/jxp_40_final_state_completion_missions.txt",
        "jxp_mission_uncommitted_register_border_ports",
    ),),
    "jxp_has_ikko_fellowship_integration_trigger": ((
        "missions/jxp_40_final_state_completion_missions.txt",
        "jxp_mission_ikko_realm_of_fellowship",
    ),),
    "jxp_has_kami_classics_network_trigger": ((
        "missions/jxp_56_final_tag_identity_missions.txt",
        "jxp_mission_cjp_kami_classics",
    ),),
    "jxp_has_shrine_envoy_network_trigger": ((
        "missions/jxp_56_final_tag_identity_missions.txt",
        "jxp_mission_ejp_shrine_envoys",
    ),),
}

COMPANION_ONLY_REFERENCE = re.compile(
    r"\bjxp_map_[A-Za-z0-9_]+\b|\b49(?:4[2-9]|[5-7][0-9]|8[01])\b"
)


# This is the executable design contract for the fixed semantic gates.  It is
# deliberately independent from the live scripted-trigger file: validating
# only names and call sites would allow a trigger body to regress to
# ``always = yes`` while the release gate remained green.  Clausewitz objects
# are compared after stripping comments, source locations, and entry order.
_EXPECTED_TRIGGER_DOCUMENT = parse_text(
    r"""
jxp_has_main_island_strategic_control_trigger = {
	total_development = 250
	owns_or_non_sovereign_subject_of = 4182
	owns_or_non_sovereign_subject_of = 4193
	shikoku_area = {
		type = all
		country_or_non_sovereign_subject_holds = ROOT
	}
}
jxp_has_unite_the_isles_scope_trigger = {
	jxp_has_main_island_strategic_control_trigger = yes
}
jxp_has_inherited_realm_order_trigger = {
	jxp_tenka_order_at_least_75 = yes
	total_development = 250
	owns_or_non_sovereign_subject_of = 1028
}
jxp_has_renewed_japan_integration_trigger = {
	jxp_tenka_order_at_least_75 = yes
	japan_region = {
		type = all
		country_or_non_sovereign_subject_holds = ROOT
	}
}
jxp_has_post_station_office_network_trigger = {
	num_of_provinces_owned_or_owned_by_non_sovereign_subjects_with = {
		value = 8
		region = japan_region
		OR = {
			has_building = courthouse
			has_building = town_hall
		}
	}
}
jxp_has_frontier_local_office_network_trigger = {
	num_of_provinces_owned_or_owned_by_non_sovereign_subjects_with = {
		value = 4
		region = japan_region
		OR = {
			has_building = courthouse
			has_building = town_hall
		}
	}
}
jxp_has_osaka_rice_ledger_network_trigger = {
	num_of_provinces_owned_or_owned_by_non_sovereign_subjects_with = {
		value = 6
		region = japan_region
		OR = {
			has_building = workshop
			has_building = counting_house
		}
	}
}
jxp_has_castle_town_market_network_trigger = {
	num_of_provinces_owned_or_owned_by_non_sovereign_subjects_with = {
		value = 8
		region = japan_region
		OR = {
			has_building = marketplace
			has_building = trade_depot
			has_building = stock_exchange
		}
	}
}
jxp_can_settle_preunification_realm_trigger = {
	jxp_has_main_island_strategic_control_trigger = yes
}
jxp_has_kami_classics_network_trigger = {
	owns_or_non_sovereign_subject_of = 1020
	owns_or_non_sovereign_subject_of = 4359
	num_of_provinces_owned_or_owned_by_non_sovereign_subjects_with = {
		value = 6
		region = japan_region
		OR = {
			has_building = temple
			has_building = cathedral
		}
	}
}
jxp_has_kokushi_circuit_coverage_trigger = {
	owns_or_non_sovereign_subject_of = 1020
	owns_or_non_sovereign_subject_of = 1028
	owns_or_non_sovereign_subject_of = 4182
	owns_or_non_sovereign_subject_of = 4193
	owns_or_non_sovereign_subject_of = 4359
	shikoku_area = {
		type = all
		country_or_non_sovereign_subject_holds = ROOT
	}
}
jxp_has_shrine_envoy_network_trigger = {
	owns_or_non_sovereign_subject_of = 1020
	owns_or_non_sovereign_subject_of = 4359
	num_of_provinces_owned_or_owned_by_non_sovereign_subjects_with = {
		value = 6
		region = japan_region
		OR = {
			has_building = temple
			has_building = cathedral
		}
	}
}
jxp_can_summon_realm_council_trigger = {
	jxp_tenka_order_at_least_50 = yes
	jxp_imperial_sanction_at_least_30 = yes
}
jxp_has_domain_memorial_network_trigger = {
	num_of_provinces_owned_or_owned_by_non_sovereign_subjects_with = {
		value = 6
		region = japan_region
		OR = {
			has_building = courthouse
			has_building = town_hall
		}
	}
}
jxp_has_border_port_coverage_trigger = {
	OR = {
		owns_or_non_sovereign_subject_of = 1015
		owns_or_non_sovereign_subject_of = 4182
		owns_or_non_sovereign_subject_of = 4193
		owns_or_non_sovereign_subject_of = 4651
	}
}
jxp_has_ikko_fellowship_integration_trigger = {
	jxp_tenka_order_at_least_75 = yes
	religious_unity = 0.9
}
jxp_has_shrine_castle_town_network_trigger = {
	num_of_provinces_owned_or_owned_by_non_sovereign_subjects_with = {
		value = 5
		region = japan_region
		OR = {
			has_building = temple
			has_building = cathedral
		}
		OR = {
			has_building = marketplace
			has_building = trade_depot
			has_building = stock_exchange
		}
	}
}
jxp_has_ritual_census_network_trigger = {
	num_of_provinces_owned_or_owned_by_non_sovereign_subjects_with = {
		value = 8
		region = japan_region
		OR = {
			has_building = courthouse
			has_building = town_hall
		}
	}
}
jxp_has_halal_granary_network_trigger = {
	num_of_provinces_owned_or_owned_by_non_sovereign_subjects_with = {
		value = 6
		region = japan_region
		OR = {
			has_building = workshop
			has_building = counting_house
		}
	}
}
jxp_has_ikko_commonwealth_order_trigger = {
	jxp_tenka_order_at_least_50 = yes
	religious_unity = 0.8
}
"""
)
EXPECTED_TRIGGER_BODIES = {
    entry.key: entry.value
    for entry in _EXPECTED_TRIGGER_DOCUMENT.root.entries
    if entry.key is not None and isinstance(entry.value, Object)
}


def _canonical_object(obj: Object) -> tuple[object, ...]:
    """Return a location- and order-independent representation of an object."""

    members: list[tuple[object, ...]] = []
    for entry in obj.entries:
        if isinstance(entry.value, Object):
            value: tuple[object, ...] = ("object", _canonical_object(entry.value))
        elif isinstance(entry.value, Scalar):
            value = ("scalar", entry.value.text)
        else:  # pragma: no cover - Clausewitz Value is intentionally exhaustive.
            raise TypeError(f"unsupported Clausewitz value: {type(entry.value)!r}")
        members.append((entry.key, entry.operator, value))
    return tuple(sorted(members, key=repr))


def check_map_scale_progression(context: ValidationContext) -> CheckResult:
    result = CheckResult("Map-scale-sensitive progression gates")

    legacy_occurrences = []
    for value in LEGACY_CITY_THRESHOLDS:
        legacy_occurrences.extend(context.assignment_occurrences("num_of_cities", value))
    for occurrence in legacy_occurrences:
        result.add(
            "map_scale.legacy_city_threshold",
            f"replace map-sensitive num_of_cities = {occurrence.value} with a semantic gate",
            context.relative(occurrence.source),
            occurrence.entry.line,
        )

    trigger_source = context.mod_root / SEMANTIC_TRIGGER_FILE
    trigger_document = context.document(trigger_source) if trigger_source.is_file() else None
    trigger_root = trigger_document.root if trigger_document is not None else None
    defined = 0
    contracts_matched = 0
    if trigger_document is None:
        result.add(
            "map_scale.trigger_file_missing",
            "semantic map-scale trigger file is missing or invalid",
            SEMANTIC_TRIGGER_FILE.as_posix(),
        )
    else:
        source_text = trigger_source.read_text(encoding="utf-8")
        for match in COMPANION_ONLY_REFERENCE.finditer(source_text):
            line = source_text.count("\n", 0, match.start()) + 1
            result.add(
                "map_scale.companion_only_reference",
                f"main-mod semantic gate references companion-only object {match.group(0)}",
                SEMANTIC_TRIGGER_FILE.as_posix(),
                line,
            )

    matched_calls = 0
    for trigger_name, expected_body in EXPECTED_TRIGGER_BODIES.items():
        definition_entries = (
            tuple(
                entry
                for entry in trigger_root.entries
                if entry.key == trigger_name
            )
            if trigger_root is not None
            else ()
        )
        if (
            len(definition_entries) != 1
            or definition_entries[0].operator != "="
            or not isinstance(definition_entries[0].value, Object)
        ):
            result.add(
                "map_scale.trigger_missing",
                f"{trigger_name} has {len(definition_entries)} definitions; "
                "expected exactly one object assignment",
                SEMANTIC_TRIGGER_FILE.as_posix(),
            )
        else:
            defined += 1
            definition = definition_entries[0].value
            if _canonical_object(definition) != _canonical_object(expected_body):
                result.add(
                    "map_scale.trigger_contract",
                    f"{trigger_name} no longer matches its fixed semantic contract",
                    SEMANTIC_TRIGGER_FILE.as_posix(),
                )
            else:
                contracts_matched += 1

    matched_calls = 0
    expected_call_count = sum(len(sites) for sites in EXPECTED_CALLS.values())
    for trigger_name, expected_sites in EXPECTED_CALLS.items():
        occurrences = context.assignment_occurrences(trigger_name, "yes")
        if len(occurrences) != len(expected_sites):
            result.add(
                "map_scale.call_count",
                f"{trigger_name} has {len(occurrences)} gameplay calls; expected exactly {len(expected_sites)}",
            )
        for expected_source, expected_anchor in expected_sites:
            candidates = [
                occurrence
                for occurrence in occurrences
                if context.relative(occurrence.source) == expected_source
                and expected_anchor in occurrence.path
            ]
            if len(candidates) != 1:
                result.add(
                    "map_scale.call_site",
                    f"{trigger_name} has {len(candidates)} calls at {expected_source}::{expected_anchor}; expected one",
                    expected_source,
                )
                continue
            occurrence = candidates[0]
            anchor_index = occurrence.path.index(expected_anchor)
            expected_scope = "allow" if expected_source.startswith("decisions/") else "trigger"
            if (
                anchor_index + 1 >= len(occurrence.path)
                or occurrence.path[anchor_index + 1] != expected_scope
            ):
                result.add(
                    "map_scale.call_context",
                    f"{trigger_name} is inside {expected_anchor} but not its {expected_scope} block",
                    expected_source,
                    occurrence.entry.line,
                )
                continue
            if any(
                component in {"NOT", "NOR", "NAND"}
                for component in occurrence.path[anchor_index + 2 :]
            ):
                result.add(
                    "map_scale.call_polarity",
                    f"{trigger_name} is negated inside {expected_anchor}'s {expected_scope} block",
                    expected_source,
                    occurrence.entry.line,
                )
                continue
            matched_calls += 1

    result.metrics.update(
        {
            "legacy_city_thresholds": len(legacy_occurrences),
            "semantic_triggers": defined,
            "semantic_contracts": contracts_matched,
            "matched_calls": matched_calls,
        }
    )
    result.summary = (
        f"{matched_calls}/{expected_call_count} semantic replacements; "
        f"{contracts_matched}/{len(EXPECTED_TRIGGER_BODIES)} fixed contracts; "
        f"{len(legacy_occurrences)} legacy 25/30-city thresholds"
    )
    return result
