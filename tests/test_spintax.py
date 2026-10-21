import unittest
from spintax import spin


class TestSpintax(unittest.TestCase):
    def test_empty_template(self):
        """Verifies handling of empty or None templates."""
        self.assertEqual(spin(""), "")
        self.assertEqual(spin(None), "")

    def test_plain_text(self):
        """Verifies plain text without brackets remains intact."""
        text = "Hello world! Great video."
        self.assertEqual(spin(text), text)

    def test_single_spintax_group(self):
        """Verifies simple {a|b} resolution selects one of the options."""
        template = "{красиво|отлично|супер}"
        options = {"красиво", "отлично", "супер"}
        results = set()
        for _ in range(50):
            res = spin(template)
            self.assertIn(res, options)
            results.add(res)
        # With 50 trials, all 3 options should be hit
        self.assertEqual(results, options)

    def test_nested_spintax(self):
        """Verifies nested {a|{b|c}} constructs resolve properly."""
        template = "{привет|{здравствуйте|добрый день}}"
        valid_options = {"привет", "здравствуйте", "добрый день"}
        for _ in range(30):
            res = spin(template)
            self.assertIn(res, valid_options)

    def test_user_replacement(self):
        """Verifies that @{user} and {user} placeholders are cleanly replaced."""
        template = "@{user} {согласен|плюсую}"
        res = spin(template, target_user="Maksym_99")
        self.assertTrue(res.startswith("@Maksym_99 "))
        self.assertIn(res.split(" ")[1], ["согласен", "плюсую"])

    def test_user_with_at_symbol(self):
        """Verifies that user already having @ does not result in @@."""
        template = "@{user} привет!"
        res = spin(template, target_user="@Dmitry")
        self.assertEqual(res, "@Dmitry привет!")

    def test_missing_user_cleans_placeholder(self):
        """Verifies that when target_user is None or empty, the placeholder is removed without stray @."""
        template = "@{user} отличное видео!"
        res = spin(template, target_user=None)
        self.assertEqual(res, "отличное видео!")

    def test_whitespace_normalization(self):
        """Verifies that double spaces are normalized to a single space."""
        template = "  {слово1|слово2}   {слово3|слово4}  "
        res = spin(template)
        self.assertNotIn("  ", res)
        self.assertFalse(res.startswith(" "))
        self.assertFalse(res.endswith(" "))


if __name__ == "__main__":
    unittest.main()
