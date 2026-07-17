from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest


REPO_ROOT = Path(__file__).resolve().parents[4]
VALIDATOR_PATH = (
    REPO_ROOT
    / "japan_expanded_v2_map/tools/jxp_map_validation/validate_history.py"
)


def _load_validator():
    module_name = "_jxp_map_country_name_validation_test"
    spec = importlib.util.spec_from_file_location(module_name, VALIDATOR_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load map validator: {VALIDATOR_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


class MapCountryNamePoolTests(unittest.TestCase):
    def test_generated_ship_pool_and_short_pool_mutation(self) -> None:
        validator = _load_validator()
        report = validator.Report()
        suffixes = validator.read_builder_ship_name_suffixes(report)
        names = validator.expected_map_ship_names(
            {"name": "Rokkaku", "tag": "RKK"}, suffixes
        )
        self.assertEqual(32, len(suffixes))
        self.assertEqual(32, len(names))
        self.assertEqual([], report.errors)

        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "short.txt"
            path.write_text(
                "ship_names = {\n\t"
                + " ".join(f'\"Ship {index}\"' for index in range(10))
                + "\n}\n",
                encoding="cp1252",
            )
            mutated = validator.Report()
            validator.validate_country_ship_names(path, names, "BAD", mutated)
            self.assertTrue(mutated.errors)


if __name__ == "__main__":
    unittest.main()
