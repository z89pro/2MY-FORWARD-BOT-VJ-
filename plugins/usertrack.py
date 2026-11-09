import html
import re
import logging
from datetime import datetime, timedelta
from config import Config
from database import db
from pyrogram import Client, filters, enums
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery, Message
from pyrogram.errors import ListenerTimeout

logger = logging.getLogger("SkinetUserTrack")

PAGE_SIZE = 8

async def is_authorized(user_id: int) -> bool:
    if not user_id:
        return False
    try:
        owners = [int(x) for x in Config.BOT_OWNER_ID if str(x).isdigit()]
        if int(user_id) in owners:
            return True
    except Exception:
        pass
    return await db.is_admin(user_id)

def is_owner(user_id: int) -> bool:
    try:
        owners = [int(x) for x in Config.BOT_OWNER_ID if str(x).isdigit()]
        admins = [int(x) for x in Config.ADMINS if str(x).isdigit()]
        return int(user_id) in owners or int(user_id) in admins
    except Exception:
        return False

_HTML_TAG = re.compile(r'<[^>]*>?')
_HTML_ENTITY = re.compile(r'&[a-zA-Z0-9#]+;')

def display_name(doc) -> str:
    """Plain, display-safe name for a user document.

    Strips any markup, unclosed HTML tags, and ensures fragments like
    `<a href="tg://user?...` never leak into the display.
    """
    if not doc or not isinstance(doc, dict):
        return "User"
    uid = doc.get("id") or doc.get("user_id")
    raw = doc.get("name")
    if raw:
        cleaned = _HTML_TAG.sub('', str(raw))
        cleaned = _HTML_ENTITY.sub('', cleaned)
        cleaned = html.unescape(cleaned).strip()
        # Verify it doesn't still contain broken tag remnants
        if cleaned and not cleaned.startswith(("<", "tg://", "href=")) and "tg://user" not in cleaned:
            return cleaned[:24]
    uname = doc.get("username")
    if uname:
        return f"@{uname.lstrip('@')}"
    return f"User {uid}" if uid else "User"

def user_mention(doc) -> str:
    """Clickable mention built from the id, so it never depends on stored HTML."""
    uid = doc.get("id") or doc.get("user_id")
    name = html.escape(display_name(doc))
    if not uid:
        return f"<b>{name}</b>"
    return f'<a href="tg://user?id={int(uid)}">{name}</a>'

def fmt_dt(dt):
    if not dt:
        return "—"
    try:
        if isinstance(dt, str):
            dt = datetime.fromisoformat(dt)
        return dt.strftime("%d %b %Y %H:%M")
    except Exception:
        return "—"

