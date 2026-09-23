import unittest

from services.replacement_parser import normalize_group_name
from services.text_utils import match_group_name


class GroupNameNormalizationTest(unittest.TestCase):
    def test_converts_latin_homoglyphs_to_cyrillic(self) -> None:
        self.assertEqual(normalize_group_name("OE-251"), "ОЕ-251")
        self.assertEqual(normalize_group_name("ME-231"), "МЕ-231")
        self.assertEqual(normalize_group_name("AT-233"), "АТ-233")

    def test_normalizes_spacing_and_missing_separator(self) -> None:
        self.assertEqual(normalize_group_name("  п і _ 231 "), "ПІ-231")
        self.assertEqual(normalize_group_name("ПОШ123"), "ПОШ-123")

    def test_normalizes_additional_latin_homoglyphs(self) -> None:
        self.assertEqual(normalize_group_name("VY-241"), "ВУ-241")

    def test_does_not_fuzzy_match_unrelated_group(self) -> None:
        matched, status, candidates = match_group_name("ПОШ-123", ["ОЕ-251", "МЕ-231"])
        self.assertIsNone(matched)
        self.assertEqual(status, "unmatched")
        self.assertEqual(candidates, [])


if __name__ == "__main__":
    unittest.main()