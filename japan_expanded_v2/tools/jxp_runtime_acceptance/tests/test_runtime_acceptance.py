from __future__ import annotations

import base64
import contextlib
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import struct
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import zipfile
import zlib


TOOLS_ROOT = Path(__file__).resolve().parents[2]
if str(TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(TOOLS_ROOT))

from jxp_runtime_acceptance import runtime_acceptance as runtime
from jxp_runtime_acceptance import r13_python_runner as r13_runner


LIVE_REPO = Path(__file__).resolve().parents[4]
ATTESTED_AT = "2026-07-13T16:00:00+00:00"


def _write(path: Path, text: str = "payload\n") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _write_json(path: Path, value: object) -> Path:
    return _write(
        path,
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
    )


def _png_chunk(kind: bytes, payload: bytes) -> bytes:
    crc = zlib.crc32(kind + payload) & 0xFFFFFFFF
    return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", crc)


def _write_png(path: Path, rgb: tuple[int, int, int] = (30, 90, 160)) -> Path:
    """Write a fully structured 64x64 RGB PNG with valid scanlines and CRCs."""

    path.parent.mkdir(parents=True, exist_ok=True)
    width = height = 64
    scanlines = (b"\x00" + bytes(rgb) * width) * height
    payload = b"".join(
        (
            b"\x89PNG\r\n\x1a\n",
            _png_chunk(
                b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
            ),
            _png_chunk(b"IDAT", zlib.compress(scanlines)),
            _png_chunk(b"IEND", b""),
        )
    )
    path.write_bytes(payload)
    return path


def _write_eu4(path: Path, marker: str = "fixture") -> Path:
    """Write a structured, balanced ZIP-form EU4 text save fixture."""

    path.parent.mkdir(parents=True, exist_ok=True)
    meta = bytearray(
        b"EU4txt\n"
        b"date=1444.11.11\n"
        b'save_game="fixture.eu4"\n'
        b'player="JPN"\n'
        b"savegame_version={\n"
        b"\tfirst=1\n\tsecond=37\n\tthird=5\n\tforth=0\n"
        b'\tname="Inca"\n}\nmeta_fixture={\n'
    )
    counter = 0
    while len(meta) < 1024:
        digest = sha256(f"{marker}:meta:{counter}".encode("utf-8")).hexdigest()
        meta.extend(f'\titem="{digest}"\n'.encode("ascii"))
        counter += 1
    meta.extend(b"}\n")

    gamestate = bytearray(
        b"EU4txt\nplayers_countries={\n\t\"Player\"\n\t\"JPN\"\n}\n"
        b"gameplaysettings={\n\tsetgameplayoptions={ 0 0 0 }\n}\n"
        b"countries={\n\tJPN={\n\t\tcapital=1020\n\t}\n}\nfixture_data={\n"
    )
    counter = 0
    while len(gamestate) < 300 * 1024:
        digest = sha256(f"{marker}:gamestate:{counter}".encode("utf-8")).hexdigest()
        gamestate.extend(f'\titem="{digest}"\n'.encode("ascii"))
        counter += 1
    gamestate.extend(b"}\n")

    def stable_payload(value: bytearray) -> bytes:
        payload = bytearray(value)
        counter = 0
        while len(payload) < 1024:
            payload.extend(sha256(f"{marker}:{counter}".encode("utf-8")).digest())
            counter += 1
        return bytes(payload)

    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("meta", stable_payload(meta))
        archive.writestr("gamestate", stable_payload(gamestate))
    return path


def _component(root: Path, key: str = "main") -> runtime.Component:
    source = root / f"source-{key}"
    for directory in runtime.RUNTIME_DIRECTORIES[key]:
        _write(source / directory / "payload.txt")
    version = "0.1.3-alpha" if key == "map" else "0.28.0"
    _write(
        source / "descriptor.mod",
        f'supported_version="1.37.*"\nversion="{version}"\n',
    )
    _write_png(source / "thumbnail.png")
    outer = root / f"{key}.mod"
    _write(outer, f'name="fixture"\nversion="{version}"\n')
    _write(source / "tools" / "must-not-deploy.py")
    _write(source / "dev_logs" / "must-not-deploy.md")
    _write(source / "localisation_source" / "must-not-deploy.yml")
    _write(source / "AGENTS.md")
    _write_png(source / "thumbnail_imagegen_source.png", (90, 20, 10))
    return runtime.Component(key, source, outer)


@contextlib.contextmanager
def _runtime_environment(root: Path):
    """Patch canonical locations and all twelve pins into a hermetic test tree."""

    root = root.resolve()
    repo = root / "repo"
    game = root / "game"
    user_data = root / "acceptance"
    daily_user_data = root / "daily"
    for directory in (repo, game, user_data, daily_user_data):
        directory.mkdir(parents=True, exist_ok=True)

    _write(
        repo / "japan_expanded_v2" / "descriptor.mod",
        'version="0.28.0"\n',
    )
    _write(
        repo / "japan_expanded_v2_map" / "descriptor.mod",
        'version="0.1.3-alpha"\n',
    )

    (game / "eu4.exe").write_bytes(b"pinned executable fixture\n")
    (game / "userdir.txt").write_bytes(b"")
    _write_json(
        game / "launcher-settings.json",
        {
            "gameDataPath": str(daily_user_data),
            "exePath": "./eu4.exe",
            "version": "EU4 v1.37.5.0 Inca (491d)",
        },
    )
    protocol_pins = {
        name: runtime._sha256_file(game / name)
        for name in ("eu4.exe", "userdir.txt", "launcher-settings.json")
    }

    gameplay_pins: list[dict[str, str]] = []
    for number in range(9):
        relative = Path("pins") / f"pin-{number}.txt"
        _write(game / relative, f"gameplay pin {number}\n")
        gameplay_pins.append(
            {
                "path": relative.as_posix(),
                "sha256": runtime._sha256_file(game / relative),
            }
        )
    pin_manifest = {
        "eu4_display_version": "EU4 v1.37.5.0 Inca (491d)",
        "files": gameplay_pins[:3],
        "generic_files": gameplay_pins[3:6],
        "mandate_files": gameplay_pins[6:],
    }
    gameplay_groups = (
        (
            "files",
            tuple((item["path"], item["sha256"]) for item in gameplay_pins[:3]),
        ),
        (
            "generic_files",
            tuple((item["path"], item["sha256"]) for item in gameplay_pins[3:6]),
        ),
        (
            "mandate_files",
            tuple((item["path"], item["sha256"]) for item in gameplay_pins[6:]),
        ),
    )

    def committed_test_manifest(
        component: str, _revision: str
    ) -> tuple[tuple[str, int, str], ...]:
        source = root / "components" / f"source-{component}"
        outer = root / "components" / f"{component}.mod"
        records = runtime._manifest(runtime.Component(component, source, outer))
        return tuple(runtime._normalized_manifest_record(item) for item in records)

    _write(
        daily_user_data / "dlc_load.json",
        '{"enabled_mods": [], "disabled_dlcs": []}\n',
    )
    (daily_user_data / "launcher-v2.sqlite").write_bytes(
        b"daily launcher fixture\n"
    )

    with contextlib.ExitStack() as stack:
        stack.enter_context(
            patch.object(runtime, "DEFAULT_ACCEPTANCE_USER_DATA", user_data)
        )
        stack.enter_context(patch.object(runtime, "DEFAULT_USER_DATA", daily_user_data))
        stack.enter_context(patch.object(runtime, "DEFAULT_GAME_ROOT", game))
        stack.enter_context(patch.object(runtime, "PINNED_PROTOCOL_FILES", protocol_pins))
        stack.enter_context(
            patch.object(runtime, "PINNED_GAMEPLAY_GROUPS", gameplay_groups)
        )
        stack.enter_context(
            patch.object(runtime, "_load_pin_manifest", return_value=pin_manifest)
        )
        stack.enter_context(
            patch.object(
                runtime,
                "_require_canonical_runtime_roots",
                side_effect=lambda repo_value, game_value: (
                    Path(repo_value).resolve(),
                    Path(game_value).resolve(),
                ),
            )
        )
        stack.enter_context(
            patch.object(
                runtime,
                "_require_canonical_repo",
                side_effect=lambda repo_value: Path(repo_value).resolve(),
            )
        )
        stack.enter_context(
            patch.object(
                runtime,
                "_git_snapshot_manifest_records",
                side_effect=committed_test_manifest,
            )
        )
        stack.enter_context(
            patch.object(runtime, "_running_eu4_processes", return_value=())
        )
        stack.enter_context(
            patch.object(
                runtime, "_r13_current_toolchain_revision", return_value="d" * 40
            )
        )
        stack.enter_context(
            patch.object(runtime, "_r13_prepare_gate_python_runtime")
        )
        yield SimpleNamespace(
            root=root,
            repo=repo.resolve(),
            game=game.resolve(),
            user=user_data.resolve(),
            daily=daily_user_data.resolve(),
            protocol_pins=protocol_pins,
            pin_manifest=pin_manifest,
        )


def _deploy_pair(env: SimpleNamespace) -> tuple[Path, Path]:
    mod_dir = env.user / "mod"
    mod_dir.mkdir(parents=True, exist_ok=True)
    candidate = runtime._current_candidate_revision()
    main = runtime._deploy_component(
        _component(env.root / "components", "main"),
        mod_dir,
        "current",
        candidate,
        None,
    )
    map_record = runtime._deploy_component(
        _component(env.root / "components", "map"),
        mod_dir,
        "current",
        candidate,
        str(main["display_name"]),
    )
    return Path(main["descriptor"]), Path(map_record["descriptor"])


def _configure_before(
    env: SimpleNamespace,
    descriptors: list[Path],
    scenario: str = "PROBE",
    phase: str | None = None,
    *,
    input_saves: tuple[str, ...] = (),
    parent_collections: tuple[str, ...] = (),
) -> dict[str, object]:
    runtime.configure_playset(env.user, scenario, phase, descriptors)
    return runtime.before_session(
        env.user,
        scenario,
        phase,
        None,
        descriptors,
        daily_user_data=env.daily,
        repo=env.repo,
        game_root=env.game,
        permission_reference="test-only simulated visible-start authorization",
        input_saves=input_saves,
        parent_collections=parent_collections,
    )


def _observe_exact(before: dict[str, object]) -> dict[str, object]:
    session = Path(str(before["session"]))
    expected = list(before["expected_argv"])
    session_record = runtime._read_json_object(session / "session.json", "session")
    process = {
        "ProcessId": 4242,
        "ExecutablePath": expected[0],
        "CommandLine": f'"{expected[0]}" {expected[1]}',
        "CreationDate": session_record["started_at"],
    }
    with (
        patch.object(runtime, "_running_eu4_processes", return_value=("eu4.exe",)),
        patch.object(runtime, "_eu4_process_details", return_value=[process]),
        patch.object(runtime, "_windows_command_line_argv", return_value=expected),
    ):
        return runtime.observe_process(session)


def _write_probe_outputs(user_data: Path, token: str) -> Path:
    _write(user_data / "logs" / "error.log", f"clean probe error log {token}\n")
    _write(
        user_data / "logs" / "game.log",
        f"{runtime.EXPECTED_GAME_VERSION_LOG}\nprobe token: {token}\n",
    )
    _write(user_data / "settings.txt", f"probe settings {token}\n")
    color = (20 + len(token) % 200, 40, 180)
    return _write_png(
        user_data / "Screenshots" / f"JXP_ACC_PROBE_MAIN_MENU_{token}.png",
        color,
    )


def _assertion_entry(
    assertion_id: str,
    status: str,
    roles: list[str],
) -> dict[str, object]:
    return {
        "id": assertion_id,
        "status": status,
        "note": f"schema-4 {status.lower()} attestation",
        "attestor": "RuntimeAcceptanceTests",
        "attested_at": ATTESTED_AT,
        "artifact_roles": roles,
    }


def _attest_session_manifest(
    before: dict[str, object],
    screenshot: Path,
    statuses: dict[str, str] | None = None,
) -> Path:
    session = Path(str(before["session"]))
    manifest_path = Path(str(before["evidence_manifest"]))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    scenario = runtime._scenario(str(before["scenario"]))
    normalized = runtime._normalized_evidence_contract(
        scenario, before.get("phase")
    )
    for artifact in manifest["artifacts"]:
        if artifact["source"] == "operator_file":
            if artifact["kind"] != "screenshot":
                raise AssertionError(
                    f"unexpected operator PROBE role: {artifact['role']}"
                )
            artifact["paths"] = [str(screenshot)]
    requested = statuses or {}
    manifest["assertions"] = []
    for assertion in normalized["assertions"]:
        assertion_id = str(assertion["id"])
        roles = [
            role
            for role, spec in normalized["artifact_specs"].items()
            if assertion_id in spec["supports_assertion_ids"]
        ]
        manifest["assertions"].append(
            _assertion_entry(assertion_id, requested.get(assertion_id, "PASS"), roles)
        )
    for fixture in manifest["fixture_uses"]:
        fixture["note"] = "fixture console and distinct before/after saves observed"
    _write_json(manifest_path, manifest)
    return manifest_path


def _complete_probe(
    env: SimpleNamespace,
    descriptors: list[Path],
    token: str = "pass",
) -> tuple[dict[str, object], dict[str, object], Path]:
    before = _configure_before(env, descriptors)
    _observe_exact(before)
    screenshot = _write_probe_outputs(env.user, token)
    manifest = _attest_session_manifest(before, screenshot)
    result, ready = runtime.collect(Path(str(before["session"])), [], manifest)
    if not ready:
        raise AssertionError(f"simulated PROBE did not become review-ready: {result}")
    return before, result, Path(str(before["session"]))


def _r13_without_blockers() -> dict[str, object]:
    normalized = runtime._normalized_evidence_contract(
        runtime._scenario("R13"), None
    )
    return {**normalized, "blockers": []}


