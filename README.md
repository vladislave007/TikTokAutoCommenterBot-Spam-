<h1 align="center">
  🚀 TikTok Auto Commenter & Reply Bot
</h1>

<p align="center">
  <a href="https://github.com/vladislave007/TikTokAutoCommenterBot-Spam-/actions"><img src="https://github.com/vladislave007/TikTokAutoCommenterBot-Spam-/actions/workflows/tests.yml/badge.svg" alt="CI Tests"></a>
  <img src="https://img.shields.io/badge/Python-3.8+-3776AB?style=flat-square&logo=python&logoColor=white" alt="python">
  <img src="https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20macOS-blue?style=flat-square" alt="platform">
  <img src="https://img.shields.io/badge/Tests-49%20passed-brightgreen?style=flat-square" alt="tests">
  <img src="https://img.shields.io/badge/Signatures-Gorgon%20%7C%20Argus%20%7C%20Ladon-orange?style=flat-square" alt="signatures">
  <img src="https://img.shields.io/badge/Status-Working%202026-success?style=flat-square" alt="status">
  <img src="https://img.shields.io/badge/License-MIT-green?style=flat-square" alt="license">
</p>

<p align="center">
  An automated TikTok interaction script using TikTok's internal private mobile API. Powered by real-time signature generation (<b>Gorgon</b>, <b>Argus</b>, <b>Ladon</b>, <b>Khronos</b>), FYP feed discovery, and comment replying functionality.
</p>

---

## 🌟 Key Features

- 🔄 **Multi-Account Carousel (Round-Robin)**: Add 2, 5, or 20+ accounts to `accounts.txt`. The bot rotates through active accounts on each comment, distributing load across accounts. If an account is placed in cooldown, the bot continues with the remaining available accounts.
- 🛡️ **Spintax Permutation Engine**: Generates randomized comment variants using recursive `{option1|option2}` syntax and dynamic `@{user}` mention injection, reducing repetitive identical strings.
- ⚡ **Feed Browsing & Interaction Simulation**: Requests recommendation feed, pauses 2–4s per video, and can optionally submit likes (`commit/item/digg/`) and follows (`commit/follow/user/`) before commenting.
- ⏱️ **Configurable Phase Maintenance & Cooldowns**: Supports scheduled rest periods (cooldowns every N comments per account) and configurable delays between video feed requests.
- 🔍 **Smart Session Validation**: Checks accounts upon startup against TikTok authentication. Distinguishes between confirmed auth failures (401/403/expired) and transient issues (429 rate limit, 5xx server errors, network drops) so accounts are not disabled prematurely.
- 🔔 **Targeted Push Notification Replies**: Replies directly to existing comments under videos, triggering notifications for target comment authors.
- 🔀 **3 Operating Modes**:
  - **Mixed Mode (Recommended)**: Combines comment replies with video-level comments.
  - **Replies Only**: Focuses on replying to existing comments.
  - **Video Comments Only**: Posts direct comments on recommended videos.
- 📊 **Response Structure Verification**:
  - Requires non-empty comment ID (`cid`) in response body and records TikTok moderation status code (`status == 1` vs `status == 2`).
  - Centralized logging in console and `bot.log` with detailed diagnostics.
- 🧪 **Comprehensive Automated Test Suite & CI**: 49 automated unit tests executed via GitHub Actions CI covering mobile signing (Gorgon, Argus, Ladon), session validation edge cases, comment status confirmation, Spintax resolution, carousel rotation, cooldown recovery, and configuration fallback.

---

## 📁 Project Structure

```text
├── .github/workflows/   # Continuous Integration (automated tests on push & PR)
│   └── tests.yml        # GitHub Actions CI workflow (Python 3.10, 3.11, 3.12)
├── main.py              # Main entrypoint and carousel loop orchestrator
├── client.py            # TikTokClient network layer, mobile signing, and API interactions
├── pool.py              # Account, AccountPool, phase maintenance, and carousel state management
├── config.py            # Accounts & Spintax configuration loading and fallback
├── logger.py            # Centralized logging (console + bot.log)
├── spintax.py           # Recursive Spintax template engine and user mention injector
├── comments.json        # Clean Spintax comment templates (RU, UA, EN)
├── tests/               # Automated unit test suite (49 unit tests)
│   ├── test_client.py   # Comment verification, warm-up, and session validation tests
│   ├── test_pool.py     # Round-robin carousel, phase maintenance, cooldown, and edge-case tests
│   ├── test_gorgon.py   # Signature calculation and Gorgon.hash unit tests
│   ├── test_spintax.py  # Spintax resolution and username injection tests
│   └── test_config.py   # File loader and fallback configuration tests
├── requirements.txt     # Python package dependencies
├── run.bat              # 1-click Windows launcher
├── MedoSigner/          # Cryptographic signature algorithms (Gorgon, Argus, Ladon, Khronos)
├── .gitignore           # Keeps your credentials (config.json, accounts.txt) safe & private
└── README.md            # Project documentation
```

---

## ⚙️ Installation & Usage

### Option 1: Quick Start on Windows
1. Make sure you have [Python 3.8+](https://www.python.org/) installed.
2. Double-click **`run.bat`** (it will automatically install any missing dependencies, run the bot, and guide you).

### Option 2: Linux / macOS / Terminal
```bash
# 1. Clone the repository
git clone https://github.com/vladislave007/TikTokAutoCommenterBot-Spam-.git
cd TikTokAutoCommenterBot-Spam-

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run automated tests (optional, verify setup)
python -m unittest discover tests

# 4. Run the bot
python main.py
```

---

## 🧪 Running Automated Tests

The project includes 49 unit tests covering cryptographic signatures, session validation, comment verification, warm-up simulation, Spintax parsing, configuration loading, and account carousel logic:

```bash
python -m unittest discover tests -v
```

Expected output:
```text
Ran 49 tests in 0.15s
OK
```

---

## 🔑 How to Get Your TikTok `sessionid`

1. Open your desktop browser (Chrome, Edge, Opera, or Firefox) and log into your account on [tiktok.com](https://www.tiktok.com).
2. Press **`F12`** to open Developer Tools.
3. Go to the **Application** tab (or **Storage** in Firefox).
4. In the left sidebar, expand **Cookies** $\rightarrow$ click on `https://www.tiktok.com`.
5. Find the cookie named **`sessionid`** and copy its **Value** (a long alphanumeric string).
6. Add it to `accounts.txt` (one per line) or paste it into the bot prompt on first run.

---

## 📝 Customizing Spintax Comments

Open `comments.json` to customize your comment templates. The bot uses **Spintax** format `{synonym1|synonym2|...}` and automatically injects the target user's nickname via `@{user}`:

```json
{
  "RU": [
    "{хаха|ору|жесть|блин} {в точку|жиза|согласен|реально так} {😂|😭|🔥}",
    "@{user} {слушай|бро|друг}, {а ты реально так думаешь?|тоже это заметил?} 🤔"
  ],
  "EN": [
    "{haha|lmao|omg|bro} {this is so true|literally me|on point} {😂|💀|🔥}",
    "@{user} {honestly|wait}, {did you notice that too?|facts right there} 🤔"
  ]
}
```

Every response generated is unique, preventing duplicate spam triggers and keeping comments publicly visible!

---

## ⚠️ Disclaimer
*This tool is created for educational and research purposes only. Automation of social media accounts must comply with the platform's Terms of Service. The author is not responsible for any misuse, account restrictions, or bans resulting from the use of this tool.*

---

## 🤝 Contributing & License
Contributions, issues, and feature requests are welcome!  
Distributed under the MIT License.

