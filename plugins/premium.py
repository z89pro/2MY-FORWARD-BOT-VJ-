"""
plugins/premium.py
──────────────────
Enterprise Premium & VIP Subscription System for Skinet Verse
Inspired by ZSRCBOT / Skinet-Src VIP architecture.

Features:
  1. Tiered VIP Plans (Starter, Pro Monthly, Ultra Lifetime)
  2. Direct UPI Intent & Dynamic 400x400 QR Code Generation
  3. Crypto & Direct Admin Fallback
  4. Manual UTR / Screenshot Proof Submission Workflow
  5. 1-Click Admin Approval & Rejection in LOG_CHANNEL / Owners
  6. Instant VIP Activation, Expiry Tracking & Verification Bypass
  7. /myplan, /plans, /addpremium, /delpremium Admin Management
"""

import os
import time
import asyncio
import logging
import urllib.parse
from datetime import datetime, timezone, timedelta

from pyrogram import Client, filters, enums
from pyrogram import StopPropagation
from pyrogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from buttons import btn, btn_url, row, markup, colored_markup

from config import Config
from database import db

logger = logging.getLogger(__name__)

IST = timezone(timedelta(hours=5, minutes=30))

# ── Plan Specifications ──────────────────────────────────────────────
PLANS = {
    "starter": {
        "id": "starter",
        "name": "🥉 Starter Pass",
        "tag": "Starter (7 Days)",
        "days": 7,
        "price": 49,
        "stars": 35,
        "speed": "1.0s (Fast)",
        "batch_limit": "500 msgs",
        "perks": [
            "⚡ 1.0s Fast Forwarding Speed",
            "🛡️ 0 Token Verification / Captcha Required",
            "📦 500 Messages Batch Forwarding",
            "🤖 1 UserBot / Bot Slot",
            "⏳ 7 Days Full VIP Access"
        ]
    },
    "pro": {
        "id": "pro",
        "name": "🥈 Pro Pass",
        "tag": "Pro Monthly (30 Days)",
        "days": 30,
        "price": 149,
        "stars": 110,
        "speed": "0.5s (Extreme Turbo)",
        "batch_limit": "Unlimited",
        "perks": [
            "⚡ 0.5s Extreme Turbo Speed",
            "🚀 Unlimited Batch Forwarding",
            "📡 Smart AutoSave 24/7 Channel Monitor",
            "🎓 Course Seller Mode & Auto Syllabus Index",
            "🛡️ 0 Verification Forever (Permanent Pass)",
            "🤖 Up to 3 Bot / UserBot Slots",
            "⏳ 30 Days Full VIP Access"
        ]
    },
    "ultra": {
        "id": "ultra",
        "name": "🥇 Ultra Lifetime Pass",
        "tag": "Ultra Lifetime (365 Days)",
        "days": 365,
        "price": 399,
        "stars": 290,
        "speed": "0.2s (Ultra Turbo)",
        "batch_limit": "Unlimited",
        "perks": [
            "⚡ 0.2s Ultra Turbo Speed",
            "🚀 Unlimited Everything & Dedicated Queue",
            "📦 Dedicated Stealth Dump Channel",
            "🎓 Full Course Seller Suite + Indexer",
            "🛡️ Permanent Verification Bypass",
            "🤖 10 UserBot Slots",
            "👑 Priority VIP Allocation & Direct Support",
            "⏳ 365 Days / Lifetime Validity"
        ]
    }
}

# In-memory conversational state: user_id -> {"order_id": str, "mode": "utr" | "screenshot"}
_SUBMIT_STATE = {}


def _get_admin_contact_link() -> str:
    contact = getattr(Config, "ADMIN_CONTACT", "").strip() or "@TheSkinet"
    if contact.startswith(("http://", "https://", "tg://")):
        return contact
    return f"https://t.me/{contact.lstrip('@')}"


def _format_time_ist(epoch: float) -> str:
    if not epoch:
        return "N/A"
    dt = datetime.fromtimestamp(epoch, tz=IST)
    return dt.strftime("%d-%b-%Y %I:%M %p")


def _build_qr_url(data_payload: str) -> str:
    encoded = urllib.parse.quote(data_payload)
    return f"https://api.qrserver.com/v1/create-qr-code/?size=400x400&margin=10&data={encoded}"


def _build_upi_intent(vpa: str, payee_name: str, amount: float, note: str, order_id: str) -> str:
    params = {
        "pa": vpa.strip(),
        "pn": payee_name.strip(),
        "am": f"{float(amount):.2f}",
        "cu": "INR",
        "tn": f"{note} #{order_id[-6:]}",
        "tr": order_id
    }
    return f"upi://pay?{urllib.parse.urlencode(params)}"


# ── UI Builders ───────────────────────────────────────────────────────

async def build_plans_view(user_id: int) -> tuple[str, InlineKeyboardMarkup]:
    prem_user = await db.get_premium_user(user_id)
    is_owner = await db.is_admin(user_id)

    if is_owner:
        user_badge = "👑 <b>ᴏᴡɴᴇʀ / sᴜᴘᴇʀ ᴀᴅᴍɪɴ</b> (ᴘᴇʀᴍᴀɴᴇɴᴛ ᴜɴʟɪᴍɪᴛᴇᴅ ᴠɪᴘ)"
    elif prem_user:
        exp_str = _format_time_ist(prem_user.get("expires_at", 0))
        plan_name = PLANS.get(prem_user.get("plan", "pro"), {}).get("name", "VIP Member")
        user_badge = f"💎 <b>ᴀᴄᴛɪᴠᴇ:</b> {plan_name} (ᴇxᴘɪʀᴇs: <code>{exp_str} IST</code>)"
    else:
        user_badge = "🥉 <b>ғʀᴇᴇ ᴍᴇᴍʙᴇʀ</b> (sᴛᴀɴᴅᴀʀᴅ sᴘᴇᴇᴅ, ᴠᴇʀɪғɪᴄᴀᴛɪᴏɴ ʀᴇǫᴜɪʀᴇᴅ)"

    text = (
        "<blockquote><b>💎 <u>sᴋɪɴᴇᴛ ᴠᴇʀsᴇ — ᴠɪᴘ ᴘʀᴇᴍɪᴜᴍ ᴘʟᴀɴs</u></b></blockquote>\n\n"
        f"<b>ʏᴏᴜʀ sᴛᴀᴛᴜs:</b> {user_badge}\n\n"
        "<i>ᴜɴʟᴏᴄᴋ ᴜɴʀᴇsᴛʀɪᴄᴛᴇᴅ ᴄʜᴀɴɴᴇʟ ᴄʟᴏɴɪɴɢ, ᴇxᴛʀᴇᴍᴇ 0.5s ᴛᴜʀʙᴏ sᴘᴇᴇᴅ, sᴍᴀʀᴛ ᴀᴜᴛᴏsᴀᴠᴇ ʟɪsᴛᴇɴᴇʀs, ᴀɴᴅ ʙʏᴘᴀss ᴀʟʟ ᴠᴇʀɪғɪᴄᴀᴛɪᴏɴs!</i>\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "<b>🥉 sᴛᴀʀᴛᴇʀ ᴘᴀss</b> — <code>₹49</code> (or 35 ⭐ Stars)\n"
        "  • <b>ᴠᴀʟɪᴅɪᴛʏ:</b> 7 ᴅᴀʏs\n"
        "  • <b>sᴘᴇᴇᴅ:</b> 1.0s ғᴀsᴛ ғᴏʀᴡᴀʀᴅ\n"
        "  • <b>ʙᴀᴛᴄʜ:</b> 500 ᴍᴇssᴀɢᴇs\n"
        "  • <b>ᴘᴇʀᴋs:</b> 0 ᴠᴇʀɪғɪᴄᴀᴛɪᴏɴ ʀᴇǫᴜɪʀᴇᴅ · 1 ʙᴏᴛ sʟᴏᴛ\n\n"
        "<b>🥈 ᴘʀᴏ ᴍᴏɴᴛʜʟʏ ᴘᴀss</b> — <code>₹149</code> (or 110 ⭐ Stars) 🔥 <b>POPULAR</b>\n"
        "  • <b>ᴠᴀʟɪᴅɪᴛʏ:</b> 30 ᴅᴀʏs\n"
        "  • <b>sᴘᴇᴇᴅ:</b> 0.5s ᴇxᴛʀᴇᴍᴇ ᴛᴜʀʙᴏ\n"
        "  • <b>ʙᴀᴛᴄʜ:</b> ᴜɴʟɪᴍɪᴛᴇᴅ ғᴏʀᴡᴀʀᴅɪɴɢ\n"
        "  • <b>ᴘᴇʀᴋs:</b> ᴀᴜᴛᴏsᴀᴠᴇ ᴍᴏɴɪᴛᴏʀ · ᴄᴏᴜʀsᴇ sᴇʟʟᴇʀ ᴍᴏᴅᴇ · 3 ʙᴏᴛ sʟᴏᴛs · 0 ᴠᴇʀɪғɪᴄᴀᴛɪᴏɴ\n\n"
        "<b>🥇 ᴜʟᴛʀᴀ ʟɪғᴇᴛɪᴍᴇ ᴘᴀss</b> — <code>₹399</code> (or 290 ⭐ Stars) 👑 <b>BEST VALUE</b>\n"
        "  • <b>ᴠᴀʟɪᴅɪᴛʏ:</b> 365 ᴅᴀʏs / ʟɪғᴇᴛɪᴍᴇ\n"
        "  • <b>sᴘᴇᴇᴅ:</b> 0.2s ᴜʟᴛʀᴀ ᴛᴜʀʙᴏ\n"
        "  • <b>ʙᴀᴛᴄʜ:</b> ᴜɴʟɪᴍɪᴛᴇᴅ ᴇᴠᴇʀʏᴛʜɪɴɢ\n"
        "  • <b>ᴘᴇʀᴋs:</b> ᴅᴇᴅɪᴄᴀᴛᴇᴅ ᴅᴜᴍᴘ ᴄʜᴀɴɴᴇʟ · 10 ʙᴏᴛ sʟᴏᴛs · ᴘʀɪᴏʀɪᴛʏ ᴀʟʟᴏᴄᴀᴛɪᴏɴ\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "👇 <b>sᴇʟᴇᴄᴛ ᴀ ᴘʟᴀɴ ʙᴇʟᴏᴡ ᴛᴏ ᴘᴜʀᴄʜᴀsᴇ ᴠɪᴀ ᴜᴘɪ / ǫʀ ᴏʀ ᴄᴏɴᴛᴀᴄᴛ ᴀᴅᴍɪɴ:</b>"
    )

    admin_link = _get_admin_contact_link()
    rows = [
        row(
            btn("🥉 ʙᴜʏ sᴛᴀʀᴛᴇʀ (₹49)", "prem_buy_starter", "green"),
            btn("🥈 ʙᴜʏ ᴘʀᴏ (₹149)", "prem_buy_pro", "green")
        ),
        row(
            btn("🥇 ʙᴜʏ ᴜʟᴛʀᴀ ʟɪғᴇᴛɪᴍᴇ (₹399)", "prem_buy_ultra", "green")
        ),
        row(
            btn("💳 ᴍʏ ᴀᴄᴛɪᴠᴇ ᴘʟᴀɴ", "prem_myplan", "blue"),
            btn_url("💬 ᴄᴏɴᴛᴀᴄᴛ ᴀᴅᴍɪɴ", admin_link, "blue")
        )
    ]
    if is_owner or await db.is_admin(user_id):
        rows.append(row(btn("👑 ᴠɪᴘ ᴀᴅᴍɪɴ ᴘᴀɴᴇʟ", "vipadmin_main", "yellow")))
    rows.append(row(btn("🔙 ʙᴀᴄᴋ ᴛᴏ ʜᴏᴍᴇ", "back", "blue"), btn("❌ ᴄʟᴏsᴇ", "close_btn", "red")))
    return text, markup(*rows)


