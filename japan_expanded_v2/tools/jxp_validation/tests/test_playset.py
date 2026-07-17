from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from jxp_validation.playset import audit_active_playset


def _write(path: Path, payload: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload, encoding="cp1252", newline="")


def _write_bytes(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)


EAST_SEA = "\x10\x1cN\x10wm"
TOKAIDO = EAST_SEA + "\x10S\x90"


def _area_localisation(key: str, escaped_label: str) -> bytes:
    return (
        f"\ufeffl_english:\n {key}:0 \"{escaped_label}\"\n"
    ).encode("utf-8")


def _descriptor(path: Path, root: Path) -> None:
    _write(path, f'name="fixture"\npath="{root.as_posix()}"\n')


def _province(owner_1444: str, owner_1598: str) -> str:
    return (
        f"owner = {owner_1444}\ncontroller = {owner_1444}\n"
        "1586.1.1 = {\n\towner = TOY\n\tcontroller = TOY\n}\n"
        f"1590.1.1 = {{\n\towner = {owner_1598}\n\tcontroller = {owner_1598}\n}}\n"
        "1600.10.21 = {\n\towner = TKG\n\tcontroller = TKG\n}\n"
    )


class ActivePlaysetTests(unittest.TestCase):
    def _fixture(self, root: Path) -> tuple[Path, Path, Path, Path]:
        user = root / "user"
        game = root / "game"
        repo_main = root / "repo-main"
        repo_map = root / "repo-map"
        live_main = root / "live-main"
        live_map = root / "live-map"
        translation = root / "translation"
        relative = Path("history/provinces/1030 - Owari.txt")
        _write(repo_map / relative, _province("ODA", "TOY"))
        _write(live_map / relative, _province("ODA", "TOY"))
        _write(translation / relative, _province("ODA", "TOY"))
        _write(repo_main / "history/countries/ODA - Oda.txt", "government = monarchy\n")
        _write(live_main / "history/countries/ODA - Oda.txt", "government = monarchy\n")
        _write(translation / "history/countries/ODA - Oda.txt", "government = monarchy\n")
        for name, payload in (
            ("generate_visualizer.py", b"generator\n"),
            ("jxp_visualizer.html", b"<html>review</html>\n"),
            ("test_generate_visualizer.py", b"tests\n"),
        ):
            relative_artifact = Path("tools/jxp_visualizer") / name
            _write_bytes(repo_main / relative_artifact, payload)
            _write_bytes(live_main / relative_artifact, payload)
        area = "jxp_tokai_area = {\n\t1030\n}\n"
        _write(repo_map / "map/area.txt", area)
        _write(live_map / "map/area.txt", area)
        _write_bytes(
            repo_map / "localisation/jxp_map_l_english.yml",
            _area_localisation("jxp_tokai_area", TOKAIDO),
        )
        _write_bytes(
            live_map / "localisation/jxp_map_l_english.yml",
            _area_localisation("jxp_tokai_area", TOKAIDO),
        )
        _write_bytes(
            game / "localisation/areas_l_english.yml",
            _area_localisation("east_china_sea_area", EAST_SEA),
        )
        descriptors = {
            "mod/japan_expanded_v2_map.mod": live_map,
            "mod/japan_expanded_v2.mod": live_main,
            "mod/translation.mod": translation,
        }
        for reference, payload_root in descriptors.items():
            _descriptor(user.joinpath(*Path(reference).parts), payload_root)
        return user, game, repo_main, repo_map

    def test_convergent_translation_passes_in_any_order(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            user, game, repo_main, repo_map = self._fixture(Path(temporary))
            _write(
                user / "dlc_load.json",
                json.dumps(
                    {
                        "enabled_mods": [
                            "mod/translation.mod",
                            "mod/japan_expanded_v2.mod",
                            "mod/japan_expanded_v2_map.mod",
                        ],
                        "disabled_dlcs": [],
                    }
                ),
            )
            result = audit_active_playset(user, game, repo_main, repo_map)
            self.assertEqual([], result.issues, result.to_dict())
            self.assertEqual(1, result.metrics["custom_area_keys"])
            self.assertEqual(0, result.metrics["custom_area_label_collisions"])
            self.assertEqual(3, result.metrics["current_review_artifacts"])

    def test_divergent_translation_reproduces_dual_identity_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            user, game, repo_main, repo_map = self._fixture(Path(temporary))
            _write(
                root := Path(temporary) / "translation" / "history/provinces/1030 - Owari.txt",
                _province("ODA", "ODA"),
            )
            _write(
                user / "dlc_load.json",
                json.dumps(
                    {
                        "enabled_mods": [
                            "mod/translation.mod",
                            "mod/japan_expanded_v2.mod",
                            "mod/japan_expanded_v2_map.mod",
                        ],
                        "disabled_dlcs": [],
                    }
                ),
            )
            result = audit_active_playset(user, game, repo_main, repo_map)
            codes = {issue.code for issue in result.issues}
            self.assertIn("playset.conflict_divergence", codes)
            self.assertIn("playset.post_handoff_oda_provider", codes)

    def test_duplicate_decoded_custom_area_label_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            user, game, repo_main, repo_map = self._fixture(Path(temporary))
            duplicate = _area_localisation("jxp_tokai_area", EAST_SEA)
            _write_bytes(repo_map / "localisation/jxp_map_l_english.yml", duplicate)
            _write_bytes(
                Path(temporary) / "live-map/localisation/jxp_map_l_english.yml",
                duplicate,
            )
            _write(
                user / "dlc_load.json",
                json.dumps(
                    {
                        "enabled_mods": [
                            "mod/translation.mod",
                            "mod/japan_expanded_v2.mod",
                            "mod/japan_expanded_v2_map.mod",
                        ],
                        "disabled_dlcs": [],
                    }
                ),
            )
            result = audit_active_playset(user, game, repo_main, repo_map)
            codes = {issue.code for issue in result.issues}
            self.assertIn("playset.area_localisation_collision", codes)
            self.assertEqual(1, result.metrics["custom_area_label_collisions"])

    def test_obsolete_deployed_runtime_file_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            user, game, repo_main, repo_map = self._fixture(Path(temporary))
            _write(
                Path(temporary)
                / "live-main/common/ideas/00_0_jxp_obsolete_ideas.txt",
                "obsolete_ideas = { free = yes }\n",
            )
            _write(
                user / "dlc_load.json",
                json.dumps(
                    {
                        "enabled_mods": [
                            "mod/translation.mod",
                            "mod/japan_expanded_v2.mod",
                            "mod/japan_expanded_v2_map.mod",
                        ],
                        "disabled_dlcs": [],
                    }
                ),
            )
            result = audit_active_playset(user, game, repo_main, repo_map)
            self.assertIn(
                "playset.deployed_orphan",
                {issue.code for issue in result.issues},
            )

    def test_missing_deployed_visualizer_artifact_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            user, game, repo_main, repo_map = self._fixture(Path(temporary))
            (Path(temporary) / "live-main/tools/jxp_visualizer/jxp_visualizer.html").unlink()
            _write(
                user / "dlc_load.json",
                json.dumps(
                    {
                        "enabled_mods": [
                            "mod/translation.mod",
                            "mod/japan_expanded_v2.mod",
                            "mod/japan_expanded_v2_map.mod",
                        ],
                        "disabled_dlcs": [],
                    }
                ),
            )
            result = audit_active_playset(user, game, repo_main, repo_map)
            self.assertIn(
                "playset.review_artifact_stale",
                {issue.code for issue in result.issues},
            )


if __name__ == "__main__":
    unittest.main()
