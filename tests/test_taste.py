import unittest

from _module_loader import load_script_module

utils = load_script_module("utils.py", "utils_taste")
TASTE = utils.load_taste()


class TestTaste(unittest.TestCase):
    def test_lanes_match_registries(self) -> None:
        for lane, spec in TASTE["lanes"].items():
            module = load_script_module(spec["script"], f"taste_{lane}")
            with self.subTest(lane=lane):
                self.assertEqual(set(spec["kept"]), set(module.STYLES))
                self.assertFalse(set(spec["cut"]) & set(module.STYLES))


if __name__ == "__main__":
    unittest.main()
