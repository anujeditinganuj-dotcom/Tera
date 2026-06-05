# 🤖 TeraBox VIP Downloader Bot

Fast, feature-rich Telegram bot to download files from 40+ TeraBox domains.

---

## ✨ Features

- 📥 40+ TeraBox domain support
- 📂 Recursive folder download
- 🍪 Auto-load cookies from `downloads/tera_cookies.txt` (Netscape format)
- 🗄️ MongoDB database (free/premium users)
- 💎 Free & Premium plans with UPI QR payment
- 🤝 Share-bot referral → 24h free premium
- 👑 Admin commands: `/addpremium`, `/removepremium`, `/users`
- 🔄 `/reloadcookies` — hot-reload cookies without restart
- 🚀 4 GB upload via Pyrogram String Session
- ⏳ 1-hour auto-delete

---

## 📁 Project Structure

```
terabox_bot/
├── bot.py              ← Main bot (run this)
├── config.py           ← All settings
├── database.py         ← MongoDB helpers
├── terabox_api.py      ← TeraBox resolver + downloader
├── helpers.py          ← Formatting + keyboard builders
├── cookie_loader.py    ← Netscape cookies.txt parser
├── requirements.txt
├── .gitignore
└── downloads/
    ├── tera_cookies.txt   ← PUT YOUR COOKIES HERE
    └── temp/              ← Temporary download cache
```

---

## ⚡ Quick Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Edit `config.py`

Fill in these fields:

```python
BOT_TOKEN      = "123456:ABC..."    # @BotFather
API_ID         = 12345678           # my.telegram.org
API_HASH       = "abcdef..."        # my.telegram.org
STRING_SESSION = "BQA..."           # optional, for 4 GB upload
OWNER_ID       = 987654321          # your Telegram user ID
MONGO_URI      = "mongodb+srv://..."
BOT_USERNAME   = "@YourBotUsername"
SUPPORT_GROUP  = "https://t.me/..."
CHANNEL_LINK   = "https://t.me/..."
UPI_ID         = "yourname@upi"
UPI_QR_CODES   = {1: "file_id_1", 2: "file_id_2", 3: "file_id_3"}
```

### 3. Add TeraBox cookies

Export cookies from your browser in **Netscape format** and save to:

```
downloads/tera_cookies.txt
```

**How to export:**
1. Install **"Get cookies.txt LOCALLY"** extension (Chrome/Firefox)
2. Login to [terabox.com](https://terabox.com) or [1024tera.com](https://1024tera.com)
3. Click extension → **Export** → save as `downloads/tera_cookies.txt`

> Without cookies, the bot still works for public links.

### 4. Generate String Session (optional, for 4 GB upload)

```bash
python -c "
from pyrogram import Client
import asyncio

async def gen():
    async with Client('my_account', api_id=API_ID, api_hash='API_HASH') as c:
        print(await c.export_session_string())

asyncio.run(gen())
"
```

Paste the output as `STRING_SESSION` in `config.py`.

### 5. Run the bot

```bash
python bot.py
```

---

## 👑 Admin Commands

| Command | Description |
|---|---|
| `/addpremium <user_id> <days>` | Add premium to a user |
| `/removepremium <user_id>` | Remove premium from a user |
| `/users` | Total / premium user count |
| `/reloadcookies` | Hot-reload cookies from file |

## 💬 User Commands

| Command | Description |
|---|---|
| `/start` | Welcome + plan info |
| `/help` | How to use |
| `/plan` | Your plan details |
| `/stats` | Download statistics |
| `/status` | Active downloads |
| `/share` | Referral link (earn 24h premium) |
| `/premium` | Buy premium |

---

## 💎 Premium Plans (default)

| Plan | Days | Price |
|---|---|---|
| 🔥 Trial | 7 | ₹19 |
| 🎯 Starter | 15 | ₹39 |
| 💎 Monthly | 30 | ₹59 |
| ⭐ Best Plan | 90 | ₹99 |
| 🥳 VIP Deal | 180 | ₹149 |
| ♾️ Yearly | 365 | ₹249 |

Edit `PREMIUM_PLANS` in `config.py` to change.

---

## 🍪 Cookie Hot-Reload

You can update `downloads/tera_cookies.txt` at any time **without restarting** the bot.  
Cookies are re-read on every `/reloadcookies` command or automatically on each new download request.

---

## 📝 Notes

- Files auto-delete after 1 hour (configurable via `AUTO_DELETE_SECS`)
- Free users: 2000 downloads/day, queue limit 2
- Premium users: unlimited downloads, queue limit 20
- Bot tries user client (4 GB) first, falls back to bot client (2 GB)
- `downloads/temp/` is used as cache; safe to clear anytime
