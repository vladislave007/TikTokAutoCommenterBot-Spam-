import os
import json
from logger import logger

ACCOUNTS_FILE = "accounts.txt"
CONFIG_FILE = "config.json"
COMMENTS_FILE = "comments.json"

DEFAULT_COMMENTS = {
    "RU": [
        "{хаха|ору|жесть|блин|ахах} {в точку|жиза|согласен|реально так|тоже так думал} {😂|😭|💀|🔥}",
        "@{user} {слушай|бро|друг}, {а ты реально так думаешь?|тоже это заметил?|серьезно?} 🤔",
        "{это просто|чисто|реально} {шедевр|разрыв|гениально|лучшее за сегодня} {👏|✨|🔥|🙌}",
        "@{user} {хах|ахах}, {я сначала даже не понял|у меня точно такая же реакция была} 😅",
        "{не ну это|честно говоря это|вообще-то это} {очень мощно|сильно сказано|чистая правда} 👍",
        "@{user} {поддерживаю|плюсую|факт|солидарен с тобой} {на все 100%|полностью} 🤝"
    ],
    "UA": [
        "{хаха|ору|жерсть|блін|ахах} {в точку|жиза|погоджуюсь|реально так|теж так думав} {😂|😭|💀|🔥}",
        "@{user} {слухай|бро|друже}, {а ти реально так думаєш?|теж це помітив?|серйозно?} 🤔",
        "{це просто|чисто|реально} {шедевр|розрив|геніально|найкраще за сьогодні} {👏|✨|🔥|🙌}",
        "@{user} {підтримую|плюсую|факт|солідарний з тобою} {на всі 100%|повністю} 🤝"
    ],
    "EN": [
        "{haha|lmao|omg|bro} {this is so true|literally me|on point|spot on} {😂|😭|💀|🔥}",
        "@{user} {listen|honestly|wait}, {did you notice that too?|facts right there} 🤔",
        "{this is pure|actually|literally} {gold|perfection|genius|top tier content} {👏|✨|🔥|🙌}",
        "@{user} {100% agree|valid point|spitting facts|well said} 🤝"
    ]
}


def load_accounts(accounts_path: str = ACCOUNTS_FILE, config_path: str = CONFIG_FILE) -> list:
    """
    Loads session IDs from accounts.txt with fallback to config.json.
    Deduplicates and skips commented or empty lines.
    """
    sessions = []

    # 1. Primary source: accounts.txt
    if os.path.exists(accounts_path):
        try:
            with open(accounts_path, "r", encoding="utf-8") as f:
                for line_num, line in enumerate(f, 1):
                    s = line.strip()
                    if s and not s.startswith("#"):
                        if s not in sessions:
                            sessions.append(s)
            if sessions:
                logger.info(f"Loaded {len(sessions)} session(s) from '{accounts_path}'.")
                return sessions
        except Exception as e:
            logger.error(f"Error reading '{accounts_path}': {e}")

    # 2. Fallback source: config.json
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as cf:
                cfg = json.load(cf)
                raw_sessions = cfg.get("sessions")
                if isinstance(raw_sessions, list):
                    sessions = [s.strip() for s in raw_sessions if s and s.strip()]
                elif cfg.get("sessionid"):
                    sessions = [cfg["sessionid"].strip()]
            if sessions:
                logger.info(f"Loaded {len(sessions)} session(s) from '{config_path}'.")
                return sessions
        except Exception as e:
            logger.error(f"Error reading '{config_path}': {e}")

    return sessions


def save_accounts(sessions: list, accounts_path: str = ACCOUNTS_FILE, config_path: str = CONFIG_FILE) -> bool:
    """Saves session IDs to accounts.txt and config.json safely."""
    if not sessions:
        return False

    success = True
    try:
        with open(accounts_path, "w", encoding="utf-8") as f:
            f.write("# TikTok Session IDs (one per line)\n\n")
            for s in sessions:
                f.write(s + "\n")
    except Exception as e:
        logger.error(f"Failed to write '{accounts_path}': {e}")
        success = False

    try:
        with open(config_path, "w", encoding="utf-8") as cf:
            json.dump({"sessions": sessions, "sessionid": sessions[0]}, cf, indent=4)
    except Exception as e:
        logger.error(f"Failed to write '{config_path}': {e}")
        success = False

    return success


def load_comments(comments_path: str = COMMENTS_FILE) -> dict:
    """
    Loads Spintax templates from comments.json.
    Creates default file if it doesn't exist.
    """
    if not os.path.exists(comments_path):
        logger.warning(f"'{comments_path}' not found. Creating default Spintax file...")
        save_comments(DEFAULT_COMMENTS, comments_path)
        return DEFAULT_COMMENTS

    try:
        with open(comments_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict) and data:
                return data
            else:
                logger.warning(f"Invalid format in '{comments_path}', resetting to defaults.")
                save_comments(DEFAULT_COMMENTS, comments_path)
                return DEFAULT_COMMENTS
    except Exception as e:
        logger.error(f"Error reading '{comments_path}': {e}. Using defaults.")
        return DEFAULT_COMMENTS


def save_comments(comments_dict: dict, comments_path: str = COMMENTS_FILE) -> bool:
    """Saves comments dictionary to comments.json with utf-8 formatting."""
    try:
        with open(comments_path, "w", encoding="utf-8") as f:
            json.dump(comments_dict, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        logger.error(f"Failed to save comments to '{comments_path}': {e}")
        return False