# ── Commands ──────────────────────────────────────────────────────────

@Client.on_message(filters.private & filters.command(["plans", "premium", "buy", "vip"]))
async def plans_cmd(bot: Client, message: Message):
    text, reply_markup = await build_plans_view(message.from_user.id)
    await message.reply_text(text, reply_markup=reply_markup, disable_web_page_preview=True, quote=True)


@Client.on_message(filters.private & filters.command(["myplan", "plan"]))
async def myplan_cmd(bot: Client, message: Message):
    user_id = message.from_user.id
    prem_user = await db.get_premium_user(user_id)
    is_owner = await db.is_admin(user_id)

    if is_owner:
        txt = (
            "<blockquote><b>👑 <u>ʏᴏᴜʀ ᴠɪᴘ sᴛᴀᴛᴜs — sᴜᴘᴇʀ ᴀᴅᴍɪɴ</u></b></blockquote>\n\n"
            "• <b>Tier:</b> <code>Lifetime Super Admin</code>\n"
            "• <b>Expires:</b> <code>Never (Permanent)</code>\n"
            "• <b>Speed:</b> <code>0.2s Ultra Turbo</code>\n"
            "• <b>Batch Limit:</b> <code>Unlimited</code>\n"
            "• <b>AutoSave:</b> <code>Full Multi-Channel</code>\n"
            "• <b>Verification:</b> <code>Permanent Bypass</code>"
        )
    elif prem_user:
        plan_info = PLANS.get(prem_user.get("plan", "pro"), PLANS["pro"])
        exp_str = _format_time_ist(prem_user.get("expires_at", 0))
        rem_secs = max(0, int(prem_user.get("expires_at", 0) - time.time()))
        rem_days = rem_secs // 86400
        rem_hrs = (rem_secs % 86400) // 3600

        perks_formatted = "\n".join([f"  • {p}" for p in plan_info["perks"]])

        txt = (
            f"<blockquote><b>💎 <u>ʏᴏᴜʀ ᴠɪᴘ sᴛᴀᴛᴜs — {plan_info['name'].upper()}</u></b></blockquote>\n\n"
            f"• <b>Plan:</b> {plan_info['name']}\n"
            f"• <b>Expiry Date:</b> <code>{exp_str} IST</code>\n"
            f"• <b>Remaining:</b> <code>{rem_days} Days, {rem_hrs} Hours</code>\n"
            f"• <b>Speed:</b> <code>{plan_info['speed']}</code>\n"
            f"• <b>Batch Limit:</b> <code>{plan_info['batch_limit']}</code>\n\n"
            f"<b>Active Perks:</b>\n{perks_formatted}"
        )
    else:
        txt = (
            "<blockquote><b>🥉 <u>ʏᴏᴜʀ ᴠɪᴘ sᴛᴀᴛᴜs — ғʀᴇᴇ ᴍᴇᴍʙᴇʀ</u></b></blockquote>\n\n"
            "• <b>Current Plan:</b> <code>Free Tier</code>\n"
            "• <b>Forward Speed:</b> <code>Normal / Fast (1.0s - 3.0s)</code>\n"
            "• <b>Verification:</b> <code>Required via Shortener / Referral</code>\n"
            "• <b>AutoSave:</b> <code>Basic</code>\n\n"
            "👉 <i>Upgrade to VIP Premium for extreme 0.5s turbo speed, 0 captcha, and unlimited channels!</i>"
        )

    btn_list = [
        row(btn("💎 ᴠɪᴇᴡ ᴠɪᴘ ᴘʟᴀɴs", "prem_plans", "green")),
        row(btn("🔙 ʙᴀᴄᴋ ᴛᴏ ʜᴏᴍᴇ", "back", "red"))
    ]
    await message.reply_text(txt, reply_markup=markup(*btn_list), quote=True)


# ── Enterprise VIP Admin Control Center & Commands ───────────────────

VIP_PAGE_SIZE = 5

async def build_vip_admin_view() -> tuple[str, InlineKeyboardMarkup]:
    prem_count = await db.get_premium_count()
    pending_orders = await db.get_pending_premium_orders(limit=100)
    upi_id = getattr(Config, "UPI_ID", "").strip() or "<i>ɴᴏᴛ sᴇᴛ</i>"

    text = (
        "<blockquote><b>👑 <u>sᴋɪɴᴇᴛ ᴠᴇʀsᴇ — ᴠɪᴘ ᴀᴅᴍɪɴ ᴄᴏɴᴛʀᴏʟ ᴄᴇɴᴛᴇʀ</u></b></blockquote>\n\n"
        "<i>ᴍᴀɴᴀɢᴇ ᴜsᴇʀ sᴜʙsᴄʀɪᴘᴛɪᴏɴs, ɢʀᴀɴᴛ / ʀᴇᴠᴏᴋᴇ ᴠɪᴘ, ʀᴇᴠɪᴇᴡ ᴘᴀʏᴍᴇɴᴛ ᴘʀᴏᴏғs, ᴀɴᴅ ᴛʀᴀᴄᴋ ᴀᴄᴛɪᴠᴇ ᴍᴇᴍʙᴇʀs.</i>\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"💎 <b>ᴀᴄᴛɪᴠᴇ ᴠɪᴘ ᴜsᴇʀs:</b> <code>{prem_count}</code>\n"
        f"💳 <b>ᴘᴇɴᴅɪɴɢ ᴏʀᴅᴇʀs:</b> <code>{len(pending_orders)}</code>\n"
        f"📲 <b>ᴜᴘɪ ᴘᴀʏᴍᴇɴᴛ ɪᴅ:</b> <code>{upi_id}</code>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "👇 <b>sᴇʟᴇᴄᴛ ᴀɴ ᴀᴅᴍɪɴɪsᴛʀᴀᴛɪᴠᴇ ᴀᴄᴛɪᴏɴ:</b>"
    )

    rows = [
        row(
            btn("➕ ɢʀᴀɴᴛ ᴠɪᴘ", "vipadmin_grant_prompt", "green"),
            btn("➖ ʀᴇᴠᴏᴋᴇ ᴠɪᴘ", "vipadmin_revoke_prompt", "red")
        ),
        row(
            btn(f"📋 ᴀᴄᴛɪᴠᴇ ᴠɪᴘs ({prem_count})", "vipadmin_list_0", "blue"),
            btn(f"💳 ᴘᴇɴᴅɪɴɢ ᴏʀᴅᴇʀs ({len(pending_orders)})", "vipadmin_orders_0", "yellow")
        ),
        row(
            btn("💎 ᴠɪᴇᴡ ᴘʟᴀɴs", "prem_plans", "blue"),
            btn("⚙️ sʏsᴛᴇᴍ ᴄᴏɴғɪɢ", "config#main", "blue")
        ),
        row(
            btn("🔙 ʙᴀᴄᴋ ᴛᴏ ʜᴏᴍᴇ", "back", "blue"),
            btn("❌ ᴄʟᴏsᴇ", "close_btn", "red")
        )
    ]
    return text, markup(*rows)


