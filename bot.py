"""
bot.py  —  Main Telegram bot handlers.
"""

import asyncio
import time
from pathlib import Path
from datetime import datetime

from pyrogram import Client, filters
from pyrogram.types import (
    Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
)

from config import (
    BOT_TOKEN, API_ID, API_HASH, STRING_SESSION,
    SUDO_USERS, SUPPORT_GROUP, UPI_QR_CODES, UPI_ID,
    AUTO_DELETE_SECS, FREE_DAILY_LIMIT, FREE_QUEUE_LIMIT,
    get_cookies, get_cookie_string,
)
from database import (
    init_mongo, get_user, update_user, inc_downloads,
    is_premium, premium_days_left, add_premium, remove_premium, count_users,
    db,
)
from terabox_api import TeraBoxAPI, download_file, find_tb_url
from helpers import (
    format_size, format_size_mb, format_time, progress_bar,
    make_order_id, build_welcome, build_caption,
    main_menu_kb, bottom_kb, premium_plans_kb,
    payment_channel_kb, qr_payment_kb, upgrade_kb, share_kb,
    upload_mode_label,
)

# ── Clients ───────────────────────────────────────────────────────────────────

bot = Client(
    "terabox_bot",
    bot_token=BOT_TOKEN,
    api_id=API_ID,
    api_hash=API_HASH,
)

user_client = Client(
    "terabox_user",
    session_string=STRING_SESSION,
    api_id=API_ID,
    api_hash=API_HASH,
)

tb_api = TeraBoxAPI()

# pending UPI orders: {user_id: {days, price, qr, order_id}}
pending_orders: dict = {}


# ── Auto-delete ───────────────────────────────────────────────────────────────

async def schedule_delete(chat_id: int, message_ids: list, delay: int = AUTO_DELETE_SECS):
    await asyncio.sleep(delay)
    for mid in message_ids:
        for c in (user_client, bot):
            try:
                await c.delete_messages(chat_id, mid)
                break
            except Exception:
                pass


# ╔══════════════════════════════════════════════════════╗
# ║                    COMMANDS                         ║
# ╚══════════════════════════════════════════════════════╝

@bot.on_message(filters.command("start"))
async def cmd_start(_, msg: Message):
    user_id = msg.from_user.id
    name    = msg.from_user.first_name or "User"

    doc = await get_user(user_id)
    await update_user(user_id, name=name)

    # ── Referral ──
    args = msg.text.split()
    if len(args) > 1 and args[1].startswith("ref_"):
        try:
            ref_id = int(args[1][4:])
            if ref_id != user_id:
                ref_doc = await get_user(ref_id)
                today   = str(datetime.now().date())
                shares  = ref_doc.get("shares_today", 0) if ref_doc.get("shares_date") == today else 0
                if shares < 3:
                    await add_premium(ref_id, 1)
                    await update_user(ref_id, shares_today=shares + 1, shares_date=today)
                    try:
                        await bot.send_message(
                            ref_id,
                            "🎁 **Someone joined via your link!**\n\n"
                            "✅ You got **24 hours FREE Premium** added!",
                        )
                    except Exception:
                        pass
        except Exception:
            pass

    is_prem    = is_premium(doc)
    expiry_str = f"{premium_days_left(doc)} days remaining" if is_prem else "No active plan"
    text       = build_welcome(name, is_prem, expiry_str)

    try:
        await msg.reply_photo(
            photo="https://telegra.ph/file/terabox-welcome.jpg",
            caption=text,
            reply_markup=main_menu_kb(),
            quote=True,
        )
    except Exception:
        await msg.reply_text(text, reply_markup=main_menu_kb(), quote=True)


@bot.on_message(filters.command("help"))
async def cmd_help(_, msg: Message):
    await msg.reply_text(
        "🔍 **How to Use This Bot**\n\n"
        "1️⃣ Send any TeraBox link\n"
        "2️⃣ Bot downloads & sends the file\n"
        "3️⃣ Folder links work too — all files auto-downloaded!\n\n"
        "🔄 **Troubleshooting:**\n"
        "• Link invalid/private → check cookies\n"
        "• Large files take more time\n"
        "• Send one link at a time\n\n"
        "**Commands:**\n"
        "/plan — Your plan details\n"
        "/stats — Download stats\n"
        "/status — Active downloads\n"
        "/share — Earn free premium\n"
        "/premium — Buy premium",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("💡 Tips & Tricks", callback_data="tips")],
            [InlineKeyboardButton("🆘 Support Group",  url=SUPPORT_GROUP)],
        ]),
        quote=True,
    )


