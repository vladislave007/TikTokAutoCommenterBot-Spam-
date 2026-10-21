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

    def test_register_success_increments_counts(self):
        """Verifies that register_success correctly increments comment and visibility metrics."""
        acc = self.pool.accounts[0]
        acc.register_success(is_public=True, is_shadow=False, threshold=50)
        self.assertEqual(acc.sent_count, 1)
        self.assertEqual(acc.public_count, 1)
        self.assertEqual(acc.shadow_count, 0)
        self.assertEqual(acc.sent_since_warmup, 1)

        acc.register_success(is_public=False, is_shadow=True, threshold=50)
        self.assertEqual(acc.sent_count, 2)
        self.assertEqual(acc.public_count, 1)
        self.assertEqual(acc.shadow_count, 1)
        self.assertEqual(acc.sent_since_warmup, 2)

    def test_register_success_triggers_phase_maintenance(self):
        """Verifies that reaching threshold triggers organic re-warmup and rest cooldown."""
        acc = self.pool.accounts[0]
        with unittest.mock.patch.object(acc.client, "warm_up") as mock_warm:
            mock_warm.return_value = {"watched": 3, "liked": 1, "followed": 0}
            
            # Send up to threshold - 1
            triggered1 = acc.register_success(is_public=True, threshold=3)
            self.assertFalse(triggered1)
            self.assertEqual(acc.state, AccountState.READY)
            mock_warm.assert_not_called()

            triggered2 = acc.register_success(is_public=True, threshold=3)
            self.assertFalse(triggered2)
            mock_warm.assert_not_called()

            # 3rd comment reaches threshold of 3 -> triggers phase maintenance
            triggered3 = acc.register_success(is_public=True, threshold=3)
            self.assertTrue(triggered3)
            mock_warm.assert_called_once()
            self.assertEqual(acc.sent_since_warmup, 0)
            self.assertEqual(acc.state, AccountState.COOLDOWN)
            self.assertGreaterEqual(acc.cooldown_remaining, 299)

    def test_get_next_available_all_accounts_invalid_or_dead(self):
        """Verifies get_next_available returns None and never selects an invalid/dead account."""
        self.pool.accounts[0].state = AccountState.INVALID
        self.pool.accounts[1].state = AccountState.DEAD
        self.pool.accounts[2].state = AccountState.INVALID

        self.assertEqual(len(self.pool.active_accounts), 0)
        selected = self.pool.get_next_available()
        self.assertIsNone(selected)

    def test_register_success_warmup_exception_soft_backoff(self):
        """Verifies that 1st warm_up failure applies a 3-comment soft backoff without entering cooldown."""
        acc = self.pool.accounts[0]
        acc.sent_since_warmup = 14  # Next comment triggers threshold 15
        with unittest.mock.patch.object(acc.client, "warm_up") as mock_warm:
            mock_warm.side_effect = RuntimeError("TikTok API connection reset")

            triggered = acc.register_success(is_public=True, threshold=15)
            self.assertFalse(triggered)
            self.assertEqual(acc.warmup_fails, 1)
            self.assertEqual(acc.sent_since_warmup, 12)  # 15 - 3
            self.assertEqual(acc.state, AccountState.READY)
            self.assertEqual(acc.cooldown_remaining, 0)

    def test_register_success_warmup_zero_watched_soft_backoff(self):
        """Verifies that zero watched videos on 1st attempt applies soft backoff without cooldown."""
        acc = self.pool.accounts[0]
        acc.sent_since_warmup = 14
        with unittest.mock.patch.object(acc.client, "warm_up") as mock_warm:
            mock_warm.return_value = {"watched": 0, "liked": 0, "followed": 0}

            triggered = acc.register_success(is_public=True, threshold=15)
            self.assertFalse(triggered)
            self.assertEqual(acc.warmup_fails, 1)
            self.assertEqual(acc.sent_since_warmup, 12)  # 15 - 3
            self.assertEqual(acc.state, AccountState.READY)

    def test_register_success_warmup_consecutive_failures_triggers_protective_cooldown(self):
        """Verifies that 2 consecutive warm_up failures place the account on protective cooldown with immediate re-check offset."""
        acc = self.pool.accounts[0]
        acc.sent_since_warmup = 14
        with unittest.mock.patch.object(acc.client, "warm_up") as mock_warm:
            mock_warm.side_effect = RuntimeError("TikTok API connection reset")

            # 1st failure -> soft backoff to 12
            acc.register_success(is_public=True, threshold=15)
            self.assertEqual(acc.warmup_fails, 1)
            self.assertEqual(acc.sent_since_warmup, 12)
            self.assertEqual(acc.state, AccountState.READY)

            # Fast forward to 14, then trigger 2nd failure
            acc.sent_since_warmup = 14
            acc.register_success(is_public=True, threshold=15)

            # 2nd failure -> protective cooldown (180-300s), sent_since_warmup is 14 (re-checks immediately after 1 comment)
            self.assertEqual(acc.warmup_fails, 2)
            self.assertEqual(acc.sent_since_warmup, 14)
            self.assertEqual(acc.state, AccountState.COOLDOWN)
            self.assertGreaterEqual(acc.cooldown_remaining, 179)
            self.assertLessEqual(acc.cooldown_remaining, 301)

    def test_register_success_warmup_third_failure_triggers_long_cooldown(self):
        """Verifies that 3 consecutive failures trigger a long 15-minute protective cooldown."""
        acc = self.pool.accounts[0]
        acc.warmup_fails = 2
        acc.sent_since_warmup = 14
        with unittest.mock.patch.object(acc.client, "warm_up") as mock_warm:
            mock_warm.side_effect = RuntimeError("TikTok API connection reset")

            acc.register_success(is_public=True, threshold=15)

            # 3rd failure -> 900s cooldown, counters fully reset
            self.assertEqual(acc.warmup_fails, 0)
            self.assertEqual(acc.sent_since_warmup, 0)
            self.assertEqual(acc.state, AccountState.COOLDOWN)
            self.assertGreaterEqual(acc.cooldown_remaining, 899)
            self.assertLessEqual(acc.cooldown_remaining, 901)

    def test_register_success_counters_incremented_strictly_once(self):
        """Verifies that each call to register_success increments metrics strictly once."""
        acc = self.pool.accounts[0]
        self.assertEqual(acc.sent_count, 0)
        self.assertEqual(acc.public_count, 0)
        self.assertEqual(acc.shadow_count, 0)
        self.assertEqual(acc.sent_since_warmup, 0)

        acc.register_success(is_public=True, is_shadow=False, threshold=100)
        self.assertEqual(acc.sent_count, 1)
        self.assertEqual(acc.public_count, 1)
        self.assertEqual(acc.shadow_count, 0)
        self.assertEqual(acc.sent_since_warmup, 1)

        acc.register_success(is_public=False, is_shadow=True, threshold=100)
        self.assertEqual(acc.sent_count, 2)
        self.assertEqual(acc.public_count, 1)
        self.assertEqual(acc.shadow_count, 1)
        self.assertEqual(acc.sent_since_warmup, 2)

    def test_cooldown_expired_transitions_to_ready(self):
        """Verifies that once cooldown_until passes, is_available transitions account to READY."""
        acc = self.pool.accounts[0]
        acc.trigger_cooldown(seconds=500)
        self.assertEqual(acc.state, AccountState.COOLDOWN)
        self.assertFalse(acc.is_available)

        # Fast forward time past cooldown
        acc.cooldown_until = time.time() - 5
        self.assertTrue(acc.is_available)
        self.assertEqual(acc.state, AccountState.READY)


if __name__ == "__main__":
    unittest.main()
