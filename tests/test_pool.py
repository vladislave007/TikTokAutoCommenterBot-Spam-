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


if __name__ == "__main__":
    unittest.main()
