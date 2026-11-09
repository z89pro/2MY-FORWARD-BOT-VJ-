# 📤 Telegram Forward Bot

A powerful multi-user **Telegram Forward/Clone Bot** that copies messages from any chat (private groups, public channels) to your target — with **no "Forwarded from" tag**.

---

## ✨ Features

- 🔐 **User Login** via OTP (+ 2FA support)
- 📥 **Forward from private groups** you're a member of
- 📡 **Clone public channels** with `/clone`
- ⚡ **Fast Mode** — 1,000 msgs per cycle → 5-min break → repeat
- 🐢 **Safe Mode** — Auto-activates after 3 FloodWaits
- 🌊 **Smart FloodWait** — Auto-waits with live countdown
- 💾 **Resume support** — Progress saved on restart
- 🎛️ **Inline Control Panel** — Full control via buttons

---

## 🚀 Quick Deploy

### Prerequisites
- Python 3.10+
- Telegram API ID & Hash → [my.telegram.org](https://my.telegram.org)
- Bot Token → [@BotFather](https://t.me/BotFather)
- MongoDB URI → [MongoDB Atlas](https://mongodb.com/atlas) (free tier)

### 1. Clone & Setup
```bash
cd "your-project-folder"
pip install -r requirements.txt
```

### 2. Configure Environment
```bash
cp .env.example .env
# Edit .env with your values
```

### 3. Run Locally
```bash
python bot.py
```

---

## ☁️ Deploy on Render

1. Push code to GitHub
2. Create new **Background Worker** on [render.com](https://render.com)
3. Connect your GitHub repo
4. Set environment variables (API_ID, API_HASH, BOT_TOKEN, MONGO_URI)
5. Build command: `pip install -r requirements.txt`
6. Start command: `python bot.py`

---

## ☁️ Deploy on Koyeb

1. Create new app → Docker or Git deploy
2. Set env vars in the Koyeb dashboard
3. Set start command: `python bot.py`

---

## 📋 Commands

| Command | Description |
|---|---|
| `/start` | Welcome message |
| `/login` | Login with your Telegram account |
| `/logout` | Logout and delete session |
| `/target @username` | Set target channel/group |
| `/forward` | Open forward control panel |
| `/clone @source` | Clone a public/private channel |
| `/stop` | Stop active forwarding |
| `/help` | Full help guide |

---

## ⚡ Forward Modes

| Mode | Batch Size | Break After | Break Duration |
|---|---|---|---|
| Fast | 100 msgs | 1,000 msgs | 5 minutes |
| Safe | 20 msgs | 200 msgs | 10 minutes |

Auto-switches to **Safe Mode** after **3 FloodWaits**.

---

## ⚠️ Disclaimer

This bot uses your **personal Telegram account** to forward messages. Mass forwarding may violate Telegram's Terms of Service. Use responsibly. The developer is not responsible for any account bans.
