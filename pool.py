import random
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
        self.sent_since_warmup = 0
        self.warmup_fails = 0

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

    def register_success(self, is_public: bool = False, is_shadow: bool = False, threshold: int = 15) -> bool:
        """
        Registers a successfully posted comment, tracks metrics, and triggers
        periodic organic micro-warmup (FYP scroll + like) and a natural rest cooldown.
        If warm_up fails:
        - 1st failure: sets sent_since_warmup back by 3 comments (soft buffer) so
          the account does not retry warm_up on every consecutive comment.
        - 2nd consecutive failure: places account on protective cooldown (180-300s)
          to avoid posting without organic warmup, resetting counter to 0.
        Returns True if phase maintenance was successfully completed.
        """
        self.sent_count += 1
        self.sent_since_warmup += 1
        if is_public:
            self.public_count += 1
        elif is_shadow:
            self.shadow_count += 1

        if self.sent_since_warmup >= threshold:
            logger.info(f"[{self.label}] Лимит активности ({self.sent_since_warmup} комментов). Запуск планового микро-прогрева...")
            warm_success = False
            try:
                stats = self.client.warm_up(min_videos=2, max_videos=3)
                if isinstance(stats, dict) and stats.get("watched", 0) > 0:
                    w = stats.get("watched", 0)
                    l = stats.get("liked", 0)
                    logger.info(f"[{self.label}] Микро-прогрев завершен: просмотрено {w} видео, {l} лайков.")
                    warm_success = True
                else:
                    logger.warning(f"[{self.label}] Микро-прогрев не вернул просмотров: {stats}")
            except Exception as e:
                logger.warning(f"[{self.label}] Исключение при выполнении микро-прогрева: {e}")

            if warm_success:
                self.sent_since_warmup = 0
                self.warmup_fails = 0
                rest_seconds = random.randint(300, 480)
                self.trigger_cooldown(rest_seconds, reason="Плановый органический отдых (режим 8-12ч)")
                return True
            else:
                self.warmup_fails += 1
                if self.warmup_fails >= 2:
                    logger.warning(
                        f"[{self.label}] Повторный сбой прогрева ({self.warmup_fails} подряд). "
                        "Запуск защитного отдыха во избежание спама без прогрева."
                    )
                    self.sent_since_warmup = 0
                    self.warmup_fails = 0
                    rest_seconds = random.randint(180, 300)
                    self.trigger_cooldown(rest_seconds, reason="Защитный отдых после неудачного прогрева")
                else:
                    retry_offset = 3 if threshold >= 5 else 1
                    self.sent_since_warmup = max(0, threshold - retry_offset)
                    logger.warning(
                        f"[{self.label}] Прогрев не удался (сбой #{self.warmup_fails}). Повтор через {retry_offset} коммент(а) "
                        f"(счётчик: {self.sent_since_warmup}/{threshold}), отдых отменён."
                    )
                return False
        return False


class AccountPool:
    def __init__(self, sessions: list) -> None:
        self.accounts = [Account(s, i + 1) for i, s in enumerate(sessions)]
        self.current_idx = 0

    @property
    def active_accounts(self) -> list:
        return [a for a in self.accounts if a.state not in (AccountState.INVALID, AccountState.DEAD)]

    def get_next_available(self) -> Account:
        """
        Retrieves the next ready account in round-robin sequence from active accounts.
        If all accounts are INVALID or DEAD, returns None immediately.
        If all active accounts are in cooldown, waits for the shortest cooldown to expire.
        Guarantees that an INVALID or DEAD account is NEVER returned.
        """
        active = self.active_accounts
        if not active:
            logger.critical("No valid/active accounts remaining in the carousel pool!")
            return None

        # Check only among active accounts in round-robin order
        for _ in range(len(active)):
            acc = active[self.current_idx % len(active)]
            self.current_idx = (self.current_idx + 1) % len(active)
            if acc.is_available:
                return acc

        # Re-check active accounts
        active = self.active_accounts
        if not active:
            logger.critical("No valid/active accounts remaining in the carousel pool!")
            return None

        # All active accounts are currently resting in cooldown
        shortest_acc = min(active, key=lambda a: a.cooldown_remaining)
        wait_time = shortest_acc.cooldown_remaining
        if wait_time > 0:
            logger.info(f"All {len(active)} active account(s) are resting. Waiting {wait_time + 1}s for {shortest_acc.label}...")
            time.sleep(wait_time + 1)

        # Ensure account is active and not INVALID or DEAD
        if shortest_acc.state in (AccountState.INVALID, AccountState.DEAD):
            active = self.active_accounts
            if not active:
                return None
            return self.get_next_available()

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
