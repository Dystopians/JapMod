from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from jxp_runtime_acceptance import runtime_acceptance as runtime


LIVE_REPO = Path(__file__).resolve().parents[4]


def _write(path: Path, text: str = "payload\n") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _component(root: Path, key: str = "main") -> runtime.Component:
    source = root / f"source-{key}"
    for directory in runtime.RUNTIME_DIRECTORIES[key]:
        _write(source / directory / "payload.txt")
    descriptor = 'supported_version="1.37.*"\nversion="0.28.0"\n'
    _write(source / "descriptor.mod", descriptor)
    (source / "thumbnail.png").write_bytes(b"png")
    outer = root / f"{key}.mod"
    _write(outer, 'name="fixture"\nversion="0.28.0"\n')
    _write(source / "tools" / "must-not-deploy.py")
    _write(source / "dev_logs" / "must-not-deploy.md")
    _write(source / "localisation_source" / "must-not-deploy.yml")
    _write(source / "AGENTS.md")
    _write(source / "thumbnail_imagegen_source.png")
    return runtime.Component(key, source, outer)


class RuntimeAcceptanceTests(unittest.TestCase):
    def test_matrix_covers_every_runtime_batch_and_open_todo(self) -> None:
        matrix = json.loads(
            (Path(runtime.__file__).with_name("runtime_scenarios.json")).read_text(
                encoding="utf-8"
            )
        )
        scenarios = matrix["scenarios"]
        self.assertEqual([f"R{number}" for number in range(1, 14)], [item["id"] for item in scenarios])
        covered = {todo for item in scenarios for todo in item["todos"]}
        self.assertEqual(
            {
                "JXP-001",
                "JXP-002",
                "JXP-004",
                "JXP-005",
                "JXP-008",
                "JXP-009",
                "JXP-010",
                "JXP-016",
                "JXP-017",
                "JXP-018",
                "JXP-020",
                "JXP-022",
                "JXP-023",
            },
            covered,
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

    def test_before_session_requires_exact_isolated_playset(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            user_data = Path(temporary)
            descriptor = user_data / "mod" / "jxp-current.mod"
            _write(descriptor, 'name="JXP"\n')
            _write(
                user_data / "dlc_load.json",
                json.dumps({"enabled_mods": ["mod/jxp-current.mod"], "disabled_dlcs": []}),
            )
            _write(user_data / "logs" / "error.log", "old baseline\n")
            with patch.object(runtime, "_assert_processes_stopped"):
                result = runtime.before_session(
                    user_data, "R1", None, [descriptor]
                )
            session = Path(result["session"])
            self.assertTrue((session / "session.json").is_file())
            record = json.loads((session / "session.json").read_text(encoding="utf-8"))
            self.assertEqual("R1", record["scenario"]["id"])
            self.assertFalse(record["game_started_by_tool"])

            _write(
                user_data / "dlc_load.json",
                json.dumps(
                    {
                        "enabled_mods": [
                            "mod/jxp-current.mod",
                            "mod/ugc_253263609.mod",
                        ],
                        "disabled_dlcs": [],
                    }
                ),
            )
            with patch.object(runtime, "_assert_processes_stopped"):
                with self.assertRaises(runtime.AcceptanceError):
                    runtime.before_session(user_data, "R1", None, [descriptor])

    def test_collect_flags_release_blockers(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            user_data = Path(temporary)
            descriptor = user_data / "mod" / "jxp-current.mod"
            _write(descriptor, 'name="JXP"\n')
            _write(
                user_data / "dlc_load.json",
                json.dumps({"enabled_mods": ["mod/jxp-current.mod"], "disabled_dlcs": []}),
            )
            _write(user_data / "logs" / "error.log", "baseline\n")
            with patch.object(runtime, "_assert_processes_stopped"):
                before = runtime.before_session(user_data, "R1", None, [descriptor])
            _write(
                user_data / "logs" / "error.log",
                "[effectimplementation.cpp] Unknown effect type: jxp_bad\n"
                "[mission.cpp:353] collision\n",
            )
            with patch.object(runtime, "_assert_processes_stopped"):
                result, passed = runtime.collect(Path(before["session"]), [])
            self.assertFalse(passed)
            self.assertTrue(
                {"unknown_effect", "mission_collision"}.issubset(
                    {item["code"] for item in result["blockers"]}
                )
            )
            self.assertTrue(
                (Path(before["session"]) / "collection.json").is_file()
            )

    def test_cli_deliberately_has_no_launch_command(self) -> None:
        parser = runtime._parser()
        choices = parser._subparsers._group_actions[0].choices
        self.assertEqual(
            {"preflight", "deploy", "before-session", "collect"}, set(choices)
        )


if __name__ == "__main__":
    unittest.main()
