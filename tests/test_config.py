import os
import json
import tempfile
import unittest
from config import load_accounts, save_accounts, load_comments, save_comments, DEFAULT_COMMENTS


class TestConfig(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.TemporaryDirectory()
        self.acc_path = os.path.join(self.test_dir.name, "test_accounts.txt")
        self.cfg_path = os.path.join(self.test_dir.name, "test_config.json")
        self.com_path = os.path.join(self.test_dir.name, "test_comments.json")

    def tearDown(self):
        self.test_dir.cleanup()

    def test_load_accounts_from_file(self):
        """Verifies loading sessions from accounts.txt with comments and whitespace."""
        with open(self.acc_path, "w", encoding="utf-8") as f:
            f.write("# Header comment\n")
            f.write("\n")
            f.write("session_aaa_111\n")
            f.write("  session_bbb_222  \n")
            f.write("# Disabled session\n")
            f.write("session_aaa_111\n")  # duplicate

        sessions = load_accounts(accounts_path=self.acc_path, config_path=self.cfg_path)
        self.assertEqual(sessions, ["session_aaa_111", "session_bbb_222"])

    def test_fallback_to_config_json(self):
        """Verifies fallback to config.json when accounts.txt is missing."""
        with open(self.cfg_path, "w", encoding="utf-8") as f:
            json.dump({"sessions": ["json_sess_1", "json_sess_2"]}, f)

        sessions = load_accounts(accounts_path=self.acc_path, config_path=self.cfg_path)
        self.assertEqual(sessions, ["json_sess_1", "json_sess_2"])

    def test_save_and_reload_accounts(self):
        """Verifies saving and re-loading sessions."""
        test_sessions = ["alpha_1", "beta_2", "gamma_3"]
        save_accounts(test_sessions, accounts_path=self.acc_path, config_path=self.cfg_path)

        loaded = load_accounts(accounts_path=self.acc_path, config_path=self.cfg_path)
        self.assertEqual(loaded, test_sessions)

    def test_load_and_save_comments(self):
        """Verifies comment dictionary persistence and default creation."""
        # Non-existent file should generate defaults
        com = load_comments(comments_path=self.com_path)
        self.assertIn("RU", com)
        self.assertIn("UA", com)
        self.assertTrue(os.path.exists(self.com_path))

        # Custom comments save and reload
        custom = {"RU": ["{круто|топ} 🔥"]}
        save_comments(custom, comments_path=self.com_path)
        reloaded = load_comments(comments_path=self.com_path)
        self.assertEqual(reloaded, custom)


if __name__ == "__main__":
    unittest.main()