@bot.on_message(filters.command("plan"))
async def cmd_plan(_, msg: Message):
    doc  = await get_user(msg.from_user.id)
    prem = is_premium(doc)
    if prem:
        text = (
            f"🔒 **Your Plan Details**\n\n"
            f"**Plan:** 💎 Premium\n"
            f"**Expiry:** {premium_days_left(doc)} days remaining\n\n"
            f"• ♾️ Unlimited downloads\n"
            f"• 🚀 Queue up to 20 URLs\n"
            f"• 📦 4 GB file + folder support\n"
            f"• 🚫 No ads"
        )
        kb = None
    else:
        text = (
            f"🔒 **Your Plan Details**\n\n"
            f"**Plan:** 🆓 Free\n"
            f"**Today:** {doc['today_downloads']} / {FREE_DAILY_LIMIT}\n"
            f"**Remaining:** {FREE_DAILY_LIMIT - doc['today_downloads']}\n\n"
            f"• {FREE_DAILY_LIMIT} downloads/day\n"
            f"• Queue: {FREE_QUEUE_LIMIT} URLs\n"
            f"• Limited speed"
        )
        kb = upgrade_kb()
    await msg.reply_text(text, reply_markup=kb, quote=True)


@bot.on_message(filters.command("stats"))
async def cmd_stats(_, msg: Message):
    doc  = await get_user(msg.from_user.id)
    prem = is_premium(doc)
    rem  = "Unlimited" if prem else str(FREE_DAILY_LIMIT - doc["today_downloads"])
    await msg.reply_text(
        f"👤 **{msg.from_user.first_name}**\n\n"
        f"📈 Total downloads: **{doc['total_downloads']}**\n"
        f"⚡ Plan: {'💎 Premium' if prem else '🆓 Free'}\n"
        f"🗓 Today: {doc['today_downloads']} / {'∞' if prem else FREE_DAILY_LIMIT}\n"
        f"⏳ Remaining: {rem}",
        reply_markup=upgrade_kb() if not prem else None,
        quote=True,
    )


@bot.on_message(filters.command("status"))
async def cmd_status(_, msg: Message):
    doc  = await get_user(msg.from_user.id)
    prem = is_premium(doc)
    await msg.reply_text(
        f"🔄 **Active downloads:** 0 / {20 if prem else 1}\n\n"
        f"{'⚡ Premium: Multi-threading enabled!' if prem else '⚡ Upgrade for multi-threading!'}",
        reply_markup=upgrade_kb() if not prem else None,
        quote=True,
    )


@bot.on_message(filters.command("share"))
async def cmd_share(_, msg: Message):
    await _send_share(msg, msg.from_user.id)


@bot.on_message(filters.command("premium"))
async def cmd_premium(_, msg: Message):
    await _send_premium_menu(msg)


# ── Admin commands ────────────────────────────────────────────────────────────

@bot.on_message(filters.command("addpremium") & filters.user(SUDO_USERS))
async def cmd_add_premium(_, msg: Message):
    parts = msg.text.split()
    if len(parts) < 3:
        await msg.reply_text("⚙️ Usage: `/addpremium <user_id> <days>`")
        return
    try:
        target_id = int(parts[1])
        days      = int(parts[2])
        exp       = await add_premium(target_id, days)
        await msg.reply_text(
            f"✅ **Premium Added!**\n\n"
            f"👤 User: `{target_id}`\n"
            f"📅 Days: **{days}**\n"
            f"⏳ Expires: `{exp.strftime('%Y-%m-%d %H:%M')}`"
        )
        try:
            await bot.send_message(
                target_id,
                f"🎉 **Premium Activated!**\n\n"
                f"💎 Upgraded to Premium for **{days} days**.\n"
                f"⏳ Expires: `{exp.strftime('%Y-%m-%d')}`\n\n"
                f"Enjoy unlimited downloads! 🚀",
            )
        except Exception:
            pass
    except Exception as e:
        await msg.reply_text(f"❌ Error: `{e}`")


@bot.on_message(filters.command("removepremium") & filters.user(SUDO_USERS))
async def cmd_remove_premium(_, msg: Message):
    parts = msg.text.split()
    if len(parts) < 2:
        await msg.reply_text("⚙️ Usage: `/removepremium <user_id>`")
        return
    try:
        target_id = int(parts[1])
        await remove_premium(target_id)
        await msg.reply_text(
            f"✅ **Premium Removed!**\n\n"
            f"👤 User: `{target_id}`\n"
            f"📊 Plan: Reverted to 🆓 Free"
        )
        try:
            await bot.send_message(
                target_id,
                "⚠️ **Premium Expired**\n\n"
                "Your premium plan has been removed by admin.\n"
                "Use /premium to subscribe again.",
            )
        except Exception:
            pass
    except Exception as e:
        await msg.reply_text(f"❌ Error: `{e}`")


