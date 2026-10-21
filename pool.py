import time
from enum import Enum
from client import TikTokClient
from logger import logger


class AccountState(Enum):
    READY = "Ready"
    COOLDOWN = "Cooldown"
    INVALID = "Invalid"
    DEAD = "Dead"


class Account:
    def __init__(self, sessionid: str, index: int) -> None:
        self.sessionid = sessionid
        self.index = index
        self.label = f"Acc #{index} (...{sessionid[-6:]})" if len(sessionid) >= 6 else f"Acc #{index}"
        self.client = TikTokClient(sessionid)
        self.cooldown_until = 0
        self.state = AccountState.READY
        self.invalid_reason = ""
        self.username = ""
        
        # Stats tracking
        self.sent_count = 0
        self.fail_count = 0
        self.public_count = 0
        self.shadow_count = 0

    @property
    def is_available(self) -> bool:
        if self.state in (AccountState.INVALID, AccountState.DEAD):
            return False
        if time.time() >= self.cooldown_until:
            self.state = AccountState.READY
            return True
        return False

    @property
    def cooldown_remaining(self) -> int:
        return max(0, int(self.cooldown_until - time.time()))

    def trigger_cooldown(self, seconds: int = 600, reason: str = "Rate limit / spam") -> None:
        self.cooldown_until = time.time() + seconds
        self.state = AccountState.COOLDOWN
        logger.warning(f"[{self.label}] Placed on cooldown for {seconds}s: {reason}")

    def mark_invalid(self, reason: str = "Invalid or expired session") -> None:
        self.state = AccountState.INVALID
        self.invalid_reason = reason
        logger.error(f"[{self.label}] Marked as INVALID: {reason}")


class AccountPool:
    def __init__(self, sessions: list) -> None:
        self.accounts = [Account(s, i + 1) for i, s in enumerate(sessions)]
        self.current_idx = 0

    @property
    def active_accounts(self) -> list:
        return [a for a in self.accounts if a.state not in (AccountState.INVALID, AccountState.DEAD)]

    def get_next_available(self) -> Account:
        """
        Retrieves the next ready account in round-robin sequence.
        Skips invalid/dead accounts.
        If all active accounts are in cooldown, waits for the shortest cooldown to expire.
        """
        active = self.active_accounts
        if not active:
            logger.critical("No valid/active accounts remaining in the carousel pool!")
            return None

        # Check in round-robin order
        for _ in range(len(self.accounts)):
            acc = self.accounts[self.current_idx % len(self.accounts)]
            self.current_idx = (self.current_idx + 1) % len(self.accounts)
            if acc.is_available:
                return acc

        # All active accounts are currently resting
        shortest_acc = min(active, key=lambda a: a.cooldown_remaining)
        wait_time = shortest_acc.cooldown_remaining
        logger.info(f"All {len(active)} active account(s) are resting. Waiting {wait_time + 1}s for {shortest_acc.label}...")
        time.sleep(wait_time + 1)
        shortest_acc.state = AccountState.READY
        return shortest_acc

    def validate_all(self) -> None:
        """
        Validates all accounts in the pool against TikTok authentication.
        Distinguishes between definitive auth failures (401/403/expired) and
        transient issues (429 rate limit, 5xx server errors, network drops)
        so accounts are never disabled accidentally.
        """
        logger.info(f"Validating {len(self.accounts)} accounts against TikTok authentication...")
        for acc in self.accounts:
            res = acc.client.validate_session()
            if res.get("valid"):
                acc.username = res.get("username") or "User"
                logger.info(f"  • {acc.label}: Valid (@{acc.username})")
            elif res.get("is_temporary") or res.get("is_network_error"):
                # Network or TikTok service temporarily unreachable / rate limited: keep account active
                err_msg = res.get("error", "Temporary service issue")
                logger.warning(f"  • {acc.label}: Temporary issue ({err_msg}). Account remains active.")
            elif res.get("is_auth_error"):
                # Definitive authentication rejection
                err = res.get("error", "Authentication failed")
                acc.mark_invalid(err)
            else:
                # Fallback: keep active unless explicitly confirmed dead
                err = res.get("error", "Unverified session")
                logger.warning(f"  • {acc.label}: Unverified ({err}). Account remains active.")

    def print_summary(self) -> None:
        print(f"\n[+] Loaded {len(self.accounts)} TikTok Account(s) into Carousel:")
        for acc in self.accounts:
            user_tag = f" (@{acc.username})" if acc.username else ""
            if acc.state == AccountState.READY:
                status_str = "Ready"
            elif acc.state == AccountState.COOLDOWN:
                status_str = f"Cooldown ({acc.cooldown_remaining}s)"
            else:
                status_str = f"Disabled ({acc.invalid_reason or acc.state.value})"
            print(f"    • {acc.label}{user_tag} - Status: {status_str}")
        print("")