async def build_userstats_overview():
    cursor = db.col.find({})
    users = [doc async for doc in cursor]
    now = datetime.now()
    day_ago = now - timedelta(days=1)
    week_ago = now - timedelta(days=7)

    total = len(users)
    new_today = 0
    new_week = 0
    act_today = 0
    act_week = 0
    total_forwards = 0

    for doc in users:
        total_forwards += int(doc.get("forward_count", 0))
        fs = doc.get("first_seen")
        ls = doc.get("last_seen")
        if fs:
            try:
                if isinstance(fs, str): fs = datetime.fromisoformat(fs)
                if fs >= day_ago: new_today += 1
                if fs >= week_ago: new_week += 1
            except Exception: pass
        if ls:
            try:
                if isinstance(ls, str): ls = datetime.fromisoformat(ls)
                if ls >= day_ago: act_today += 1
                if ls >= week_ago: act_week += 1
            except Exception: pass

    growth_pct = (new_week / max(1, total)) * 100

    text = (
        "<blockquote><b>📊 <u>sᴋɪɴᴇᴛ ᴠᴇʀsᴇ — ᴜsᴇʀ ᴛʀᴀᴄᴋɪɴɢ ᴅᴀsʜʙᴏᴀʀᴅ</u></b></blockquote>\n\n"
        "<b>ᴄᴏᴍᴘʀᴇʜᴇɴsɪᴠᴇ ᴀɴᴀʟʏᴛɪᴄs & ʀᴇᴀʟ-ᴛɪᴍᴇ ᴛᴇʟᴇᴍᴇᴛʀʏ ᴏᴠᴇʀ ʏᴏᴜʀ ʙᴏᴛ's ᴜsᴇʀʙᴀsᴇ:</b>\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👥 <b>ᴛᴏᴛᴀʟ ʀᴇɢɪsᴛᴇʀᴇᴅ ᴜsᴇʀs:</b> <code>{total}</code>\n"
        f"🔁 <b>ᴛᴏᴛᴀʟ ᴍᴇssᴀɢᴇs ғᴏʀᴡᴀʀᴅᴇᴅ:</b> <code>{total_forwards}</code>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🆕 <b>ɴᴇᴡ ᴜsᴇʀs (24h):</b> <code>{new_today}</code>\n"
        f"📅 <b>ɴᴇᴡ ᴜsᴇʀs (7d):</b> <code>{new_week}</code>\n"
        f"🟢 <b>ᴀᴄᴛɪᴠᴇ ᴜsᴇʀs (24h):</b> <code>{act_today}</code>\n"
        f"⚡️ <b>ᴀᴄᴛɪᴠᴇ ᴜsᴇʀs (7d):</b> <code>{act_week}</code>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📈 <b>7-ᴅᴀʏ ɢʀᴏᴡᴛʜ ᴠᴇʟᴏᴄɪᴛʏ:</b> <code>{growth_pct:.1f}%</code>\n\n"
        "<i>💡 ʟᴏᴏᴋᴜᴘ ᴀɴʏ ᴜsᴇʀ ᴘʀᴏғɪʟᴇ:</i> <code>/userstats &lt;user_id&gt;</code>"
    )

    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🕒 ɴᴇᴡ ᴜsᴇʀs", callback_data="utr_new_0"),
            InlineKeyboardButton("🟢 ᴀᴄᴛɪᴠᴇ ᴜsᴇʀs", callback_data="utr_act_0")
        ],
        [
            InlineKeyboardButton("🎁 ʀᴇғᴇʀʀᴀʟ sᴛᴀᴛs", callback_data="referral#admin"),
            InlineKeyboardButton("⚙️ sʏsᴛᴇᴍ ᴄᴏɴғɪɢ", callback_data="config#main")
        ],
        [
            InlineKeyboardButton("📥 ᴄsᴠ ᴇxᴘᴏʀᴛ", callback_data="utr_export_csv"),
            InlineKeyboardButton("📥 ᴊsᴏɴ ᴇxᴘᴏʀᴛ", callback_data="utr_export_json")
        ],
        [
            InlineKeyboardButton("• ʙᴀᴄᴋ ᴛᴏ ᴍᴀɪɴ", callback_data="back"),
            InlineKeyboardButton("❌ ᴄʟᴏsᴇ", callback_data="close_btn")
        ]
    ])
    return text, buttons