@bot.on_message(filters.command("users") & filters.user(SUDO_USERS))
async def cmd_users(_, msg: Message):
    total, prem_count = await count_users()
    await msg.reply_text(
        f"📊 **Bot Statistics**\n\n"
        f"👥 Total users: **{total}**\n"
        f"💎 Premium: **{prem_count}**\n"
        f"🆓 Free: **{total - prem_count}**"
    )


# ── Cookie reload command (admin) ─────────────────────────────────────────────

@bot.on_message(filters.command("reloadcookies") & filters.user(SUDO_USERS))
async def cmd_reload_cookies(_, msg: Message):
    tb_api._refresh()
    count = len(tb_api.cookies)
    await msg.reply_text(
        f"🍪 **Cookies Reloaded!**\n\n"
        f"✅ Loaded **{count}** cookies from `downloads/tera_cookies.txt`"
        if count else
        "⚠️ No cookies found in `downloads/tera_cookies.txt`\n"
        "Bot will work for public links only."
    )


# ╔══════════════════════════════════════════════════════╗
# ║              SHARED UI HELPERS                      ║
# ╚══════════════════════════════════════════════════════╝

async def _send_share(target, user_id: int, edit=False):
    text = (
        "🤝 **Share & Earn FREE Premium!**\n\n"
        "📥 **What friends get:**\n"
        "• Instant TeraBox downloads\n"
        "• HD video support\n"
        "• Completely free!\n\n"
        "🎁 **You get:** 24h FREE Premium per new join\n"
        "_(max 3 per day)_"
    )
    kb = share_kb(user_id)
    if edit and hasattr(target, "message"):
        await target.message.edit_text(text, reply_markup=kb)
    elif hasattr(target, "message"):
        await target.message.reply_text(text, reply_markup=kb, quote=True)
    else:
        await target.reply_text(text, reply_markup=kb, quote=True)


async def _send_premium_menu(target, edit=False):
    text = (
        "💎 **AR BOTS PREMIUM**\n\n"
        "Pay via Paytm, GPay, or PhonePe.\n\n"
        "**Benefits:**\n"
        "• ♾️ Unlimited fast downloads\n"
        "• 🚀 Queue up to 20 URLs\n"
        "• 🚫 No ads or wait time\n"
        "• 📁 4 GB file + folder support\n"
        "• 🆘 24/7 support\n\n"
        "⭐ Best value: Rs.99 for 90 days (~Re.1/day)\n\n"
        "**Choose your plan:**"
    )
    if edit and hasattr(target, "message"):
        await target.message.edit_text(text, reply_markup=premium_plans_kb())
    elif hasattr(target, "message"):
        await target.message.reply_text(text, reply_markup=premium_plans_kb(), quote=True)
    else:
        await target.reply_text(text, reply_markup=premium_plans_kb(), quote=True)


# ╔══════════════════════════════════════════════════════╗
# ║             CALLBACK QUERY HANDLER                  ║
# ╚══════════════════════════════════════════════════════╝