def _r13_parent_records(
    env: SimpleNamespace,
    normalized: dict[str, object],
) -> list[dict[str, object]]:
    compatibility = {
        "matrix_sha256": runtime._scenario_matrix_sha256(),
        "candidate_revision": runtime._current_candidate_revision(),
        "game_pins": runtime._verified_twelve_pins(env.repo, env.game),
        "repo": str(env.repo),
        "game_root": str(env.game),
        "user_data": str(env.user),
        "daily_user_data": str(env.daily),
    }
    records: list[dict[str, object]] = []
    for index, requirement in enumerate(normalized["parents"], 1):
        role = str(requirement["role"])
        parent_normalized = runtime._normalized_evidence_contract(
            runtime._scenario(str(requirement["scenario"])),
            requirement["phase"],
        )
        parent_contract, _ = runtime._scenario_session_contract(
            runtime._scenario(str(requirement["scenario"])),
            requirement["phase"],
        )
        artifact_roles = {
            "sealed_parent_evidence": {
                "kind": "text",
                "sha256": f"{index + 100:064x}",
            }
        }
        assertions = [
            {
                "id": item["id"],
                "text": item["text"],
                "status": "PASS",
                "note": f"ready parent assertion {item['id']}",
                "attestor": "RuntimeAcceptanceTests",
                "attested_at": ATTESTED_AT,
                "artifact_roles": [
                    artifact_role
                    for artifact_role, spec in parent_normalized[
                        "artifact_specs"
                    ].items()
                    if item["id"] in spec["supports_assertion_ids"]
                ],
                "matrix_blocker_ids": [],
            }
            for item in parent_normalized["assertions"]
        ]
        snapshots = [
            {
                "component": component,
                "version": parent_contract["required_versions"][component],
                "source_revision": parent_contract.get(
                    "required_source_revisions", {}
                ).get(component, runtime._current_candidate_revision()),
                "fingerprint": (
                    "a" * 64 if component == "main" else "b" * 64
                ),
            }
            for offset, component in enumerate(parent_contract["required_components"])
        ]
        sealed_inputs: list[dict[str, object]] = []
        parent_dependencies: list[dict[str, object]] = []
        fixture_uses: list[dict[str, object]] = []
        required_fixture_records: list[dict[str, object]] = []
        record = dict.fromkeys(runtime._PARENT_DEPENDENCY_RECORD_KEYS)
        record.update(
            {
                "role": role,
                "collection_path": str(
                    (env.root / "parents" / role / runtime.COLLECTION_NAME).resolve()
                ),
                "collection_sha256": f"{index:064x}",
                "collection_seal_path": str(
                    (
                        env.root
                        / "parents"
                        / role
                        / runtime.COLLECTION_SEAL_NAME
                    ).resolve()
                ),
                "collection_seal_sha256": f"{index + 20:064x}",
                "collection_status": "READY_FOR_LEAD_REVIEW",
                "ready_for_lead_review": True,
                "automated_checks_passed": True,
                "manual_assertions_complete": True,
                "manual_assertions_passed": True,
                "scenario_id": requirement["scenario"],
                "phase": requirement["phase"],
                "candidate_revision": runtime._current_candidate_revision(),
                "session_id": f"{index:032x}",
                "session_path": str((env.root / "parents" / role).resolve()),
                "session_sha256": f"{index + 40:064x}",
                "session_seal_path": str(
                    (env.root / "parents" / role / runtime.SESSION_SEAL_NAME).resolve()
                ),
                "session_seal_sha256": f"{index + 60:064x}",
                "contract_sha256": f"{index + 80:064x}",
                "artifact_roles": artifact_roles,
                "artifact_roles_sha256": runtime._object_sha256(artifact_roles),
                "assertions": assertions,
                "assertions_sha256": runtime._object_sha256(assertions),
                "snapshots": snapshots,
                "snapshots_sha256": runtime._object_sha256(snapshots),
                "sealed_inputs": sealed_inputs,
                "sealed_inputs_sha256": runtime._object_sha256(sealed_inputs),
                "parent_dependencies": parent_dependencies,
                "parent_dependencies_sha256": runtime._object_sha256(
                    parent_dependencies
                ),
                "fixture_uses": fixture_uses,
                "fixture_uses_sha256": runtime._object_sha256(fixture_uses),
                "required_fixture_records": required_fixture_records,
                "required_fixture_records_sha256": runtime._object_sha256(
                    required_fixture_records
                ),
                "runtime_oracle_evidence_sha256": runtime._object_sha256([]),
                "compatibility": compatibility,
            }
        )
        records.append(record)
    return records


def _r13_parent_args(env: SimpleNamespace, normalized: dict[str, object]) -> list[str]:
    return [
        f"{item['role']}={env.root / 'parents' / str(item['role'])}"
        for item in normalized["parents"]
    ]


def _r13_fake_parent_sealer(records: list[dict[str, object]]):
    by_role = {str(item["role"]): item for item in records}

    def seal(values: list[str]) -> list[dict[str, object]]:
        parsed = runtime._parse_role_paths(values, "--parent-collection")
        return [by_role[role] for role in sorted(parsed)]

    return seal


def _r13_context(env: SimpleNamespace) -> dict[str, object]:
    return {
        "candidate_revision": runtime._current_candidate_revision(),
        "toolchain_revision": "d" * 40,
        "matrix_sha256": runtime._scenario_matrix_sha256(),
        "game_pins": runtime._verified_twelve_pins(env.repo, env.game),
        "repo": str(env.repo),
        "game_root": str(env.game),
        "user_data": str(env.user),
        "daily_user_data": str(env.daily),
    }


def _r13_fake_toolchain_guard() -> dict[str, object]:
    body: dict[str, object] = {
        "schema": "jxp_r13_gate_toolchain/v2",
        "records": [
            {
                "kind": "file",
                "path": "C:\\controlled\\validator.exe",
                "bytes": 1,
                "sha256": "a" * 64,
            }
        ],
        "installed_skill": {
            "source_revision": "d" * 40,
            "git_tree_sha256": "c" * 64,
            "file_count": 1,
            "sha256": runtime._object_sha256(
                [{"path": "SKILL.md", "bytes": 1, "sha256": "a" * 64}]
            ),
        },
    }
    return {**body, "toolchain_sha256": runtime._object_sha256(body)}


def _r13_fake_gate_verifications(
    env: SimpleNamespace,
    parents: list[dict[str, object]],
) -> dict[str, dict[str, object]]:
    context = _r13_context(env)
    common = runtime._r13_common_evidence_identity(parents, context)
    specs = runtime._r13_static_gate_specs(context)
    toolchain_guard = _r13_fake_toolchain_guard()
    results: dict[str, dict[str, object]] = {}
    for role, spec in specs.items():
        expectation = runtime._r13_gate_receipt_expectation(role, context)
        executions: list[dict[str, object]] = []
        marker_proofs: list[dict[str, object]] = []
        for command, markers in zip(
            expectation["commands"], spec["required_markers"], strict=True
        ):
            stdout = ("\n".join(markers) + "\n").encode("utf-8")
            stderr = b""
            executions.append(
                {
                    "argv": command,
                    "cwd": spec["cwd"],
                    "effective_environment": spec["environment"],
                    "effective_environment_sha256": runtime._object_sha256(
                        spec["environment"]
                    ),
                    "executable": runtime._r13_toolchain_file_record(
                        Path(command[0]), "fake gate executable"
                    ),
                    "toolchain_guard_sha256_before": toolchain_guard[
                        "toolchain_sha256"
                    ],
                    "toolchain_guard_sha256_after": toolchain_guard[
                        "toolchain_sha256"
                    ],
                    "started_at": ATTESTED_AT,
                    "completed_at": ATTESTED_AT,
                    "exit_code": 0,
                    "stdout_b64": base64.b64encode(stdout).decode("ascii"),
                    "stdout_bytes": len(stdout),
                    "stdout_sha256": sha256(stdout).hexdigest(),
                    "stderr_b64": "",
                    "stderr_bytes": 0,
                    "stderr_sha256": sha256(stderr).hexdigest(),
                    "framed_output_sha256": sha256(
                        struct.pack(">Q", len(stdout))
                        + stdout
                        + struct.pack(">Q", len(stderr))
                        + stderr
                    ).hexdigest(),
                }
            )
            marker_proofs.append(
                {
                    "required_markers": markers,
                    "required_markers_sha256": runtime._object_sha256(markers),
                    "matched": True,
                }
            )
        additional = (
            {
                "skill_mirror_sha256": toolchain_guard["installed_skill"]["sha256"],
                "skill_file_count": 1,
                "source_revision": "d" * 40,
                "git_tree_sha256": "c" * 64,
            }
            if role == "r13_skill_validation_output_if_changed"
            else {}
        )
        results[role] = {
            **expectation,
            "passed": True,
            "execution_mode": "live_close_release",
            "payload_guard": common["tested_payload"],
            "toolchain_guard": toolchain_guard,
            "executions": executions,
            "marker_proofs": marker_proofs,
            "additional_proof": additional,
        }
    return results


def _r13_artifact_args(
    env: SimpleNamespace,
    normalized: dict[str, object],
    parents: list[dict[str, object]],
) -> list[str]:
    root = env.root / "r13-artifacts"
    daily_records = runtime._required_configuration_records(env.daily)
    daily_vfs = runtime._daily_vfs_inventory(env.daily)
    context = _r13_context(env)
    common = runtime._r13_common_evidence_identity(parents, context)
    assertion_rows = runtime._r13_assertion_result_rows(parents, normalized)
    lineage_rows = runtime._r13_lineage_rows(parents, normalized)
    ledger_entry_id = "RUNTIME-TEST-R13-CLOSURE"
    runtime_status = "RUNTIME_PASS" if not normalized["blockers"] else "RUNTIME_BLOCKED"
    ledger_path = (
        env.repo
        / "japan_expanded_v2"
        / "dev_logs"
        / "JXP_SHARED_DEVELOPMENT_LEDGER.md"
    )
    parent_hashes = [str(item["collection_sha256"]) for item in parents]
    journal_entry = runtime._expected_r13_journal_entry(
        ledger_entry_id,
        ATTESTED_AT,
        parents,
        normalized,
        common,
    )
    _write(
        ledger_path,
        "\n".join(
            (
                "# Test Ledger",
                "",
                "## Update Journal",
                "",
                f"### 2026-07-13 - {ledger_entry_id} - Test closure",
                "",
                "```jxp-r13-journal-json",
                json.dumps(journal_entry, ensure_ascii=False, indent=2),
                "```",
            )
        )
        + "\n",
    )
    values: list[str] = []
    for role, kind in normalized["artifact_roles"].items():
        path = root / f"{role}.json"
        if role == "r13_assertion_result_manifest":
            payload = {
                "schema": "jxp_r13_assertion_results/v1",
                "status": "PASS",
                "candidate_revision": common["candidate_revision"],
                "matrix_sha256": common["matrix_sha256"],
                "parent_lineage_sha256": common["parent_lineage_sha256"],
                "assertion_count": len(assertion_rows),
                "assertions": assertion_rows,
                "generated_at": ATTESTED_AT,
            }
        elif role == "r13_evidence_lineage_index":
            payload = {
                "schema": "jxp_r13_evidence_lineage/v1",
                "status": "PASS",
                "candidate_revision": common["candidate_revision"],
                "matrix_sha256": common["matrix_sha256"],
                "parent_lineage_sha256": common["parent_lineage_sha256"],
                "parent_count": len(lineage_rows),
                "parents": lineage_rows,
                "generated_at": ATTESTED_AT,
            }
        elif role in runtime._R13_GATE_CHECK_IDS:
            expectation = runtime._r13_gate_receipt_expectation(role, context)
            payload = {
                "schema": "jxp_r13_static_gate_output/v3",
                "role": role,
                "status": "PASS",
                **common,
                "commands": expectation["commands"],
                "exit_codes": expectation["exit_codes"],
                "completed_at": ATTESTED_AT,
                "checks": expectation["checks"],
                "transcript": expectation["transcript"],
            }
        elif role == "r13_daily_configuration_final_hashes":
            payload = {
                "schema": "jxp_r13_daily_state/v1",
                "status": "PASS",
                "candidate_revision": common["candidate_revision"],
                "matrix_sha256": common["matrix_sha256"],
                "parent_lineage_sha256": common["parent_lineage_sha256"],
                "daily_configuration": daily_records,
                "daily_configuration_sha256": runtime._object_sha256(daily_records),
                "daily_vfs_sha256": runtime._object_sha256(daily_vfs),
                "recorded_at": ATTESTED_AT,
            }
        elif role == "r13_canonical_ledger_update":
            payload = {
                "schema": "jxp_r13_ledger_update/v2",
                "status": "PASS",
                "candidate_revision": common["candidate_revision"],
                "matrix_sha256": common["matrix_sha256"],
                "parent_lineage_sha256": common["parent_lineage_sha256"],
                "ledger_path": str(ledger_path.resolve()),
                "ledger_sha256": runtime._sha256_file(ledger_path),
                "entry_id": ledger_entry_id,
                "entry_sha256": runtime._object_sha256(journal_entry),
                "runtime_status": runtime_status,
                "parent_collection_sha256s": parent_hashes,
                "remaining_blocker_ids": [
                    str(item["id"]) for item in normalized["blockers"]
                ],
                "updated_at": ATTESTED_AT,
            }
        else:
            raise AssertionError(f"unhandled R13 artifact role: {role}/{kind}")
        _write_json(path, payload)
        values.append(f"{role}={path}")
    return values


def _r13_assertion_manifest(
    env: SimpleNamespace,
    normalized: dict[str, object],
) -> Path:
    assertions = []
    for assertion in normalized["assertions"]:
        assertion_id = str(assertion["id"])
        roles = [
            role
            for role, spec in normalized["artifact_specs"].items()
            if assertion_id in spec["supports_assertion_ids"]
        ]
        assertions.append(
            {
                "id": assertion_id,
                "status": "PASS",
                "note": f"R13 finite-slice attestation for {assertion_id}",
                "attestor": "RuntimeAcceptanceTests",
                "attested_at": ATTESTED_AT,
                "artifact_roles": roles,
            }
        )
    return _write_json(
        env.root / "r13-manual-assertions.json",
        {
            "schema": runtime.EVIDENCE_MANIFEST_SCHEMA,
            "scenario_id": "R13",
            "phase": "closure",
            "assertions": assertions,
        },
    )


