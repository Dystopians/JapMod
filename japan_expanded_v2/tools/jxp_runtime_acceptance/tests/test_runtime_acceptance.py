from __future__ import annotations

import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import zipfile

from jxp_runtime_acceptance import runtime_acceptance as runtime


LIVE_REPO = Path(__file__).resolve().parents[4]


def _write(path: Path, text: str = "payload\n") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _component(root: Path, key: str = "main") -> runtime.Component:
    source = root / f"source-{key}"
    for directory in runtime.RUNTIME_DIRECTORIES[key]:
        _write(source / directory / "payload.txt")
    version = "0.1.3-alpha" if key == "map" else "0.28.0"
    descriptor = f'supported_version="1.37.*"\nversion="{version}"\n'
    _write(source / "descriptor.mod", descriptor)
    (source / "thumbnail.png").write_bytes(b"png")
    outer = root / f"{key}.mod"
    _write(outer, f'name="fixture"\nversion="{version}"\n')
    _write(source / "tools" / "must-not-deploy.py")
    _write(source / "dev_logs" / "must-not-deploy.md")
    _write(source / "localisation_source" / "must-not-deploy.yml")
    _write(source / "AGENTS.md")
    _write(source / "thumbnail_imagegen_source.png")
    return runtime.Component(key, source, outer)


def _install_pair(root: Path) -> tuple[Path, Path, Path]:
    user_data = root / "user"
    mod_dir = user_data / "mod"
    mod_dir.mkdir(parents=True)
    daily_user_data = root / "daily"
    _write(
        daily_user_data / "dlc_load.json",
        json.dumps({"enabled_mods": [], "disabled_dlcs": []}),
    )
    (daily_user_data / "launcher-v2.sqlite").write_bytes(b"daily launcher fixture\n")
    main = _component(root, "main")
    candidate_revision = runtime._current_candidate_revision()
    main_record = runtime._deploy_component(
        main, mod_dir, "current", candidate_revision, None
    )
    map_component = _component(root, "map")
    map_record = runtime._deploy_component(
        map_component,
        mod_dir,
        "current",
        candidate_revision,
        str(main_record["display_name"]),
    )
    return (
        user_data.resolve(),
        Path(main_record["descriptor"]),
        Path(map_record["descriptor"]),
    )


def _before_session(
    user_data: Path,
    scenario_id: str,
    phase: str | None,
    evidence_root: Path | None,
    descriptors: list[Path],
    candidate_revision: str | None = None,
) -> dict[str, object]:
    return runtime.before_session(
        user_data,
        scenario_id,
        phase,
        evidence_root,
        descriptors,
        candidate_revision,
        user_data.parent / "daily",
    )


