<h1 align="center">
  🚀 TikTok Auto Commenter & Reply Bot
</h1>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.8+-3776AB?style=flat-square&logo=python&logoColor=white" alt="python">
  <img src="https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20macOS-blue?style=flat-square" alt="platform">
  <img src="https://img.shields.io/badge/Signatures-Gorgon%20%7C%20Argus%20%7C%20Ladon-orange?style=flat-square" alt="signatures">
  <img src="https://img.shields.io/badge/Status-Working%202026-success?style=flat-square" alt="status">
  <img src="https://img.shields.io/badge/License-MIT-green?style=flat-square" alt="license">
</p>

<p align="center">
  An advanced, automated TikTok marketing and interaction bot using TikTok's internal private mobile API. Powered by real-time signature generation (<b>Gorgon</b>, <b>Argus</b>, <b>Ladon</b>, <b>Khronos</b>), FYP feed discovery, and an intelligent reply mode that triggers <b>direct mobile push notifications</b> to users.
</p>

---

## 🌟 Key Features

- 🔥 **Real FYP (For You Page) Feed**: Automatically discovers fresh, active videos directly from TikTok's live algorithmic recommendation feed (`/aweme/v1/feed/`).
- 🔔 **Targeted Push Notification Replies**: Instead of just posting top-level comments that get lost in the noise, the bot can directly reply to real user comments under videos. This triggers **instant mobile push notifications** on their phones!
- 🔀 **3 Operating Modes**:
  - **Mixed Mode (Recommended)**: Seamlessly blends comment replies (70%) with video-level comments (30%).
  - **Replies Only**: Focuses 100% on replying to users to maximize direct push notifications and profile visits.
  - **Video Comments Only**: Standard automated commenting directly on recommended videos.
- 🛡️ **Anti-Spam & Rate-Limit Shield**:
  - Dynamic randomized delays (5–8s) to mimic human browsing behavior.
  - Intelligent action-block detector: automatically pauses with a 60-second cooldown when a rate limit is detected, then resumes smoothly without getting accounts banned.
- 💾 **Session Caching**: Stores your `sessionid` locally in `config.json` so you can launch in 1 click without having to copy-paste cookies every time.
- 🌐 **Multilingual Support**: Ready-to-use customizable comment databases for **EN**, **UA**, and **RU** in `comments.json`.
- 🪟 **Windows 1-Click Launcher**: Includes `run.bat` for instant startup without dealing with the command line.

---

## 📁 Project Structure

```text
├── main.py              # Main bot execution script
├── comments.json        # Database of custom comments by language (EN, UA, RU)
├── requirements.txt     # Python package dependencies
├── run.bat              # 1-click Windows launcher
├── MedoSigner/          # TikTok signature engine (Gorgon, Argus, Ladon, Khronos)
├── .gitignore           # Keeps your credentials (config.json) safe & private
└── README.md            # Project documentation
```

---

## ⚙️ Installation & Usage

### Option 1: Quick Start on Windows
1. Make sure you have [Python 3.8+](https://www.python.org/) installed.
2. Double-click **`run.bat`** (it will automatically install any missing dependencies and launch the bot).

### Option 2: Linux / macOS / Terminal
```bash
# 1. Clone the repository
git clone https://github.com/vladislave007/TikTokAutoCommenterBot-Spam-.git
cd TikTokAutoCommenterBot-Spam-

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the bot
python main.py
```

---

## 🔑 How to Get Your TikTok `sessionid`

1. Open your desktop browser (Chrome, Edge, Opera, or Firefox) and log into your account on [tiktok.com](https://www.tiktok.com).
2. Press **`F12`** to open Developer Tools.
3. Go to the **Application** tab (or **Storage** in Firefox).
4. In the left sidebar, expand **Cookies** $\rightarrow$ click on `https://www.tiktok.com`.
5. Find the cookie named **`sessionid`** and copy its **Value** (a long alphanumeric string).
6. Paste it into the bot prompt on first run.

---

## 📝 Customizing Comments

Open `comments.json` to customize your comments. The bot randomly selects phrases from the chosen language category for every interaction, preventing repetitive patterns.

```json
{
  "EN": [
    "Check out my page for more info! ⭐",
    "Details are pinned on my profile 👇",
    "Check my bio for the full guide 🔥"
  ]
}
```

---

## ⚠️ Disclaimer
*This tool is created for educational and research purposes only. Automation of social media accounts must comply with the platform's Terms of Service. The author is not responsible for any misuse, account restrictions, or bans resulting from the use of this tool.*

---

## 🤝 Contributing & License
Contributions, issues, and feature requests are welcome!  
Distributed under the MIT License.
