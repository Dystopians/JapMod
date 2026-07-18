from __future__ import annotations

from collections import Counter
import importlib.util
from pathlib import Path
import re
import sys
import unittest

from jxp_validation.clausewitz import parse_text


MAIN_ROOT = Path(__file__).resolve().parents[3]
REPO_ROOT = MAIN_ROOT.parent
TOOLS_ROOT = MAIN_ROOT / "tools"
if str(TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(TOOLS_ROOT))

from jxp_runtime_acceptance import runtime_acceptance as runtime


BUILDER_PATH = (
    MAIN_ROOT / "tools/jxp_a_content_builder/build_start_screen.py"
)
GAME_ROOT = Path(r"D:\Steam\steamapps\common\Europa Universalis IV")

spec = importlib.util.spec_from_file_location("_jxp_start_screen_builder", BUILDER_PATH)
if spec is None or spec.loader is None:
    raise RuntimeError("cannot load Japanese start-screen builder")
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


class JapaneseStartScreenTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.plan = builder.load_plan()
        cls.daimyo = cls.plan["daimyo"]
        cls.records = builder._house_records(cls.plan)
        cls.custom_path = builder.CUSTOMISABLE_PATH
        cls.source_path = builder.SOURCE_PATH
        cls.active_path = builder.ACTIVE_PATH
        cls.custom = cls.custom_path.read_text(encoding="utf-8")
        cls.source = cls.source_path.read_text(encoding="utf-8")

    def test_authority_covers_every_house_and_toyotomi(self) -> None:
        builder.validate_plan(self.plan)
        self.assertEqual(67, len(self.daimyo))
        self.assertEqual(
            Counter({"main": 37, "map": 30}),
            Counter(record["surface"] for record in self.daimyo),
        )
        self.assertEqual(68, len(self.records))
        self.assertEqual("TOY", self.records[-1]["tag"])
        self.assertEqual(68, len({record["tag"] for record in self.records}))

        chronicles = [builder.house_chronicle(record) for record in self.records]
        counsels = [builder.house_counsel(record) for record in self.records]
        self.assertEqual(68, len(set(chronicles)))
        self.assertEqual(68, len(set(counsels)))
        self.assertGreaterEqual(min(map(len, chronicles)), 125)
        self.assertGreaterEqual(min(map(len, counsels)), 100)
        for banned in (
            "militancy",
            "动态强邻",
            "历史盟友灭亡",
            "动态替代",
            "互斥终局",
            "全国遗产",
            "三选一",
            "长期不同",
        ):
            self.assertNotIn(banned, "\n".join(chronicles + counsels))

    def test_generated_outputs_are_exact_and_encoded_for_eu4(self) -> None:
        outputs = builder.render_outputs(self.plan)
        for path, expected in outputs.items():
            actual = (
                path.read_bytes()
                if isinstance(expected, bytes)
                else path.read_text(encoding="utf-8")
            )
            self.assertEqual(expected, actual, path)

        custom_bytes = self.custom_path.read_bytes()
        active_bytes = self.active_path.read_bytes()
        self.assertFalse(custom_bytes.startswith(b"\xef\xbb\xbf"))
        self.assertEqual(self.custom, custom_bytes.decode("ascii"))
        self.assertTrue(active_bytes.startswith(b"\xef\xbb\xbf"))
        self.assertIsNone(
            re.search(r"[\u3400-\u9fff]", active_bytes.decode("utf-8-sig"))
        )

    def test_clausewitz_functions_and_vanilla_fallbacks_are_safe(self) -> None:
        parse_text(self.custom, self.custom_path)
        names = re.findall(r"(?m)^\s*name\s*=\s*(JxpStart[A-Za-z]+)$", self.custom)
        self.assertEqual(19, len(names))
        self.assertEqual(len(names), len(set(names)))

        for ui_key, jxp_name, vanilla_name, suffix in builder.UI_FIELDS:
            self.assertEqual(
                1,
                self.source.count(f' {ui_key}:0 "[{jxp_name}]"'),
            )
            self.assertEqual(
                1,
                self.source.count(
                    f' jxp_start_vanilla_{suffix}:0 "[Root.{vanilla_name}]"'
                ),
            )
        self.assertNotIn("[Root.JxpStartScreen", self.source)
        self.assertNotIn("localisation_key = START_SCREEN_", self.custom)

    def test_house_age_and_government_branches_are_complete(self) -> None:
        generic_index = self.custom.index("jxp_start_house_generic_chronicle")
        for record in self.records:
            tag = record["tag"]
            if record["surface"] == "main":
                needle = f"tag = {tag}"
            else:
                needle = f"has_country_flag = jxp_map_origin_{tag.lower()}"
                self.assertNotRegex(self.custom, rf"(?m)^\s*tag\s*=\s*{tag}\s*$")
            self.assertEqual(2, self.custom.count(needle), tag)
            self.assertLess(self.custom.index(needle), generic_index, tag)
            for suffix in ("chronicle", "counsel"):
                self.assertEqual(
                    1,
                    self.source.count(f" jxp_start_house_{tag.lower()}_{suffix}:0 "),
                    (tag, suffix),
                )

        for era in builder.ERAS:
            self.assertEqual(
                7,
                self.custom.count(f"current_age = {era['trigger']}"),
                era["id"],
            )
            for suffix in (
                "name",
                "lead",
                "overview",
                "faith",
                "role_shogunate",
                "role_daimyo",
                "role_realm",
            ):
                self.assertIn(f"jxp_start_age_{era['id']}_{suffix}", self.source)

        self.assertEqual(7, self.custom.count(builder.DAIMYO_REFORM_TRIGGER))
        self.assertNotIn("jxp_is_daimyo_stage_trigger", self.custom)
        self.assertIn("[Root.JxpStartAgeLead]", self.source)
        self.assertIn("religion = jodo_shinshu", self.custom)
        self.assertIn("jxp_start_doctrine_jodo_shinshu", self.source)
        self.assertIn("jxp_start_house_toy_chronicle", self.source)

    def test_runtime_snapshot_keeps_customisable_localisation(self) -> None:
        self.assertIn("customizable_localization", runtime.RUNTIME_DIRECTORIES["main"])

    def test_pinned_vanilla_contract_is_still_present(self) -> None:
        if not GAME_ROOT.is_dir():
            self.skipTest("EU4 1.37.5 game root is unavailable")
        builder.validate_vanilla(GAME_ROOT)
        vanilla = (GAME_ROOT / builder.VANILLA_CUSTOMISABLE_RELATIVE).read_text(
            encoding="utf-8-sig"
        )
        for _ui_key, _jxp_name, vanilla_name, _suffix in builder.UI_FIELDS:
            self.assertEqual(1, vanilla.count(f"name = {vanilla_name}"))


if __name__ == "__main__":
    unittest.main()