@bot.on_callback_query()
async def handle_callback(_, cb: CallbackQuery):
    data    = cb.data
    user_id = cb.from_user.id
    doc     = await get_user(user_id)

    if data == "how_to_use":
        await cb.message.edit_text(
            "🔍 **How to Use This Bot**\n\n"
            "1️⃣ Send any TeraBox link\n"
            "2️⃣ Bot processes & sends the file\n"
            "3️⃣ Folders downloaded recursively 📂\n\n"
            "🔄 **Troubleshooting:**\n"
            "• Invalid/expired link → try again\n"
            "• Large files → be patient\n"
            "• Private files → cookies needed",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💡 Tips & Tricks", callback_data="tips")],
                [InlineKeyboardButton("⬅️ Back",          callback_data="back_main")],
            ]),
        )

    elif data == "tips":
        await cb.message.edit_text(
            "💡 **Tips & Tricks**\n\n"
            "• Links must be public\n"
            "• Folder links work — all files downloaded!\n"
            "• Premium = priority + unlimited\n"
            "• Share bot → earn 24h premium\n\n"
            "**Commands:**\n"
            "/plan /stats /status /share /premium",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Back", callback_data="how_to_use")],
            ]),
        )

    elif data == "plan_info":
        prem = is_premium(doc)
        if prem:
            text = (
                f"🔒 **Plan:** 💎 Premium\n"
                f"**Expiry:** {premium_days_left(doc)} days remaining\n\n"
                f"• ♾️ Unlimited downloads\n"
                f"• 🚀 Queue 20 URLs\n"
                f"• 📦 4 GB support\n• 🚫 No ads"
            )
            rows = [[InlineKeyboardButton("⬅️ Back", callback_data="back_main")]]
        else:
            text = (
                f"🔒 **Plan:** 🆓 Free\n"
                f"**Today:** {doc['today_downloads']} / {FREE_DAILY_LIMIT}\n"
                f"**Remaining:** {FREE_DAILY_LIMIT - doc['today_downloads']}\n\n"
                f"• {FREE_DAILY_LIMIT} downloads/day\n"
                f"• Queue: {FREE_QUEUE_LIMIT} URLs"
            )
            rows = [
                [InlineKeyboardButton("💎 Upgrade", callback_data="premium_menu")],
                [InlineKeyboardButton("⬅️ Back",    callback_data="back_main")],
            ]
        await cb.message.edit_text(text, reply_markup=InlineKeyboardMarkup(rows))

    elif data == "my_queue":
        prem  = is_premium(doc)
        await cb.message.edit_text(
            f"🗂 **Queue Status**\n\n"
            f"Queue: Empty\n"
            f"Plan: {'💎 Premium' if prem else '🆓 Free'}\n"
            f"Daily: {doc['today_downloads']} / {'∞' if prem else FREE_DAILY_LIMIT}\n"
            f"Queue limit: {20 if prem else FREE_QUEUE_LIMIT} URLs",
            reply_markup=InlineKeyboardMarkup([
                [] if prem else [InlineKeyboardButton("💎 Upgrade", callback_data="premium_menu")],
                [InlineKeyboardButton("⬅️ Back", callback_data="back_main")],
            ]),
        )

    elif data == "share_bot":
        await _send_share(cb, user_id, edit=True)

    elif data.startswith("copy_link_"):
        uid      = data.split("_")[-1]
        from config import BOT_USERNAME
        bot_name = BOT_USERNAME.lstrip("@")
        await cb.answer(
            f"https://t.me/{bot_name}?start=ref_{uid}",
            show_alert=True,
        )

    elif data == "premium_menu":
        await _send_premium_menu(cb, edit=True)

    elif data.startswith("buy_"):
        _, days, price = data.split("_")
        await cb.message.edit_text(
            "⚙️ **Select Payment Channel**\n\n"
            "Agar ek QR slow ho toh doosra try karein:",
            reply_markup=payment_channel_kb(int(days), int(price)),
        )

    elif data.startswith("qr_"):
        parts    = data.split("_")
        qr_num   = int(parts[1])
        days     = int(parts[2])
        price    = int(parts[3])
        order_id = make_order_id(user_id)

        pending_orders[user_id] = {
            "days": days, "price": price, "qr": qr_num, "order_id": order_id
        }

        caption = (
            f"🎉 **{days} Days Premium — ₹{price}.00**\n\n"
            f"🔑 Order ID: `{order_id}`\n\n"
            f"**Steps:**\n"
            f"1️⃣ Scan QR with any UPI app\n"
            f"2️⃣ Pay exactly ₹{price}\n"
            f"3️⃣ Premium auto-activates after verification\n\n"
            f"📱 UPI ID: `{UPI_ID}`\n\n"
            f"💡 _Payment fail? Switch QR channel._"
        )
        qr_file = UPI_QR_CODES.get(qr_num)
        kb      = qr_payment_kb(qr_num, days, price)
        try:
            await cb.message.delete()
            await bot.send_photo(cb.message.chat.id, photo=qr_file, caption=caption, reply_markup=kb)
        except Exception:
            await cb.message.edit_text(caption, reply_markup=kb)

    elif data == "cancel_order":
        pending_orders.pop(user_id, None)
        await cb.message.edit_text(
            "❌ Order cancelled.\n\nSend a TeraBox link to start downloading!",
            reply_markup=bottom_kb(),
        )

    elif data == "cancel":
        await cb.message.edit_text(
            "Cancelled. Send a TeraBox link to start!",
            reply_markup=bottom_kb(),
        )

    elif data == "back_main":
        prem       = is_premium(doc)
        expiry_str = f"{premium_days_left(doc)} days remaining" if prem else "No active plan"
        text       = build_welcome(cb.from_user.first_name or "User", prem, expiry_str)
        try:
            await cb.message.edit_text(text, reply_markup=main_menu_kb())
        except Exception:
            pass

    await cb.answer()