async def build_user_profile(user_id: int):
    user = await db.get_user(user_id)
    if not user:
        return f"<b>❌ ᴜsᴇʀ <code>{user_id}</code> ɴᴏᴛ ғᴏᴜɴᴅ ɪɴ ᴅᴀᴛᴀʙᴀsᴇ.</b>", None

    name = html.escape(display_name(user))
    owner_badge = " 👑 ᴏᴡɴᴇʀ" if is_owner(user_id) else ""
    first_seen = fmt_dt(user.get("first_seen"))
    last_seen = fmt_dt(user.get("last_seen"))
    forwards = user.get("forward_count", 0)
    activity = user.get("activity_count", 1)
    
    ref = user.get("referral", {})
    referred_by = ref.get("referred_by") or "ɴᴏɴᴇ (ᴅɪʀᴇᴄᴛ)"
    ref_count = ref.get("referral_count", 0)
    ref_points = ref.get("referral_points", 0)
    
    channels = await db.get_user_channels(user_id)
    bot_info = await db.get_bot(user_id)
    bot_status = "✅ ᴄᴏɴɴᴇᴄᴛᴇᴅ" if bot_info else "❌ ɴᴏᴛ ᴀᴅᴅᴇᴅ"
    bot_type = "ᴜsᴇʀʙᴏᴛ" if (bot_info and not bot_info.get("is_bot")) else ("ʙᴏᴛ" if bot_info else "ɴᴏɴᴇ")

    prem = await db.get_premium_user(user_id)
    if prem:
        exp_str = fmt_dt(datetime.fromtimestamp(prem.get("expires_at", 0)))
        plan_str = prem.get("plan", "pro").upper()
        vip_status = f"💎 <b>ᴠɪᴘ sᴛᴀᴛᴜs:</b> <code>ᴀᴄᴛɪᴠᴇ ({plan_str})</code> (ᴇxᴘ: <code>{exp_str}</code>)"
        vip_btn_text = "⚙️ ᴍᴀɴᴀɢᴇ ᴠɪᴘ"
    else:
        vip_status = "🥉 <b>ᴠɪᴘ sᴛᴀᴛᴜs:</b> <code>ғʀᴇᴇ ᴍᴇᴍʙᴇʀ</code>"
        vip_btn_text = "💎 ɢʀᴀɴᴛ ᴠɪᴘ"

    is_banned, ban_reason = await db.is_user_banned(user_id)
    ban_display = f"🔴 <b>ʙᴀɴɴᴇᴅ</b> (<i>{ban_reason}</i>)" if is_banned else "🟢 <b>ᴄʟᴇᴀɴ / ᴀᴄᴛɪᴠᴇ</b>"
    
    active_task = await db.get_user_active_task(user_id)
    task_display = f"⚡️ <b>ʀᴜɴɴɪɴɢ</b> (<code>{active_task.get('task_id')}</code>)" if active_task else "💤 <b>ɪᴅʟᴇ</b>"

    ch_list_str = ""
    if channels:
        ch_items = []
        for c in channels[:6]:
            c_title = html.escape(str(c.get("title") or "Channel"))
            c_id = c.get("chat_id")
            c_uname = c.get("username")
            u_tag = f" (@{c_uname.lstrip('@')})" if c_uname and c_uname != "private" else ""
            ch_items.append(f"  • <b>{c_title}</b> (<code>{c_id}</code>){u_tag}")
        ch_list_str = "\n" + "\n".join(ch_items)
        if len(channels) > 6:
            ch_list_str += f"\n  <i>...and {len(channels) - 6} more</i>"
    else:
        ch_list_str = " <i>(ɴᴏɴᴇ ᴀᴅᴅᴇᴅ)</i>"

    text = (
        f"<blockquote><b>👤 <u>ᴜsᴇʀ ᴘʀᴏғɪʟᴇ: {name}{owner_badge}</u></b></blockquote>\n\n"
        f"🆔 <b>ᴛᴇʟᴇɢʀᴀᴍ ID:</b> <code>{user_id}</code>\n"
        f"👤 <b>ɴᴀᴍᴇ:</b> <b>{name}</b>{owner_badge}\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📅 <b>ғɪʀsᴛ sᴇᴇɴ:</b> <code>{first_seen}</code>\n"
        f"🕒 <b>ʟᴀsᴛ ᴀᴄᴛɪᴠᴇ:</b> <code>{last_seen}</code>\n"
        f"🔁 <b>ᴍᴇssᴀɢᴇs ғᴏʀᴡᴀʀᴅᴇᴅ:</b> <code>{forwards}</code>\n"
        f"⚡️ <b>ɪɴᴛᴇʀᴀᴄᴛɪᴏɴ ᴄᴏᴜɴᴛ:</b> <code>{activity}</code>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🤖 <b>ʙᴏᴛ ᴇɴɢɪɴᴇ:</b> <code>{bot_status} ({bot_type})</code>\n"
        f"🏷 <b>ᴄᴏɴғɪɢᴜʀᴇᴅ ᴄʜᴀɴɴᴇʟs ({len(channels)}):</b>{ch_list_str}\n"
        f"{vip_status}\n"
        f"🛡️ <b>ᴀᴄᴄᴏᴜɴᴛ sᴛᴀᴛᴜs:</b> {ban_display}\n"
        f"🔄 <b>ғᴏʀᴡᴀʀᴅ ᴛᴀsᴋ:</b> {task_display}\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🔗 <b>ʀᴇғᴇʀʀᴇᴅ ʙʏ:</b> <code>{referred_by}</code>\n"
        f"👥 <b>ɪɴᴠɪᴛᴇᴅ ғʀɪᴇɴᴅs:</b> <code>{ref_count}</code>\n"
        f"💎 <b>ʀᴇғᴇʀʀᴀʟ ᴘᴏɪɴᴛs:</b> <code>{ref_points} ᴘᴛs</code>"
    )

    action_buttons = []
    if active_task:
        action_buttons.append(InlineKeyboardButton("🛑 sᴛᴏᴘ ᴛᴀsᴋ", callback_data=f"mod_stop_{active_task.get('task_id')}"))
    if is_banned:
        action_buttons.append(InlineKeyboardButton("🔓 ᴜɴʙᴀɴ", callback_data=f"mod_unban_{user_id}"))
    else:
        action_buttons.append(InlineKeyboardButton("🚫 ʙᴀɴ", callback_data=f"mod_ban_{user_id}"))

    btn_rows = [
        [
            InlineKeyboardButton("➕ ᴀᴅᴅ ᴘᴏɪɴᴛs", callback_data=f"utr_addpts_{user_id}"),
            InlineKeyboardButton(vip_btn_text, callback_data=f"utr_vip_{user_id}")
        ]
    ]
    if action_buttons:
        btn_rows.append(action_buttons)
    btn_rows.append([
        InlineKeyboardButton("🔙 ᴅᴀsʜʙᴏᴀʀᴅ", callback_data="utr_overview"),
        InlineKeyboardButton("❌ ᴄʟᴏsᴇ", callback_data="close_btn")
    ])

    return text, InlineKeyboardMarkup(btn_rows)