class RuntimeAcceptanceTests(unittest.TestCase):
    def test_acceptance_userdir_path_is_unambiguous(self) -> None:
        self.assertTrue(str(runtime.DEFAULT_ACCEPTANCE_USER_DATA).isascii())
        self.assertIsNone(
            re.search(r'[\s"]', str(runtime.DEFAULT_ACCEPTANCE_USER_DATA))
        )
        with tempfile.TemporaryDirectory() as temporary:
            unsafe = Path(temporary) / "unsafe - acceptance"
            unsafe.mkdir()
            with self.assertRaises(runtime.AcceptanceError):
                runtime._require_isolated_user_data(unsafe)

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
            for component in components:
                self.assertTrue(component.source.is_dir())
                self.assertTrue(component.outer_descriptor.is_file())

    def test_preflight_pins_executable_and_userdir_protocol_files(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            repo = root / "repo"
            game = root / "game"
            user_data = root / "daily"
            game.mkdir()
            user_data.mkdir()
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
            _write(
                user_data / "dlc_load.json",
                json.dumps({"enabled_mods": [], "disabled_dlcs": []}),
            )
            protocol_pins = {
                name: runtime._sha256_file(game / name)
                for name in ("eu4.exe", "userdir.txt")
            }
            manifest = {
                "eu4_display_version": "fixture",
                "files": [],
                "generic_files": [],
                "mandate_files": [],
            }
            with (
                patch.object(runtime, "PINNED_PROTOCOL_FILES", protocol_pins),
                patch.object(runtime, "_load_pin_manifest", return_value=manifest),
                patch.object(runtime, "_running_eu4_processes", return_value=()),
            ):
                result = runtime.preflight(repo, game, user_data)
                self.assertTrue(result["ready_for_safe_deploy"])
                self.assertEqual(
                    {"eu4.exe", "userdir.txt"},
                    {item["path"] for item in result["pinned_files"]},
                )
                (game / "userdir.txt").write_bytes(b"unexpected override\n")
                result = runtime.preflight(repo, game, user_data)
                self.assertFalse(result["ready_for_safe_deploy"])

    def test_matrix_covers_every_runtime_batch_and_open_todo(self) -> None:
        matrix = json.loads(
            (Path(runtime.__file__).with_name("runtime_scenarios.json")).read_text(
                encoding="utf-8"
            )
        )
        scenarios = matrix["scenarios"]
        self.assertEqual([f"R{number}" for number in range(1, 14)], [item["id"] for item in scenarios])
        covered = {todo for item in scenarios for todo in item["todos"]}
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
        for scenario in scenarios[:-1]:
            contracts = scenario.get("session_phases") or {
                "default": scenario.get("session_contract")
            }
            self.assertTrue(all(isinstance(item, dict) for item in contracts.values()))
            for contract in contracts.values():
                self.assertIn("required_components", contract)
                self.assertIn("required_versions", contract)
                self.assertIn("minimum_screenshots", contract)
                self.assertIn("minimum_saves", contract)
        self.assertEqual(
            runtime.PINNED_PRE_IDENTITY_REVISION,
            matrix["legacy_sources"]["0.25.0"]["commit"],
        )
        self.assertEqual(
            runtime.PINNED_LEGACY_REVISION,
            matrix["legacy_sources"]["0.27.0"]["commit"],
        )
        self.assertEqual(
            "external_required",
            matrix["legacy_sources"]["pre-0.24.2"]["availability"],
        )

    def test_runtime_whitelist_excludes_development_material(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            component = _component(Path(temporary))
            relative = {
                path.relative_to(component.source).as_posix()
                for path in runtime._runtime_files(component)
            }
        self.assertIn("common/payload.txt", relative)
        self.assertIn("descriptor.mod", relative)
        self.assertIn("thumbnail.png", relative)
        self.assertFalse(any(item.startswith("tools/") for item in relative))
        self.assertFalse(any(item.startswith("dev_logs/") for item in relative))
        self.assertFalse(any(item.startswith("localisation_source/") for item in relative))
        self.assertNotIn("AGENTS.md", relative)
        self.assertNotIn("thumbnail_imagegen_source.png", relative)

    def test_runtime_whitelist_excludes_nested_source_preview_and_backups(self) -> None:
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
            _write(
                component.source
                / "gfx"
                / "flags"
                / "source"
                / "__pycache__"
                / "builder.cpython-313.pyc"
            )
            _write(component.source / "gfx" / "flags" / "live.tga")
            relative = {
                path.relative_to(component.source).as_posix()
                for path in runtime._runtime_files(component)
            }
        self.assertIn("gfx/flags/live.tga", relative)
        self.assertFalse(any("/source/" in item for item in relative))
        self.assertFalse(any("/preview/" in item for item in relative))
        self.assertFalse(any("/backup_before_imagegen/" in item for item in relative))
        self.assertFalse(any(item.endswith(".pyc") for item in relative))

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

    def test_windows_path_escape_and_duplicate_evidence_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            target = root / "target"
            target.mkdir()
            malicious = {
                "path": r"C:\outside.txt",
                "bytes": 1,
                "sha256": "a" * 64,
            }
            with self.assertRaises(runtime.AcceptanceError):
                runtime._verify_installed_manifest(target, [malicious])

            development = {
                "path": "gfx/flags/source/build.pyc",
                "bytes": 1,
                "sha256": "a" * 64,
            }
            with self.assertRaises(runtime.AcceptanceError):
                runtime._snapshot_fingerprint_for_records(
                    "main", [development], "a" * 40
                )

            archive = root / "malicious.zip"
            with zipfile.ZipFile(archive, "w") as bundle:
                bundle.writestr(r"C:\outside.txt", "x")
            with self.assertRaises(runtime.AcceptanceError):
                runtime._safe_extract_zip(archive, root / "extract")

            duplicate = {
                "path": str(root / "same.png"),
                "bytes": 1,
                "mtime_ns": 10_000_000_000,
                "sha256": "b" * 64,
            }
            artifact_checks = runtime._artifact_requirement_checks(
                runtime._scenario("R1"),
                None,
                [duplicate, duplicate, duplicate],
                10_000_000_000,
            )
            screenshot_check = next(
                item for item in artifact_checks if item["kind"] == "screenshots"
            )
            self.assertEqual(1, screenshot_check["actual"])
            self.assertFalse(screenshot_check["matched"])

            game_log = root / "game.log"
            _write(
                game_log,
                "Setting up DLC Mandate of Heaven : Disabled\n"
                "Setting up DLC Mandate of Heaven : Enabled\n",
            )
            dlc_check = runtime._runtime_dlc_checks(
                runtime._scenario("R10"), None, [game_log]
            )[0]
            self.assertFalse(dlc_check["matched"])

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

    def test_content_addressed_deploy_is_ordinary_verified_and_idempotent(self) -> None:
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
            payload = Path(first["payload"])
            descriptor = Path(first["descriptor"])
            self.assertEqual(first, second)
            self.assertTrue(payload.is_dir())
            self.assertFalse(runtime._is_link_or_junction(payload))
            self.assertTrue((payload / ".jxp_acceptance_snapshot.json").is_file())
            self.assertTrue((payload / "common" / "payload.txt").is_file())
            self.assertFalse((payload / "tools").exists())
            self.assertTrue(descriptor.is_file())
            self.assertIn(
                f'path="mod/{payload.name}"',
                descriptor.read_text(encoding="utf-8"),
            )
            self.assertEqual([], list(mod_dir.glob(".jxp-stage-*")))

            (payload / "unexpected.txt").write_text("drift\n", encoding="utf-8")
            with self.assertRaises(runtime.AcceptanceError):
                runtime._deploy_component(
                    component, mod_dir, "current", "abc123+dirty", None
                )
            (payload / "unexpected.txt").unlink()
            marker = payload / ".jxp_acceptance_snapshot.json"
            marker_text = marker.read_text(encoding="utf-8")
            marker_value = json.loads(marker_text)
            marker_value["source_revision"] = "tampered"
            marker.write_text(json.dumps(marker_value), encoding="utf-8")
            with self.assertRaises(runtime.AcceptanceError):
                runtime._deploy_component(
                    component, mod_dir, "current", "abc123+dirty", None
                )
            marker.write_text(marker_text, encoding="utf-8")

            descriptor.write_text("unrelated\n", encoding="utf-8")
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

    def test_configure_playset_writes_only_isolated_exact_contract(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            user_data, main_descriptor, map_descriptor = _install_pair(Path(temporary))
            with patch.object(runtime, "_assert_processes_stopped"):
                configured = runtime.configure_playset(
                    user_data,
                    "R1",
                    None,
                    [map_descriptor, main_descriptor],
                )
            self.assertEqual(
                {
                    "enabled_mods": [
                        f"mod/{main_descriptor.name}",
                        f"mod/{map_descriptor.name}",
                    ],
                    "disabled_dlcs": [],
                },
                configured["configuration"],
            )
            self.assertFalse(configured["game_started"])
            self.assertFalse(configured["daily_launcher_configuration_modified"])
            self.assertFalse((user_data / "launcher-v2.sqlite").exists())
            self.assertEqual(
                configured["configuration"],
                json.loads((user_data / "dlc_load.json").read_text(encoding="utf-8")),
            )
            self.assertEqual([], list(user_data.glob(".dlc_load.*.tmp")))

            with patch.object(runtime, "_assert_processes_stopped"):
                dlc_off = runtime.configure_playset(
                    user_data, "R11", None, [main_descriptor]
                )
            self.assertEqual(
                [runtime.DLC_CONFIG_PATHS["Mandate of Heaven"]],
                dlc_off["configuration"]["disabled_dlcs"],
            )
            with patch.object(runtime, "_assert_processes_stopped"):
                with self.assertRaises(runtime.AcceptanceError):
                    _before_session(
                        user_data,
                        "R10",
                        None,
                        None,
                        [main_descriptor],
                    )

    def test_install_run_fixtures_is_verified_idempotent_and_non_overwriting(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            user_data = Path(temporary) / "user"
            user_data.mkdir()
            other = Path(temporary) / "other"
            other.mkdir()
            fixtures = runtime._verified_run_fixture_records()
            conflict = user_data / str(fixtures[-1]["name"])
            _write(conflict, "different fixture\n")
            with (
                patch.object(runtime, "DEFAULT_ACCEPTANCE_USER_DATA", user_data),
                patch.object(runtime, "_assert_processes_stopped"),
            ):
                with self.assertRaises(runtime.AcceptanceError):
                    runtime.install_run_fixtures(other)
                with self.assertRaises(runtime.AcceptanceError):
                    runtime.install_run_fixtures(user_data)
            self.assertTrue(conflict.is_file())
            self.assertFalse(
                any(
                    (user_data / str(item["name"])).exists()
                    for item in fixtures[:-1]
                )
            )
            conflict.unlink()

            def partial_copy(_source: Path, destination: Path) -> None:
                destination.write_bytes(b"partial")
                raise OSError("injected staging failure")

            with (
                patch.object(runtime, "DEFAULT_ACCEPTANCE_USER_DATA", user_data),
                patch.object(runtime, "_assert_processes_stopped"),
                patch.object(runtime.shutil, "copy2", side_effect=partial_copy),
            ):
                with self.assertRaises(OSError):
                    runtime.install_run_fixtures(user_data)
            self.assertFalse(any(user_data.glob("JXP_ACC_*.txt")))
            self.assertFalse(any(user_data.glob(".*.tmp")))

            real_link = os.link
            link_calls = 0

            def fail_second_link(source: Path, destination: Path) -> None:
                nonlocal link_calls
                link_calls += 1
                if link_calls == 2:
                    raise OSError("injected commit failure")
                real_link(source, destination)

            with (
                patch.object(runtime, "DEFAULT_ACCEPTANCE_USER_DATA", user_data),
                patch.object(runtime, "_assert_processes_stopped"),
                patch.object(runtime.os, "link", side_effect=fail_second_link),
            ):
                with self.assertRaises(OSError):
                    runtime.install_run_fixtures(user_data)
            self.assertFalse(any(user_data.glob("JXP_ACC_*.txt")))
            self.assertFalse(any(user_data.glob(".*.tmp")))

            with (
                patch.object(runtime, "DEFAULT_ACCEPTANCE_USER_DATA", user_data),
                patch.object(runtime, "_assert_processes_stopped"),
            ):
                first = runtime.install_run_fixtures(user_data)
            self.assertEqual("debug_fixture_setup_installed", first["status"])
            self.assertEqual(5, len(first["installed"]))
            self.assertEqual(
                {"R4", "R6", "R8", "R10"},
                {item["scenario"] for item in first["installed"]},
            )
            self.assertTrue(all(not item["reused"] for item in first["installed"]))
            self.assertFalse((user_data / "dlc_load.json").exists())
            self.assertFalse((user_data / "launcher-v2.sqlite").exists())
            self.assertEqual([], list(user_data.glob(".*.tmp")))
            with (
                patch.object(runtime, "DEFAULT_ACCEPTANCE_USER_DATA", user_data),
                patch.object(runtime, "_assert_processes_stopped"),
            ):
                second = runtime.install_run_fixtures(user_data)
            self.assertTrue(all(item["reused"] for item in second["installed"]))
            target = user_data / str(first["installed"][0]["name"])
            _write(target, "different fixture\n")
            with (
                patch.object(runtime, "DEFAULT_ACCEPTANCE_USER_DATA", user_data),
                patch.object(runtime, "_assert_processes_stopped"),
            ):
                with self.assertRaises(runtime.AcceptanceError):
                    runtime.install_run_fixtures(user_data)

    def test_before_session_requires_exact_isolated_playset(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            user_data, main_descriptor, map_descriptor = _install_pair(Path(temporary))
            _write(
                user_data / "dlc_load.json",
                json.dumps(
                    {
                        "enabled_mods": [
                            f"mod/{main_descriptor.name}",
                            f"mod/{map_descriptor.name}",
                        ],
                        "disabled_dlcs": [],
                    }
                ),
            )
            _write(user_data / "logs" / "error.log", "old baseline\n")
            with patch.object(runtime, "_assert_processes_stopped"):
                result = _before_session(
                    user_data, "R1", None, None, [main_descriptor, map_descriptor]
                )
            session = Path(result["session"])
            self.assertTrue((session / "session.json").is_file())
            record = json.loads((session / "session.json").read_text(encoding="utf-8"))
            self.assertEqual(runtime.SESSION_SCHEMA, record["schema"])
            self.assertEqual("R1", record["scenario"]["id"])
            self.assertEqual(str(user_data.parent / "daily"), record["daily_user_data"])
            self.assertEqual(
                {"dlc_load.json", "launcher-v2.sqlite"},
                {
                    Path(item["path"]).name
                    for item in record["daily_configuration_baseline"]
                },
            )
            self.assertFalse(record["game_started_by_tool"])

            _write(
                user_data / "dlc_load.json",
                json.dumps(
                    {
                        "enabled_mods": [
                            f"mod/{main_descriptor.name}",
                            f"mod/{map_descriptor.name}",
                            "mod/ugc_253263609.mod",
                        ],
                        "disabled_dlcs": [],
                    }
                ),
            )
            with patch.object(runtime, "_assert_processes_stopped"):
                with self.assertRaises(runtime.AcceptanceError):
                    _before_session(
                        user_data,
                        "R1",
                        None,
                        None,
                        [main_descriptor, map_descriptor],
                    )

    def test_before_session_enforces_versions_components_and_phases(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            user_data, main_descriptor, map_descriptor = _install_pair(Path(temporary))
            _write(
                user_data / "dlc_load.json",
                json.dumps(
                    {
                        "enabled_mods": [f"mod/{main_descriptor.name}"],
                        "disabled_dlcs": [],
                    }
                ),
            )
            with patch.object(runtime, "_assert_processes_stopped"):
                with self.assertRaises(runtime.AcceptanceError):
                    _before_session(
                        user_data, "R1", None, None, [main_descriptor]
                    )
                with self.assertRaises(runtime.AcceptanceError):
                    _before_session(
                        user_data, "R4", None, None, [main_descriptor]
                    )
                with self.assertRaises(runtime.AcceptanceError):
                    _before_session(
                        user_data,
                        "R4",
                        "current-migrate",
                        None,
                        [main_descriptor],
                        "b" * 40,
                    )
                with self.assertRaises(runtime.AcceptanceError):
                    _before_session(
                        user_data, "R13", None, None, [main_descriptor]
                    )
                result = _before_session(
                    user_data,
                    "R4",
                    "current-migrate",
                    None,
                    [main_descriptor],
                )
            self.assertEqual("current-migrate", result["phase"])

    def test_collect_flags_release_blockers(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            user_data, main_descriptor, map_descriptor = _install_pair(Path(temporary))
            _write(
                user_data / "dlc_load.json",
                json.dumps(
                    {
                        "enabled_mods": [
                            f"mod/{main_descriptor.name}",
                            f"mod/{map_descriptor.name}",
                        ],
                        "disabled_dlcs": [],
                    }
                ),
            )
            _write(user_data / "logs" / "error.log", "baseline\n")
            with patch.object(runtime, "_assert_processes_stopped"):
                before = _before_session(
                    user_data,
                    "R1",
                    None,
                    None,
                    [main_descriptor, map_descriptor],
                )
            _write(
                user_data / "logs" / "error.log",
                "[effectimplementation.cpp] Unknown effect type: jxp_bad\n"
                "[mission.cpp:353] collision\n"
                "Unknown country tag: ZZZ\n",
            )
            _write(user_data / "logs" / "game.log", "runtime\n")
            session_file = Path(before["session"]) / "session.json"
            valid_session_text = session_file.read_text(encoding="utf-8")
            stale_session = json.loads(valid_session_text)
            stale_session["schema"] = 1
            session_file.write_text(json.dumps(stale_session), encoding="utf-8")
            with patch.object(runtime, "_assert_processes_stopped"):
                with self.assertRaises(runtime.AcceptanceError):
                    runtime.collect(Path(before["session"]), [])
            session_file.write_text(valid_session_text, encoding="utf-8")
            with patch.object(runtime, "_assert_processes_stopped"):
                result, passed = runtime.collect(Path(before["session"]), [])
            self.assertFalse(passed)
            self.assertTrue(
                {"unknown_effect", "mission_collision", "unknown_object"}.issubset(
                    {item["code"] for item in result["blockers"]}
                )
            )
            self.assertTrue(
                (Path(before["session"]) / "collection.json").is_file()
            )

    def test_collect_rejects_daily_configuration_changes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            user_data, main_descriptor, map_descriptor = _install_pair(Path(temporary))
            _write(
                user_data / "dlc_load.json",
                json.dumps(
                    {
                        "enabled_mods": [
                            f"mod/{main_descriptor.name}",
                            f"mod/{map_descriptor.name}",
                        ],
                        "disabled_dlcs": [],
                    }
                ),
            )
            with patch.object(runtime, "_assert_processes_stopped"):
                before = _before_session(
                    user_data,
                    "R1",
                    None,
                    None,
                    [main_descriptor, map_descriptor],
                )
            _write(user_data / "logs" / "error.log", "clean\n")
            _write(user_data / "logs" / "game.log", "runtime\n")
            for number in range(3):
                _write(
                    user_data / "Screenshots" / f"JXP_ACC_R1_{number}.png",
                    f"screenshot {number}\n",
                )
            _write(user_data / "save games" / "JXP_ACC_R1_BASELINE.eu4")
            _write(
                user_data.parent / "daily" / "dlc_load.json",
                json.dumps(
                    {
                        "enabled_mods": ["mod/unexpected.mod"],
                        "disabled_dlcs": [],
                    }
                ),
            )
            with patch.object(runtime, "_assert_processes_stopped"):
                result, passed = runtime.collect(Path(before["session"]), [])
            self.assertFalse(passed)
            self.assertFalse(result["daily_configuration_stable"])
            self.assertFalse(
                next(
                    item["matched"]
                    for item in result["daily_configuration_checks"]
                    if item["name"] == "dlc_load.json"
                )
            )
            self.assertTrue(result["isolated_configuration_stable"])

    def test_collect_ignores_stale_aux_logs_and_requires_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            user_data, main_descriptor, map_descriptor = _install_pair(Path(temporary))
            _write(
                user_data / "dlc_load.json",
                json.dumps(
                    {
                        "enabled_mods": [
                            f"mod/{main_descriptor.name}",
                            f"mod/{map_descriptor.name}",
                        ],
                        "disabled_dlcs": [],
                    }
                ),
            )
            _write(user_data / "logs" / "old_setup.log", "Unknown effect type: old\n")
            old = (user_data / "logs" / "old_setup.log").stat().st_mtime - 60
            os.utime(user_data / "logs" / "old_setup.log", (old, old))
            with patch.object(runtime, "_assert_processes_stopped"):
                before = _before_session(
                    user_data,
                    "R1",
                    None,
                    None,
                    [main_descriptor, map_descriptor],
                )
            _write(user_data / "logs" / "error.log", "clean\n")
            _write(user_data / "logs" / "game.log", "runtime\n")
            for number in range(3):
                _write(
                    user_data / "Screenshots" / f"JXP_ACC_R1_{number}.png",
                    f"screenshot {number}\n",
                )
            _write(user_data / "save games" / "JXP_ACC_R1_BASELINE.eu4")
            with patch.object(runtime, "_assert_processes_stopped"):
                result, passed = runtime.collect(Path(before["session"]), [])
            self.assertTrue(passed)
            self.assertTrue(result["passed_collection_gate"])
            self.assertEqual([], result["blockers"])

            for artifact in (user_data / "Screenshots").glob("*.png"):
                artifact.unlink()
            with patch.object(runtime, "_assert_processes_stopped"):
                second = _before_session(
                    user_data,
                    "R1",
                    None,
                    None,
                    [main_descriptor, map_descriptor],
                )
            _write(user_data / "logs" / "error.log", "clean again\n")
            _write(user_data / "logs" / "game.log", "runtime again\n")
            with patch.object(runtime, "_assert_processes_stopped"):
                result, passed = runtime.collect(Path(second["session"]), [])
            self.assertFalse(passed)
            self.assertFalse(
                next(
                    item["matched"]
                    for item in result["artifact_requirement_checks"]
                    if item["kind"] == "screenshots"
                )
            )

    def test_cli_deliberately_has_no_launch_command(self) -> None:
        parser = runtime._parser()
        choices = parser._subparsers._group_actions[0].choices
        self.assertEqual(
            {
                "preflight",
                "deploy",
                "configure-playset",
                "install-fixtures",
                "before-session",
                "collect",
            },
            set(choices),
        )
        self.assertEqual(
            runtime.DEFAULT_USER_DATA, parser.parse_args(["preflight"]).user_data
        )
        self.assertEqual(
            runtime.DEFAULT_ACCEPTANCE_USER_DATA,
            parser.parse_args(["deploy"]).user_data,
        )
        before_args = parser.parse_args(["before-session", "R1"])
        self.assertEqual(runtime.DEFAULT_ACCEPTANCE_USER_DATA, before_args.user_data)
        self.assertEqual(runtime.DEFAULT_USER_DATA, before_args.daily_user_data)
        self.assertEqual(
            runtime.DEFAULT_ACCEPTANCE_USER_DATA,
            parser.parse_args(["configure-playset", "R1"]).user_data,
        )
        self.assertEqual(
            runtime.DEFAULT_ACCEPTANCE_USER_DATA,
            parser.parse_args(["install-fixtures"]).user_data,
        )
        with self.assertRaises(runtime.AcceptanceError):
            runtime._require_isolated_user_data(runtime.DEFAULT_USER_DATA)


if __name__ == "__main__":
    unittest.main()
