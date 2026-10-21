import time
import unittest
from pool import Account, AccountPool, AccountState


class TestAccountPool(unittest.TestCase):
    def setUp(self):
        self.sessions = ["sess_1_111111", "sess_2_222222", "sess_3_333333"]
        self.pool = AccountPool(self.sessions)

    def test_initial_pool_state(self):
        """Verifies that all accounts are initially Ready and indexed properly."""
        self.assertEqual(len(self.pool.accounts), 3)
        for i, acc in enumerate(self.pool.accounts, 1):
            self.assertEqual(acc.index, i)
            self.assertTrue(acc.is_available)
            self.assertEqual(acc.state, AccountState.READY)

    def test_round_robin_sequence(self):
        """Verifies that get_next_available cycles in round-robin order."""
        acc1 = self.pool.get_next_available()
        acc2 = self.pool.get_next_available()
        acc3 = self.pool.get_next_available()
        acc4 = self.pool.get_next_available()

        self.assertEqual(acc1.index, 1)
        self.assertEqual(acc2.index, 2)
        self.assertEqual(acc3.index, 3)
        self.assertEqual(acc4.index, 1)

    def test_cooldown_skipping(self):
        """Verifies that an account placed on cooldown is skipped."""
        self.pool.accounts[0].trigger_cooldown(seconds=300)
        self.assertFalse(self.pool.accounts[0].is_available)

        # Next available should be account 2, then 3, then 2 again
        next_acc = self.pool.get_next_available()
        self.assertEqual(next_acc.index, 2)

    def test_mark_invalid(self):
        """Verifies that an invalid/dead account is permanently removed from active selection."""
        self.pool.accounts[1].mark_invalid("Session expired test")
        self.assertEqual(self.pool.accounts[1].state, AccountState.INVALID)
        self.assertFalse(self.pool.accounts[1].is_available)
        self.assertEqual(len(self.pool.active_accounts), 2)

        # Iterating should only yield accounts 1 and 3
        seen_indices = {self.pool.get_next_available().index for _ in range(6)}
        self.assertEqual(seen_indices, {1, 3})

    def test_validate_all_valid_session(self):
        """Verifies that a valid session sets username and keeps account READY."""
        with unittest.mock.patch.object(self.pool.accounts[0].client, "validate_session") as mock_val:
            mock_val.return_value = {
                "valid": True,
                "username": "tiktok_pro",
                "is_auth_error": False,
                "is_temporary": False
            }
            # Only validate account 0
            single_pool = AccountPool(["sess_mock_valid"])
            single_pool.accounts[0].client.validate_session = mock_val
            single_pool.validate_all()

            self.assertEqual(single_pool.accounts[0].state, AccountState.READY)
            self.assertEqual(single_pool.accounts[0].username, "tiktok_pro")
            self.assertTrue(single_pool.accounts[0].is_available)

    def test_validate_all_temporary_error_keeps_account_active(self):
        """Verifies that 429, 5xx, or network errors DO NOT mark the account INVALID."""
        with unittest.mock.patch.object(self.pool.accounts[0].client, "validate_session") as mock_val:
            mock_val.return_value = {
                "valid": False,
                "error": "HTTP 429 Rate Limited",
                "is_auth_error": False,
                "is_temporary": True
            }
            single_pool = AccountPool(["sess_mock_temp"])
            single_pool.accounts[0].client.validate_session = mock_val
            single_pool.validate_all()

            # Account MUST remain READY, not disabled
            self.assertEqual(single_pool.accounts[0].state, AccountState.READY)
            self.assertTrue(single_pool.accounts[0].is_available)
            self.assertEqual(len(single_pool.active_accounts), 1)

    def test_validate_all_auth_error_marks_invalid(self):
        """Verifies that confirmed 401/403 or expired session marks the account INVALID."""
        with unittest.mock.patch.object(self.pool.accounts[0].client, "validate_session") as mock_val:
            mock_val.return_value = {
                "valid": False,
                "error": "HTTP 401 Unauthorized",
                "is_auth_error": True,
                "is_temporary": False
            }
            single_pool = AccountPool(["sess_mock_auth_fail"])
            single_pool.accounts[0].client.validate_session = mock_val
            single_pool.validate_all()

            self.assertEqual(single_pool.accounts[0].state, AccountState.INVALID)
            self.assertFalse(single_pool.accounts[0].is_available)
            self.assertEqual(len(single_pool.active_accounts), 0)


if __name__ == "__main__":
    unittest.main()