def _unit_manifest_contract(
    role_specs: dict[str, dict[str, object]],
    *,
    assertion_id: str = "unit_assertion",
    fixtures: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    return {
        "scenario_id": "UNIT",
        "phase": None,
        "prefix": "JXP_ACC_UNIT_",
        "minimum_screenshots": 0,
        "minimum_saves": 0,
        "runnable": True,
        "assertions": [{"id": assertion_id, "text": "unit assertion"}],
        "artifact_roles": {
            role: str(spec["kind"]) for role, spec in role_specs.items()
        },
        "artifact_specs": role_specs,
        "parents": [],
        "inputs": [],
        "fixtures": fixtures or [],
        "blockers": [],
    }


def _unit_manifest(
    session_sha256: str,
    contract_sha256: str,
    artifacts: list[dict[str, object]],
    assertion: dict[str, object],
    fixture_uses: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    return {
        "schema": runtime.EVIDENCE_MANIFEST_SCHEMA,
        "scenario_id": "UNIT",
        "phase": None,
        "session_sha256": session_sha256,
        "contract_sha256": contract_sha256,
        "artifacts": artifacts,
        "assertions": [assertion],
        "fixture_uses": fixture_uses or [],
    }


class RuntimeAcceptanceTests(unittest.TestCase):
    def test_default_acceptance_userdir_path_is_unambiguous(self) -> None:
        self.assertTrue(str(runtime.DEFAULT_ACCEPTANCE_USER_DATA).isascii())
        self.assertIsNone(
            re.search(r'[\s"]', str(runtime.DEFAULT_ACCEPTANCE_USER_DATA))
        )
        with tempfile.TemporaryDirectory() as temporary:
            unsafe = Path(temporary) / "unsafe - acceptance"
            unsafe.mkdir()
            with self.assertRaises(runtime.AcceptanceError):
                runtime._require_isolated_user_data(unsafe)

    def test_canonical_roots_and_launcher_derived_daily_reject_decoys(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            with _runtime_environment(Path(temporary)) as env:
                decoy_acceptance = env.root / "other-acceptance"
                decoy_daily = env.root / "other-daily"
                decoy_acceptance.mkdir()
                decoy_daily.mkdir()
                self.assertEqual(
                    env.user,
                    runtime._require_canonical_acceptance_user_data(env.user),
                )
                self.assertEqual(env.daily, runtime._launcher_daily_user_data(env.game))
                self.assertEqual(
                    env.daily,
                    runtime._require_canonical_daily_user_data(env.daily, env.game),
                )
                with self.assertRaises(runtime.AcceptanceError):
                    runtime._require_canonical_acceptance_user_data(decoy_acceptance)
                with self.assertRaises(runtime.AcceptanceError):
                    runtime._require_canonical_daily_user_data(decoy_daily, env.game)
                _write(env.game / "launcher-settings.json", "{}\n")
                with self.assertRaises(runtime.AcceptanceError):
                    runtime._launcher_daily_user_data(env.game)

    def test_redirected_documents_reparse_ancestors_and_session_roots_fail_closed(
        self,
    ) -> None:
        self.assertEqual(0x00004000, runtime.KF_FLAG_DONT_VERIFY)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            ancestor = root / "ordinary-ancestor"
            child = ancestor / "child"
            child.mkdir(parents=True)
            with patch.object(
                runtime,
                "_is_link_or_junction",
                side_effect=lambda path: Path(path) == ancestor,
            ):
                with self.assertRaises(runtime.AcceptanceError):
                    runtime._require_ordinary_directory(
                        child, "simulated ancestor-junction path"
                    )

        with tempfile.TemporaryDirectory() as temporary:
            with _runtime_environment(Path(temporary)) as env:
                evidence_root = env.user / "jxp_runtime_evidence"
                session = evidence_root / "direct-session"
                nested_session = evidence_root / "nested" / "nested-session"
                outside_session = env.root / "outside" / "outside-session"
                for path in (session, nested_session, outside_session):
                    path.mkdir(parents=True)
                record = {
                    "user_data": str(env.user),
                    "evidence_root": str(evidence_root),
                }
                self.assertEqual(
                    (env.user, evidence_root),
                    runtime._require_recorded_session_location(session, record),
                )
                with self.assertRaises(runtime.AcceptanceError):
                    runtime._require_recorded_session_location(
                        nested_session, record
                    )
                with self.assertRaises(runtime.AcceptanceError):
                    runtime._require_recorded_session_location(
                        outside_session, record
                    )
                for reserved in (
                    env.user / "mod",
                    env.user / "logs",
                    env.user / "Screenshots",
                    env.user / "save games",
                ):
                    reserved.mkdir(parents=True, exist_ok=True)
                    with self.assertRaises(runtime.AcceptanceError):
                        runtime._require_canonical_evidence_root(
                            env.user, reserved, create=False
                        )

                unsafe_collect = env.root / "unrelated-ordinary-directory"
                _write_json(
                    unsafe_collect / runtime.COLLECTION_NAME,
                    {"unrelated": True},
                )
                sentinel = _write(
                    unsafe_collect / "after" / "must-survive.txt",
                    "do not delete\n",
                )
                with self.assertRaises(runtime.AcceptanceError):
                    runtime.collect(
                        unsafe_collect,
                        [],
                        unsafe_collect / runtime.EVIDENCE_MANIFEST_NAME,
                    )
                self.assertTrue((unsafe_collect / runtime.COLLECTION_NAME).is_file())
                self.assertEqual("do not delete\n", sentinel.read_text(encoding="utf-8"))

    def test_twelve_pin_records_include_three_protocol_and_nine_gameplay_files(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            with _runtime_environment(Path(temporary)) as env:
                records = runtime._verified_twelve_pins(env.repo, env.game)
                self.assertEqual(12, len(records))
                self.assertEqual(12, len({item["path"] for item in records}))
                self.assertTrue(all(item["matched"] for item in records))
                self.assertEqual(
                    {"eu4.exe", "userdir.txt", "launcher-settings.json"},
                    {item["path"] for item in records[:3]},
                )
                preflight = runtime.preflight(env.repo, env.game, env.daily)
                self.assertTrue(preflight["ready_for_safe_deploy"])
                _write(env.game / "pins" / "pin-8.txt", "tampered\n")
                self.assertFalse(
                    runtime.preflight(env.repo, env.game, env.daily)[
                        "ready_for_safe_deploy"
                    ]
                )
                with self.assertRaises(runtime.AcceptanceError):
                    runtime._verified_twelve_pins(env.repo, env.game)

    def test_revision_components_can_pin_main_and_map(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            components, revision = runtime._revision_components(
                LIVE_REPO,
                runtime._current_candidate_revision(),
                Path(temporary),
                False,
            )
            self.assertEqual(runtime._current_candidate_revision(), revision)
            self.assertEqual(["main", "map"], [item.key for item in components])
            self.assertTrue(all(item.source.is_dir() for item in components))

    def test_matrix_schema2_has_independent_probe_and_exact_blocker_scope(self) -> None:
        matrix = runtime._scenario_matrix()
        self.assertEqual(2, matrix["schema"])
        self.assertEqual("PROBE", matrix["protocol_probe"]["id"])
        scenario_ids = [item["id"] for item in matrix["scenarios"]]
        self.assertEqual([f"R{number}" for number in range(1, 14)], scenario_ids)
        self.assertNotIn("PROBE", scenario_ids)
        probe = runtime._normalized_evidence_contract(runtime._scenario("PROBE"), None)
        self.assertEqual("default", probe["phase"])
        self.assertEqual([], probe["parents"])
        self.assertEqual([], probe["inputs"])
        r1 = runtime._normalized_evidence_contract(runtime._scenario("R1"), None)
        self.assertEqual(
            [("protocol_probe_collection", "PROBE", "default")],
            [
                (item["role"], item["scenario"], item["phase"])
                for item in r1["parents"]
            ],
        )
        blocked_scenarios = {
            item["id"]
            for item in matrix["scenarios"]
            if item.get("blockers")
        }
        self.assertEqual({"R5", "R13"}, blocked_scenarios)

    def test_matrix_contracts_close_assertions_roles_fixtures_and_todos(self) -> None:
        matrix = runtime._scenario_matrix()
        normalized_contracts: list[dict[str, object]] = [
            runtime._normalized_evidence_contract(runtime._scenario("PROBE"), None)
        ]
        for scenario in matrix["scenarios"]:
            if scenario["id"] == "R13":
                normalized_contracts.append(
                    runtime._normalized_evidence_contract(scenario, None)
                )
                continue
            phases = scenario.get("session_phases")
            if isinstance(phases, dict):
                normalized_contracts.extend(
                    runtime._normalized_evidence_contract(scenario, phase)
                    for phase in phases
                )
            else:
                normalized_contracts.append(
                    runtime._normalized_evidence_contract(scenario, None)
                )
        for contract in normalized_contracts:
            assertion_ids = {item["id"] for item in contract["assertions"]}
            supported = {
                assertion_id
                for spec in contract["artifact_specs"].values()
                for assertion_id in spec["supports_assertion_ids"]
            }
            self.assertEqual(assertion_ids, supported)
            self.assertTrue(all(spec["distinct"] for spec in contract["artifact_specs"].values()))
            for fixture in contract["fixtures"]:
                self.assertEqual(
                    "screenshot",
                    contract["artifact_roles"][fixture["console_screenshot_role"]],
                )
                self.assertEqual(
                    "save", contract["artifact_roles"][fixture["before_save_role"]]
                )
                self.assertEqual(
                    "save", contract["artifact_roles"][fixture["after_save_role"]]
                )
        covered = {
            todo for scenario in matrix["scenarios"] for todo in scenario["todos"]
        }
        ledger = (
            LIVE_REPO
            / "japan_expanded_v2"
            / "dev_logs"
            / "JXP_SHARED_DEVELOPMENT_LEDGER.md"
        ).read_text(encoding="utf-8")
        in_progress = {
            match.group(1)
            for match in re.finditer(
                r"^\|\s*(JXP-\d+)\s*\|[^\n]*\|\s*IN_PROGRESS\s*\|",
                ledger,
                re.MULTILINE,
            )
        }
        self.assertEqual(in_progress, covered)

    def test_runtime_whitelist_excludes_development_material(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            component = _component(Path(temporary))
            _write(component.source / "gfx" / "flags" / "source" / "source.png")
            _write(component.source / "gfx" / "flags" / "preview" / "preview.png")
            _write(
                component.source
                / "gfx"
                / "flags"
                / "backup_before_imagegen"
                / "old.tga"
            )
            _write(component.source / "gfx" / "flags" / "live.tga")
            relative = {
                path.relative_to(component.source).as_posix()
                for path in runtime._runtime_files(component)
            }
        self.assertIn("common/payload.txt", relative)
        self.assertIn("gfx/flags/live.tga", relative)
        self.assertIn("descriptor.mod", relative)
        self.assertNotIn("AGENTS.md", relative)
        self.assertFalse(any(item.startswith("tools/") for item in relative))
        self.assertFalse(any(item.startswith("dev_logs/") for item in relative))
        self.assertFalse(any("/source/" in item for item in relative))
        self.assertFalse(any("/preview/" in item for item in relative))
        self.assertFalse(any("/backup_before_imagegen/" in item for item in relative))

    def test_windows_reparse_fallback_covers_python_311(self) -> None:
        path = Path("junction-fixture")
        with (
            patch.object(type(path), "is_symlink", return_value=False),
            patch.object(type(path), "is_junction", return_value=False, create=True),
            patch.object(runtime.os, "name", "nt"),
            patch.object(
                runtime.os,
                "lstat",
                return_value=SimpleNamespace(st_file_attributes=0x400),
            ),
        ):
            self.assertTrue(runtime._is_link_or_junction(path))

    def test_path_escape_and_unsafe_zip_entries_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            target = root / "target"
            target.mkdir()
            with self.assertRaises(runtime.AcceptanceError):
                runtime._verify_installed_manifest(
                    target,
                    [{"path": r"C:\outside.txt", "bytes": 1, "sha256": "a" * 64}],
                )
            archive = root / "malicious.zip"
            with zipfile.ZipFile(archive, "w") as bundle:
                bundle.writestr(r"C:\outside.txt", "x")
            with self.assertRaises(runtime.AcceptanceError):
                runtime._safe_extract_zip(archive, root / "extract")

    def test_live_release_manifest_is_tracked_and_development_free(self) -> None:
        candidate_revision = runtime._current_candidate_revision()
        candidate_paths = ["japan_expanded_v2.mod", "japan_expanded_v2_map.mod"]
        tracked = set(
            subprocess.run(
                ["git", "-C", str(LIVE_REPO), "ls-files"],
                check=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
            ).stdout.splitlines()
        )
        for component in runtime._current_components(LIVE_REPO, False):
            component_root = component.source.relative_to(LIVE_REPO).as_posix()
            candidate_paths.extend(
                f"{component_root}/{relative}"
                for relative in (
                    *runtime.RUNTIME_DIRECTORIES[component.key],
                    *runtime.RUNTIME_ROOT_FILES,
                )
            )
            files = runtime._runtime_files(component)
            relative_to_repo = {
                path.relative_to(LIVE_REPO).as_posix() for path in files
            }
            self.assertTrue(relative_to_repo)
            self.assertEqual(set(), relative_to_repo - tracked)
            self.assertFalse(
                any(
                    runtime._is_development_runtime_path(
                        path.relative_to(component.source)
                    )
                    for path in files
                )
            )
        subprocess.run(
            [
                "git",
                "-C",
                str(LIVE_REPO),
                "diff",
                "--quiet",
                candidate_revision,
                "--",
                *candidate_paths,
            ],
            check=True,
        )

    def test_content_addressed_deploy_is_verified_and_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            component = _component(root)
            mod_dir = root / "user" / "mod"
            mod_dir.mkdir(parents=True)
            first = runtime._deploy_component(
                component, mod_dir, "current", "abc123+dirty", None
            )
            second = runtime._deploy_component(
                component, mod_dir, "current", "abc123+dirty", None
            )
            self.assertEqual(first, second)
            payload = Path(first["payload"])
            self.assertTrue((payload / ".jxp_acceptance_snapshot.json").is_file())
            self.assertFalse(runtime._is_link_or_junction(payload))
            self.assertFalse((payload / "tools").exists())
            (payload / "unexpected.txt").write_text("drift\n", encoding="utf-8")
            with self.assertRaises(runtime.AcceptanceError):
                runtime._deploy_component(
                    component, mod_dir, "current", "abc123+dirty", None
                )

    def test_map_descriptor_uses_exact_acceptance_dependency(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            component = _component(Path(temporary), "map")
            text = runtime._build_outer_descriptor(
                component,
                "JXP Acceptance current map [123]",
                "jxp-map-123",
                "JXP Acceptance current main [456]",
            )
        self.assertIn('"JXP Acceptance current main [456]"', text)
        self.assertIn('path="mod/jxp-map-123"', text)

    def test_dlc_load_strict_keys_order_duplicates_and_component_order(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            with _runtime_environment(Path(temporary)) as env:
                main_descriptor, map_descriptor = _deploy_pair(env)
                configured = runtime.configure_playset(
                    env.user,
                    "PROBE",
                    None,
                    [map_descriptor, main_descriptor],
                )
                self.assertEqual(
                    [
                        f"mod/{main_descriptor.name}",
                        f"mod/{map_descriptor.name}",
                    ],
                    configured["configuration"]["enabled_mods"],
                )
                raw = (env.user / "dlc_load.json").read_text(encoding="utf-8")
                self.assertLess(raw.index('"enabled_mods"'), raw.index('"disabled_dlcs"'))
                receipt = runtime._read_json_object(
                    env.user / runtime.CONFIGURE_RECEIPT_NAME, "configure receipt"
                )
                runtime._verify_self_seal(
                    receipt, "receipt_sha256", "configure receipt"
                )

                invalid_payloads = (
                    '{"disabled_dlcs": [], "enabled_mods": []}\n',
                    '{"enabled_mods": [], "enabled_mods": [], "disabled_dlcs": []}\n',
                    '{"enabled_mods": [], "disabled_dlcs": [], "extra": []}\n',
                )
                for payload in invalid_payloads:
                    with self.subTest(payload=payload):
                        _write(env.user / "dlc_load.json", payload)
                        with self.assertRaises(runtime.AcceptanceError):
                            runtime._dlc_load(env.user)

                _write(
                    env.user / "dlc_load.json",
                    '{"enabled_mods": [], "disabled_dlcs": []}\n',
                )
                r11 = runtime.configure_playset(
                    env.user, "R11", None, [main_descriptor]
                )
                self.assertEqual(
                    [runtime.DLC_CONFIG_PATHS["Mandate of Heaven"]],
                    r11["configuration"]["disabled_dlcs"],
                )

    def test_daily_vfs_inventory_detects_wrong_root_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            with _runtime_environment(Path(temporary)) as env:
                before = runtime._daily_vfs_inventory(env.daily)
                _write(env.daily / "logs" / "wrong-userdir.log", "unexpected\n")
                after = runtime._daily_vfs_inventory(env.daily)
                self.assertNotEqual(before, after)
                self.assertEqual(
                    list(runtime.DAILY_VFS_COVERAGE),
                    ["*", *runtime.DAILY_CRITICAL_VFS_PATHS],
                )

    def test_install_run_fixtures_uses_dynamic_manifest_count_and_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            user_data = Path(temporary) / "acceptance"
            user_data.mkdir()
            fixtures = runtime._verified_run_fixture_records()
            manifest = json.loads(
                (runtime.RUN_FIXTURE_ROOT / "manifest.json").read_text(encoding="utf-8")
            )
            self.assertEqual(len(manifest["files"]), len(fixtures))
            with (
                patch.object(runtime, "DEFAULT_ACCEPTANCE_USER_DATA", user_data),
                patch.object(runtime, "_running_eu4_processes", return_value=()),
            ):
                first = runtime.install_run_fixtures(user_data)
                second = runtime.install_run_fixtures(user_data)
            self.assertEqual(len(fixtures), len(first["installed"]))
            self.assertTrue(all(not item["reused"] for item in first["installed"]))
            self.assertTrue(all(item["reused"] for item in second["installed"]))
            target = user_data / str(fixtures[0]["name"])
            _write(target, "different fixture\n")
            with (
                patch.object(runtime, "DEFAULT_ACCEPTANCE_USER_DATA", user_data),
                patch.object(runtime, "_running_eu4_processes", return_value=()),
            ):
                with self.assertRaises(runtime.AcceptanceError):
                    runtime.install_run_fixtures(user_data)

    def test_valid_png_and_eu4_factories_pass_but_text_spoofs_fail(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            png = _write_png(root / "real.png")
            save = _write_eu4(root / "real.eu4")
            self.assertEqual("png", runtime._validate_image_artifact(png)["format"])
            self.assertEqual("eu4zip", runtime._validate_eu4_save(save)["format"])
            fake_png = _write(root / "fake.png", "not a png\n")
            fake_save = _write(root / "fake.eu4", "not a save\n")
            with self.assertRaises(runtime.AcceptanceError):
                runtime._validate_image_artifact(fake_png)
            with self.assertRaises(runtime.AcceptanceError):
                runtime._validate_eu4_save(fake_save)
            corrupt_png = root / "corrupt.png"
            corrupt_payload = bytearray(png.read_bytes())
            corrupt_payload[-1] ^= 0xFF
            corrupt_png.write_bytes(corrupt_payload)
            with self.assertRaises(runtime.AcceptanceError):
                runtime._validate_image_artifact(corrupt_png)

    def test_evidence_screenshot_cases_are_role_and_hash_distinct(self) -> None:
        def run_case(duplicate_bytes: bool) -> None:
            with tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                user = root / "user"
                session = root / "session"
                (user / "Screenshots").mkdir(parents=True)
                session.mkdir()
                first = _write_png(
                    user / "Screenshots" / "JXP_ACC_UNIT_CASE_A.png", (1, 2, 3)
                )
                second = _write_png(
                    user / "Screenshots" / "JXP_ACC_UNIT_CASE_B.png",
                    (1, 2, 3) if duplicate_bytes else (4, 5, 6),
                )
                role = "unit_case_set"
                spec = {
                    "kind": "screenshot_set",
                    "supports_assertion_ids": ["unit_assertion"],
                    "distinct": True,
                    "min_items": 2,
                    "case_ids": ["case_a", "case_b"],
                }
                normalized = _unit_manifest_contract({role: spec})
                session_sha = "a" * 64
                contract_sha = "b" * 64
                manifest = _unit_manifest(
                    session_sha,
                    contract_sha,
                    [
                        {
                            "role": role,
                            "kind": "screenshot_set",
                            "source": "operator_file",
                            "min_items": 2,
                            "cases": {
                                "case_a": str(first),
                                "case_b": str(second),
                            },
                        }
                    ],
                    _assertion_entry("unit_assertion", "PASS", [role]),
                )
                manifest_path = _write_json(
                    session / runtime.EVIDENCE_MANIFEST_NAME, manifest
                )
                record = {
                    "scenario": {"id": "UNIT"},
                    "phase": None,
                    "contract_sha256": contract_sha,
                    "user_data": str(user),
                    "artifact_inventory": [],
                }
                call = lambda: runtime._validate_evidence_manifest(
                    manifest_path,
                    session,
                    record,
                    session_sha,
                    normalized,
                    {},
                    [],
                    [],
                )
                if duplicate_bytes:
                    with self.assertRaises(runtime.AcceptanceError):
                        call()
                else:
                    role_records, *_ = call()
                    self.assertEqual(
                        {"case_a", "case_b"},
                        {item["case_id"] for item in role_records[role]},
                    )

        run_case(False)
        run_case(True)

    def test_manual_assertions_have_pass_fail_and_blocked_states(self) -> None:
        outcomes: dict[str, tuple[bool, bool]] = {}
        for status in ("PASS", "FAIL", "BLOCKED"):
            with self.subTest(status=status), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                user = root / "user"
                session = root / "session"
                (user / "Screenshots").mkdir(parents=True)
                session.mkdir()
                screenshot = _write_png(
                    user / "Screenshots" / f"JXP_ACC_UNIT_{status}.png"
                )
                role = "unit_screenshot"
                spec = {
                    "kind": "screenshot",
                    "supports_assertion_ids": ["unit_assertion"],
                    "distinct": True,
                }
                normalized = _unit_manifest_contract({role: spec})
                session_sha = "c" * 64
                contract_sha = "d" * 64
                manifest = _unit_manifest(
                    session_sha,
                    contract_sha,
                    [
                        {
                            "role": role,
                            "kind": "screenshot",
                            "source": "operator_file",
                            "paths": [str(screenshot)],
                        }
                    ],
                    _assertion_entry("unit_assertion", status, [role]),
                )
                manifest_path = _write_json(
                    session / runtime.EVIDENCE_MANIFEST_NAME, manifest
                )
                result = runtime._validate_evidence_manifest(
                    manifest_path,
                    session,
                    {
                        "scenario": {"id": "UNIT"},
                        "phase": None,
                        "contract_sha256": contract_sha,
                        "user_data": str(user),
                        "artifact_inventory": [],
                    },
                    session_sha,
                    normalized,
                    {},
                    [],
                    [],
                )
                outcomes[status] = (result[2], result[3])
                self.assertEqual(status, result[1][0]["status"])
                self.assertEqual("RuntimeAcceptanceTests", result[1][0]["attestor"])
        self.assertEqual(
            {
                "PASS": (True, True),
                "FAIL": (True, False),
                "BLOCKED": (True, False),
            },
            outcomes,
        )

    def test_fixture_use_binds_console_and_distinct_before_after_saves(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            user = root / "user"
            session = root / "session"
            (user / "Screenshots").mkdir(parents=True)
            (user / "save games").mkdir(parents=True)
            session.mkdir()
            console = _write_png(
                user / "Screenshots" / "JXP_ACC_UNIT_CONSOLE.png", (10, 20, 30)
            )
            before_save = _write_eu4(
                user / "save games" / "JXP_ACC_UNIT_BEFORE.eu4", "before"
            )
            after_save = _write_eu4(
                user / "save games" / "JXP_ACC_UNIT_AFTER.eu4", "after"
            )
            roles = {
                "fixture_console": {
                    "kind": "screenshot",
                    "supports_assertion_ids": ["unit_assertion"],
                    "distinct": True,
                },
                "fixture_before": {
                    "kind": "save",
                    "supports_assertion_ids": ["unit_assertion"],
                    "distinct": True,
                },
                "fixture_after": {
                    "kind": "save",
                    "supports_assertion_ids": ["unit_assertion"],
                    "distinct": True,
                },
            }
            fixture_contract = {
                "name": "JXP_ACC_UNIT_fixture.txt",
                "console_screenshot_role": "fixture_console",
                "before_save_role": "fixture_before",
                "after_save_role": "fixture_after",
            }
            normalized = _unit_manifest_contract(
                roles, fixtures=[fixture_contract]
            )
            fixture_record = {
                **fixture_contract,
                "sha256": "e" * 64,
                "claim_limit": "setup only",
            }
            session_sha = "f" * 64
            contract_sha = "1" * 64
            manifest = _unit_manifest(
                session_sha,
                contract_sha,
                [
                    {
                        "role": role,
                        "kind": spec["kind"],
                        "source": "operator_file",
                        "paths": [str(path)],
                    }
                    for role, spec, path in (
                        ("fixture_console", roles["fixture_console"], console),
                        ("fixture_before", roles["fixture_before"], before_save),
                        ("fixture_after", roles["fixture_after"], after_save),
                    )
                ],
                _assertion_entry("unit_assertion", "PASS", list(roles)),
                [
                    {
                        **fixture_contract,
                        "note": "console command and both fork saves observed",
                    }
                ],
            )
            manifest_path = _write_json(
                session / runtime.EVIDENCE_MANIFEST_NAME, manifest
            )
            result = runtime._validate_evidence_manifest(
                manifest_path,
                session,
                {
                    "scenario": {"id": "UNIT"},
                    "phase": None,
                    "contract_sha256": contract_sha,
                    "user_data": str(user),
                    "artifact_inventory": [],
                },
                session_sha,
                normalized,
                {},
                [fixture_record],
                [],
            )
            self.assertTrue(result[4][0]["matched"])
            self.assertNotEqual(
                result[0]["fixture_before"][0]["sha256"],
                result[0]["fixture_after"][0]["sha256"],
            )

    def test_input_saves_are_validated_copied_and_hash_distinct(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            first = _write_eu4(root / "first.eu4", "one")
            second = _write_eu4(root / "second.eu4", "two")
            records = runtime._seal_input_saves(
                root / "session",
                (f"first_role={first}", f"second_role={second}"),
            )
            self.assertEqual({"first_role", "second_role"}, {item["role"] for item in records})
            self.assertTrue(all(Path(item["sealed_path"]).is_file() for item in records))
            with self.assertRaises(runtime.AcceptanceError):
                runtime._seal_input_saves(
                    root / "duplicate-session",
                    (f"first_role={first}", f"second_role={first}"),
                )

    def test_parent_input_dependency_requires_exact_parent_artifact_hash(self) -> None:
        normalized = {
            "parents": [
                {"role": "parent_role", "scenario": "PROBE", "phase": "default"}
            ],
            "inputs": [
                {
                    "role": "child_input",
                    "parent_collection_role": "parent_role",
                    "parent_artifact_role": "parent_save",
                }
            ],
        }
        compatibility = {"identity": "same exact runtime"}
        artifact_roles = {
            "parent_save": {"kind": "save", "sha256": "2" * 64}
        }
        empty: list[dict[str, object]] = []
        parent = dict.fromkeys(runtime._PARENT_DEPENDENCY_RECORD_KEYS)
        parent.update(
            {
                "role": "parent_role",
                "collection_path": "C:/sealed/collection.json",
                "collection_sha256": "3" * 64,
                "collection_seal_path": "C:/sealed/collection.seal.json",
                "collection_seal_sha256": "4" * 64,
                "collection_status": "READY_FOR_LEAD_REVIEW",
                "ready_for_lead_review": True,
                "automated_checks_passed": True,
                "manual_assertions_complete": True,
                "manual_assertions_passed": True,
                "scenario_id": "PROBE",
                "phase": "default",
                "candidate_revision": "5" * 40,
                "session_id": "6" * 32,
                "session_path": "C:/sealed/session",
                "session_sha256": "7" * 64,
                "session_seal_path": "C:/sealed/session/session.seal.json",
                "session_seal_sha256": "8" * 64,
                "contract_sha256": "9" * 64,
                "artifact_roles": artifact_roles,
                "artifact_roles_sha256": runtime._object_sha256(artifact_roles),
                "assertions": empty,
                "assertions_sha256": runtime._object_sha256(empty),
                "snapshots": empty,
                "snapshots_sha256": runtime._object_sha256(empty),
                "sealed_inputs": empty,
                "sealed_inputs_sha256": runtime._object_sha256(empty),
                "parent_dependencies": empty,
                "parent_dependencies_sha256": runtime._object_sha256(empty),
                "fixture_uses": empty,
                "fixture_uses_sha256": runtime._object_sha256(empty),
                "required_fixture_records": empty,
                "required_fixture_records_sha256": runtime._object_sha256(empty),
                "runtime_oracle_evidence_sha256": runtime._object_sha256(empty),
                "compatibility": compatibility,
            }
        )
        sealed = {"role": "child_input", "sha256": "2" * 64}
        with patch.object(
            runtime, "_normalized_evidence_contract", return_value=normalized
        ):
            runtime._validate_dependency_closure(
                {"id": "UNIT"}, None, [sealed], [parent], compatibility
            )
            with self.assertRaises(runtime.AcceptanceError):
                runtime._validate_dependency_closure(
                    {"id": "UNIT"},
                    None,
                    [{"role": "child_input", "sha256": "3" * 64}],
                    [parent],
                    compatibility,
                )

    def test_external_input_provenance_binds_original_size_hash_and_attestation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            original = _write_eu4(root / "original-pre0242.eu4", "authentic")
            digest = runtime._sha256_file(original)
            size = original.stat().st_size
            normalized = runtime._normalized_evidence_contract(
                runtime._scenario("R5"), None
            )
            requirement = next(
                item
                for item in normalized["inputs"]
                if item.get("source") == "external_original"
            )
            provenance = {
                "source_machine_or_custodian": "test custodian",
                "source_path_or_archive_name": "old-machine-backup.zip",
                "original_filename": original.name,
                "acquired_at_utc": "2026-07-13T16:00:00Z",
                "chain_of_custody": ["custodian", "test harness"],
                "size_bytes": size,
                "sha256": digest,
                "eu4_version_if_known": "unknown",
                "jxp_version_or_release_evidence": "pre-0.24.2 release evidence",
                "original_failure_description": "serialized mission regression",
                "unaltered_bytes_attestation": True,
            }
            provenance_path = _write_json(root / "provenance.json", provenance)
            hash_path = _write(
                root / "hash.txt", f"{original.name} {size} {digest}\n"
            )
            input_role = str(requirement["role"])
            provenance_role = str(requirement["provenance_role"])
            hash_role = str(requirement["hash_role"])
            record = {
                "sealed_inputs": [
                    {
                        "role": input_role,
                        "source_path": str(original),
                        "bytes": size,
                        "sha256": digest,
                    }
                ]
            }
            role_records = {
                input_role: [{"sha256": digest}],
                provenance_role: [
                    {"path": str(provenance_path), "sha256": sha256(provenance_path.read_bytes()).hexdigest()}
                ],
                hash_role: [
                    {"path": str(hash_path), "sha256": sha256(hash_path.read_bytes()).hexdigest()}
                ],
            }
            checks = runtime._external_input_evidence_checks(
                normalized, record, role_records
            )
            self.assertTrue(checks[0]["matched"])
            provenance["unaltered_bytes_attestation"] = False
            _write_json(provenance_path, provenance)
            with self.assertRaises(runtime.AcceptanceError):
                runtime._external_input_evidence_checks(
                    normalized, record, role_records
                )

    def test_receipt_active_lock_session_seal_and_abort_lifecycle(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            with _runtime_environment(Path(temporary)) as env:
                descriptors = list(_deploy_pair(env))
                runtime.configure_playset(env.user, "PROBE", None, descriptors)
                with self.assertRaises(runtime.AcceptanceError):
                    runtime.before_session(
                        env.user,
                        "PROBE",
                        None,
                        None,
                        descriptors,
                        daily_user_data=env.daily,
                        repo=env.repo,
                        game_root=env.game,
                    )
                self.assertFalse((env.user / runtime.ACTIVE_SESSION_NAME).exists())
                before = runtime.before_session(
                    env.user,
                    "PROBE",
                    None,
                    None,
                    descriptors,
                    daily_user_data=env.daily,
                    repo=env.repo,
                    game_root=env.game,
                    permission_reference="explicit test permission",
                )
                session = Path(str(before["session"]))
                self.assertTrue((env.user / runtime.ACTIVE_SESSION_NAME).is_file())
                self.assertTrue((session / runtime.SESSION_SEAL_NAME).is_file())
                runtime._verified_session_seal(session)
                with self.assertRaises(runtime.AcceptanceError):
                    runtime.configure_playset(env.user, "PROBE", None, descriptors)

                session_file = session / "session.json"
                original = session_file.read_bytes()
                session_file.write_bytes(original + b"\n")
                with self.assertRaises(runtime.AcceptanceError):
                    runtime.abort_session(session, "tamper check")
                session_file.write_bytes(original)
                aborted = runtime.abort_session(session, "operator ended dry run")
                self.assertEqual("aborted", aborted["status"])
                self.assertFalse((env.user / runtime.ACTIVE_SESSION_NAME).exists())
                self.assertFalse(aborted["game_started_by_tool"])
                with self.assertRaises(runtime.AcceptanceError):
                    runtime.abort_session(session, "second abort")

    def test_observe_process_requires_exact_single_argv_and_creation_date(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            with _runtime_environment(Path(temporary)) as env:
                descriptors = list(_deploy_pair(env))
                before = _configure_before(env, descriptors)
                session = Path(str(before["session"]))
                expected = list(before["expected_argv"])
                process = {
                    "ProcessId": 1234,
                    "ExecutablePath": expected[0],
                    "CommandLine": f'"{expected[0]}" {expected[1]} --extra',
                    "CreationDate": runtime._read_json_object(
                        session / "session.json", "session"
                    )["started_at"],
                }
                with (
                    patch.object(
                        runtime,
                        "_running_eu4_processes",
                        return_value=("eu4.exe",),
                    ),
                    patch.object(runtime, "_eu4_process_details", return_value=[process]),
                    patch.object(
                        runtime,
                        "_windows_command_line_argv",
                        return_value=[*expected, "--extra"],
                    ),
                ):
                    with self.assertRaises(runtime.AcceptanceError):
                        runtime.observe_process(session)
                observation = _observe_exact(before)
                self.assertEqual(expected, observation["argv"])
                self.assertTrue(observation["creation_date"])
                with self.assertRaises(runtime.AcceptanceError):
                    _observe_exact(before)
                runtime.abort_session(session, "observation test complete")

    def test_probe_collection_is_ready_sealed_immutable_and_never_launches(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            with _runtime_environment(Path(temporary)) as env:
                descriptors = list(_deploy_pair(env))
                before, result, session = _complete_probe(env, descriptors)
                self.assertEqual(runtime.COLLECTION_SCHEMA, result["schema"])
                self.assertEqual("PROBE", result["scenario_id"])
                self.assertEqual("default", result["phase"])
                self.assertEqual("READY_FOR_LEAD_REVIEW", result["status"])
                self.assertTrue(result["automated_checks_passed"])
                self.assertTrue(result["manual_assertions_complete"])
                self.assertTrue(result["manual_assertions_passed"])
                self.assertTrue(result["ready_for_lead_review"])
                self.assertFalse(result["scenario_pass_claimed"])
                self.assertFalse((env.user / runtime.ACTIVE_SESSION_NAME).exists())
                collection, seal = runtime._verified_collection_file(session)
                self.assertEqual(runtime._COLLECTION_SCHEMA4_KEYS, set(collection))
                self.assertEqual(result["session_sha256"], seal["session_sha256"])
                self.assertEqual(result["session_id"], collection["session_id"])
                self.assertFalse(
                    json.loads(
                        (session / "session.json").read_text(encoding="utf-8")
                    )["game_started_by_tool"]
                )
                collection_path = session / runtime.COLLECTION_NAME
                seal_path = session / runtime.COLLECTION_SEAL_NAME
                before_hashes = (
                    runtime._sha256_file(collection_path),
                    runtime._sha256_file(seal_path),
                )
                repeated, repeated_ready = runtime.collect(
                    session,
                    [],
                    Path(str(before["evidence_manifest"])),
                )
                self.assertTrue(repeated_ready)
                self.assertEqual(result, repeated)
                self.assertEqual(
                    before_hashes,
                    (
                        runtime._sha256_file(collection_path),
                        runtime._sha256_file(seal_path),
                    ),
                )

    def test_parent_collection_rejects_forged_ready_claims_and_schema(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            with _runtime_environment(Path(temporary)) as env:
                descriptors = list(_deploy_pair(env))
                _, _, session = _complete_probe(env, descriptors, "forged-ready")
                collection_path = session / runtime.COLLECTION_NAME
                seal_path = session / runtime.COLLECTION_SEAL_NAME
                original_collection = collection_path.read_bytes()
                original_seal = seal_path.read_bytes()

                def forge(mutator) -> None:
                    collection = json.loads(original_collection.decode("utf-8"))
                    mutator(collection)
                    _write_json(collection_path, collection)
                    seal = json.loads(original_seal.decode("utf-8"))
                    seal["collection_sha256"] = runtime._sha256_file(collection_path)
                    _write_json(seal_path, seal)

                cases = (
                    (
                        "unknown schema key",
                        lambda value: value.__setitem__("unexpected", True),
                    ),
                    (
                        "forged status",
                        lambda value: value.__setitem__("status", "NOT_READY"),
                    ),
                    (
                        "forged ready boolean",
                        lambda value: value.__setitem__(
                            "ready_for_lead_review", False
                        ),
                    ),
                    (
                        "forged automated boolean",
                        lambda value: value.__setitem__(
                            "automated_checks_passed", False
                        ),
                    ),
                    (
                        "forged manual boolean",
                        lambda value: value.__setitem__(
                            "manual_assertions_passed", False
                        ),
                    ),
                    (
                        "hidden failed assertion",
                        lambda value: value["assertions"][0].__setitem__(
                            "status", "FAIL"
                        ),
                    ),
                )
                try:
                    for label, mutator in cases:
                        with self.subTest(label=label):
                            forge(mutator)
                            with self.assertRaises(runtime.AcceptanceError):
                                runtime._verified_collection_file(session)
                finally:
                    collection_path.write_bytes(original_collection)
                    seal_path.write_bytes(original_seal)

    def test_parent_collection_rechecks_identity_paths_bytes_formats_and_replay(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            with _runtime_environment(Path(temporary)) as env:
                descriptors = list(_deploy_pair(env))
                _, _, session = _complete_probe(env, descriptors, "forged-artifacts")
                collection_path = session / runtime.COLLECTION_NAME
                seal_path = session / runtime.COLLECTION_SEAL_NAME
                original_collection = collection_path.read_bytes()
                original_seal = seal_path.read_bytes()
                baseline = json.loads(original_collection.decode("utf-8"))

                def records(value: dict[str, object], kind: str) -> list[dict[str, object]]:
                    matched: list[dict[str, object]] = []
                    for raw_records in value["artifact_roles"].values():
                        sequence = raw_records if isinstance(raw_records, list) else [raw_records]
                        matched.extend(
                            item
                            for item in sequence
                            if isinstance(item, dict) and item.get("kind") == kind
                        )
                    return matched

                def forge(mutator) -> None:
                    collection = json.loads(original_collection.decode("utf-8"))
                    mutator(collection)
                    _write_json(collection_path, collection)
                    seal = json.loads(original_seal.decode("utf-8"))
                    seal["collection_sha256"] = runtime._sha256_file(collection_path)
                    _write_json(seal_path, seal)

                screenshot_record = records(baseline, "screenshot")[0]
                screenshot_path = Path(str(screenshot_record["path"]))
                screenshot_bytes = screenshot_path.read_bytes()
                outside = _write_png(env.root / "outside-parent-evidence.png", (1, 2, 3))
                invalid = _write(
                    session / "after" / "artifacts" / "forged-image.png",
                    "not a PNG despite a recomputed record\n",
                )

                def point_screenshot_at(value, path: Path) -> None:
                    record = records(value, "screenshot")[0]
                    record.update(runtime._file_record(path.resolve()))

                def replay_vfs(value) -> None:
                    first, second = records(value, "vfs_inventory")
                    second.update(
                        {
                            key: first[key]
                            for key in ("path", "bytes", "mtime_ns", "sha256")
                        }
                    )

                mutations = (
                    (
                        "cross-session identity",
                        lambda value: value.__setitem__("session_id", "0" * 32),
                    ),
                    (
                        "outside-after artifact",
                        lambda value: point_screenshot_at(value, outside),
                    ),
                    (
                        "non-file artifact",
                        lambda value: records(value, "screenshot")[0].__setitem__(
                            "path", str((session / "after").resolve())
                        ),
                    ),
                    (
                        "format spoof with recomputed bytes",
                        lambda value: point_screenshot_at(value, invalid),
                    ),
                    ("cross-role replay", replay_vfs),
                )
                try:
                    for label, mutator in mutations:
                        with self.subTest(label=label):
                            forge(mutator)
                            with self.assertRaises(runtime.AcceptanceError):
                                runtime._verified_collection_file(session)

                    collection_path.write_bytes(original_collection)
                    seal_path.write_bytes(original_seal)
                    with self.subTest(label="artifact bytes changed after sealing"):
                        screenshot_path.write_bytes(screenshot_bytes + b"tampered")
                        with self.assertRaises(runtime.AcceptanceError):
                            runtime._verified_collection_file(session)
                        screenshot_path.write_bytes(screenshot_bytes)

                    with self.subTest(label="hard-link replay"):
                        replay_path = screenshot_path.with_name("hard-link-replay.png")
                        os.link(screenshot_path, replay_path)
                        try:
                            with self.assertRaises(runtime.AcceptanceError):
                                runtime._verified_collection_file(session)
                        finally:
                            replay_path.unlink()
                finally:
                    screenshot_path.write_bytes(screenshot_bytes)
                    collection_path.write_bytes(original_collection)
                    seal_path.write_bytes(original_seal)
                    invalid.unlink(missing_ok=True)

    def test_ready_probe_collection_can_be_exact_r1_parent(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            with _runtime_environment(Path(temporary)) as env:
                descriptors = list(_deploy_pair(env))
                _, _, probe_session = _complete_probe(env, descriptors, "parent")
                before = _configure_before(
                    env,
                    descriptors,
                    "R1",
                    parent_collections=(
                        f"protocol_probe_collection={probe_session}",
                    ),
                )
                session_record = runtime._read_json_object(
                    Path(str(before["session"])) / "session.json", "session"
                )
                self.assertEqual(1, len(session_record["parents"]))
                parent = session_record["parents"][0]
                self.assertEqual("PROBE", parent["scenario_id"])
                self.assertEqual("default", parent["phase"])
                self.assertEqual(
                    "protocol_probe_collection", parent["role"]
                )
                self.assertEqual(runtime._PARENT_DEPENDENCY_RECORD_KEYS, set(parent))
                self.assertEqual(
                    runtime._sha256_file(probe_session / runtime.COLLECTION_NAME),
                    parent["collection_sha256"],
                )
                self.assertEqual(
                    runtime._sha256_file(
                        probe_session / runtime.COLLECTION_SEAL_NAME
                    ),
                    parent["collection_seal_sha256"],
                )
                self.assertEqual(
                    runtime._sha256_file(runtime._session_seal_file(probe_session)),
                    parent["session_seal_sha256"],
                )
                self.assertEqual(
                    runtime._object_sha256(parent["artifact_roles"]),
                    parent["artifact_roles_sha256"],
                )
                runtime.abort_session(
                    Path(str(before["session"])), "parent lineage verified"
                )

    def test_close_release_is_sealed_nonruntime_and_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            with _runtime_environment(Path(temporary)) as env:
                normalized = _r13_without_blockers()
                parents = _r13_parent_records(env, normalized)
                parent_args = _r13_parent_args(env, normalized)
                artifact_args = _r13_artifact_args(env, normalized, parents)
                gate_verifications = _r13_fake_gate_verifications(env, parents)
                assertions = _r13_assertion_manifest(env, normalized)
                output = env.user / "unit-release-closure"
                with (
                    patch.object(
                        runtime,
                        "_normalized_evidence_contract",
                        return_value=normalized,
                    ),
                    patch.object(
                        runtime,
                        "_seal_parent_collections",
                        side_effect=_r13_fake_parent_sealer(parents),
                    ),
                    patch.object(
                        runtime,
                        "_run_r13_static_gate_verifications",
                        return_value=gate_verifications,
                    ) as gate_runner,
                    patch.object(
                        runtime,
                        "_r13_gate_toolchain_guard",
                        return_value=_r13_fake_toolchain_guard(),
                    ),
                ):
                    result, ready = runtime.close_release(
                        env.repo,
                        env.game,
                        env.daily,
                        env.user,
                        parent_args,
                        artifact_args,
                        assertions,
                        output,
                    )
                    before_hashes = (
                        runtime._sha256_file(output / runtime.CLOSURE_NAME),
                        runtime._sha256_file(output / runtime.CLOSURE_SEAL_NAME),
                    )
                    repeated, repeated_ready = runtime.close_release(
                        env.repo,
                        env.game,
                        env.daily,
                        env.user,
                        parent_args,
                        artifact_args,
                        assertions,
                        output,
                    )
                    closure_path = output / runtime.CLOSURE_NAME
                    seal_path = output / runtime.CLOSURE_SEAL_NAME
                    original_closure = closure_path.read_bytes()
                    original_seal = seal_path.read_bytes()
                    for case in (
                        "parent ready bool",
                        "context game pin bool",
                        "artifact validation bool",
                        "assertion validation bool",
                    ):
                        closure_value = json.loads(original_closure)
                        seal_value = json.loads(original_seal)
                        if case == "parent ready bool":
                            closure_value["parents"][0]["ready_for_lead_review"] = 1
                        elif case == "context game pin bool":
                            closure_value["game_pins"][0]["matched"] = 1
                        elif case == "artifact validation bool":
                            first_role = next(iter(closure_value["artifact_roles"]))
                            closure_value["artifact_roles"][first_role]["validation"][
                                "passed"
                            ] = 1
                        else:
                            closure_value["assertion_manifest"]["validation"][
                                "passed"
                            ] = 1
                        if case.startswith("parent"):
                            closure_value["parent_lineage_sha256"] = runtime._object_sha256(
                                closure_value["parents"]
                            )
                            seal_value["parent_lineage_sha256"] = closure_value[
                                "parent_lineage_sha256"
                            ]
                        if case.startswith("artifact"):
                            closure_value["artifact_roles_sha256"] = runtime._object_sha256(
                                closure_value["artifact_roles"]
                            )
                            seal_value["artifact_roles_sha256"] = closure_value[
                                "artifact_roles_sha256"
                            ]
                        _write_json(closure_path, closure_value)
                        seal_value["closure_sha256"] = runtime._sha256_file(closure_path)
                        _write_json(seal_path, seal_value)
                        with self.subTest(case=case), self.assertRaises(
                            runtime.AcceptanceError
                        ):
                            runtime.close_release(
                                env.repo,
                                env.game,
                                env.daily,
                                env.user,
                                parent_args,
                                artifact_args,
                                assertions,
                                output,
                            )
                        closure_path.write_bytes(original_closure)
                        seal_path.write_bytes(original_seal)
                    gate_runner.side_effect = runtime.AcceptanceError(
                        "fresh replay gate failed"
                    )
                    with self.assertRaises(runtime.AcceptanceError):
                        runtime.close_release(
                            env.repo,
                            env.game,
                            env.daily,
                            env.user,
                            parent_args,
                            artifact_args,
                            assertions,
                            output,
                        )
                self.assertEqual(7, gate_runner.call_count)
                self.assertTrue(ready)
                self.assertTrue(repeated_ready)
                self.assertEqual(result, repeated)
                self.assertEqual("READY_FOR_LEAD_REVIEW", result["status"])
                self.assertEqual(16, len(result["parents"]))
                self.assertEqual(10, len(result["artifact_roles"]))
                self.assertEqual(6, len(result["assertions"]))
                self.assertEqual(12, len(result["automated_check_results"]))
                self.assertTrue(result["automated_checks_passed"])
                self.assertTrue(
                    all(item["matched"] for item in result["automated_check_results"])
                )
                self.assertFalse(result["game_session_created"])
                self.assertFalse(result["active_lock_created"])
                self.assertFalse(result["game_started"])
                self.assertFalse((env.user / runtime.ACTIVE_SESSION_NAME).exists())
                self.assertEqual(
                    before_hashes,
                    (
                        runtime._sha256_file(output / runtime.CLOSURE_NAME),
                        runtime._sha256_file(output / runtime.CLOSURE_SEAL_NAME),
                    ),
                )
                self.assertTrue(
                    all(
                        runtime._is_relative_to(Path(item["path"]), output / "artifacts")
                        for item in result["artifact_roles"].values()
                    )
                )

    def test_r13_gate_runner_uses_controlled_commands_and_seals_real_output(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            with _runtime_environment(Path(temporary)) as env:
                normalized = _r13_without_blockers()
                parents = _r13_parent_records(env, normalized)
                context = _r13_context(env)
                expected_payload = runtime._r13_common_evidence_identity(
                    parents, context
                )["tested_payload"]
                specs = runtime._r13_static_gate_specs(context)
                fake_toolchain = _r13_fake_toolchain_guard()
                with patch.dict(
                    os.environ,
                    {
                        "SystemRoot": r"C:\hostile-system-root",
                        "PATH": r"C:\hostile-path",
                        "PYTHONHOME": r"C:\hostile-python-home",
                        "CODEX_HOME": r"C:\hostile-codex-home",
                    },
                    clear=False,
                ):
                    self.assertEqual(specs, runtime._r13_static_gate_specs(context))
                marker_by_command = {
                    tuple(command): markers
                    for spec in specs.values()
                    for command, markers in zip(
                        spec["commands"], spec["required_markers"], strict=True
                    )
                }

                def completed(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[bytes]:
                    markers = marker_by_command[tuple(command)]
                    return subprocess.CompletedProcess(
                        command,
                        0,
                        ("\n".join(markers) + "\n").encode("utf-8"),
                        b"",
                    )

                with (
                    patch.object(
                        runtime,
                        "_r13_live_runtime_payload_guard",
                        return_value=expected_payload,
                    ),
                    patch.object(
                        runtime,
                        "_r13_skill_tree_manifest",
                        return_value=[
                            {"path": "SKILL.md", "bytes": 1, "sha256": "a" * 64}
                        ],
                    ),
                    patch.object(
                        runtime,
                        "_r13_gate_toolchain_guard",
                        return_value=fake_toolchain,
                    ),
                    patch.object(
                        runtime, "_run_r13_bounded_process", side_effect=completed
                    ) as run,
                ):
                    results = runtime._run_r13_static_gate_verifications(
                        context, expected_payload
                    )
                self.assertEqual(set(runtime._R13_GATE_CHECK_IDS), set(results))
                self.assertEqual(7, run.call_count)
                for invocation in run.call_args_list:
                    effective = invocation.kwargs["env"]
                    self.assertNotIn("PYTHONHOME", effective)
                    self.assertNotIn("CODEX_HOME", effective)
                    self.assertNotIn("PYTHONPATH", effective)
                    self.assertEqual("1", effective["PYTHONSAFEPATH"])
                    self.assertEqual(
                        str(
                            env.repo
                            / "skills"
                            / "eu4-modding"
                            / "scripts"
                            / "check_mission_series_overlap.py"
                        ),
                        effective["JXP_R13_MISSION_OVERLAP_SCRIPT"],
                    )
                    self.assertNotIn(r"C:\hostile-path", effective["PATH"])
                    self.assertEqual(effective, dict(effective))
                for role, verification in results.items():
                    self.assertEqual("live_close_release", verification["execution_mode"])
                    self.assertEqual(expected_payload, verification["payload_guard"])
                    self.assertTrue(verification["executions"])
                    with patch.object(
                        runtime,
                        "_r13_gate_toolchain_guard",
                        return_value=fake_toolchain,
                    ):
                        validated = runtime._validated_r13_live_gate_verification(
                            role, context, verification
                        )
                    self.assertEqual(verification, validated)
                    for execution in verification["executions"]:
                        argv = execution["argv"]
                        self.assertFalse(
                            any(item.casefold().startswith("-userdir") for item in argv)
                        )
                        self.assertNotIn("-skipmainmodvalidation", [item.casefold() for item in argv])

                tampered = json.loads(
                    json.dumps(results["r13_main_static_gate_output"])
                )
                tampered["executions"][0]["stdout_b64"] = base64.b64encode(
                    b"forged PASS output\n"
                ).decode("ascii")
                with (
                    patch.object(
                        runtime,
                        "_r13_gate_toolchain_guard",
                        return_value=fake_toolchain,
                    ),
                    self.assertRaises(runtime.AcceptanceError),
                ):
                    runtime._validated_r13_live_gate_verification(
                        "r13_main_static_gate_output", context, tampered
                    )
                strict_type_mutations = (
                    ("boolean exit", ("executions", 0, "exit_code"), False),
                    ("boolean empty byte count", ("executions", 0, "stderr_bytes"), False),
                    ("non-string base64", ("executions", 0, "stderr_b64"), 0),
                    ("integer marker match", ("marker_proofs", 0, "matched"), 1),
                )
                for case, path, replacement in strict_type_mutations:
                    malformed = json.loads(
                        json.dumps(results["r13_main_static_gate_output"])
                    )
                    malformed[path[0]][path[1]][path[2]] = replacement
                    with (
                        self.subTest(case=case),
                        patch.object(
                            runtime,
                            "_r13_gate_toolchain_guard",
                            return_value=fake_toolchain,
                        ),
                        self.assertRaises(runtime.AcceptanceError),
                    ):
                        runtime._validated_r13_live_gate_verification(
                            "r13_main_static_gate_output", context, malformed
                        )

                def missing_markers(
                    command: list[str], **_kwargs: object
                ) -> subprocess.CompletedProcess[bytes]:
                    return subprocess.CompletedProcess(command, 0, b"PASS\n", b"")

                with (
                    patch.object(
                        runtime,
                        "_r13_live_runtime_payload_guard",
                        return_value=expected_payload,
                    ),
                    patch.object(
                        runtime,
                        "_r13_gate_toolchain_guard",
                        return_value=fake_toolchain,
                    ),
                    patch.object(
                        runtime,
                        "_run_r13_bounded_process",
                        side_effect=missing_markers,
                    ),
                    self.assertRaises(runtime.AcceptanceError),
                ):
                    runtime._run_r13_static_gate_verifications(
                        context, expected_payload
                    )

                broken_specs = json.loads(json.dumps(specs))
                broken_specs["r13_main_static_gate_output"]["commands"][0].append(
                    "-userdir=C:\\unsafe"
                )
                with (
                    patch.object(
                        runtime,
                        "_r13_live_runtime_payload_guard",
                        return_value=expected_payload,
                    ),
                    patch.object(
                        runtime, "_r13_static_gate_specs", return_value=broken_specs
                    ),
                    patch.object(
                        runtime,
                        "_r13_gate_toolchain_guard",
                        return_value=fake_toolchain,
                    ),
                    patch.object(
                        runtime, "_run_r13_bounded_process"
                    ) as forbidden_run,
                    self.assertRaises(runtime.AcceptanceError),
                ):
                    runtime._run_r13_static_gate_verifications(
                        context, expected_payload
                    )
                forbidden_run.assert_not_called()

                drifted_toolchain = json.loads(json.dumps(fake_toolchain))
                drifted_toolchain["toolchain_sha256"] = "b" * 64
                with (
                    patch.object(
                        runtime,
                        "_r13_live_runtime_payload_guard",
                        return_value=expected_payload,
                    ),
                    patch.object(
                        runtime,
                        "_r13_gate_toolchain_guard",
                        side_effect=[
                            fake_toolchain,
                            fake_toolchain,
                            drifted_toolchain,
                        ],
                    ),
                    patch.object(
                        runtime, "_run_r13_bounded_process", side_effect=completed
                    ),
                    self.assertRaises(runtime.AcceptanceError),
                ):
                    runtime._run_r13_static_gate_verifications(
                        context, expected_payload
                    )
                self.assertFalse((env.user / ".jxp_r13_gate_temp").exists())

                with (
                    patch.object(
                        runtime,
                        "_r13_live_runtime_payload_guard",
                        return_value=expected_payload,
                    ),
                    patch.object(
                        runtime,
                        "_r13_gate_toolchain_guard",
                        return_value=fake_toolchain,
                    ),
                    patch.object(
                        runtime, "_run_r13_bounded_process", side_effect=completed
                    ),
                    patch.object(runtime, "_R13_GATE_MAX_TOTAL_TRANSCRIPT_BYTES", 1),
                    self.assertRaises(runtime.AcceptanceError),
                ):
                    runtime._run_r13_static_gate_verifications(
                        context, expected_payload
                    )

    def test_r13_python_runner_allows_only_the_pinned_skill_script(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            main_tools = root / "main-tools"
            map_tools = root / "map-tools"
            dependency_site = root / "dependencies"
            pycache = root / "pycache"
            skill_scripts = root / "skill-scripts"
            for directory in (
                main_tools,
                map_tools,
                dependency_site,
                pycache,
                skill_scripts,
            ):
                directory.mkdir()
            quick_validate = _write(root / "quick_validate.py")
            allowed = _write(
                skill_scripts / "check_mission_series_overlap.py",
                "print('allowed')\n",
            )
            denied = _write(skill_scripts / "unrelated.py", "print('denied')\n")
            same_name_elsewhere = _write(
                root / "installed-skill" / "scripts" / allowed.name,
                "print('same name, wrong capability')\n",
            )
            configured = (
                main_tools,
                map_tools,
                dependency_site,
                quick_validate,
                allowed,
            )
            runner_environment = {
                "JXP_R13_MAIN_TOOLS": str(main_tools),
                "JXP_R13_MAP_TOOLS": str(map_tools),
                "JXP_R13_DEPENDENCY_SITE": str(dependency_site),
                "JXP_R13_PYCACHE_ROOT": str(pycache),
                "JXP_R13_QUICK_VALIDATE": str(quick_validate),
                "JXP_R13_MISSION_OVERLAP_SCRIPT": str(allowed),
            }
            base = Path(sys.base_prefix).resolve()
            isolated_sys = SimpleNamespace(
                flags=SimpleNamespace(isolated=1, no_site=1, safe_path=True),
                dont_write_bytecode=True,
                pycache_prefix=str(pycache),
                base_prefix=str(base),
                path=[str(base / "Lib")],
            )
            with (
                patch.dict(os.environ, runner_environment, clear=True),
                patch.object(r13_runner, "sys", isolated_sys),
                patch.object(r13_runner, "_package_origin"),
            ):
                self.assertEqual(configured, r13_runner._configure_paths())
            self.assertEqual(
                [str(main_tools), str(map_tools), str(dependency_site)],
                isolated_sys.path[-3:],
            )
            self.assertNotIn(str(skill_scripts), isolated_sys.path)
            self.assertIn(
                "skills/eu4-modding", runtime._R13_GIT_TOOLCHAIN_PATHS
            )

            incomplete_environment = dict(runner_environment)
            incomplete_environment.pop("JXP_R13_MISSION_OVERLAP_SCRIPT")
            with (
                patch.dict(os.environ, incomplete_environment, clear=True),
                patch.object(r13_runner, "sys", isolated_sys),
                self.assertRaisesRegex(RuntimeError, "environment is incomplete"),
            ):
                r13_runner._configure_paths()

            with (
                patch.object(r13_runner, "_configure_paths", return_value=configured),
                patch.object(
                    r13_runner,
                    "_ordinary",
                    side_effect=lambda value, **_kwargs: Path(value).resolve(),
                ),
                patch.object(r13_runner.runpy, "run_path") as run_path,
                patch.object(sys, "argv", ["r13_python_runner.py", str(allowed)]),
            ):
                r13_runner._run()
            run_path.assert_called_once_with(str(allowed), run_name="__main__")

            for rejected in (denied, same_name_elsewhere):
                with (
                    self.subTest(rejected=str(rejected)),
                    patch.object(
                        r13_runner, "_configure_paths", return_value=configured
                    ),
                    patch.object(
                        r13_runner,
                        "_ordinary",
                        side_effect=lambda value, **_kwargs: Path(value).resolve(),
                    ),
                    patch.object(r13_runner.runpy, "run_path"),
                    patch.object(
                        sys, "argv", ["r13_python_runner.py", str(rejected)]
                    ),
                    self.assertRaisesRegex(RuntimeError, "rejected script"),
                ):
                    r13_runner._run()

    def test_r13_bounded_process_stops_output_floods_during_read(self) -> None:
        command = [
            sys.executable,
            "-c",
            "import os; os.write(1, b'x' * (256 * 1024))",
        ]
        with (
            patch.object(runtime, "_R13_GATE_TIMEOUT_SECONDS", 10),
            self.assertRaisesRegex(
                runtime.AcceptanceError, "streaming output budget"
            ),
        ):
            runtime._run_r13_bounded_process(
                command,
                cwd=Path.cwd(),
                env=dict(os.environ),
                max_output_bytes=1024,
            )
        for descriptor in (1, 2):
            with self.subTest(descriptor=descriptor), self.assertRaisesRegex(
                runtime.AcceptanceError, "streaming output budget"
            ):
                runtime._run_r13_bounded_process(
                    [
                        sys.executable,
                        "-c",
                        f"import os; os.write({descriptor}, b'x' * 4096)",
                    ],
                    cwd=Path.cwd(),
                    env=dict(os.environ),
                    max_output_bytes=1024,
                )
        exact = runtime._run_r13_bounded_process(
            [
                sys.executable,
                "-c",
                "import os; os.write(1,b'o'*512); os.write(2,b'e'*512)",
            ],
            cwd=Path.cwd(),
            env=dict(os.environ),
            max_output_bytes=1024,
        )
        self.assertEqual(b"o" * 512, exact.stdout)
        self.assertEqual(b"e" * 512, exact.stderr)
        with (
            patch.object(runtime, "_R13_GATE_TIMEOUT_SECONDS", 0.05),
            self.assertRaisesRegex(runtime.AcceptanceError, "timed out"),
        ):
            runtime._run_r13_bounded_process(
                [sys.executable, "-c", "import time; time.sleep(2)"],
                cwd=Path.cwd(),
                env=dict(os.environ),
                max_output_bytes=1024,
            )

    def test_r13_journal_uses_commonmark_lines_and_exact_reserved_fence(self) -> None:
        entry_id = "R13_TEST_ENTRY"
        payload = {"updated_at": "2026-07-13T00:00:00+00:00"}
        base = "\n".join(
            (
                "# Ledger",
                "",
                "## Update Journal",
                "",
                f"### 2026-07-13 - {entry_id} - Test",
                "```jxp-r13-journal-json",
                json.dumps(payload),
                "```",
                "",
            )
        )
        for newline in ("\n", "\r\n", "\r"):
            with self.subTest(newline=repr(newline)):
                parsed, _section = runtime._r13_journal_entry(
                    base.replace("\n", newline), entry_id
                )
                self.assertEqual(payload, parsed)
        for separator in (
            "\x00",
            "\x0b",
            "\x0c",
            "\x1c",
            "\x1d",
            "\x1e",
            "\x85",
            "\u2028",
            "\u2029",
        ):
            hidden = base.replace("# Ledger\n", f"# Ledger{separator}", 1)
            with self.subTest(separator=repr(separator)), self.assertRaises(
                runtime.AcceptanceError
            ):
                runtime._r13_journal_entry(hidden, entry_id)

        aliases = (
            ("```jxp-r13-journal-json ", "```"),
            (" ````jxp-r13-journal-json", " ````"),
            ("~~~jxp-r13-journal-json", "~~~"),
            ("```jxp-r13-journal-json extra", "```"),
            (" ```jxp-r13-journal-json", " ```"),
            ("```jxp-r13-journal-json", "```"),
        )
        insertion = base.rfind("\n")
        for opener, closer in aliases:
            conflicting = (
                base[:insertion]
                + "\n"
                + opener
                + "\n{}\n"
                + closer
                + base[insertion:]
            )
            with self.subTest(opener=opener), self.assertRaises(
                runtime.AcceptanceError
            ):
                runtime._r13_journal_entry(conflicting, entry_id)

    def test_r13_closure_caps_aggregate_inputs_and_the_whole_tree(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            with _runtime_environment(Path(temporary)) as env:
                normalized = _r13_without_blockers()
                parents = _r13_parent_records(env, normalized)
                artifact_args = _r13_artifact_args(env, normalized, parents)
                assertion = _r13_assertion_manifest(env, normalized)
                parsed = runtime._parse_role_paths(artifact_args, "--artifact")
                total = sum(path.stat().st_size for path in parsed.values())
                total += assertion.stat().st_size
                with patch.object(
                    runtime, "_R13_CLOSURE_MAX_INPUT_BYTES", total
                ):
                    preflight = runtime._preflight_r13_closure_inputs(
                        artifact_args, assertion, normalized
                    )
                self.assertEqual(total, preflight["total_bytes"])
                with (
                    patch.object(
                        runtime, "_R13_CLOSURE_MAX_INPUT_BYTES", total - 1
                    ),
                    self.assertRaisesRegex(
                        runtime.AcceptanceError, "aggregate closure inputs"
                    ),
                ):
                    runtime._preflight_r13_closure_inputs(
                        artifact_args, assertion, normalized
                    )

                tree = env.user / "tree-cap"
                tree.mkdir()
                (tree / "a.bin").write_bytes(b"a" * 5)
                (tree / "b.bin").write_bytes(b"b" * 5)
                with patch.object(runtime, "_R13_CLOSURE_MAX_BYTES", 10):
                    self.assertEqual(
                        10, runtime._r13_closure_tree_total_bytes(tree, "test tree")
                    )
                with (
                    patch.object(runtime, "_R13_CLOSURE_MAX_BYTES", 9),
                    self.assertRaisesRegex(
                        runtime.AcceptanceError, "whole-tree size limit"
                    ),
                ):
                    runtime._r13_closure_tree_total_bytes(tree, "test tree")

    def test_r13_git_toolchain_rejects_tracked_untracked_and_ignored_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repo = Path(temporary).resolve()
            runtime._git(repo, "init")
            _write(repo / ".gitignore", "*.pyc\n")
            tracked = repo / "tools" / "validator.py"
            _write(tracked, "print('PASS')\n")
            runtime._git(repo, "add", ".gitignore", "tools/validator.py")
            runtime._git(
                repo,
                "-c",
                "user.name=R13 Test",
                "-c",
                "user.email=r13@example.invalid",
                "-c",
                "commit.gpgsign=false",
                "commit",
                "-m",
                "baseline",
            )
            clean = runtime._r13_git_tree_record(repo, "tools", "test tools")
            self.assertEqual(1, clean["file_count"])

            original = tracked.read_bytes()
            tracked.write_bytes(b"print('FORGED PASS')\n")
            with self.assertRaises(runtime.AcceptanceError):
                runtime._r13_git_tree_record(repo, "tools", "test tools")
            tracked.write_bytes(original)

            untracked = repo / "tools" / "unittest.py"
            _write(untracked, "print('forged')\n")
            with self.assertRaises(runtime.AcceptanceError):
                runtime._r13_git_tree_record(repo, "tools", "test tools")
            untracked.unlink()

            ignored = repo / "tools" / "cache.pyc"
            ignored.write_bytes(b"ignored but executable import data")
            with self.assertRaises(runtime.AcceptanceError):
                runtime._r13_git_tree_record(repo, "tools", "test tools")

    def test_close_release_rejects_missing_failed_stale_and_inexact_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            with _runtime_environment(Path(temporary)) as env:
                normalized = _r13_without_blockers()
                parent_args = _r13_parent_args(env, normalized)
                baseline_parents = _r13_parent_records(env, normalized)
                artifact_args = _r13_artifact_args(
                    env, normalized, baseline_parents
                )
                assertion_path = _r13_assertion_manifest(env, normalized)

                def call(
                    parents: list[dict[str, object]],
                    parent_values: list[str],
                    artifact_values: list[str],
                    output_name: str,
                ) -> None:
                    with (
                        patch.object(
                            runtime,
                            "_normalized_evidence_contract",
                            return_value=normalized,
                        ),
                        patch.object(
                            runtime,
                            "_seal_parent_collections",
                            side_effect=_r13_fake_parent_sealer(parents),
                        ),
                        patch.object(
                            runtime,
                            "_run_r13_static_gate_verifications",
                            return_value=_r13_fake_gate_verifications(env, parents),
                        ),
                        patch.object(
                            runtime,
                            "_r13_gate_toolchain_guard",
                            return_value=_r13_fake_toolchain_guard(),
                        ),
                    ):
                        runtime.close_release(
                            env.repo,
                            env.game,
                            env.daily,
                            env.user,
                            parent_values,
                            artifact_values,
                            assertion_path,
                            env.user / output_name,
                        )

                with self.subTest(case="missing parent"):
                    with self.assertRaises(runtime.AcceptanceError):
                        call(
                            baseline_parents,
                            parent_args[:-1],
                            artifact_args,
                            "missing-parent",
                        )
                with self.subTest(case="missing artifact"):
                    with self.assertRaises(runtime.AcceptanceError):
                        call(
                            baseline_parents,
                            parent_args,
                            artifact_args[:-1],
                            "missing-artifact",
                        )
                main_gate_path = Path(
                    next(
                        item.split("=", 1)[1]
                        for item in artifact_args
                        if item.startswith("r13_main_static_gate_output=")
                    )
                )
                main_gate = json.loads(main_gate_path.read_text(encoding="utf-8"))
                _write_json(
                    main_gate_path,
                    {"role": "r13_main_static_gate_output", "complete": True},
                )
                with self.subTest(case="free-form static gate claim"):
                    with self.assertRaises(runtime.AcceptanceError):
                        call(
                            baseline_parents,
                            parent_args,
                            artifact_args,
                            "forged-static-gate",
                        )
                _write_json(main_gate_path, main_gate)
                main_gate["exit_codes"][0] = False
                _write_json(main_gate_path, main_gate)
                with self.subTest(case="boolean static gate exit code"):
                    with self.assertRaises(runtime.AcceptanceError):
                        call(
                            baseline_parents,
                            parent_args,
                            artifact_args,
                            "boolean-static-gate-exit",
                        )
                main_gate["exit_codes"][0] = 0
                _write_json(main_gate_path, main_gate)

                ledger_artifact_path = Path(
                    next(
                        item.split("=", 1)[1]
                        for item in artifact_args
                        if item.startswith("r13_canonical_ledger_update=")
                    )
                )
                ledger_artifact = json.loads(
                    ledger_artifact_path.read_text(encoding="utf-8")
                )
                ledger_path = Path(ledger_artifact["ledger_path"])
                ledger_original = ledger_path.read_text(encoding="utf-8")
                target_entry, _section = runtime._r13_journal_entry(
                    ledger_original, ledger_artifact["entry_id"]
                )
                fenced_fake = "\n".join(
                    (
                        "# Fenced example only",
                        "",
                        "````text",
                        "## Update Journal",
                        "",
                        f"### 2026-07-13 - {ledger_artifact['entry_id']} - Fake",
                        "```jxp-r13-journal-json",
                        json.dumps(target_entry, ensure_ascii=False),
                        "```",
                        "````",
                        "",
                    )
                )
                with self.subTest(case="fenced fake journal entry is not structural"):
                    with self.assertRaises(runtime.AcceptanceError):
                        runtime._r13_journal_entry(
                            fenced_fake, ledger_artifact["entry_id"]
                        )
                decorated = fenced_fake + ledger_original
                self.assertEqual(
                    target_entry,
                    runtime._r13_journal_entry(
                        decorated, ledger_artifact["entry_id"]
                    )[0],
                )
                with self.subTest(case="unclosed journal fence fails closed"):
                    with self.assertRaises(runtime.AcceptanceError):
                        runtime._r13_journal_entry(
                            ledger_original + "\n````unclosed\n",
                            ledger_artifact["entry_id"],
                        )
                for case, wrapped in (
                    (
                        "cross-section HTML comment",
                        "<!--\n" + ledger_original + "\n-->\n",
                    ),
                    (
                        "raw script HTML block",
                        "<script>\n" + ledger_original + "\n</script>\n",
                    ),
                ):
                    with self.subTest(case=case):
                        with self.assertRaises(runtime.AcceptanceError):
                            runtime._r13_journal_entry(
                                wrapped, ledger_artifact["entry_id"]
                            )
                for field, replacement in (
                    ("ready_for_lead_review", 1),
                    ("r13_scenario_pass_claimed", 0),
                    ("r13_game_started", 0),
                    ("continuous_obligations_closed", 0),
                ):
                    typed_entry = json.loads(json.dumps(target_entry))
                    typed_entry[field] = replacement
                    typed_ledger = ledger_original.replace(
                        json.dumps(target_entry, ensure_ascii=False, indent=2),
                        json.dumps(typed_entry, ensure_ascii=False, indent=2),
                        1,
                    )
                    _write(ledger_path, typed_ledger)
                    typed_receipt = json.loads(json.dumps(ledger_artifact))
                    typed_receipt["ledger_sha256"] = runtime._sha256_file(ledger_path)
                    typed_receipt["entry_sha256"] = runtime._object_sha256(typed_entry)
                    _write_json(ledger_artifact_path, typed_receipt)
                    with self.subTest(case=f"journal exact bool {field}"):
                        with self.assertRaises(runtime.AcceptanceError):
                            call(
                                baseline_parents,
                                parent_args,
                                artifact_args,
                                f"journal-bool-{field}",
                            )
                _write(ledger_path, ledger_original)
                _write_json(ledger_artifact_path, ledger_artifact)
                bad_entry = json.loads(json.dumps(target_entry))
                bad_entry["candidate_revision"] = "f" * 40
                bad_ledger = ledger_original.replace(
                    json.dumps(target_entry, ensure_ascii=False, indent=2),
                    json.dumps(bad_entry, ensure_ascii=False, indent=2),
                    1,
                )
                bad_ledger += (
                    "\n### 2026-07-13 - RUNTIME-TEST-SCATTER - Scattered tokens\n\n"
                    + target_entry["candidate_revision"]
                    + "\n"
                    + target_entry["runtime_status"]
                    + "\n"
                    + "\n".join(target_entry["parent_collection_sha256s"])
                    + "\n"
                )
                _write(ledger_path, bad_ledger)
                bad_receipt = json.loads(json.dumps(ledger_artifact))
                bad_receipt["ledger_sha256"] = runtime._sha256_file(ledger_path)
                bad_receipt["entry_sha256"] = runtime._object_sha256(bad_entry)
                _write_json(ledger_artifact_path, bad_receipt)
                with self.subTest(case="ledger tokens scattered across entries"):
                    with self.assertRaises(runtime.AcceptanceError):
                        call(
                            baseline_parents,
                            parent_args,
                            artifact_args,
                            "scattered-ledger-entry",
                        )
                _write(ledger_path, ledger_original)
                _write_json(ledger_artifact_path, ledger_artifact)

                result_manifest_path = Path(
                    next(
                        item.split("=", 1)[1]
                        for item in artifact_args
                        if item.startswith("r13_assertion_result_manifest=")
                    )
                )
                result_manifest = json.loads(
                    result_manifest_path.read_text(encoding="utf-8")
                )
                removed = result_manifest["assertions"].pop()
                result_manifest["assertion_count"] -= 1
                _write_json(result_manifest_path, result_manifest)
                with self.subTest(case="incomplete assertion result index"):
                    with self.assertRaises(runtime.AcceptanceError):
                        call(
                            baseline_parents,
                            parent_args,
                            artifact_args,
                            "incomplete-assertion-index",
                        )
                result_manifest["assertions"].append(removed)
                result_manifest["assertion_count"] += 1
                _write_json(result_manifest_path, result_manifest)
                failed = json.loads(json.dumps(baseline_parents))
                failed[0]["collection_status"] = "MANUAL_ASSERTION_FAILED"
                failed[0]["ready_for_lead_review"] = False
                failed[0]["manual_assertions_passed"] = False
                with self.subTest(case="failed parent"):
                    with self.assertRaises(runtime.AcceptanceError):
                        call(failed, parent_args, artifact_args, "failed-parent")
                blocked_r5 = json.loads(json.dumps(baseline_parents))
                r5_parent = next(
                    item for item in blocked_r5 if item["role"] == "r5_collection"
                )
                r5_parent["collection_status"] = "MATRIX_CONTRACT_BLOCKED"
                r5_parent["ready_for_lead_review"] = False
                r5_parent["manual_assertions_passed"] = False
                with self.subTest(case="blocked R5 is never a release parent"):
                    with self.assertRaises(runtime.AcceptanceError):
                        call(
                            blocked_r5,
                            parent_args,
                            artifact_args,
                            "blocked-r5-parent",
                        )
                stale = json.loads(json.dumps(baseline_parents))
                stale[0]["compatibility"]["candidate_revision"] = "f" * 40
                with self.subTest(case="stale parent"):
                    with self.assertRaises(runtime.AcceptanceError):
                        call(stale, parent_args, artifact_args, "stale-parent")
                manifest = json.loads(assertion_path.read_text(encoding="utf-8"))
                manifest["assertions"][0]["status"] = "FAIL"
                _write_json(assertion_path, manifest)
                with self.subTest(case="failed R13 assertion"):
                    with self.assertRaises(runtime.AcceptanceError):
                        call(
                            baseline_parents,
                            parent_args,
                            artifact_args,
                            "failed-assertion",
                        )

    def test_close_release_refuses_matrix_blocker_without_output(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            with _runtime_environment(Path(temporary)) as env:
                normalized = runtime._normalized_evidence_contract(
                    runtime._scenario("R13"), None
                )
                self.assertTrue(normalized["blockers"])
                output = env.user / "blocked-release"
                with (
                    patch.object(
                        runtime,
                        "_seal_parent_collections",
                    ) as parent_sealer,
                    patch.object(runtime, "_run_r13_static_gate_verifications") as gate_runner,
                    self.assertRaises(runtime.AcceptanceError),
                ):
                    runtime.close_release(
                        env.repo,
                        env.game,
                        env.daily,
                        env.user,
                        [],
                        [],
                        env.root / "unused-assertions.json",
                        output,
                    )
                parent_sealer.assert_not_called()
                gate_runner.assert_not_called()
                self.assertFalse(output.exists())

    def test_close_release_detects_hash_tampering_and_failed_write_is_retryable(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            with _runtime_environment(Path(temporary)) as env:
                normalized = _r13_without_blockers()
                parents = _r13_parent_records(env, normalized)
                parent_args = _r13_parent_args(env, normalized)
                artifact_args = _r13_artifact_args(env, normalized, parents)
                assertions = _r13_assertion_manifest(env, normalized)
                output = env.user / "retry-release"
                original_write = runtime._exclusive_write_json
                calls = 0

                def fail_second_write(path: Path, value: object) -> None:
                    nonlocal calls
                    calls += 1
                    if calls == 2:
                        raise runtime.AcceptanceError("injected seal write failure")
                    original_write(path, value)

                common_patches = lambda: (
                    patch.object(
                        runtime,
                        "_normalized_evidence_contract",
                        return_value=normalized,
                    ),
                    patch.object(
                        runtime,
                        "_seal_parent_collections",
                        side_effect=_r13_fake_parent_sealer(parents),
                    ),
                    patch.object(
                        runtime,
                        "_run_r13_static_gate_verifications",
                        return_value=_r13_fake_gate_verifications(env, parents),
                    ),
                    patch.object(
                        runtime,
                        "_r13_gate_toolchain_guard",
                        return_value=_r13_fake_toolchain_guard(),
                    ),
                )
                first, second, third, fourth = common_patches()
                with first, second, third, fourth, patch.object(
                    runtime,
                    "_exclusive_write_json",
                    side_effect=fail_second_write,
                ):
                    with self.assertRaises(runtime.AcceptanceError):
                        runtime.close_release(
                            env.repo,
                            env.game,
                            env.daily,
                            env.user,
                            parent_args,
                            artifact_args,
                            assertions,
                            output,
                        )
                self.assertFalse(output.exists())
                self.assertFalse(any(env.user.glob(".*.staging")))
                first, second, third, fourth = common_patches()
                with (
                    first,
                    second,
                    third,
                    fourth,
                    patch.object(runtime, "_R13_CLOSURE_MAX_BYTES", 1),
                    self.assertRaises(runtime.AcceptanceError),
                ):
                    runtime.close_release(
                        env.repo,
                        env.game,
                        env.daily,
                        env.user,
                        parent_args,
                        artifact_args,
                        assertions,
                        output,
                    )
                self.assertFalse(output.exists())
                self.assertFalse(any(env.user.glob(".*.staging")))
                first, second, third, fourth = common_patches()
                with first, second, third, fourth:
                    result, ready = runtime.close_release(
                        env.repo,
                        env.game,
                        env.daily,
                        env.user,
                        parent_args,
                        artifact_args,
                        assertions,
                        output,
                    )
                self.assertTrue(ready)
                source = Path(artifact_args[2].split("=", 1)[1])
                original_source = source.read_bytes()
                source.write_bytes(original_source + b"tampered")
                first, second, third, fourth = common_patches()
                with first, second, third, fourth, self.assertRaises(runtime.AcceptanceError):
                    runtime.close_release(
                        env.repo,
                        env.game,
                        env.daily,
                        env.user,
                        parent_args,
                        artifact_args,
                        assertions,
                        output,
                    )
                source.write_bytes(original_source)
                copied = Path(result["artifact_roles"][
                    list(result["artifact_roles"])[0]
                ]["path"])
                copied.write_bytes(copied.read_bytes() + b"tampered")
                first, second, third, fourth = common_patches()
                with first, second, third, fourth, self.assertRaises(runtime.AcceptanceError):
                    runtime.close_release(
                        env.repo,
                        env.game,
                        env.daily,
                        env.user,
                        parent_args,
                        artifact_args,
                        assertions,
                        output,
                    )

    def test_cli_has_observe_and_abort_but_no_launch_surface(self) -> None:
        parser = runtime._parser()
        choices = parser._subparsers._group_actions[0].choices
        self.assertEqual(
            {
                "preflight",
                "deploy",
                "configure-playset",
                "install-fixtures",
                "before-session",
                "observe-process",
                "abort-session",
                "collect",
                "close-release",
            },
            set(choices),
        )
        self.assertFalse(any("launch" in choice for choice in choices))
        self.assertEqual(
            runtime.DEFAULT_USER_DATA, parser.parse_args(["preflight"]).user_data
        )
        self.assertEqual(
            runtime.DEFAULT_ACCEPTANCE_USER_DATA,
            parser.parse_args(["deploy"]).user_data,
        )
        before = parser.parse_args(
            ["before-session", "R1", "--permission-reference", "explicit"]
        )
        self.assertEqual(runtime.DEFAULT_ACCEPTANCE_USER_DATA, before.user_data)
        self.assertEqual(runtime.DEFAULT_USER_DATA, before.daily_user_data)
        observed = parser.parse_args(["observe-process", "session"])
        self.assertEqual(Path("session"), observed.session)
        aborted = parser.parse_args(
            ["abort-session", "session", "--reason", "operator request"]
        )
        self.assertEqual("operator request", aborted.reason)
        closed = parser.parse_args(
            [
                "close-release",
                "--assertion-manifest",
                "r13.json",
            ]
        )
        self.assertFalse(hasattr(closed, "permission_reference"))
        self.assertEqual([], closed.parent_collection)
        self.assertEqual([], closed.artifact)


if __name__ == "__main__":
    unittest.main()