# ================= COMMANDS =================

@Client.on_message(filters.private & filters.command(["userstats", "track", "admintrack"]))
async def userstats_cmd(client: Client, message: Message):
    user_id = message.from_user.id
    if not await is_authorized(user_id):
        return await message.reply_text(
            "⚠️ <b>ᴀᴄᴄᴇss ᴅᴇɴɪᴇᴅ:</b> ᴛʜɪs ᴀɴᴀʟʏᴛɪᴄs ᴅᴀsʜʙᴏᴀʀᴅ ɪs sᴛʀɪᴄᴛʟʏ ʀᴇsᴛʀɪᴄᴛᴇᴅ ᴛᴏ ʙᴏᴛ ᴏᴡɴᴇʀs & ᴀᴅᴍɪɴs.",
            quote=True
        )

    # If specific user ID provided: /userstats <user_id>
    if len(message.command) > 1:
        raw_target = message.command[1].strip()
        if raw_target.isdigit():
            target_id = int(raw_target)
            text, buttons = await build_user_profile(target_id)
            return await message.reply_text(text, reply_markup=buttons, disable_web_page_preview=True, quote=True)

    text, buttons = await build_userstats_overview()
    await message.reply_text(text, reply_markup=buttons, disable_web_page_preview=True, quote=True)


# ================= CALLBACKS =================

