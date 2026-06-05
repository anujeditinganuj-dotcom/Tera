"""
config.py  —  All bot settings live here.
Edit this file before running the bot.
"""

from pathlib import Path
from cookie_loader import load_netscape_cookies, load_cookie_string

# ── Telegram credentials ────────────────────────────────────────────────────
BOT_TOKEN      = "YOUR_BOT_TOKEN"       # @BotFather
API_ID         = 0                       # my.telegram.org
API_HASH       = "YOUR_API_HASH"         # my.telegram.org
STRING_SESSION = "YOUR_STRING_SESSION"   # Pyrogram string session (4 GB upload)

OWNER_ID   = 0                           # Your Telegram numeric ID
SUDO_USERS = [OWNER_ID]

# ── MongoDB ─────────────────────────────────────────────────────────────────
MONGO_URI     = "mongodb+srv://user:pass@cluster.mongodb.net/terabot"
MONGO_DB_NAME = "terabot"

# ── Bot public links ─────────────────────────────────────────────────────────
BOT_USERNAME  = "@YourBotUsername"
SUPPORT_GROUP = "https://t.me/yoursupportgroup"
CHANNEL_LINK  = "https://t.me/yourchannel"

# ── Cookies ───────────────────────────────────────────────────────────────────
#  Bot automatically reads  downloads/tera_cookies.txt  (Netscape format).
#  You can also hard-code a cookie string here as fallback.
COOKIE_FILE        = Path(__file__).parent / "downloads" / "tera_cookies.txt"
COOKIE_STRING_HARD = ""   # optional hard-coded fallback

def get_cookie_string() -> str:
    """Returns cookie string: file first, fallback to hard-coded."""
    from_file = load_cookie_string(COOKIE_FILE)
    return from_file if from_file else COOKIE_STRING_HARD

def get_cookies() -> dict:
    """Returns cookies dict: file first, fallback to hard-coded."""
    from_file = load_netscape_cookies(COOKIE_FILE)
    if from_file:
        return from_file
    if COOKIE_STRING_HARD.strip():
        out = {}
        for part in COOKIE_STRING_HARD.split(";"):
            part = part.strip()
            if "=" in part:
                k, _, v = part.partition("=")
                out[k.strip()] = v.strip()
        return out
    return {}

# ── Paths ────────────────────────────────────────────────────────────────────
DOWNLOAD_DIR = Path("./downloads/temp")

# ── Auto-delete ──────────────────────────────────────────────────────────────
AUTO_DELETE_SECS = 3600   # 1 hour

# ── Free plan limits ─────────────────────────────────────────────────────────
FREE_DAILY_LIMIT = 2000
FREE_QUEUE_LIMIT = 2

# ── Premium plans ─────────────────────────────────────────────────────────────
# (label, days, price_inr, price_per_day_str)
PREMIUM_PLANS = [
    ("🔥 TRIAL",     7,   19,  "₹2.7/d"),
    ("🎯 STARTER",   15,  39,  "₹2.6/d"),
    ("💎 MONTHLY",   30,  59,  "₹1.9/d"),
    ("⭐ BEST PLAN", 90,  99,  "₹1.1/d"),
    ("🥳 VIP DEAL",  180, 149, "₹0.8/d"),
    ("♾️  YEARLY",   365, 249, "₹0.68/d"),
]

# ── UPI payment ───────────────────────────────────────────────────────────────
# Send QR images to your bot, copy the file_id from logs, paste here.
UPI_QR_CODES = {
    1: "YOUR_QR_FILE_ID_1",
    2: "YOUR_QR_FILE_ID_2",
    3: "YOUR_QR_FILE_ID_3",
}
UPI_ID = "yourname@upi"

# ── Referral ──────────────────────────────────────────────────────────────────
SHARE_PREMIUM_HOURS = 24   # free hours given to referrer per new join
MAX_SHARES_PER_DAY  = 3    # max referral bonuses per day

# ── TeraBox API ───────────────────────────────────────────────────────────────
API_DOMAINS = ["www.1024tera.com", "www.terabox.com"]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept":          "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer":         "https://www.1024tera.com/",
    "Origin":          "https://www.1024tera.com",
}
