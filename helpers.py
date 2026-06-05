"""
helpers.py  —  Formatting utilities and keyboard builders.
"""

import hashlib
import time
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import (
    PREMIUM_PLANS, UPI_QR_CODES, UPI_ID,
    BOT_USERNAME, SUPPORT_GROUP, CHANNEL_LINK,
    FREE_DAILY_LIMIT, FREE_QUEUE_LIMIT, STRING_SESSION,
)


# ── Formatting ────────────────────────────────────────────────────────────────

def format_size(size: int) -> str:
    if not size:
        return "?"
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} PB"


def format_size_mb(size: int) -> float:
    return round(size / (1024 * 1024), 1)


def format_time(secs: int) -> str:
    h, rem = divmod(secs, 3600)
    m, s   = divmod(rem, 60)
    if h:
        return f"{h}h {m}m {s}s"
    if m:
        return f"{m}m {s}s"
    return f"{s}s"


def progress_bar(done: int, total: int, width: int = 10) -> str:
    if not total:
        return ""
    pct    = done / total
    filled = int(pct * width)
    return "⬢" * filled + "⬡" * (width - filled) + f" {pct * 100:.1f}%"


def make_order_id(user_id: int) -> str:
    h = hashlib.md5(f"{user_id}{time.time()}".encode()).hexdigest()[:8].upper()
    return f"ORD-ARBOT-{h}"


def upload_mode_label() -> str:
    return "🚀 User Client (4GB)" if STRING_SESSION != "YOUR_STRING_SESSION" else "🤖 Bot Client (2GB)"


# ── Message texts ─────────────────────────────────────────────────────────────

def build_welcome(name: str, is_prem: bool, expiry_str: str) -> str:
    return (
        f"✨ **TeraBox VIP Downloader Bot** ✨\n\n"
        f"🚀 Fast • Secure • Premium Quality Downloads\n\n"
        f"╭━━━━━━━━━━━━━━━╮\n"
        f"💎 **VIP Features**\n"
        f"┣ 📥 Ultra Fast Downloading\n"
        f"┣ 🎬 HD / Full HD Video Support\n"
        f"┣ 📂 Direct File Generation\n"
        f"┣ ⚡ Instant Processing Speed\n"
        f"┣ 🔐 Secure & Private Access\n"
        f"┣ 🌍 40+ TeraBox Domains\n"
        f"╰━━━━━━━━━━━━━━━╯\n\n"
        f"📌 **How To Use:**\n"
        f"1️⃣ Send your TeraBox link\n"
        f"2️⃣ Wait a few seconds\n"
        f"3️⃣ Receive your file instantly 🚀\n\n"
        f"━━━━━━━━━━━━━━━\n"
        f"👤 **Your Plan:** {'💎 Premium' if is_prem else '🆓 Free'}\n"
        f"📅 **Expiry:** {expiry_str}\n"
        f"📤 **Upload:** {upload_mode_label()}\n"
        f"━━━━━━━━━━━━━━━"
    )


def build_caption(filename: str, size: int, is_prem: bool) -> str:
    via_user = STRING_SESSION != "YOUR_STRING_SESSION"
    return (
        f"✅ **Download Complete!**\n\n"
        f"📁 **File:** `{filename}`\n"
        f"💾 **Size:** {format_size_mb(size)} MB\n"
        f"📤 **Mode:** {'🚀 User Client (4GB)' if via_user else '🤖 Bot Client (2GB)'}\n"
        f"👤 **Plan:** {'💎 Premium' if is_prem else '🆓 Free'}\n\n"
        f"⚠️ _File 1 hour baad delete ho jayegi._\n"
        f"💡 _Save karna ho to abhi kar lo!_"
    )


# ── Keyboards ─────────────────────────────────────────────────────────────────

def main_menu_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("❓ How to Use", callback_data="how_to_use")],
        [
            InlineKeyboardButton("📢 Join Channel", url=CHANNEL_LINK),
            InlineKeyboardButton("💎 Get Premium",  callback_data="premium_menu"),
        ],
    ])


def bottom_kb():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🚀 Plan",     callback_data="plan_info"),
            InlineKeyboardButton("🗂 My Queue", callback_data="my_queue"),
        ],
        [
            InlineKeyboardButton("🤝 Share Bot", callback_data="share_bot"),
            InlineKeyboardButton("💎 Premium",   callback_data="premium_menu"),
        ],
    ])


def premium_plans_kb():
    rows = []
    for name, days, price, ppd in PREMIUM_PLANS:
        rows.append([InlineKeyboardButton(
            f"{name}  Rs.{price} | {days}d | {ppd}",
            callback_data=f"buy_{days}_{price}",
        )])
    rows.append([InlineKeyboardButton("❌ Cancel", callback_data="cancel")])
    return InlineKeyboardMarkup(rows)


def payment_channel_kb(days: int, price: int):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⭐ Pay via QR Code 1", callback_data=f"qr_1_{days}_{price}")],
        [InlineKeyboardButton("⭐ Pay via QR Code 2", callback_data=f"qr_2_{days}_{price}")],
        [InlineKeyboardButton("⭐ Pay via QR Code 3", callback_data=f"qr_3_{days}_{price}")],
        [InlineKeyboardButton("⬅️ Back", callback_data="premium_menu")],
    ])


def qr_payment_kb(qr_num: int, days: int, price: int):
    others = [i for i in [1, 2, 3] if i != qr_num]
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(f"🔄 Switch to QR-{others[0]}", callback_data=f"qr_{others[0]}_{days}_{price}"),
            InlineKeyboardButton(f"🔄 Switch to QR-{others[1]}", callback_data=f"qr_{others[1]}_{days}_{price}"),
        ],
        [InlineKeyboardButton("❌ CANCEL ORDER", callback_data="cancel_order")],
        [InlineKeyboardButton("🆘 Need Help?",   url=SUPPORT_GROUP)],
    ])


def upgrade_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💎 Upgrade to Premium", callback_data="premium_menu")],
    ])


def share_kb(user_id: int):
    bot_name = BOT_USERNAME.lstrip("@")
    ref_link = f"https://t.me/{bot_name}?start=ref_{user_id}"
    wa_text  = (
        "Hey!%20I%20found%20this%20amazing%20TeraBox%20downloader%20bot!%0A%0A"
        "%E2%9C%85%20Download%20any%20TeraBox%20file%20instantly%0A"
        "%E2%9C%85%20Completely%20FREE%20to%20use%0A"
        "%E2%9C%85%20Fast%20and%20reliable%0A%0A"
        f"Try%20it%20now%3A%20{ref_link}"
    )
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📱 Share on Telegram",
                              url=f"https://t.me/share/url?url={ref_link}")],
        [InlineKeyboardButton("💬 Share on WhatsApp",
                              url=f"https://wa.me/?text={wa_text}")],
        [InlineKeyboardButton("🔗 Copy Bot Link",       callback_data=f"copy_link_{user_id}")],
        [InlineKeyboardButton("💎 Get Premium Benefits", callback_data="premium_menu")],
    ])
