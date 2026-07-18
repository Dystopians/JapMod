from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from jxp_validation.chinese_compat import (
    COMPAT_DESCRIPTOR_NAME,
    COMPAT_DIRECTORY_NAME,
    DYNAMIC_TOKEN_HOTFIX_PATH,
    DYNAMIC_TOKEN_HOTFIX_VALUES,
    JAPANESE_HISTORY_TAGS,
    PINNED_LAUNCHER_SUPPORTED_VERSION,
    START_SCREEN_HOTFIX_PATH,
    START_SCREEN_MAIN_LOCALISATION_PATH,
    START_SCREEN_UI_FIELDS,
    audit_compat_clone,
    build_compat_clone,
)


REPO_ROOT = Path(__file__).resolve().parents[4]
ENCODER = REPO_ROOT / "skills/eu4-modding/scripts/encode_eu4_special_gameplay.py"


class ChineseCompatibilityCloneTests(unittest.TestCase):
    def test_clone_patches_every_conflict_and_canonicalizes_japanese_names(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "workshop"
            main = root / "main"
            map_mod = root / "map"
            game = root / "game"
            mod_root = root / "user" / "mod"
            target = mod_root / COMPAT_DIRECTORY_NAME
            outer = mod_root / COMPAT_DESCRIPTOR_NAME
            source.mkdir(parents=True)
            (source / "descriptor.mod").write_text(
                'name="source"\nversion="3.11.5"\n', encoding="utf-8"
            )
            (source / "thumbnail.png").write_bytes(b"fixture")
            tags: list[str] = []
            noncanonical = b'name = "\x10?e\x10\x19R"\n'
            for tag in sorted(JAPANESE_HISTORY_TAGS):
                country_name = f"{tag}.txt"
                tags.append(f'{tag} = "countries/{country_name}"')
                history_label = "Oda" if tag == "ODA" else tag
                history = source / "history" / "countries" / f"{tag} - {history_label}.txt"
                history.parent.mkdir(parents=True, exist_ok=True)
                history.write_bytes(noncanonical)
                country = source / "common" / "countries" / country_name
                country.parent.mkdir(parents=True, exist_ok=True)
                country.write_bytes(noncanonical)
            tag_file = game / "common" / "country_tags" / "00_countries.txt"
            tag_file.parent.mkdir(parents=True, exist_ok=True)
            tag_file.write_text("\n".join(tags) + "\n", encoding="utf-8")
            main_history = main / "history" / "countries" / "ODA - Oda.txt"
            main_history.parent.mkdir(parents=True, exist_ok=True)
            main_history.write_bytes(b'name = "Oda fixed"\n')
            main_mission = main / "missions" / "DOM_Japanese_Missions.txt"
            main_mission.parent.mkdir(parents=True, exist_ok=True)
            main_mission.write_bytes(b"disabled = yes\n")
            source_mission = source / "missions" / "DOM_Japanese_Missions.txt"
            source_mission.parent.mkdir(parents=True, exist_ok=True)
            source_mission.write_bytes(b"vanilla = yes\n")
            source_ideas = source / "common" / "ideas" / "00_country_ideas.txt"
            main_ideas = main / "common" / "ideas" / "00_country_ideas.txt"
            source_ideas.parent.mkdir(parents=True, exist_ok=True)
            main_ideas.parent.mkdir(parents=True, exist_ok=True)
            source_ideas.write_bytes(b"source_ideas = yes\n")
            main_ideas.write_bytes(b"jxp_ideas = yes\n")
            source_cultures = source / "common" / "cultures" / "00_cultures.txt"
            main_cultures = main / "common" / "cultures" / "00_cultures.txt"
            source_cultures.parent.mkdir(parents=True, exist_ok=True)
            main_cultures.parent.mkdir(parents=True, exist_ok=True)
            source_cultures.write_bytes(b"source_names = yes\n")
            main_cultures.write_bytes(b"jxp_names = yes\n")
            source_province_names = (
                source / "common" / "province_names" / "japanese_g.txt"
            )
            main_province_names = (
                main / "common" / "province_names" / "japanese_g.txt"
            )
            source_province_names.parent.mkdir(parents=True, exist_ok=True)
            main_province_names.parent.mkdir(parents=True, exist_ok=True)
            source_province_names.write_bytes(b"PROV1 = Source_Name\n")
            main_province_names.write_bytes(b"PROV1 = JXP_Name\n")
            main_start_screen = main / START_SCREEN_MAIN_LOCALISATION_PATH
            main_start_screen.parent.mkdir(parents=True, exist_ok=True)
            main_start_screen.write_text(
                "l_english:\n"
                + "\n".join(
                    f' {key}:0 "[{function_name}]"'
                    for key, function_name in START_SCREEN_UI_FIELDS
                )
                + "\n",
                encoding="utf-8-sig",
                newline="",
            )
            for number in range(48):
                name = f"{1000 + number} - Fixture.txt"
                source_path = source / "history" / "provinces" / name
                map_path = map_mod / "history" / "provinces" / name
                source_path.parent.mkdir(parents=True, exist_ok=True)
                map_path.parent.mkdir(parents=True, exist_ok=True)
                source_path.write_bytes(b"owner = ODA\n")
                map_path.write_bytes(b"owner = TOY\n")
            for number in range(17):
                name = f"{2000 + number} - Korea Fixture.txt"
                source_path = source / "history" / "provinces" / name
                main_path = main / "history" / "provinces" / name
                source_path.parent.mkdir(parents=True, exist_ok=True)
                main_path.parent.mkdir(parents=True, exist_ok=True)
                source_path.write_bytes(b"owner = KOR\ncontroller = ODA\n")
                main_path.write_bytes(b"owner = KOR\ncontroller = TOY\n")
            for name in (
                "SubjugationOfKyushu.txt",
                "SubjugationOfKanto.txt",
                "KoreanSevenYearsWar.txt",
                "SekigaharaCampaign.txt",
            ):
                source_path = source / "history" / "wars" / name
                main_path = main / "history" / "wars" / name
                source_path.parent.mkdir(parents=True, exist_ok=True)
                main_path.parent.mkdir(parents=True, exist_ok=True)
                source_path.write_bytes(b"add_attacker = ODA\n")
                main_path.write_bytes(b"add_attacker = TOY\n")

            built = build_compat_clone(
                source, target, outer, main, map_mod, game, ENCODER
            )
            self.assertEqual(74, built["patch_count"])
            self.assertEqual(39, built["canonical_history_files"])
            self.assertEqual(39, built["canonical_country_files"])
            for descriptor in (target / "descriptor.mod", outer):
                self.assertIn(
                    f'supported_version="{PINNED_LAUNCHER_SUPPORTED_VERSION}"',
                    descriptor.read_text(encoding="utf-8"),
                )
            self.assertEqual(
                b'name = "Oda fixed"\n',
                (target / "history/countries/ODA - Oda.txt").read_bytes(),
            )
            self.assertEqual(
                b"owner = TOY\n",
                (target / "history/provinces/1000 - Fixture.txt").read_bytes(),
            )
            self.assertEqual(
                b"jxp_ideas = yes\n",
                (target / "common/ideas/00_country_ideas.txt").read_bytes(),
            )
            self.assertEqual(
                b"jxp_names = yes\n",
                (target / "common/cultures/00_cultures.txt").read_bytes(),
            )
            self.assertEqual(
                b"PROV1 = JXP_Name\n",
                (target / "common/province_names/japanese_g.txt").read_bytes(),
            )
            self.assertNotEqual(
                noncanonical,
                (target / "common/countries/AKM.txt").read_bytes(),
            )
            manifest = json.loads(
                (target / ".jxp_compat_manifest.json").read_text(encoding="utf-8")
            )
            self.assertEqual(74, manifest["patch_count"])
            hotfix = (target / DYNAMIC_TOKEN_HOTFIX_PATH).read_bytes()
            self.assertTrue(hotfix.startswith(b"\xef\xbb\xbf"))
            self.assertEqual(
                len(DYNAMIC_TOKEN_HOTFIX_VALUES),
                hotfix.count(b"[Country.GetVaishyasName]"),
            )
            self.assertNotIn("Get\u5420\u820dName".encode("utf-8"), hotfix)
            start_screen_hotfix = (target / START_SCREEN_HOTFIX_PATH).read_bytes()
            self.assertTrue(start_screen_hotfix.startswith(b"\xef\xbb\xbf"))
            for key, function_name in START_SCREEN_UI_FIELDS:
                self.assertIn(
                    f' {key}:0 "[{function_name}]"'.encode("ascii"),
                    start_screen_hotfix,
                )
            self.assertEqual(
                len(START_SCREEN_UI_FIELDS), built["start_screen_hotfix_keys"]
            )
            audit = audit_compat_clone(
                source, target, outer, main, map_mod, game, ENCODER
            )
            self.assertEqual([], audit.issues, audit.to_dict())
            (target / DYNAMIC_TOKEN_HOTFIX_PATH).write_bytes(
                hotfix.replace(b"GetVaishyasName", b"GetBrokenName", 1)
            )
            mutated = audit_compat_clone(
                source, target, outer, main, map_mod, game, ENCODER
            )
            self.assertIn(
                "chinese_compat.dynamic_token_hotfix",
                {issue.code for issue in mutated.issues},
            )
            (target / START_SCREEN_HOTFIX_PATH).write_bytes(
                start_screen_hotfix.replace(
                    b"JxpStartScreenTitle", b"BrokenStartScreenTitle", 1
                )
            )
            mutated = audit_compat_clone(
                source, target, outer, main, map_mod, game, ENCODER
            )
            self.assertIn(
                "chinese_compat.start_screen_hotfix",
                {issue.code for issue in mutated.issues},
            )


if __name__ == "__main__":
    unittest.main()