async def build_vip_list_view(page: int = 0) -> tuple[str, InlineKeyboardMarkup]:
    prem_users = await db.get_all_premium_users()
    total = len(prem_users)
    if not prem_users:
        text = (
            "<blockquote><b>📋 <u>ᴀᴄᴛɪᴠᴇ ᴠɪᴘ sᴜʙsᴄʀɪʙᴇʀs</u></b></blockquote>\n\n"
            "<i>ɴᴏ ᴀᴄᴛɪᴠᴇ ᴠɪᴘ sᴜʙsᴄʀɪʙᴇʀs ғᴏᴜɴᴅ ɪɴ ᴅᴀᴛᴀʙᴀsᴇ.</i>\n\n"
            "💡 ᴜsᴇ <b>➕ ɢʀᴀɴᴛ ᴠɪᴘ</b> ᴛᴏ ᴍᴀɴᴜᴀʟʟʏ ᴀᴄᴛɪᴠᴀᴛᴇ ᴀ ᴜsᴇʀ."
        )
        buttons = [
            row(btn("➕ ɢʀᴀɴᴛ ᴠɪᴘ", "vipadmin_grant_prompt", "green")),
            row(btn("🔙 ᴠɪᴘ ᴀᴅᴍɪɴ", "vipadmin_main", "blue"), btn("❌ ᴄʟᴏsᴇ", "close_btn", "red"))
        ]
        return text, markup(*buttons)

    prem_users.sort(key=lambda x: x.get("expires_at", 0))

    total_pages = max(1, (total + VIP_PAGE_SIZE - 1) // VIP_PAGE_SIZE)
    page = max(0, min(page, total_pages - 1))
    slice_users = prem_users[page * VIP_PAGE_SIZE : (page + 1) * VIP_PAGE_SIZE]

    lines = [
        "<blockquote><b>📋 <u>ᴀᴄᴛɪᴠᴇ ᴠɪᴘ sᴜʙsᴄʀɪʙᴇʀs</u></b></blockquote>\n\n",
        f"ᴛᴏᴛᴀʟ ᴀᴄᴛɪᴠᴇ: <code>{total}</code> | ᴘᴀɢᴇ <code>{page + 1}/{total_pages}</code>\n",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    ]

    action_rows = []
    now = time.time()
    for u in slice_users:
        uid = u.get("user_id")
        plan_key = u.get("plan", "pro")
        plan_name = PLANS.get(plan_key, {}).get("name", plan_key.upper())
        exp_ts = u.get("expires_at", 0)
        exp_str = _format_time_ist(exp_ts)
        rem_days = max(0, int((exp_ts - now) // 86400))
        lines.append(f"• 👤 <code>{uid}</code> — {plan_name}\n   ⏳ <code>{rem_days}ᴅ ʟᴇғᴛ</code> · ᴇxᴘ: <code>{exp_str}</code>\n")
        action_rows.append(
            row(
                btn(f"🗑️ ʀᴇᴠᴏᴋᴇ {uid}", f"vipadmin_quickrev_{uid}_{page}", "red"),
                btn(f"➕ +30ᴅ", f"vipadmin_quickext_{uid}_30_{page}", "blue")
            )
        )

    nav_buttons = []
    if page > 0:
        nav_buttons.append(btn("◀️ ᴘʀᴇᴠ", f"vipadmin_list_{page - 1}", "blue"))
    nav_buttons.append(btn(f"• {page + 1}/{total_pages} •", "noop", "blue"))
    if page < total_pages - 1:
        nav_buttons.append(btn("ɴᴇxᴛ ▶️", f"vipadmin_list_{page + 1}", "blue"))

    if nav_buttons:
        action_rows.append(row(*nav_buttons))

    action_rows.append(
        row(
            btn("➕ ɢʀᴀɴᴛ ᴠɪᴘ", "vipadmin_grant_prompt", "green"),
            btn("🔙 ᴠɪᴘ ᴀᴅᴍɪɴ", "vipadmin_main", "blue"),
            btn("❌ ᴄʟᴏsᴇ", "close_btn", "red")
        )
    )
    return "".join(lines), markup(*action_rows)


async def build_vip_orders_view(page: int = 0) -> tuple[str, InlineKeyboardMarkup]:
    orders = await db.get_pending_premium_orders(limit=50)
    if not orders:
        text = (
            "<blockquote><b>💳 <u>ᴘᴇɴᴅɪɴɢ ᴠɪᴘ ᴏʀᴅᴇʀs</u></b></blockquote>\n\n"
            "✅ <i>ɴᴏ ᴘᴇɴᴅɪɴɢ ᴏʀ ᴜɴʀᴇᴠɪᴇᴡᴇᴅ ᴏʀᴅᴇʀs ᴀᴛ ᴛʜɪs ᴛɪᴍᴇ.</i>\n\n"
            "ᴀʟʟ sᴜʙᴍɪᴛᴛᴇᴅ ᴘᴀʏᴍᴇɴᴛ ᴘʀᴏᴏғs ʜᴀᴠᴇ ʙᴇᴇɴ ᴘʀᴏᴄᴇssᴇᴅ!"
        )
        buttons = [row(btn("🔙 ᴠɪᴘ ᴀᴅᴍɪɴ", "vipadmin_main", "blue"), btn("❌ ᴄʟᴏsᴇ", "close_btn", "red"))]
        return text, markup(*buttons)

    order_rows = []
    lines = [
        "<blockquote><b>💳 <u>ᴘᴇɴᴅɪɴɢ ᴠɪᴘ ᴏʀᴅᴇʀs</u></b></blockquote>\n\n",
        f"ᴛᴏᴛᴀʟ ᴘᴇɴᴅɪɴɢ: <code>{len(orders)}</code>\n",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    ]
    for ord_doc in orders[:5]:
        oid = ord_doc.get("order_id")
        uid = ord_doc.get("user_id")
        amt = ord_doc.get("amount", 0)
        pl = ord_doc.get("plan", "pro")
        pl_name = PLANS.get(pl, {}).get("name", pl.upper())
        utr = ord_doc.get("utr") or ("sᴄʀᴇᴇɴsʜᴏᴛ" if ord_doc.get("screenshot") else "ɴᴏ ᴘʀᴏᴏғ")
        st = ord_doc.get("status", "pending")
        created_str = _format_time_ist(ord_doc.get("created_at", 0))

        lines.append(
            f"🆔 <code>{oid}</code>\n"
            f"👤 <code>{uid}</code> | {pl_name} (₹{amt:.0f})\n"
            f"🧾 ʀᴇғ: <code>{utr}</code> | sᴛᴀᴛᴜs: <code>{st}</code>\n"
            f"🕒 <code>{created_str}</code>\n\n"
        )
        order_rows.append(
            row(
                btn(f"✅ ᴀᴘᴘʀᴏᴠᴇ #{oid[-6:]}", f"prem_appr_{uid}_{pl}_{oid}", "green"),
                btn(f"❌ ʀᴇᴊᴇᴄᴛ", f"prem_rej_{uid}_{oid}", "red")
            )
        )

    order_rows.append(row(btn("🔙 ᴠɪᴘ ᴀᴅᴍɪɴ", "vipadmin_main", "blue"), btn("❌ ᴄʟᴏsᴇ", "close_btn", "red")))
    return "".join(lines), markup(*order_rows)


@Client.on_message(filters.command(["vipadmin", "premiumadmin"]))
async def vipadmin_cmd(bot: Client, message: Message):
    if not await db.is_admin(message.from_user.id):
        return await message.reply_text("⚠️ <b>ᴀᴄᴄᴇss ᴅᴇɴɪᴇᴅ:</b> ᴀᴅᴍɪɴ ᴏɴʟʏ ᴄᴏᴍᴍᴀɴᴅ.", quote=True)
    text, reply_markup = await build_vip_admin_view()
    await message.reply_text(text, reply_markup=reply_markup, quote=True)


@Client.on_message(filters.command(["addpremium", "addvip"]))
async def admin_add_premium(bot: Client, message: Message):
    if not await db.is_admin(message.from_user.id):
        return await message.reply_text("⚠️ <b>ᴀᴄᴄᴇss ᴅᴇɴɪᴇᴅ:</b> ᴀᴅᴍɪɴ ᴏɴʟʏ ᴄᴏᴍᴍᴀɴᴅ.", quote=True)

    reply = message.reply_to_message
    args = message.command[1:]

    target_uid = None
    days = 30
    plan_key = "pro"

    # Case 1: Replying to user message
    if reply and reply.from_user:
        target_uid = reply.from_user.id
        if len(args) >= 1:
            val = args[0].lower()
            if val in ("lifetime", "life"):
                days = 3650
                plan_key = "ultra"
            elif val.isdigit():
                days = int(val)
                if days <= 7:
                    plan_key = "starter"
                elif days >= 365:
                    plan_key = "ultra"
            elif val in PLANS:
                plan_key = val
                days = PLANS[val]["days"]
        if len(args) >= 2:
            val2 = args[1].lower()
            if val2 in PLANS:
                plan_key = val2

    # Case 2: Argument specified directly
    elif args:
        val0 = args[0].strip()
        if val0.isdigit() or (val0.startswith("-100") and val0[1:].isdigit()):
            target_uid = int(val0)
        elif val0.startswith("@"):
            try:
                user_obj = await bot.get_users(val0)
                target_uid = user_obj.id
            except Exception as e:
                return await message.reply_text(f"❌ <b>ᴜsᴇʀ ɴᴏᴛ ғᴏᴜɴᴅ:</b> {e}", quote=True)
        else:
            return await message.reply_text(
                "❌ <b>ɪɴᴠᴀʟɪᴅ ᴜsᴇʀ ɪᴅ ᴏʀ ᴜsᴇʀɴᴀᴍᴇ.</b>\n\n"
                "<b>ᴜsᴀɢᴇ:</b> <code>/addpremium &lt;user_id&gt; [days] [plan]</code>\n"
                "<b>ᴇxᴀᴍᴘʟᴇ:</b> <code>/addpremium 123456789 30 pro</code>",
                quote=True
            )

        if len(args) >= 2:
            val1 = args[1].lower()
            if val1 in ("lifetime", "life"):
                days = 3650
                plan_key = "ultra"
            elif val1.isdigit():
                days = int(val1)
                if days <= 7:
                    plan_key = "starter"
                elif days >= 365:
                    plan_key = "ultra"
            elif val1 in PLANS:
                plan_key = val1
                days = PLANS[val1]["days"]

        if len(args) >= 3:
            val2 = args[2].lower()
            if val2 in PLANS:
                plan_key = val2

    # Case 3: Neither reply nor arguments -> Open Interactive VIP Admin Panel
    else:
        text, reply_markup = await build_vip_admin_view()
        return await message.reply_text(text, reply_markup=reply_markup, quote=True)

    new_expires = await db.set_premium_user(target_uid, days, plan_key, activated_by=message.from_user.id)
    exp_str = _format_time_ist(new_expires)
    plan_name = PLANS.get(plan_key, PLANS["pro"])["name"]

    success_markup = markup(
        row(
            btn("➕ +7 ᴅᴀʏs", f"vipadmin_quickext_{target_uid}_7_0", "blue"),
            btn("➕ +30 ᴅᴀʏs", f"vipadmin_quickext_{target_uid}_30_0", "blue"),
            btn("🗑️ ʀᴇᴠᴏᴋᴇ", f"vipadmin_quickrev_{target_uid}_0", "red")
        ),
        row(btn("👑 ᴠɪᴘ ᴀᴅᴍɪɴ", "vipadmin_main", "yellow"))
    )

    await message.reply_text(
        f"✅ <b><u>ᴘʀᴇᴍɪᴜᴍ ᴠɪᴘ sᴜᴄᴄᴇssғᴜʟʟʏ ɢʀᴀɴᴛᴇᴅ!</u></b>\n\n"
        f"👤 <b>ᴜsᴇʀ ɪᴅ:</b> <code>{target_uid}</code>\n"
        f"💎 <b>ᴘʟᴀɴ:</b> {plan_name}\n"
        f"⏳ <b>ᴅᴜʀᴀᴛɪᴏɴ ᴀᴅᴅᴇᴅ:</b> <code>{days} ᴅᴀʏs</code>\n"
        f"📅 <b>ᴠᴀʟɪᴅ ᴜɴᴛɪʟ:</b> <code>{exp_str} IST</code>\n"
        f"🛡️ <b>ᴠᴇʀɪғɪᴄᴀᴛɪᴏɴ:</b> <code>ʙʏᴘᴀssᴇᴅ (0 ᴄᴀᴘᴛᴄʜᴀ)</code>\n"
        f"⚡️ <b>sᴘᴇᴇᴅ ᴛɪᴇʀ:</b> <code>{PLANS.get(plan_key, PLANS['pro'])['speed']}</code>",
        reply_markup=success_markup,
        quote=True
    )

    try:
        await bot.send_message(
            target_uid,
            (
                "<blockquote><b>🎉 <u>ʏᴏᴜʀ ᴠɪᴘ ᴘʀᴇᴍɪᴜᴍ ʜᴀs ʙᴇᴇɴ ᴀᴄᴛɪᴠᴀᴛᴇᴅ!</u></b></blockquote>\n\n"
                f"ᴀɴ ᴀᴅᴍɪɴɪsᴛʀᴀᴛᴏʀ ʜᴀs ɢʀᴀɴᴛᴇᴅ ʏᴏᴜ ᴠɪᴘ sᴜʙsᴄʀɪᴘᴛɪᴏɴ ᴀᴄᴄᴇss!\n\n"
                f"💎 <b>ᴘʟᴀɴ:</b> {plan_name}\n"
                f"⏳ <b>ᴠᴀʟɪᴅɪᴛʏ:</b> <code>{days} ᴅᴀʏs</code>\n"
                f"📅 <b>ᴇxᴘɪʀᴇs:</b> <code>{exp_str} IST</code>\n\n"
                "<b>✨ ᴜɴʟᴏᴄᴋᴇᴅ ᴘᴇʀᴋs:</b>\n"
                "• ⚡️ ᴇxᴛʀᴇᴍᴇ 0.5s ᴛᴜʀʙᴏ ғᴏʀᴡᴀʀᴅɪɴɢ\n"
                "• 🛡️ 0 ᴛᴏᴋᴇɴ ᴠᴇʀɪғɪᴄᴀᴛɪᴏɴ / ᴄᴀᴘᴛᴄʜᴀ ʀᴇǫᴜɪʀᴇᴅ\n"
                "• 🚀 ᴜɴʟɪᴍɪᴛᴇᴅ ʙᴀᴛᴄʜ ғᴏʀᴡᴀʀᴅɪɴɢ\n"
                "• 📡 sᴍᴀʀᴛ ᴀᴜᴛᴏsᴀᴠᴇ 24/7 ᴄʜᴀɴɴᴇʟ ᴍᴏɴɪᴛᴏʀ\n"
                "• 🎓 ᴄᴏᴜʀsᴇ sᴇʟʟᴇʀ sʏʟʟᴀʙᴜs ɪɴᴅᴇxᴇʀ\n\n"
                "<i>ᴇɴᴊᴏʏ ᴜɴʀᴇsᴛʀɪᴄᴛᴇᴅ ᴀᴄᴄᴇss ᴡɪᴛʜ sᴋɪɴᴇᴛ ᴠᴇʀsᴇ!</i>"
            ),
            reply_markup=markup(row(btn("💎 ᴠɪᴇᴡ ᴍʏ ᴘʟᴀɴ", "prem_myplan", "green")))
        )
    except Exception as e:
        logger.debug(f"Could not notify user {target_uid} of VIP grant: {e}")


@Client.on_message(filters.command(["delpremium", "delvip"]))
async def admin_del_premium(bot: Client, message: Message):
    if not await db.is_admin(message.from_user.id):
        return await message.reply_text("⚠️ <b>ᴀᴄᴄᴇss ᴅᴇɴɪᴇᴅ:</b> ᴀᴅᴍɪɴ ᴏɴʟʏ ᴄᴏᴍᴍᴀɴᴅ.", quote=True)

    reply = message.reply_to_message
    args = message.command[1:]

    target_uid = None
    if reply and reply.from_user:
        target_uid = reply.from_user.id
    elif args:
        val0 = args[0].strip()
        if val0.isdigit() or (val0.startswith("-100") and val0[1:].isdigit()):
            target_uid = int(val0)
        elif val0.startswith("@"):
            try:
                user_obj = await bot.get_users(val0)
                target_uid = user_obj.id
            except Exception as e:
                return await message.reply_text(f"❌ <b>ᴜsᴇʀ ɴᴏᴛ ғᴏᴜɴᴅ:</b> {e}", quote=True)
        else:
            return await message.reply_text("❌ <b>ɪɴᴠᴀʟɪᴅ ᴜsᴇʀ ɪᴅ ᴏʀ ᴜsᴇʀɴᴀᴍᴇ.</b>", quote=True)
    else:
        return await message.reply_text(
            "<b><u>🗑️ ʀᴇᴠᴏᴋᴇ ᴠɪᴘ sᴜʙsᴄʀɪᴘᴛɪᴏɴ</u></b>\n\n"
            "<b>ᴜsᴀɢᴇ:</b>\n"
            "• ʀᴇᴘʟʏ ᴛᴏ ᴀɴʏ ᴜsᴇʀ ᴍᴇssᴀɢᴇ ᴡɪᴛʜ <code>/delpremium</code>\n"
            "• ᴏʀ ᴛʏᴘᴇ <code>/delpremium &lt;user_id&gt;</code>\n"
            "• ᴏʀ ᴜsᴇ ᴛʜᴇ ɪɴᴛᴇʀᴀᴄᴛɪᴠᴇ ʟɪsᴛ ʙᴇʟᴏᴡ:",
            reply_markup=markup(
                row(btn("📋 ᴠɪᴇᴡ ᴀᴄᴛɪᴠᴇ ᴠɪᴘs", "vipadmin_list_0", "blue")),
                row(btn("👑 ᴠɪᴘ ᴀᴅᴍɪɴ ᴘᴀɴᴇʟ", "vipadmin_main", "yellow"))
            ),
            quote=True
        )

    await db.remove_premium_user(target_uid)
    await message.reply_text(
        f"✅ <b>ᴘʀᴇᴍɪᴜᴍ ᴠɪᴘ ʀᴇᴍᴏᴠᴇᴅ ғᴏʀ ᴜsᴇʀ <code>{target_uid}</code>.</b>",
        reply_markup=markup(row(btn("👑 ᴠɪᴘ ᴀᴅᴍɪɴ", "vipadmin_main", "blue"))),
        quote=True
    )
    try:
        await bot.send_message(
            target_uid,
            (
                "<blockquote><b>⚠️ <u>ʏᴏᴜʀ ᴠɪᴘ sᴜʙsᴄʀɪᴘᴛɪᴏɴ ʜᴀs ᴇxᴘɪʀᴇᴅ / ʀᴇᴠᴏᴋᴇᴅ</u></b></blockquote>\n\n"
                "ʏᴏᴜʀ ᴠɪᴘ ᴘᴀss ʜᴀs ʙᴇᴇɴ ʀᴇᴠᴏᴋᴇᴅ ᴏʀ ʜᴀs ᴇxᴘɪʀᴇᴅ.\n"
                "ᴜsᴇ /plans ᴛᴏ ʀᴇɴᴇᴡ ᴏʀ ᴜᴘɢʀᴀᴅᴇ ʏᴏᴜʀ ᴘʟᴀɴ ᴀᴛ ᴀɴʏ ᴛɪᴍᴇ."
            ),
            reply_markup=markup(row(btn("💎 ᴠɪᴇᴡ ᴠɪᴘ ᴘʟᴀɴs", "prem_plans", "green")))
        )
    except Exception:
        pass


# ── VIP Admin Callback Handlers ────────────────────────────────────────

@Client.on_callback_query(filters.regex(r"^vipadmin_main$"))
async def cb_vipadmin_main(bot: Client, query: CallbackQuery):
    if not await db.is_admin(query.from_user.id):
        return await query.answer("⚠️ Admin only!", show_alert=True)
    text, reply_markup = await build_vip_admin_view()
    await query.message.edit_text(text, reply_markup=reply_markup)


@Client.on_callback_query(filters.regex(r"^vipadmin_list_(\d+)$"))
async def cb_vipadmin_list(bot: Client, query: CallbackQuery):
    if not await db.is_admin(query.from_user.id):
        return await query.answer("⚠️ Admin only!", show_alert=True)
    page = int(query.matches[0].group(1))
    text, reply_markup = await build_vip_list_view(page)
    await query.message.edit_text(text, reply_markup=reply_markup)


@Client.on_callback_query(filters.regex(r"^vipadmin_orders_(\d+)$"))
async def cb_vipadmin_orders(bot: Client, query: CallbackQuery):
    if not await db.is_admin(query.from_user.id):
        return await query.answer("⚠️ Admin only!", show_alert=True)
    page = int(query.matches[0].group(1))
    text, reply_markup = await build_vip_orders_view(page)
    await query.message.edit_text(text, reply_markup=reply_markup)


@Client.on_callback_query(filters.regex(r"^vipadmin_grant_prompt$"))
async def cb_vipadmin_grant_prompt(bot: Client, query: CallbackQuery):
    if not await db.is_admin(query.from_user.id):
        return await query.answer("⚠️ Admin only!", show_alert=True)

    await query.answer()
    try:
        ask_msg = await bot.ask(
            chat_id=query.message.chat.id,
            text=(
                "<blockquote><b>➕ <u>ɢʀᴀɴᴛ ᴠɪᴘ sᴜʙsᴄʀɪᴘᴛɪᴏɴ</u></b></blockquote>\n\n"
                "ᴘʟᴇᴀsᴇ sᴇɴᴅ ᴛʜᴇ ᴛᴀʀɢᴇᴛ <b>ᴜsᴇʀ ɪᴅ</b> ᴏʀ <b>@ᴜsᴇʀɴᴀᴍᴇ</b>:\n\n"
                "<i>sᴇɴᴅ <code>/cancel</code> ᴛᴏ ᴀʙᴏʀᴛ.</i>"
            ),
            filters=filters.text,
            timeout=120
        )
    except Exception as e:
        return await query.message.reply_text(f"⚠️ <b>ᴘʀᴏᴍᴘᴛ ᴛɪᴍᴇᴏᴜᴛ ᴏʀ ᴇʀʀᴏʀ:</b> {e}")

    if not ask_msg.text or ask_msg.text.strip().lower() == "/cancel":
        return await query.message.reply_text("❌ <b>ᴏᴘᴇʀᴀᴛɪᴏɴ ᴄᴀɴᴄᴇʟʟᴇᴅ.</b>")

    raw_input = ask_msg.text.strip()
    target_uid = None
    if raw_input.isdigit() or (raw_input.startswith("-100") and raw_input[1:].isdigit()):
        target_uid = int(raw_input)
    elif raw_input.startswith("@"):
        try:
            u_obj = await bot.get_users(raw_input)
            target_uid = u_obj.id
        except Exception as e:
            return await query.message.reply_text(f"❌ <b>ᴜsᴇʀ ɴᴏᴛ ғᴏᴜɴᴅ:</b> {e}")
    else:
        return await query.message.reply_text("❌ <b>ɪɴᴠᴀʟɪᴅ ᴜsᴇʀ ɪᴅ. ᴍᴜsᴛ ʙᴇ ɴᴜᴍᴇʀɪᴄ ᴏʀ @ᴜsᴇʀɴᴀᴍᴇ.</b>")

    dur_markup = markup(
        row(
            btn("🥉 7 ᴅᴀʏs (₹49)", f"vipadmin_set_{target_uid}_7_starter", "green"),
            btn("🥈 30 ᴅᴀʏs (₹149)", f"vipadmin_set_{target_uid}_30_pro", "green")
        ),
        row(
            btn("🥇 365 ᴅᴀʏs (₹399)", f"vipadmin_set_{target_uid}_365_ultra", "green"),
            btn("👑 ʟɪғᴇᴛɪᴍᴇ (10 ʏʀ)", f"vipadmin_set_{target_uid}_3650_ultra", "yellow")
        ),
        row(
            btn("🔙 ᴠɪᴘ ᴀᴅᴍɪɴ", "vipadmin_main", "red")
        )
    )

    await query.message.reply_text(
        f"<blockquote><b>💎 <u>sᴇʟᴇᴄᴛ ᴠɪᴘ ᴘʟᴀɴ ᴅᴜʀᴀᴛɪᴏɴ</u></b></blockquote>\n\n"
        f"👤 <b>ᴛᴀʀɢᴇᴛ ᴜsᴇʀ:</b> <code>{target_uid}</code>\n\n"
        "ᴄʜᴏᴏsᴇ ᴛʜᴇ sᴜʙsᴄʀɪᴘᴛɪᴏɴ ᴅᴜʀᴀᴛɪᴏɴ ᴛᴏ ᴀᴄᴛɪᴠᴀᴛᴇ ɪɴsᴛᴀɴᴛʟʏ:",
        reply_markup=dur_markup
    )


@Client.on_callback_query(filters.regex(r"^vipadmin_revoke_prompt$"))
async def cb_vipadmin_revoke_prompt(bot: Client, query: CallbackQuery):
    if not await db.is_admin(query.from_user.id):
        return await query.answer("⚠️ Admin only!", show_alert=True)

    await query.answer()
    try:
        ask_msg = await bot.ask(
            chat_id=query.message.chat.id,
            text=(
                "<blockquote><b>🗑️ <u>ʀᴇᴠᴏᴋᴇ ᴠɪᴘ sᴜʙsᴄʀɪᴘᴛɪᴏɴ</u></b></blockquote>\n\n"
                "ᴘʟᴇᴀsᴇ sᴇɴᴅ ᴛʜᴇ <b>ᴜsᴇʀ ɪᴅ</b> ᴏʀ <b>@ᴜsᴇʀɴᴀᴍᴇ</b> ᴛᴏ ʀᴇᴠᴏᴋᴇ:\n\n"
                "<i>sᴇɴᴅ <code>/cancel</code> ᴛᴏ ᴀʙᴏʀᴛ.</i>"
            ),
            filters=filters.text,
            timeout=120
        )
    except Exception as e:
        return await query.message.reply_text(f"⚠️ <b>ᴘʀᴏᴍᴘᴛ ᴛɪᴍᴇᴏᴜᴛ ᴏʀ ᴇʀʀᴏʀ:</b> {e}")

    if not ask_msg.text or ask_msg.text.strip().lower() == "/cancel":
        return await query.message.reply_text("❌ <b>ᴏᴘᴇʀᴀᴛɪᴏɴ ᴄᴀɴᴄᴇʟʟᴇᴅ.</b>")

    raw_input = ask_msg.text.strip()
    target_uid = None
    if raw_input.isdigit():
        target_uid = int(raw_input)
    elif raw_input.startswith("@"):
        try:
            u_obj = await bot.get_users(raw_input)
            target_uid = u_obj.id
        except Exception as e:
            return await query.message.reply_text(f"❌ <b>ᴜsᴇʀ ɴᴏᴛ ғᴏᴜɴᴅ:</b> {e}")
    else:
        return await query.message.reply_text("❌ <b>ɪɴᴠᴀʟɪᴅ ᴜsᴇʀ ɪᴅ.</b>")

    await db.remove_premium_user(target_uid)
    await query.message.reply_text(
        f"✅ <b>ᴘʀᴇᴍɪᴜᴍ ᴠɪᴘ ʀᴇᴠᴏᴋᴇᴅ ғᴏʀ ᴜsᴇʀ <code>{target_uid}</code>!</b>",
        reply_markup=markup(row(btn("👑 ᴠɪᴘ ᴀᴅᴍɪɴ", "vipadmin_main", "blue")))
    )
    try:
        await bot.send_message(
            target_uid,
            (
                "<blockquote><b>⚠️ <u>ʏᴏᴜʀ ᴠɪᴘ sᴜʙsᴄʀɪᴘᴛɪᴏɴ ʜᴀs ᴇxᴘɪʀᴇᴅ / ʀᴇᴠᴏᴋᴇᴅ</u></b></blockquote>\n\n"
                "ʏᴏᴜʀ ᴠɪᴘ ᴘᴀss ʜᴀs ʙᴇᴇɴ ʀᴇᴠᴏᴋᴇᴅ ᴏʀ ʜᴀs ᴇxᴘɪʀᴇᴅ.\n"
                "ᴜsᴇ /plans ᴛᴏ ʀᴇɴᴇᴡ ᴏʀ ᴜᴘɢʀᴀᴅᴇ ʏᴏᴜʀ ᴘʟᴀɴ ᴀᴛ ᴀɴʏ ᴛɪᴍᴇ."
            ),
            reply_markup=markup(row(btn("💎 ᴠɪᴇᴡ ᴠɪᴘ ᴘʟᴀɴs", "prem_plans", "green")))
        )
    except Exception:
        pass


@Client.on_callback_query(filters.regex(r"^vipadmin_set_"))
async def cb_vipadmin_set(bot: Client, query: CallbackQuery):
    if not await db.is_admin(query.from_user.id):
        return await query.answer("⚠️ Admin only!", show_alert=True)

    parts = query.data.split("_")
    # vipadmin_set_{target_uid}_{days}_{plan}
    target_uid = int(parts[2])
    days = int(parts[3])
    plan_key = parts[4] if len(parts) >= 5 else "pro"
    plan_info = PLANS.get(plan_key, PLANS["pro"])

    new_expires = await db.set_premium_user(target_uid, days, plan_key, activated_by=query.from_user.id)
    exp_str = _format_time_ist(new_expires)

    await query.answer(f"✅ Granted {days} days to {target_uid}!", show_alert=True)

    post_markup = markup(
        row(
            btn("➕ +7 ᴅᴀʏs", f"vipadmin_quickext_{target_uid}_7_0", "blue"),
            btn("➕ +30 ᴅᴀʏs", f"vipadmin_quickext_{target_uid}_30_0", "blue"),
            btn("🗑️ ʀᴇᴠᴏᴋᴇ", f"vipadmin_quickrev_{target_uid}_0", "red")
        ),
        row(btn("👑 ᴠɪᴘ ᴀᴅᴍɪɴ", "vipadmin_main", "yellow"))
    )

    await query.message.edit_text(
        f"✅ <b><u>ᴘʀᴇᴍɪᴜᴍ ᴠɪᴘ sᴜᴄᴄᴇssғᴜʟʟʏ ɢʀᴀɴᴛᴇᴅ!</u></b>\n\n"
        f"👤 <b>ᴜsᴇʀ ɪᴅ:</b> <code>{target_uid}</code>\n"
        f"💎 <b>ᴘʟᴀɴ:</b> {plan_info['name']}\n"
        f"⏳ <b>ᴅᴜʀᴀᴛɪᴏɴ:</b> <code>{days} ᴅᴀʏs</code>\n"
        f"📅 <b>ᴇxᴘɪʀᴇs:</b> <code>{exp_str} IST</code>\n"
        f"🛡️ <b>ᴠᴇʀɪғɪᴄᴀᴛɪᴏɴ:</b> <code>ʙʏᴘᴀssᴇᴅ (0 ᴄᴀᴘᴛᴄʜᴀ)</code>\n"
        f"⚡️ <b>sᴘᴇᴇᴅ:</b> <code>{plan_info['speed']}</code>",
        reply_markup=post_markup
    )

    try:
        await bot.send_message(
            target_uid,
            (
                "<blockquote><b>🎉 <u>ʏᴏᴜʀ ᴠɪᴘ ᴘʀᴇᴍɪᴜᴍ ʜᴀs ʙᴇᴇɴ ᴀᴄᴛɪᴠᴀᴛᴇᴅ!</u></b></blockquote>\n\n"
                f"ᴀɴ ᴀᴅᴍɪɴɪsᴛʀᴀᴛᴏʀ ʜᴀs ɢʀᴀɴᴛᴇᴅ ʏᴏᴜ ᴠɪᴘ sᴜʙsᴄʀɪᴘᴛɪᴏɴ ᴀᴄᴄᴇss!\n\n"
                f"💎 <b>ᴘʟᴀɴ:</b> {plan_info['name']}\n"
                f"⏳ <b>ᴠᴀʟɪᴅɪᴛʏ:</b> <code>{days} ᴅᴀʏs</code>\n"
                f"📅 <b>ᴇxᴘɪʀᴇs:</b> <code>{exp_str} IST</code>\n\n"
                "<b>✨ ᴜɴʟᴏᴄᴋᴇᴅ ᴘᴇʀᴋs:</b>\n"
                "• ⚡️ ᴇxᴛʀᴇᴍᴇ 0.5s ᴛᴜʀʙᴏ ғᴏʀᴡᴀʀᴅɪɴɢ\n"
                "• 🛡️ 0 ᴛᴏᴋᴇɴ ᴠᴇʀɪғɪᴄᴀᴛɪᴏɴ / ᴄᴀᴘᴛᴄʜᴀ ʀᴇǫᴜɪʀᴇᴅ\n"
                "• 🚀 ᴜɴʟɪᴍɪᴛᴇᴅ ʙᴀᴛᴄʜ ғᴏʀᴡᴀʀᴅɪɴɢ\n"
                "• 📡 sᴍᴀʀᴛ ᴀᴜᴛᴏsᴀᴠᴇ 24/7 ᴄʜᴀɴɴᴇʟ ᴍᴏɴɪᴛᴏʀ\n"
                "• 🎓 ᴄᴏᴜʀsᴇ sᴇʟʟᴇʀ sʏʟʟᴀʙᴜs ɪɴᴅᴇxᴇʀ\n\n"
                "<i>ᴇɴᴊᴏʏ ᴜɴʀᴇsᴛʀɪᴄᴛᴇᴅ ᴀᴄᴄᴇss ᴡɪᴛʜ sᴋɪɴᴇᴛ ᴠᴇʀsᴇ!</i>"
            ),
            reply_markup=markup(row(btn("💎 ᴠɪᴇᴡ ᴍʏ ᴘʟᴀɴ", "prem_myplan", "green")))
        )
    except Exception:
        pass


@Client.on_callback_query(filters.regex(r"^vipadmin_quickrev_"))
async def cb_vipadmin_quickrev(bot: Client, query: CallbackQuery):
    if not await db.is_admin(query.from_user.id):
        return await query.answer("⚠️ Admin only!", show_alert=True)

    parts = query.data.split("_")
    # vipadmin_quickrev_{target_uid}_{page}
    target_uid = int(parts[2])
    page = int(parts[3]) if len(parts) >= 4 else 0

    await db.remove_premium_user(target_uid)
    await query.answer(f"🗑️ VIP revoked for {target_uid}!", show_alert=True)

    try:
        await bot.send_message(
            target_uid,
            (
                "<blockquote><b>⚠️ <u>ʏᴏᴜʀ ᴠɪᴘ sᴜʙsᴄʀɪᴘᴛɪᴏɴ ʜᴀs ᴇxᴘɪʀᴇᴅ / ʀᴇᴠᴏᴋᴇᴅ</u></b></blockquote>\n\n"
                "ʏᴏᴜʀ ᴠɪᴘ ᴘᴀss ʜᴀs ʙᴇᴇɴ ʀᴇᴠᴏᴋᴇᴅ ᴏʀ ʜᴀs ᴇxᴘɪʀᴇᴅ.\n"
                "ᴜsᴇ /plans ᴛᴏ ʀᴇɴᴇᴡ ᴏʀ ᴜᴘɢʀᴀᴅᴇ ʏᴏᴜʀ ᴘʟᴀɴ ᴀᴛ ᴀɴʏ ᴛɪᴍᴇ."
            ),
            reply_markup=markup(row(btn("💎 ᴠɪᴇᴡ ᴠɪᴘ ᴘʟᴀɴs", "prem_plans", "green")))
        )
    except Exception:
        pass

    text, reply_markup = await build_vip_list_view(page)
    try:
        await query.message.edit_text(text, reply_markup=reply_markup)
    except Exception:
        pass


@Client.on_callback_query(filters.regex(r"^vipadmin_quickext_"))
async def cb_vipadmin_quickext(bot: Client, query: CallbackQuery):
    if not await db.is_admin(query.from_user.id):
        return await query.answer("⚠️ Admin only!", show_alert=True)

    parts = query.data.split("_")
    # vipadmin_quickext_{target_uid}_{days}_{page}
    target_uid = int(parts[2])
    days = int(parts[3])
    page = int(parts[4]) if len(parts) >= 5 else 0

    current = await db.get_premium_user(target_uid)
    plan_key = current.get("plan", "pro") if current else "pro"
    new_expires = await db.set_premium_user(target_uid, days, plan_key, activated_by=query.from_user.id)
    exp_str = _format_time_ist(new_expires)

    await query.answer(f"✅ Added +{days} days to {target_uid}!", show_alert=True)

    try:
        await bot.send_message(
            target_uid,
            (
                "<blockquote><b>🎉 <u>ʏᴏᴜʀ ᴠɪᴘ sᴜʙsᴄʀɪᴘᴛɪᴏɴ ʜᴀs ʙᴇᴇɴ ᴇxᴛᴇɴᴅᴇᴅ!</u></b></blockquote>\n\n"
                f"ᴀɴ ᴀᴅᴍɪɴɪsᴛʀᴀᴛᴏʀ ʜᴀs ᴇxᴛᴇɴᴅᴇᴅ ʏᴏᴜʀ ᴠɪᴘ sᴜʙsᴄʀɪᴘᴛɪᴏɴ ʙʏ <code>{days} ᴅᴀʏs</code>!\n\n"
                f"📅 <b>ɴᴇᴡ ᴇxᴘɪʀʏ ᴅᴀᴛᴇ:</b> <code>{exp_str} IST</code>\n\n"
                "<i>ᴛʜᴀɴᴋ ʏᴏᴜ ғᴏʀ sᴜᴘᴘᴏʀᴛɪɴɢ sᴋɪɴᴇᴛ ᴠᴇʀsᴇ!</i>"
            ),
            reply_markup=markup(row(btn("💎 ᴠɪᴇᴡ ᴍʏ ᴘʟᴀɴ", "prem_myplan", "green")))
        )
    except Exception:
        pass

    text, reply_markup = await build_vip_list_view(page)
    try:
        await query.message.edit_text(text, reply_markup=reply_markup)
    except Exception:
        pass


# ── Callback Handlers ─────────────────────────────────────────────────

@Client.on_callback_query(filters.regex(r"^prem_plans$"))
async def cb_prem_plans(bot: Client, query: CallbackQuery):
    text, reply_markup = await build_plans_view(query.from_user.id)
    await query.message.edit_text(text, reply_markup=reply_markup, disable_web_page_preview=True)


@Client.on_callback_query(filters.regex(r"^prem_myplan$"))
async def cb_prem_myplan(bot: Client, query: CallbackQuery):
    user_id = query.from_user.id
    prem_user = await db.get_premium_user(user_id)
    is_owner = await db.is_admin(user_id)

    if is_owner:
        txt = (
            "<blockquote><b>👑 <u>ʏᴏᴜʀ ᴠɪᴘ sᴛᴀᴛᴜs — sᴜᴘᴇʀ ᴀᴅᴍɪɴ</u></b></blockquote>\n\n"
            "• <b>Tier:</b> <code>Lifetime Super Admin</code>\n"
            "• <b>Expires:</b> <code>Never (Permanent)</code>\n"
            "• <b>Speed:</b> <code>0.2s Ultra Turbo</code>\n"
            "• <b>Batch Limit:</b> <code>Unlimited</code>\n"
            "• <b>Verification:</b> <code>Permanent Bypass</code>"
        )
    elif prem_user:
        plan_info = PLANS.get(prem_user.get("plan", "pro"), PLANS["pro"])
        exp_str = _format_time_ist(prem_user.get("expires_at", 0))
        rem_secs = max(0, int(prem_user.get("expires_at", 0) - time.time()))
        rem_days = rem_secs // 86400
        rem_hrs = (rem_secs % 86400) // 3600

        perks_formatted = "\n".join([f"  • {p}" for p in plan_info["perks"]])

        txt = (
            f"<blockquote><b>💎 <u>ʏᴏᴜʀ ᴠɪᴘ sᴛᴀᴛᴜs — {plan_info['name'].upper()}</u></b></blockquote>\n\n"
            f"• <b>Plan:</b> {plan_info['name']}\n"
            f"• <b>Expiry Date:</b> <code>{exp_str} IST</code>\n"
            f"• <b>Remaining:</b> <code>{rem_days} Days, {rem_hrs} Hours</code>\n"
            f"• <b>Speed:</b> <code>{plan_info['speed']}</code>\n"
            f"• <b>Batch Limit:</b> <code>{plan_info['batch_limit']}</code>\n\n"
            f"<b>Active Perks:</b>\n{perks_formatted}"
        )
    else:
        txt = (
            "<blockquote><b>🥉 <u>ʏᴏᴜʀ ᴠɪᴘ sᴛᴀᴛᴜs — ғʀᴇᴇ ᴍᴇᴍʙᴇʀ</u></b></blockquote>\n\n"
            "• <b>Current Plan:</b> <code>Free Tier</code>\n"
            "• <b>Forward Speed:</b> <code>Normal / Fast (1.0s - 3.0s)</code>\n"
            "• <b>Verification:</b> <code>Required via Shortener / Referral</code>\n"
            "• <b>AutoSave:</b> <code>Basic</code>\n\n"
            "👉 <i>Upgrade to VIP Premium for extreme 0.5s turbo speed, 0 captcha, and unlimited channels!</i>"
        )

    btn_list = [
        row(btn("💎 ᴜᴘɢʀᴀᴅᴇ ᴘʟᴀɴ", "prem_plans", "green")),
        row(btn("🔙 ʙᴀᴄᴋ ᴛᴏ ʜᴏᴍᴇ", "back", "red"))
    ]
    await query.message.edit_text(txt, reply_markup=markup(*btn_list))


@Client.on_callback_query(filters.regex(r"^prem_buy_(starter|pro|ultra)$"))
async def cb_prem_buy(bot: Client, query: CallbackQuery):
    plan_key = query.data.split("_")[2]
    plan = PLANS.get(plan_key)
    if not plan:
        return await query.answer("Invalid plan selected.", show_alert=True)

    user_id = query.from_user.id
    order_id = f"ORD_{user_id}_{int(time.time())}"
    vpa = getattr(Config, "UPI_ID", "").strip() or "Available on request / Contact Admin"
    payee_name = getattr(Config, "UPI_NAME", "Skinet Verse").strip()
    amount = float(plan["price"])

    upi_intent = _build_upi_intent(vpa, payee_name, amount, plan["tag"], order_id) if "@" in vpa else ""
    qr_code_url = _build_qr_url(upi_intent if upi_intent else f"PAY_SKINET_{order_id}_{amount}")

    order_doc = {
        "order_id": order_id,
        "user_id": user_id,
        "user_mention": query.from_user.mention,
        "plan": plan_key,
        "amount": amount,
        "days": plan["days"],
        "status": "pending",
        "utr": None,
        "screenshot": None,
        "created_at": time.time(),
        "expires_at": time.time() + 1800
    }
    await db.create_premium_order(order_doc)

    admin_link = _get_admin_contact_link()
    crypto_addr = getattr(Config, "CRYPTO_ADDRESS", "").strip()
    crypto_line = f"\n🪙 <b>USDT (TRC20):</b> <code>{crypto_addr}</code>" if crypto_addr else ""

    text = (
        f"<blockquote><b>💳 <u>ᴄʜᴇᴄᴋᴏᴜᴛ — {plan['name'].upper()}</u></b></blockquote>\n\n"
        f"🆔 <b>ᴏʀᴅᴇʀ ɪᴅ:</b> <code>{order_id}</code>\n"
        f"📦 <b>ᴘʟᴀɴ:</b> {plan['name']} (<code>{plan['days']} ᴅᴀʏs</code>)\n"
        f"💰 <b>ᴀᴍᴏᴜɴᴛ ᴘᴀʏᴀʙʟᴇ:</b> <code>₹{amount:.2f}</code> (or <code>{plan['stars']} ⭐</code>)\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📲 <b>ᴜᴘɪ ɪᴅ:</b> <code>{vpa}</code>\n"
        f"👤 <b>ᴘᴀʏᴇᴇ:</b> <code>{payee_name}</code>{crypto_line}\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "<b>📌 ᴘᴀʏᴍᴇɴᴛ ɪɴsᴛʀᴜᴄᴛɪᴏɴs:</b>\n"
        "1️⃣ ᴏᴘᴇɴ GPᴀʏ / PʜᴏɴᴇPᴇ / Pᴀʏᴛᴍ / BHIM / Cʀᴇᴅ.\n"
        "2️⃣ ᴘᴀʏ ᴛʜᴇ ᴇxᴀᴄᴛ ᴀᴍᴏᴜɴᴛ ᴛᴏ ᴛʜᴇ UPI ID ᴀʙᴏᴠᴇ.\n"
        "3️⃣ ᴛᴀᴘ <b>📤 sᴜʙᴍɪᴛ ᴜᴛʀ / ʀᴇғ</b> ᴏʀ <b>📸 sᴇɴᴅ sᴄʀᴇᴇɴsʜᴏᴛ</b> ʙᴇʟᴏᴡ.\n"
        "4️⃣ ᴏɴᴄᴇ ᴠᴇʀɪғɪᴇᴅ ʙʏ ᴏᴜʀ ᴀᴜᴛᴏᴍᴀᴛᴇᴅ ᴇɴɢɪɴᴇ ᴏʀ ᴀᴅᴍɪɴ, ʏᴏᴜʀ VIP ᴀᴄᴛɪᴠᴀᴛᴇs ɪɴsᴛᴀɴᴛʟʏ!"
    )

    action_buttons = [
        row(
            btn("📤 sᴜʙᴍɪᴛ ᴜᴛʀ / ʀᴇғ ɴᴏ", f"prem_utr_{order_id}", "green"),
            btn("📸 sᴜʙᴍɪᴛ sᴄʀᴇᴇɴsʜᴏᴛ", f"prem_ss_{order_id}", "green")
        ),
        row(
            btn_url("💬 ᴄᴏɴᴛᴀᴄᴛ ᴀᴅᴍɪɴ / ᴅɪʀᴇᴄᴛ ʙᴜʏ", admin_link, "blue")
        ),
        row(
            btn("❌ ᴄᴀɴᴄᴇʟ ᴏʀᴅᴇʀ", f"prem_cancel_{order_id}", "red"),
            btn("🔙 ᴀʟʟ ᴘʟᴀɴs", "prem_plans", "blue")
        )
    ]

    await query.message.edit_text(text, reply_markup=markup(*action_buttons), disable_web_page_preview=False)


@Client.on_callback_query(filters.regex(r"^prem_utr_"))
async def cb_prem_submit_utr(bot: Client, query: CallbackQuery):
    order_id = query.data.replace("prem_utr_", "")
    user_id = query.from_user.id
    _SUBMIT_STATE[user_id] = {"order_id": order_id, "mode": "utr"}

    await query.answer()
    await query.message.reply_text(
        "<blockquote><b>⌨️ <u>sᴜʙᴍɪᴛ ᴜᴛʀ / ᴛʀᴀɴsᴀᴄᴛɪᴏɴ ɪᴅ</u></b></blockquote>\n\n"
        f"ᴘʟᴇᴀsᴇ ᴇɴᴛᴇʀ ᴛʜᴇ 12-ᴅɪɢɪᴛ ᴜᴛʀ / ʀᴇғᴇʀᴇɴᴄᴇ ɴᴜᴍʙᴇʀ ғᴏʀ ᴏʀᴅᴇʀ <code>{order_id}</code>:\n\n"
        "<i>sᴇɴᴅ <code>/cancel</code> ᴛᴏ ᴀʙᴏʀᴛ.</i>"
    )


@Client.on_callback_query(filters.regex(r"^prem_ss_"))
async def cb_prem_submit_ss(bot: Client, query: CallbackQuery):
    order_id = query.data.replace("prem_ss_", "")
    user_id = query.from_user.id
    _SUBMIT_STATE[user_id] = {"order_id": order_id, "mode": "screenshot"}

    await query.answer()
    await query.message.reply_text(
        "<blockquote><b>📸 <u>sᴜʙᴍɪᴛ ᴘᴀʏᴍᴇɴᴛ sᴄʀᴇᴇɴsʜᴏᴛ</u></b></blockquote>\n\n"
        f"ᴘʟᴇᴀsᴇ sᴇɴᴅ ᴛʜᴇ ᴘᴀʏᴍᴇɴᴛ sᴄʀᴇᴇɴsʜᴏᴛ ғᴏʀ ᴏʀᴅᴇʀ <code>{order_id}</code>:\n\n"
        "<i>sᴇɴᴅ <code>/cancel</code> ᴛᴏ ᴀʙᴏʀᴛ.</i>"
    )


@Client.on_callback_query(filters.regex(r"^prem_cancel_"))
async def cb_prem_cancel(bot: Client, query: CallbackQuery):
    order_id = query.data.replace("prem_cancel_", "")
    user_id = query.from_user.id
    _SUBMIT_STATE.pop(user_id, None)
    await db.update_premium_order(order_id, {"status": "cancelled"})
    await query.answer("ᴏʀᴅᴇʀ ᴄᴀɴᴄᴇʟʟᴇᴅ.", show_alert=True)
    text, reply_markup = await build_plans_view(user_id)
    await query.message.edit_text(text, reply_markup=reply_markup, disable_web_page_preview=True)


# ── Proof Submission Listener (Text & Photo) ──────────────────────────

def _awaiting_proof(flt, client, message) -> bool:
    """True only while the sender actually has a pending proof submission.

    The filter must be state-aware: a plain "private & text" filter also matches
    every other command, and since Pyrogram runs only the first matching handler
    of a group, it would silently swallow commands depending on the order the
    plugin files happen to be loaded in.
    """
    user = message.from_user
    if not (user and user.id in _SUBMIT_STATE):
        return False
    # Any command is an escape hatch out of the submission flow, not proof text.
    return not (message.text or message.caption or "").lstrip().startswith("/")


@Client.on_message(
    filters.private
    & (filters.text | filters.photo)
    & filters.create(_awaiting_proof)
)
async def proof_submission_listener(bot: Client, message: Message):
    user_id = message.from_user.id
    st = _SUBMIT_STATE.get(user_id)
    if not st:
        return

    order_id = st["order_id"]
    mode = st["mode"]
    _SUBMIT_STATE.pop(user_id, None)

    order = await db.get_premium_order(order_id)
    if not order or order.get("status") != "pending":
        await message.reply_text("❌ <b>ᴛʜɪs ᴏʀᴅᴇʀ ɪs ɪɴᴠᴀʟɪᴅ ᴏʀ ᴇxᴘɪʀᴇᴅ. ᴘʟᴇᴀsᴇ ᴄʀᴇᴀᴛᴇ ᴀ ɴᴇᴡ ᴏʀᴅᴇʀ ɪɴ /plans.</b>")
        raise StopPropagation

    plan_info = PLANS.get(order["plan"], PLANS["pro"])
    now_ist = datetime.now(tz=IST).strftime("%d-%b-%Y %I:%M:%S %p")

    utr_val = None
    photo_file_id = None

    if mode == "utr" and message.text:
        utr_val = message.text.strip()
        await db.update_premium_order(order_id, {"utr": utr_val, "submitted_at": time.time(), "status": "verifying"})
    elif mode == "screenshot" and message.photo:
        photo_file_id = message.photo.file_id
        await db.update_premium_order(order_id, {"screenshot": photo_file_id, "submitted_at": time.time(), "status": "verifying"})
    elif message.text:
        utr_val = message.text.strip()
        await db.update_premium_order(order_id, {"utr": utr_val, "submitted_at": time.time(), "status": "verifying"})

    await message.reply_text(
        "<blockquote><b>⏳ <u>ᴘᴀʏᴍᴇɴᴛ ᴘʀᴏᴏғ sᴜʙᴍɪᴛᴛᴇᴅ!</u></b></blockquote>\n\n"
        f"ᴛʜᴀɴᴋ ʏᴏᴜ, {message.from_user.first_name}!\n"
        f"ʏᴏᴜʀ ᴘʀᴏᴏғ ғᴏʀ ᴏʀᴅᴇʀ <code>{order_id}</code> ʜᴀs ʙᴇᴇɴ ᴅɪsᴘᴀᴛᴄʜᴇᴅ ᴛᴏ ᴀᴅᴍɪɴɪsᴛʀᴀᴛᴏʀs.\n\n"
        f"💎 <b>ᴘʟᴀɴ:</b> {plan_info['name']} (<code>₹{order['amount']:.2f}</code>)\n"
        f"🧾 <b>ʀᴇғ/ᴜᴛʀ:</b> <code>{utr_val or 'sᴄʀᴇᴇɴsʜᴏᴛ ᴀᴛᴛᴀᴄʜᴇᴅ'}</code>\n\n"
        "⚡️ <i>ʏᴏᴜʀ ᴠɪᴘ ᴘᴀss ᴡɪʟʟ ʙᴇ ᴀᴄᴛɪᴠᴀᴛᴇᴅ ᴀs sᴏᴏɴ ᴀs ᴀɴ ᴀᴅᴍɪɴ ᴀᴘᴘʀᴏᴠᴇs. ʏᴏᴜ ᴡɪʟʟ ʙᴇ ɴᴏᴛɪғɪᴇᴅ ᴀᴜᴛᴏᴍᴀᴛɪᴄᴀʟʟʏ!</i>",
        reply_markup=markup(row(btn("💎 ʙᴀᴄᴋ ᴛᴏ ᴘʟᴀɴs", "prem_plans", "blue")))
    )

    # Dispatch to LOG_CHANNEL & Bot Owners for 1-click verification
    admin_alert_text = (
        "<blockquote><b>💎 <u>#NewPremiumOrderPending</u></b></blockquote>\n\n"
        f"👤 <b>ᴜsᴇʀ:</b> {message.from_user.mention} (<code>{user_id}</code>)\n"
        f"📦 <b>ᴘʟᴀɴ:</b> {plan_info['name']} (<code>{order['days']} ᴅᴀʏs</code>)\n"
        f"💰 <b>ᴀᴍᴏᴜɴᴛ:</b> <code>₹{order['amount']:.2f}</code>\n"
        f"🆔 <b>ᴏʀᴅᴇʀ ɪᴅ:</b> <code>{order_id}</code>\n"
        f"🧾 <b>ᴜᴛʀ / ʀᴇғ:</b> <code>{utr_val or 'sᴇᴇ sᴄʀᴇᴇɴsʜᴏᴛ'}</code>\n"
        f"⏰ <b>ᴛɪᴍᴇ:</b> <code>{now_ist} IST</code>\n\n"
        "👇 <b>ᴀᴘᴘʀᴏᴠᴇ ᴏʀ ʀᴇᴊᴇᴄᴛ ᴛʜɪs ᴘᴀʏᴍᴇɴᴛ:</b>"
    )

    admin_actions = markup(
        row(
            btn("✅ ᴀᴘᴘʀᴏᴠᴇ ᴠɪᴘ", f"prem_appr_{user_id}_{order['plan']}_{order_id}", "green"),
            btn("❌ ʀᴇᴊᴇᴄᴛ", f"prem_rej_{user_id}_{order_id}", "red")
        )
    )

    targets = set()
    if Config.LOG_CHANNEL:
        targets.add(Config.LOG_CHANNEL)
    for oid in Config.BOT_OWNER_ID:
        targets.add(oid)

    for target in targets:
        try:
            if photo_file_id:
                await bot.send_photo(target, photo=photo_file_id, caption=admin_alert_text, reply_markup=admin_actions)
            else:
                await bot.send_message(target, text=admin_alert_text, reply_markup=admin_actions)
        except Exception as e:
            logger.warning(f"Could not notify admin {target} of premium proof: {e}")

    # Handled: stop dispatch so the global non-command fallback (group 100)
    # does not also send its welcome card for this same message.
    raise StopPropagation


@Client.on_message(filters.private & filters.command(["cancel"]))
async def cancel_submission_cmd(bot: Client, message: Message):
    user_id = message.from_user.id
    if _SUBMIT_STATE.pop(user_id, None):
        return await message.reply_text("❌ <b>ᴘᴀʏᴍᴇɴᴛ ᴘʀᴏᴏғ sᴜʙᴍɪssɪᴏɴ ᴄᴀɴᴄᴇʟʟᴇᴅ.</b>", quote=True)
    return await message.reply_text("ℹ️ <b>ɴᴏᴛʜɪɴɢ ᴛᴏ ᴄᴀɴᴄᴇʟ.</b>", quote=True)


# ── Admin Approval & Rejection Callbacks ──────────────────────────────

@Client.on_callback_query(filters.regex(r"^prem_appr_"))
async def cb_prem_approve(bot: Client, query: CallbackQuery):
    if not await db.is_admin(query.from_user.id):
        return await query.answer("⚠️ Admin only action!", show_alert=True)

    parts = query.data.split("_")
    # prem_appr_{user_id}_{plan}_{order_id}
    target_uid = int(parts[2])
    plan_key = parts[3]
    order_id = "_".join(parts[4:])

    plan_info = PLANS.get(plan_key, PLANS["pro"])
    new_expires = await db.set_premium_user(target_uid, plan_info["days"], plan_key, activated_by=query.from_user.id)
    await db.update_premium_order(order_id, {"status": "approved", "approved_by": query.from_user.id, "approved_at": time.time()})

    exp_str = _format_time_ist(new_expires)
    admin_name = query.from_user.first_name

    await query.answer(f"✅ ᴀᴘᴘʀᴏᴠᴇᴅ! ᴠɪᴘ ɢʀᴀɴᴛᴇᴅ ᴛᴏ {target_uid}", show_alert=True)

    try:
        if query.message.caption:
            await query.message.edit_caption(
                f"{query.message.caption}\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n✅ <b>ᴀᴘᴘʀᴏᴠᴇᴅ ʙʏ {admin_name} ({query.from_user.id})</b>\n📅 <b>ᴠᴀʟɪᴅ ᴜɴᴛɪʟ:</b> <code>{exp_str} IST</code>"
            )
        else:
            await query.message.edit_text(
                f"{query.message.text}\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n✅ <b>ᴀᴘᴘʀᴏᴠᴇᴅ ʙʏ {admin_name} ({query.from_user.id})</b>\n📅 <b>ᴠᴀʟɪᴅ ᴜɴᴛɪʟ:</b> <code>{exp_str} IST</code>"
            )
    except Exception:
        pass

    # Notify user with celebration card
    try:
        await bot.send_message(
            target_uid,
            (
                "<blockquote><b>🎉 <u>ᴘʀᴇᴍɪᴜᴍ sᴜʙsᴄʀɪᴘᴛɪᴏɴ ᴀᴄᴛɪᴠᴀᴛᴇᴅ!</u></b></blockquote>\n\n"
                f"ʏᴏᴜʀ ᴘᴀʏᴍᴇɴᴛ ʜᴀs ʙᴇᴇɴ ᴠᴇʀɪғɪᴇᴅ ᴀɴᴅ ʏᴏᴜʀ ᴠɪᴘ ᴘᴀss ɪs ᴀᴄᴛɪᴠᴇ!\n\n"
                f"💎 <b>ᴘʟᴀɴ:</b> {plan_info['name']}\n"
                f"⏳ <b>ᴠᴀʟɪᴅɪᴛʏ:</b> <code>{plan_info['days']} ᴅᴀʏs</code>\n"
                f"📅 <b>ᴇxᴘɪʀᴇs:</b> <code>{exp_str} IST</code>\n\n"
                "<b>✨ ᴜɴʟᴏᴄᴋᴇᴅ ᴘᴇʀᴋs:</b>\n"
                "• ⚡️ ᴇxᴛʀᴇᴍᴇ 0.5s ᴛᴜʀʙᴏ ғᴏʀᴡᴀʀᴅɪɴɢ\n"
                "• 🛡️ 0 ᴛᴏᴋᴇɴ ᴠᴇʀɪғɪᴄᴀᴛɪᴏɴ / ᴄᴀᴘᴛᴄʜᴀ ғᴏʀᴇᴠᴇʀ\n"
                "• 🚀 ᴜɴʟɪᴍɪᴛᴇᴅ ʙᴀᴛᴄʜ ғᴏʀᴡᴀʀᴅɪɴɢ\n"
                "• 📡 sᴍᴀʀᴛ ᴀᴜᴛᴏsᴀᴠᴇ 24/7 ᴄʜᴀɴɴᴇʟ ᴍᴏɴɪᴛᴏʀ\n"
                "• 🎓 ᴄᴏᴜʀsᴇ sᴇʟʟᴇʀ sʏʟʟᴀʙᴜs ɪɴᴅᴇxᴇʀ\n\n"
                "<i>ᴛʜᴀɴᴋ ʏᴏᴜ ғᴏʀ sᴜᴘᴘᴏʀᴛɪɴɢ sᴋɪɴᴇᴛ ᴠᴇʀsᴇ!</i>"
            ),
            reply_markup=markup(row(btn("💎 ᴠɪᴇᴡ ᴍʏ ᴘʟᴀɴ", "prem_myplan", "green")))
        )
    except Exception as e:
        logger.warning(f"Failed to send VIP celebration to {target_uid}: {e}")


@Client.on_callback_query(filters.regex(r"^prem_rej_"))
async def cb_prem_reject(bot: Client, query: CallbackQuery):
    if not await db.is_admin(query.from_user.id):
        return await query.answer("⚠️ Admin only action!", show_alert=True)

    parts = query.data.split("_")
    target_uid = int(parts[2])
    order_id = "_".join(parts[3:])

    await db.update_premium_order(order_id, {"status": "rejected", "rejected_by": query.from_user.id, "rejected_at": time.time()})
    admin_name = query.from_user.first_name

    await query.answer("❌ Order rejected.", show_alert=True)

    try:
        if query.message.caption:
            await query.message.edit_caption(
                f"{query.message.caption}\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n❌ <b>ʀᴇᴊᴇᴄᴛᴇᴅ ʙʏ {admin_name}</b>"
            )
        else:
            await query.message.edit_text(
                f"{query.message.text}\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n❌ <b>ʀᴇᴊᴇᴄᴛᴇᴅ ʙʏ {admin_name}</b>"
            )
    except Exception:
        pass

    admin_link = _get_admin_contact_link()
    try:
        await bot.send_message(
            target_uid,
            (
                "<blockquote><b>⚠️ <u>ᴘᴀʏᴍᴇɴᴛ ᴠᴇʀɪғɪᴄᴀᴛɪᴏɴ ᴜɴsᴜᴄᴄᴇssғᴜʟ</u></b></blockquote>\n\n"
                f"ʏᴏᴜʀ ᴘᴀʏᴍᴇɴᴛ ᴘʀᴏᴏғ ғᴏʀ ᴏʀᴅᴇʀ <code>{order_id}</code> ᴄᴏᴜʟᴅ ɴᴏᴛ ʙᴇ ᴠᴇʀɪғɪᴇᴅ ʙʏ ᴏᴜʀ ᴛᴇᴀᴍ.\n\n"
                "<i>ɪғ ʏᴏᴜ ʙᴇʟɪᴇᴠᴇ ᴛʜɪs ɪs ᴀ ᴍɪsᴛᴀᴋᴇ, ᴘʟᴇᴀsᴇ ᴄᴏɴᴛᴀᴄᴛ ᴏᴜʀ ᴀᴅᴍɪɴɪsᴛʀᴀᴛᴏʀ ᴅɪʀᴇᴄᴛʟʏ.</i>"
            ),
            reply_markup=markup(row(btn_url("💬 ᴄᴏɴᴛᴀᴄᴛ ᴀᴅᴍɪɴ", admin_link, "blue")))
        )
    except Exception as e:
        logger.warning(f"Could not notify user of rejection: {e}")