# ╔══════════════════════════════════════════════════════╗
# ║            MAIN DOWNLOAD HANDLER                    ║
# ╚══════════════════════════════════════════════════════╝

@bot.on_message(filters.text & (filters.private | filters.group))
async def handle_link(_, msg: Message):
    url = find_tb_url(msg.text)
    if not url:
        return

    user_id = msg.from_user.id
    doc     = await get_user(user_id)
    prem    = is_premium(doc)

    # ── Daily limit check ──
    if not prem and doc["today_downloads"] >= FREE_DAILY_LIMIT:
        await msg.reply_text(
            f"⚠️ **Daily limit reached!**\n\n"
            f"Used all **{FREE_DAILY_LIMIT}** free downloads today.\n\n"
            f"⏳ Wait until tomorrow, or upgrade to Premium.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💎 Get Premium", callback_data="premium_menu")],
                [InlineKeyboardButton("🆘 Support",      url=SUPPORT_GROUP)],
            ]),
            quote=True,
        )
        return

    status_msg = await msg.reply_text("🔍 **Link check ho raha hai...**", quote=True)

    try:
        await status_msg.edit_text("⏳ **File info fetch ho rahi hai...**")

        info = await tb_api.resolve(url)
        if not info:
            await status_msg.edit_text(
                "❌ **File info nahi mili!**\n\n"
                "• Link invalid/expired ho sakta hai\n"
                "• Private file → cookies add karo\n"
                "• TeraBox server temporarily down"
            )
            return

        files     = info["files"]
        shareinfo = info["shareinfo"]
        pcftoken  = info["pcftoken"]
        cookies   = tb_api.cookies
        cookie_str = tb_api.cookie_str

        if not files:
            await status_msg.edit_text("❌ **Koi file nahi mili is link mein.**")
            return

        # ── File list preview ──
        preview = "\n".join(
            f"📄 `{f['filename']}` — **{format_size(f['size'])}**"
            for f in files[:10]
        )
        extra = f"\n_...aur {len(files) - 10} files_" if len(files) > 10 else ""
        await status_msg.edit_text(
            f"✅ **{len(files)} file(s) mili:**\n\n{preview}{extra}\n\n"
            "⬇️ **Download shuru ho raha hai...**"
        )

        sent_ids = []

        for i, f in enumerate(files):

            # ── Size guard ──
            if f["size"] / (1024 ** 3) > 4:
                m2 = await msg.reply_text(
                    f"⚠️ `{f['filename']}` — {format_size(f['size'])}\n"
                    f"4 GB se badi file — skip!",
                    quote=True,
                )
                sent_ids.append(m2.id)
                continue

            file_msg = await msg.reply_text(
                f"[{i+1}/{len(files)}] 📥 **Downloading...**\n"
                f"📄 `{f['filename']}`\n"
                f"📦 {format_size(f['size'])}",
                quote=True,
            )

            # ── Get download link ──
            dlink = f.get("dlink") or await tb_api.get_download_link(
                f["fs_id"], shareinfo, pcftoken
            )
            if not dlink:
                await file_msg.edit_text(
                    f"❌ **Download link nahi mila!**\n`{f['filename']}`"
                )
                continue

            # ── Download with progress ──
            dl_start = time.time()
            last_dl  = {"t": 0.0}

            async def dl_progress(done, total,
                                   _s=dl_start, _l=last_dl,
                                   _fm=file_msg, _f=f, _i=i, _n=len(files)):
                now = time.time()
                if now - _l["t"] < 3:
                    return
                _l["t"] = now
                elapsed = now - _s
                speed   = done / elapsed if elapsed else 0
                eta     = int((total - done) / speed) if speed else 0
                try:
                    await _fm.edit_text(
                        f"[{_i+1}/{_n}] 📥 **Downloading...**\n"
                        f"📄 `{_f['filename']}`\n"
                        f"📦 {format_size(done)} / {format_size(total)}\n"
                        f"{progress_bar(done, total)}\n"
                        f"⚡ {format_size(int(speed))}/s  ⏱ ETA: {format_time(eta)}"
                    )
                except Exception:
                    pass

            local_path = await download_file(
                dlink, f["filename"], f["size"],
                cookies, cookie_str, dl_progress,
            )

            if not local_path:
                await file_msg.edit_text(f"❌ **Download fail!**\n`{f['filename']}`")
                continue

            # ── Upload with progress ──
            await file_msg.edit_text(
                f"[{i+1}/{len(files)}] 📤 **Uploading to Telegram...**\n"
                f"📄 `{f['filename']}`"
            )

            up_start = time.time()
            last_up  = {"t": 0.0}

            async def up_progress(done, total,
                                   _s=up_start, _l=last_up,
                                   _fm=file_msg, _f=f, _i=i, _n=len(files)):
                now = time.time()
                if now - _l["t"] < 3:
                    return
                _l["t"] = now
                elapsed = now - _s
                speed   = done / elapsed if elapsed else 0
                eta     = int((total - done) / speed) if speed else 0
                try:
                    await _fm.edit_text(
                        f"[{_i+1}/{_n}] 📤 **Uploading...**\n"
                        f"📄 `{_f['filename']}`\n"
                        f"📦 {format_size(done)} / {format_size(total)}\n"
                        f"{progress_bar(done, total)}\n"
                        f"⚡ {format_size(int(speed))}/s  ⏱ ETA: {format_time(eta)}"
                    )
                except Exception:
                    pass

            ext      = Path(f["filename"]).suffix.lower()
            is_video = ext in (".mp4", ".mkv", ".avi", ".mov", ".webm", ".flv", ".m4v")
            caption  = build_caption(f["filename"], f["size"], prem)
            chat_id  = msg.chat.id
            sent     = None

            # Try user client (4 GB), fallback to bot (2 GB)
            for client in (user_client, bot):
                try:
                    if is_video:
                        sent = await client.send_video(
                            chat_id, str(local_path),
                            caption=caption, progress=up_progress,
                            reply_to_message_id=msg.id,
                            supports_streaming=True,
                        )
                    else:
                        sent = await client.send_document(
                            chat_id, str(local_path),
                            caption=caption, progress=up_progress,
                            reply_to_message_id=msg.id,
                        )
                    break
                except Exception:
                    continue

            # Cleanup local file
            try:
                local_path.unlink(missing_ok=True)
            except Exception:
                pass

            if sent:
                sent_ids.append(sent.id)
                await file_msg.delete()
                await inc_downloads(user_id)
                asyncio.create_task(
                    schedule_delete(chat_id, [sent.id], AUTO_DELETE_SECS)
                )
            else:
                await file_msg.edit_text(f"❌ **Upload fail!**\n`{f['filename']}`")

            if i < len(files) - 1:
                await asyncio.sleep(1)

        # ── Summary ──
        try:
            await status_msg.delete()
        except Exception:
            pass

        if sent_ids:
            doc2  = await get_user(user_id)
            prem2 = is_premium(doc2)
            rem   = "Unlimited" if prem2 else str(FREE_DAILY_LIMIT - doc2["today_downloads"])
            summary = await msg.reply_text(
                f"✅ **Done!** {len(sent_ids)} file(s) sent.\n"
                f"⏳ 1 ghante baad auto-delete ho jaayengi.\n\n"
                f"📊 Remaining today: **{rem}**",
                quote=True,
                reply_markup=upgrade_kb() if not prem2 else None,
            )
            asyncio.create_task(
                schedule_delete(msg.chat.id, [summary.id], AUTO_DELETE_SECS)
            )

    except Exception as e:
        try:
            await status_msg.edit_text(f"❌ **Error:** `{e}`")
        except Exception:
            pass


# ╔══════════════════════════════════════════════════════╗
# ║                       RUN                           ║
# ╚══════════════════════════════════════════════════════╝

async def main():
    from config import DOWNLOAD_DIR, get_cookies
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

    await init_mongo()

    cookies = get_cookies()
    print("🤖 TeraBox VIP Bot starting...")
    print(f"   MongoDB:        ✓")
    print(f"   Cookies:        {'✓ ' + str(len(cookies)) + ' loaded' if cookies else '✗ none (public links only)'}")
    print(f"   String session: {'✓' if STRING_SESSION != 'YOUR_STRING_SESSION' else '✗ NOT SET — 4 GB upload disabled'}")
    print(f"   Auto-delete:    {format_time(AUTO_DELETE_SECS)}")

    await asyncio.gather(bot.start(), user_client.start())
    print("✅ Bot + User client started!\n")
    await bot.idle()


if __name__ == "__main__":
    asyncio.run(main())