@Client.on_callback_query(filters.regex(r"^utr_"))
async def utr_callbacks(client: Client, query: CallbackQuery):
    user_id = query.from_user.id
    if not await is_authorized(user_id):
        return await query.answer("ᴀᴅᴍɪɴs ᴏɴʟʏ!", show_alert=True)

    data = query.data

    if data == "utr_overview":
        text, buttons = await build_userstats_overview()
        await query.message.edit_text(text, reply_markup=buttons, disable_web_page_preview=True)

    elif data.startswith("utr_new_") or data.startswith("utr_act_"):
        is_new = data.startswith("utr_new_")
        page = int(data.split("_")[-1])
        cursor = db.col.find({})
        users = [doc async for doc in cursor]

        sort_key = "first_seen" if is_new else "last_seen"
        title = "🕒 <b><u>ɴᴇᴡ ᴜsᴇʀs ʟɪsᴛ</u></b>" if is_new else "🟢 <b><u>ᴀᴄᴛɪᴠᴇ ᴜsᴇʀs ʟɪsᴛ</u></b>"
        prefix = "utr_new" if is_new else "utr_act"

        # Sort descending by date
        def sort_fn(x):
            val = x.get(sort_key)
            if not val: return datetime.min
            if isinstance(val, str):
                try: return datetime.fromisoformat(val)
                except Exception: return datetime.min
            return val

        users.sort(key=sort_fn, reverse=True)

        total_pages = max(1, (len(users) + PAGE_SIZE - 1) // PAGE_SIZE)
        page = max(0, min(page, total_pages - 1))
        chunk = users[page * PAGE_SIZE : (page + 1) * PAGE_SIZE]

        lines = [
            f"<blockquote>{title}</blockquote>\n",
            f"<b>ᴛᴏᴛᴀʟ ᴜsᴇʀs:</b> <code>{len(users)}</code> | ᴘᴀɢᴇ <b>{page+1}/{total_pages}</b>\n",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        ]

        item_buttons = []
        for u in chunk:
            uid = u.get("id")
            name = html.escape(display_name(u)[:18])
            date_val = fmt_dt(u.get(sort_key))
            badge = " 👑" if is_owner(uid) else ""
            lines.append(f"• {user_mention(u)}{badge} (<code>{uid}</code>)\n  └ <i>{date_val}</i> | ғᴏʀᴡᴀʀᴅs: <code>{u.get('forward_count', 0)}</code>")
            item_buttons.append([InlineKeyboardButton(f"👤 ᴠɪᴇᴡ {name}", callback_data=f"utr_user_{uid}")])

        lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

        # Pager row
        nav_row = []
        if page > 0:
            nav_row.append(InlineKeyboardButton("⬅️ ᴘʀᴇᴠ", callback_data=f"{prefix}_{page - 1}"))
        nav_row.append(InlineKeyboardButton(f"{page + 1} / {total_pages}", callback_data="utr_noop"))
        if page < total_pages - 1:
            nav_row.append(InlineKeyboardButton("ɴᴇxᴛ ➡️", callback_data=f"{prefix}_{page + 1}"))

        markup_rows = item_buttons + [nav_row, [
            InlineKeyboardButton("🔙 ᴅᴀsʜʙᴏᴀʀᴅ", callback_data="utr_overview"),
            InlineKeyboardButton("❌ ᴄʟᴏsᴇ", callback_data="close_btn")
        ]]
        await query.message.edit_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(markup_rows), disable_web_page_preview=True)

    elif data.startswith("utr_user_"):
        target_id = int(data.replace("utr_user_", ""))
        text, buttons = await build_user_profile(target_id)
        await query.message.edit_text(text, reply_markup=buttons, disable_web_page_preview=True)

    elif data.startswith("utr_addpts_"):
        target_id = int(data.replace("utr_addpts_", ""))
        await query.message.delete()
        try:
            ask = await client.ask(
                user_id,
                text=f"<b>👑 sᴇɴᴅ ᴘᴏɪɴᴛs ᴛᴏ ᴀᴅᴅ ᴛᴏ ᴜsᴇʀ <code>{target_id}</code>:</b>\n(e.g. <code>25</code>)\n/cancel - ᴀʙᴏʀᴛ",
                timeout=120
            )
        except ListenerTimeout:
            return await client.send_message(user_id, "⏰ ᴛɪᴍᴇᴏᴜᴛ: ɴᴏ ʀᴇsᴘᴏɴsᴇ ʀᴇᴄᴇɪᴠᴇᴅ.")
        if not ask.text or ask.text.startswith("/cancel") or not ask.text.strip().isdigit():
            return await client.send_message(user_id, "ᴘʀᴏᴄᴇss ᴄᴀɴᴄᴇʟʟᴇᴅ ᴏʀ ɪɴᴠᴀʟɪᴅ ɴᴜᴍʙᴇʀ.")
        
        pts = int(ask.text.strip())
        ref_data = await db.get_referral_data(target_id)
        ref_data['referral_points'] = ref_data.get('referral_points', 0) + pts
        ref_data['referral_earned_total'] = ref_data.get('referral_earned_total', 0) + pts
        await db.update_referral_data(target_id, ref_data)
        await db.log_referral_event('admin_grant', target_id, pts, f"Owner {user_id} grant via userstats")

        try:
            await client.send_message(
                target_id,
                f"🎁 <b>ᴀᴅᴍɪɴ ʙᴏɴᴜs:</b> ʏᴏᴜ ʜᴀᴠᴇ ʙᴇᴇɴ ɢʀᴀɴᴛᴇᴅ <b>+{pts} ʀᴇғᴇʀʀᴀʟ ᴘᴏɪɴᴛs</b> ʙʏ ᴛʜᴇ ᴀᴅᴍɪɴɪsᴛʀᴀᴛᴏʀ!\nᴄʜᴇᴄᴋ /referral."
            )
        except Exception:
            pass

        await client.send_message(
            user_id,
            f"✅ ɢʀᴀɴᴛᴇᴅ <b>+{pts} ᴘᴏɪɴᴛs</b> ᴛᴏ ᴜsᴇʀ <code>{target_id}</code>!",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("👤 ᴠɪᴇᴡ ᴘʀᴏғɪʟᴇ", callback_data=f"utr_user_{target_id}")]])
        )

    elif data.startswith("utr_vip_"):
        target_id = int(data.replace("utr_vip_", ""))
        prem = await db.get_premium_user(target_id)
        if prem:
            exp_str = fmt_dt(datetime.fromtimestamp(prem.get("expires_at", 0)))
            header = (
                f"<blockquote><b>⚙️ <u>ᴍᴀɴᴀɢᴇ ᴠɪᴘ: <code>{target_id}</code></u></b></blockquote>\n\n"
                f"• <b>ᴄᴜʀʀᴇɴᴛ ᴘʟᴀɴ:</b> <code>{prem.get('plan', 'pro').upper()}</code>\n"
                f"• <b>ᴇxᴘɪʀᴀᴛɪᴏɴ:</b> <code>{exp_str}</code>\n\n"
                "👇 <b>ᴄʜᴏᴏsᴇ ᴀɴ ᴀᴄᴛɪᴏɴ ᴛᴏ ᴇxᴛᴇɴᴅ ᴏʀ ʀᴇᴠᴏᴋᴇ:</b>"
            )
            btns = [
                [
                    InlineKeyboardButton("➕ +7 ᴅᴀʏs", callback_data=f"vipadmin_quickext_{target_id}_7_0"),
                    InlineKeyboardButton("➕ +30 ᴅᴀʏs", callback_data=f"vipadmin_quickext_{target_id}_30_0")
                ],
                [
                    InlineKeyboardButton("➕ +365 ᴅᴀʏs", callback_data=f"vipadmin_quickext_{target_id}_365_0"),
                    InlineKeyboardButton("🗑️ ʀᴇᴠᴏᴋᴇ ᴠɪᴘ", callback_data=f"vipadmin_quickrev_{target_id}_0")
                ],
                [
                    InlineKeyboardButton("🔙 ᴜsᴇʀ ᴘʀᴏғɪʟᴇ", callback_data=f"utr_user_{target_id}")
                ]
            ]
        else:
            header = (
                f"<blockquote><b>💎 <u>ɢʀᴀɴᴛ ᴠɪᴘ: <code>{target_id}</code></u></b></blockquote>\n\n"
                "ᴛʜɪs ᴜsᴇʀ ɪs ᴄᴜʀʀᴇɴᴛʟʏ ᴏɴ ᴛʜᴇ <b>ғʀᴇᴇ ᴛɪᴇʀ</b>.\n\n"
                "👇 <b>sᴇʟᴇᴄᴛ ᴀ ᴠɪᴘ ᴅᴜʀᴀᴛɪᴏɴ ᴛᴏ ᴀᴄᴛɪᴠᴀᴛᴇ:</b>"
            )
            btns = [
                [
                    InlineKeyboardButton("🥉 7 ᴅᴀʏs sᴛᴀʀᴛᴇʀ", callback_data=f"vipadmin_set_{target_id}_7_starter"),
                    InlineKeyboardButton("🥈 30 ᴅᴀʏs ᴘʀᴏ", callback_data=f"vipadmin_set_{target_id}_30_pro")
                ],
                [
                    InlineKeyboardButton("🥇 365 ᴅᴀʏs ᴜʟᴛʀᴀ", callback_data=f"vipadmin_set_{target_id}_365_ultra"),
                    InlineKeyboardButton("👑 ʟɪғᴇᴛɪᴍᴇ ᴠɪᴘ", callback_data=f"vipadmin_set_{target_id}_3650_ultra")
                ],
                [
                    InlineKeyboardButton("🔙 ᴜsᴇʀ ᴘʀᴏғɪʟᴇ", callback_data=f"utr_user_{target_id}")
                ]
            ]
        await query.message.edit_text(header, reply_markup=InlineKeyboardMarkup(btns))

    elif data == "utr_noop":
        await query.answer()

    elif data in ("utr_export_csv", "utr_export_json"):
        import csv, json, os
        await query.answer("📥 ɢᴇɴᴇʀᴀᴛɪɴɢ ᴇxᴘᴏʀᴛ...", show_alert=False)
        cursor = db.col.find({})
        users = [doc async for doc in cursor]
        
        prem_users = await db.get_all_premium_users()
        vip_ids = {p.get("user_id") for p in prem_users}
        
        is_csv = data == "utr_export_csv"
        ext = "csv" if is_csv else "json"
        path = f"/tmp/users_export.{ext}"
        
        fields = ["id", "name", "username", "first_seen", "last_seen", "forward_count", "is_vip"]
        
        export_data = []
        for u in users:
            uid = u.get("id")
            export_data.append({
                "id": uid,
                "name": u.get("name", ""),
                "username": u.get("username", ""),
                "first_seen": str(u.get("first_seen", "")),
                "last_seen": str(u.get("last_seen", "")),
                "forward_count": u.get("forward_count", 0),
                "is_vip": bool(uid in vip_ids)
            })
            
        if is_csv:
            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fields)
                writer.writeheader()
                writer.writerows(export_data)
        else:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(export_data, f, indent=2)
                
        await query.message.reply_document(
            document=path,
            caption=f"📦 <b>ᴜsᴇʀs ᴇxᴘᴏʀᴛ ({ext.upper()})</b>\n\n👥 <b>ᴛᴏᴛᴀʟ:</b> <code>{len(users)}</code>"
        )
        try:
            os.remove(path)
        except Exception:
            pass
