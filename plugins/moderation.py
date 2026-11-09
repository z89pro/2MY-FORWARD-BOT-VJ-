"""
plugins/moderation.py
──────────────────────
Content Moderation, Anti-Piracy, NSFW Prevention & Real-time Task Surveillance
Exclusively for Bot Owners & Administrators.

Commands:
  • /tasks or /alltasks  — Real-time monitor of all active user tasks with 1-click Stop & Ban
  • /canceltask <id>     — Abort any ongoing forward task immediately
  • /ban <id> [reason]   — Ban an abusive or infringing user & stop their running tasks
  • /unban <id>          — Remove ban restriction from a user
  • /banned              — View all currently banned users and violation reasons
  • /blacklist           — View global prohibited keywords and banned channels
  • /addblacklist <pat>  — Add a banned keyword or channel ID to block illegal content
  • /delblacklist <pat>  — Remove a pattern from the blacklist
"""

import logging
from pyrogram import Client, filters, enums
from pyrogram.types import Message, CallbackQuery, InlineKeyboardButton
from buttons import StyledMarkup as InlineKeyboardMarkup, btn, row, markup, colored_markup
from config import Config, temp
from database import db

logger = logging.getLogger(__name__)


# ── Active Tasks Surveillance (/tasks, /alltasks) ─────────────────────

@Client.on_message(filters.command(["tasks", "alltasks"]))
async def monitor_tasks_cmd(client: Client, message: Message):
    user_id = message.from_user.id if message.from_user else message.chat.id
    if not await db.is_admin(user_id):
        return await message.reply_text("⛔ <b>ᴛʜɪs ᴄᴏᴍᴍᴀɴᴅ ɪs ʀᴇsᴛʀɪᴄᴛᴇᴅ ᴛᴏ ʙᴏᴛ ᴀᴅᴍɪɴɪsᴛʀᴀᴛᴏʀs.</b>")

    tasks = await db.get_active_tasks()
    if not tasks:
        return await message.reply_text(
            "<blockquote><b>🛡️ <u>ᴛᴀsᴋ sᴜʀᴠᴇɪʟʟᴀɴᴄᴇ ᴄᴇɴᴛᴇʀ</u></b></blockquote>\n\n"
            "✨ <b>ɴᴏ ᴀᴄᴛɪᴠᴇ ғᴏʀᴡᴀʀᴅ ᴛᴀsᴋs ʀᴜɴɴɪɴɢ ᴄᴜʀʀᴇɴᴛʟʏ.</b>\n"
            "<i>ᴀʟʟ ᴡᴏʀᴋᴇʀs ᴀʀᴇ ɪᴅʟᴇ ᴀɴᴅ sʏsᴛᴇᴍ ɪs ᴄʟᴇᴀɴ.</i>",
            reply_markup=markup(row(btn("🔄 ʀᴇғʀᴇsʜ", "mod_tasks_refresh", "blue")))
        )

    text = (
        f"<blockquote><b>🛡️ <u>ᴀᴄᴛɪᴠᴇ ғᴏʀᴡᴀʀᴅ ᴛᴀsᴋs ({len(tasks)})</u></b></blockquote>\n"
        f"<i>ᴍᴏɴɪᴛᴏʀɪɴɢ ᴀʟʟ ʟɪᴠᴇ ᴜsᴇʀ ᴊᴏʙs ғᴏʀ ғᴀɪʀ ᴜsᴇ & ᴄᴏɴᴛᴇɴᴛ ᴘᴏʟɪᴄʏ:</i>\n\n"
    )

    rows = []
    for idx, t in enumerate(tasks[:10], start=1):
        tid = t.get("task_id", "unknown")
        uid = t.get("user_id", "unknown")
        src = t.get("from_chat", "N/A")
        dst = t.get("to_chat", "N/A")
        fetched = t.get("fetched", 0)
        tot = t.get("limit", 0)
        flt = t.get("filtered", 0)

        text += (
            f"<b>{idx}. ᴛᴀsᴋ:</b> <code>{tid}</code>\n"
            f"👤 <b>ᴜsᴇʀ:</b> <code>{uid}</code>\n"
            f"📡 <b>sᴏᴜʀᴄᴇ:</b> <code>{src}</code> ➜ 🎯 <b>ᴛᴀʀɢᴇᴛ:</b> <code>{dst}</code>\n"
            f"📊 <b>ᴘʀᴏɢʀᴇss:</b> <code>{fetched}/{tot}</code> (🚫 ғɪʟᴛᴇʀᴇᴅ: {flt})\n"
            "────────────────────────────\n"
        )

        rows.append(row(
            btn(f"🛑 sᴛᴏᴘ #{idx}", f"mod_stop_{tid}", "red"),
            btn(f"🚫 ʙᴀɴ ᴜsᴇʀ", f"mod_ban_{uid}", "red")
        ))

    rows.append(row(btn("🔄 ʀᴇғʀᴇsʜ", "mod_tasks_refresh", "blue")))

    await message.reply_text(
        text,
        reply_markup=markup(*rows),
        disable_web_page_preview=True
    )


@Client.on_callback_query(filters.regex(r"^mod_tasks_refresh$"))
async def refresh_tasks_callback(client: Client, query: CallbackQuery):
    user_id = query.from_user.id
    if not await db.is_admin(user_id):
        return await query.answer("⛔ Admin only!", show_alert=True)

    tasks = await db.get_active_tasks()
    if not tasks:
        await query.answer("No active tasks found.")
        return await query.message.edit_text(
            "<blockquote><b>🛡️ <u>ᴛᴀsᴋ sᴜʀᴠᴇɪʟʟᴀɴᴄᴇ ᴄᴇɴᴛᴇʀ</u></b></blockquote>\n\n"
            "✨ <b>ɴᴏ ᴀᴄᴛɪᴠᴇ ғᴏʀᴡᴀʀᴅ ᴛᴀsᴋs ʀᴜɴɴɪɴɢ ᴄᴜʀʀᴇɴᴛʟʏ.</b>\n"
            "<i>ᴀʟʟ ᴡᴏʀᴋᴇʀs ᴀʀᴇ ɪᴅʟᴇ ᴀɴᴅ sʏsᴛᴇᴍ ɪs ᴄʟᴇᴀɴ.</i>",
            reply_markup=markup(row(btn("🔄 ʀᴇғʀᴇsʜ", "mod_tasks_refresh", "blue")))
        )

    text = (
        f"<blockquote><b>🛡️ <u>ᴀᴄᴛɪᴠᴇ ғᴏʀᴡᴀʀᴅ ᴛᴀsᴋs ({len(tasks)})</u></b></blockquote>\n"
        f"<i>ᴍᴏɴɪᴛᴏʀɪɴɢ ᴀʟʟ ʟɪᴠᴇ ᴜsᴇʀ ᴊᴏʙs ғᴏʀ ғᴀɪʀ ᴜsᴇ & ᴄᴏɴᴛᴇɴᴛ ᴘᴏʟɪᴄʏ:</i>\n\n"
    )

    rows = []
    for idx, t in enumerate(tasks[:10], start=1):
        tid = t.get("task_id", "unknown")
        uid = t.get("user_id", "unknown")
        src = t.get("from_chat", "N/A")
        dst = t.get("to_chat", "N/A")
        fetched = t.get("fetched", 0)
        tot = t.get("limit", 0)
        flt = t.get("filtered", 0)

        text += (
            f"<b>{idx}. ᴛᴀsᴋ:</b> <code>{tid}</code>\n"
            f"👤 <b>ᴜsᴇʀ:</b> <code>{uid}</code>\n"
            f"📡 <b>sᴏᴜʀᴄᴇ:</b> <code>{src}</code> ➜ 🎯 <b>ᴛᴀʀɢᴇᴛ:</b> <code>{dst}</code>\n"
            f"📊 <b>ᴘʀᴏɢʀᴇss:</b> <code>{fetched}/{tot}</code> (🚫 ғɪʟᴛᴇʀᴇᴅ: {flt})\n"
            "────────────────────────────\n"
        )

        rows.append(row(
            btn(f"🛑 sᴛᴏᴘ #{idx}", f"mod_stop_{tid}", "red"),
            btn(f"🚫 ʙᴀɴ ᴜsᴇʀ", f"mod_ban_{uid}", "red")
        ))

    rows.append(row(btn("🔄 ʀᴇғʀᴇsʜ", "mod_tasks_refresh", "blue")))
    await query.answer()
    await query.message.edit_text(
        text,
        reply_markup=markup(*rows),
        disable_web_page_preview=True
    )


# ── Stop Task Handler ────────────────────────────────────────────────

@Client.on_callback_query(filters.regex(r"^mod_stop_(.+)$"))
async def stop_task_callback(client: Client, query: CallbackQuery):
    user_id = query.from_user.id
    if not await db.is_admin(user_id):
        return await query.answer("⛔ Admin only!", show_alert=True)

    task_id = query.matches[0].group(1)
    task = await db.get_active_task(task_id)
    if not task:
        return await query.answer("⚠️ Task already completed or removed.", show_alert=True)

    owner_uid = task.get("user_id")
    if owner_uid:
        temp.CANCEL[owner_uid] = True
    await db.delete_active_task(task_id)

    if Config.LOG_CHANNEL:
        try:
            await client.send_message(
                Config.LOG_CHANNEL,
                f"🛑 <b>#TaskTerminatedByAdmin</b>\n\n"
                f"👮 <b>Admin:</b> <code>{user_id}</code>\n"
                f"👤 <b>User:</b> <code>{owner_uid}</code>\n"
                f"🆔 <b>Task ID:</b> <code>{task_id}</code>"
            )
        except Exception:
            pass

    await query.answer(f"✅ Task {task_id} terminated!", show_alert=True)
    # Refresh view
    tasks = await db.get_active_tasks()
    if not tasks:
        await query.message.edit_text(
            "<blockquote><b>🛡️ <u>ᴛᴀsᴋ sᴜʀᴠᴇɪʟʟᴀɴᴄᴇ ᴄᴇɴᴛᴇʀ</u></b></blockquote>\n\n"
            "✨ <b>ɴᴏ ᴀᴄᴛɪᴠᴇ ғᴏʀᴡᴀʀᴅ ᴛᴀsᴋs ʀᴜɴɴɪɴɢ ᴄᴜʀʀᴇɴᴛʟʏ.</b>",
            reply_markup=markup(row(btn("🔄 ʀᴇғʀᴇsʜ", "mod_tasks_refresh", "blue")))
        )


@Client.on_message(filters.command(["canceltask"]))
async def cancel_task_cmd(client: Client, message: Message):
    user_id = message.from_user.id if message.from_user else message.chat.id
    if not await db.is_admin(user_id):
        return await message.reply_text("⛔ <b>ᴛʜɪs ᴄᴏᴍᴍᴀɴᴅ ɪs ʀᴇsᴛʀɪᴄᴛᴇᴅ ᴛᴏ ʙᴏᴛ ᴀᴅᴍɪɴɪsᴛʀᴀᴛᴏʀs.</b>")

    if len(message.command) < 2:
        return await message.reply_text("<b>ᴜsᴀɢᴇ:</b> <code>/canceltask &lt;task_id&gt;</code>")

    task_id = message.command[1].strip()
    task = await db.get_active_task(task_id)
    if not task:
        return await message.reply_text(f"⚠️ <b>ᴛᴀsᴋ <code>{task_id}</code> ɴᴏᴛ ғᴏᴜɴᴅ ᴏʀ ᴀʟʀᴇᴀᴅʏ ғɪɴɪsʜᴇᴅ.</b>")

    owner_uid = task.get("user_id")
    if owner_uid:
        temp.CANCEL[owner_uid] = True
    await db.delete_active_task(task_id)

    if Config.LOG_CHANNEL:
        try:
            await client.send_message(
                Config.LOG_CHANNEL,
                f"🛑 <b>#TaskTerminatedByAdmin</b>\n\n"
                f"👮 <b>Admin:</b> <code>{user_id}</code>\n"
                f"👤 <b>User:</b> <code>{owner_uid}</code>\n"
                f"🆔 <b>Task ID:</b> <code>{task_id}</code>"
            )
        except Exception:
            pass

    await message.reply_text(f"✅ <b>ᴛᴀsᴋ <code>{task_id}</code> ʜᴀs ʙᴇᴇɴ sᴜᴄᴄᴇssғᴜʟʟʏ ᴛᴇʀᴍɪɴᴀᴛᴇᴅ.</b>")


# ── Ban & Unban Management (/ban, /unban, /banned) ────────────────────

@Client.on_message(filters.command(["ban"]))
async def ban_user_cmd(client: Client, message: Message):
    user_id = message.from_user.id if message.from_user else message.chat.id
    if not await db.is_admin(user_id):
        return await message.reply_text("⛔ <b>ᴛʜɪs ᴄᴏᴍᴍᴀɴᴅ ɪs ʀᴇsᴛʀɪᴄᴛᴇᴅ ᴛᴏ ʙᴏᴛ ᴀᴅᴍɪɴɪsᴛʀᴀᴛᴏʀs.</b>")

    if len(message.command) < 2:
        return await message.reply_text(
            "<blockquote><b>🚫 <u>ʙᴀɴ ᴜsᴇʀ</u></b></blockquote>\n\n"
            "<b>ᴜsᴀɢᴇ:</b> <code>/ban &lt;user_id&gt; &lt;reason&gt;</code>\n"
            "<b>ᴇxᴀᴍᴘʟᴇ:</b> <code>/ban 123456789 Piracy / NSFW Violation</code>"
        )

    try:
        target_uid = int(message.command[1].strip())
    except ValueError:
        return await message.reply_text("⚠️ <b>ɪɴᴠᴀʟɪᴅ ᴜsᴇʀ ɪᴅ. ᴍᴜsᴛ ʙᴇ ᴀ ɴᴜᴍʙᴇʀ.</b>")

    if await db.is_admin(target_uid):
        return await message.reply_text("❌ <b>ᴄᴀɴɴᴏᴛ ʙᴀɴ ʙᴏᴛ ᴏᴡɴᴇʀ ᴏʀ ᴀᴅᴍɪɴ.</b>")

    reason = " ".join(message.command[2:]).strip() or "Violation of bot usage terms"
    await db.ban_user(target_uid, reason)

    # Immediately terminate any active tasks belonging to this user
    temp.CANCEL[target_uid] = True
    user_task = await db.get_user_active_task(target_uid)
    if user_task:
        await db.delete_active_task(user_task.get("task_id"))

    if Config.LOG_CHANNEL:
        try:
            await client.send_message(
                Config.LOG_CHANNEL,
                f"🚫 <b>#UserBanned</b>\n\n"
                f"👤 <b>User:</b> <code>{target_uid}</code>\n"
                f"👮 <b>Admin:</b> <code>{user_id}</code>\n"
                f"📝 <b>Reason:</b> {reason}"
            )
        except Exception:
            pass

    await message.reply_text(
        f"<blockquote><b>🚫 <u>ᴜsᴇʀ ʙᴀɴɴᴇᴅ sᴜᴄᴄᴇssғᴜʟʟʏ</u></b></blockquote>\n\n"
        f"👤 <b>ᴜsᴇʀ ɪᴅ:</b> <code>{target_uid}</code>\n"
        f"📝 <b>ʀᴇᴀsᴏɴ:</b> {reason}\n"
        f"🛑 <i>ᴀʟʟ ʀᴜɴɴɪɴɢ ᴛᴀsᴋs ғᴏʀ ᴛʜɪs ᴜsᴇʀ ʜᴀᴠᴇ ʙᴇᴇɴ ᴛᴇʀᴍɪɴᴀᴛᴇᴅ.</i>",
        reply_markup=markup(row(btn("🔓 ᴜɴʙᴀɴ", f"mod_unban_{target_uid}", "green")))
    )


@Client.on_callback_query(filters.regex(r"^mod_ban_(\d+)$"))
async def ban_callback(client: Client, query: CallbackQuery):
    user_id = query.from_user.id
    if not await db.is_admin(user_id):
        return await query.answer("⛔ Admin only!", show_alert=True)

    target_uid = int(query.matches[0].group(1))
    if await db.is_admin(target_uid):
        return await query.answer("❌ Cannot ban bot owner or admin.", show_alert=True)

    reason = "Infringing content / Moderation flag"
    await db.ban_user(target_uid, reason)
    temp.CANCEL[target_uid] = True

    user_task = await db.get_user_active_task(target_uid)
    if user_task:
        await db.delete_active_task(user_task.get("task_id"))

    if Config.LOG_CHANNEL:
        try:
            await client.send_message(
                Config.LOG_CHANNEL,
                f"🚫 <b>#UserBanned</b>\n\n"
                f"👤 <b>User:</b> <code>{target_uid}</code>\n"
                f"👮 <b>Admin:</b> <code>{user_id}</code>\n"
                f"📝 <b>Reason:</b> {reason}"
            )
        except Exception:
            pass

    await query.answer(f"✅ User {target_uid} has been banned!", show_alert=True)


@Client.on_message(filters.command(["unban"]))
async def unban_user_cmd(client: Client, message: Message):
    user_id = message.from_user.id if message.from_user else message.chat.id
    if not await db.is_admin(user_id):
        return await message.reply_text("⛔ <b>ᴛʜɪs ᴄᴏᴍᴍᴀɴᴅ ɪs ʀᴇsᴛʀɪᴄᴛᴇᴅ ᴛᴏ ʙᴏᴛ ᴀᴅᴍɪɴɪsᴛʀᴀᴛᴏʀs.</b>")

    if len(message.command) < 2:
        return await message.reply_text("<b>ᴜsᴀɢᴇ:</b> <code>/unban &lt;user_id&gt;</code>")

    try:
        target_uid = int(message.command[1].strip())
    except ValueError:
        return await message.reply_text("⚠️ <b>ɪɴᴠᴀʟɪᴅ ᴜsᴇʀ ɪᴅ. ᴍᴜsᴛ ʙᴇ ᴀ ɴᴜᴍʙᴇʀ.</b>")

    await db.remove_ban(target_uid)

    if Config.LOG_CHANNEL:
        try:
            await client.send_message(
                Config.LOG_CHANNEL,
                f"🔓 <b>#UserUnbanned</b>\n\n"
                f"👤 <b>User:</b> <code>{target_uid}</code>\n"
                f"👮 <b>Admin:</b> <code>{user_id}</code>"
            )
        except Exception:
            pass

    await message.reply_text(f"✅ <b>ᴜsᴇʀ <code>{target_uid}</code> ʜᴀs ʙᴇᴇɴ ᴜɴʙᴀɴɴᴇᴅ.</b>")


@Client.on_callback_query(filters.regex(r"^mod_unban_(\d+)$"))
async def unban_callback(client: Client, query: CallbackQuery):
    user_id = query.from_user.id
    if not await db.is_admin(user_id):
        return await query.answer("⛔ Admin only!", show_alert=True)

    target_uid = int(query.matches[0].group(1))
    await db.remove_ban(target_uid)
    await query.answer(f"✅ User {target_uid} unbanned!", show_alert=True)
    await query.message.edit_text(f"✅ <b>ᴜsᴇʀ <code>{target_uid}</code> ʜᴀs ʙᴇᴇɴ sᴜᴄᴄᴇssғᴜʟʟʏ ᴜɴʙᴀɴɴᴇᴅ.</b>")


@Client.on_message(filters.command(["banned"]))
async def list_banned_cmd(client: Client, message: Message):
    user_id = message.from_user.id if message.from_user else message.chat.id
    if not await db.is_admin(user_id):
        return await message.reply_text("⛔ <b>ᴛʜɪs ᴄᴏᴍᴍᴀɴᴅ ɪs ʀᴇsᴛʀɪᴄᴛᴇᴅ ᴛᴏ ʙᴏᴛ ᴀᴅᴍɪɴɪsᴛʀᴀᴛᴏʀs.</b>")

    banned_docs = await db.get_banned_details()
    if not banned_docs:
        return await message.reply_text("✨ <b>ɴᴏ ᴜsᴇʀs ᴀʀᴇ ᴄᴜʀʀᴇɴᴛʟʏ ʙᴀɴɴᴇᴅ.</b>")

    text = f"<blockquote><b>🚫 <u>ʙᴀɴɴᴇᴅ ᴜsᴇʀs ({len(banned_docs)})</u></b></blockquote>\n\n"
    rows = []
    for b in banned_docs[:15]:
        uid = b.get("id")
        reason = b.get("ban_status", {}).get("ban_reason", "No reason provided")
        name = b.get("name", "Unknown")
        text += f"• <b>{name}</b> (<code>{uid}</code>)\n  <i>ʀᴇᴀsᴏɴ:</i> {reason}\n\n"
        rows.append(row(btn(f"🔓 ᴜɴʙᴀɴ {uid}", f"mod_unban_{uid}", "green")))

    await message.reply_text(text, reply_markup=markup(*rows))


# ── Global Blacklist System (/blacklist, /addblacklist, /delblacklist) ─

@Client.on_message(filters.command(["blacklist"]))
async def view_blacklist_cmd(client: Client, message: Message):
    user_id = message.from_user.id if message.from_user else message.chat.id
    if not await db.is_admin(user_id):
        return await message.reply_text("⛔ <b>ᴛʜɪs ᴄᴏᴍᴍᴀɴᴅ ɪs ʀᴇsᴛʀɪᴄᴛᴇᴅ ᴛᴏ ʙᴏᴛ ᴀᴅᴍɪɴɪsᴛʀᴀᴛᴏʀs.</b>")

    bl = await db.get_blacklist()
    if not bl:
        return await message.reply_text(
            "<blockquote><b>🛡️ <u>ᴄᴏɴᴛᴇɴᴛ ᴍᴏᴅᴇʀᴀᴛɪᴏɴ ʙʟᴀᴄᴋʟɪsᴛ</u></b></blockquote>\n\n"
            "✨ <b>ᴛʜᴇ ʙʟᴀᴄᴋʟɪsᴛ ɪs ᴄᴜʀʀᴇɴᴛʟʏ ᴇᴍᴘᴛʏ.</b>\n\n"
            "👉 <b>ᴜsᴇ:</b> <code>/addblacklist &lt;keyword_or_channel_id&gt;</code> ᴛᴏ ʙʟᴏᴄᴋ ɪʟʟᴇɢᴀʟ ᴏʀ ɴsғᴡ ᴄᴏɴᴛᴇɴᴛ."
        )

    text = (
        f"<blockquote><b>🛡️ <u>ᴄᴏɴᴛᴇɴᴛ ᴍᴏᴅᴇʀᴀᴛɪᴏɴ ʙʟᴀᴄᴋʟɪsᴛ ({len(bl)})</u></b></blockquote>\n"
        f"<i>ᴀɴʏ ᴍᴀᴛᴄʜɪɴɢ ғɪʟᴇs ᴏʀ ᴄʜᴀɴɴᴇʟs ᴀʀᴇ ᴀᴜᴛᴏᴍᴀᴛɪᴄᴀʟʟʏ ʙʟᴏᴄᴋᴇᴅ & ᴀʟᴇʀᴛᴇᴅ:</i>\n\n"
    )

    kw_list = [item["pattern"] for item in bl if item.get("type") == "keyword"]
    ch_list = [item["pattern"] for item in bl if item.get("type") == "channel"]

    if ch_list:
        text += "<b>🚫 ʙᴀɴɴᴇᴅ ᴄʜᴀɴɴᴇʟs:</b>\n"
        for c in ch_list:
            text += f"• <code>{c}</code>\n"
        text += "\n"

    if kw_list:
        text += "<b>🔤 ʙᴀɴɴᴇᴅ ᴋᴇʏᴡᴏʀᴅs:</b>\n"
        for k in kw_list:
            text += f"• <code>{k}</code>\n"

    text += "\n👉 <i>ᴜsᴇ <code>/delblacklist &lt;pattern&gt;</code> ᴛᴏ ʀᴇᴍᴏᴠᴇ ᴀɴ ɪᴛᴇᴍ.</i>"
    await message.reply_text(text)


@Client.on_message(filters.command(["addblacklist", "blacklistadd"]))
async def add_blacklist_cmd(client: Client, message: Message):
    user_id = message.from_user.id if message.from_user else message.chat.id
    if not await db.is_admin(user_id):
        return await message.reply_text("⛔ <b>ᴛʜɪs ᴄᴏᴍᴍᴀɴᴅ ɪs ʀᴇsᴛʀɪᴄᴛᴇᴅ ᴛᴏ ʙᴏᴛ ᴀᴅᴍɪɴɪsᴛʀᴀᴛᴏʀs.</b>")

    if len(message.command) < 2:
        return await message.reply_text(
            "<blockquote><b>🛡️ <u>ᴀᴅᴅ ᴛᴏ ʙʟᴀᴄᴋʟɪsᴛ</u></b></blockquote>\n\n"
            "<b>ᴜsᴀɢᴇ:</b>\n"
            "• <code>/addblacklist &lt;keyword&gt;</code> — ʙʟᴏᴄᴋ ᴀ ᴡᴏʀᴅ ᴏʀ ɴsғᴡ ᴛᴇʀᴍ\n"
            "• <code>/addblacklist chan &lt;channel_id&gt;</code> — ʙʟᴏᴄᴋ ᴀɴ ᴇɴᴛɪʀᴇ ᴄʜᴀɴɴᴇʟ\n\n"
            "<b>ᴇxᴀᴍᴘʟᴇs:</b>\n"
            "<code>/addblacklist porn</code>\n"
            "<code>/addblacklist chan -1001234567890</code>"
        )

    args = message.command[1:]
    if args[0].lower() in ("chan", "channel"):
        if len(args) < 2:
            return await message.reply_text("<b>ᴜsᴀɢᴇ:</b> <code>/addblacklist chan &lt;channel_id&gt;</code>")
        itype = "channel"
        pat = args[1].strip()
    else:
        pat = " ".join(args).strip()
        itype = "channel" if pat.startswith(("-100", "@")) else "keyword"

    await db.add_blacklist(pat, itype)

    if Config.LOG_CHANNEL:
        try:
            await client.send_message(
                Config.LOG_CHANNEL,
                f"🛡️ <b>#BlacklistAdded</b>\n\n"
                f"👮 <b>Admin:</b> <code>{user_id}</code>\n"
                f"🏷️ <b>Type:</b> <code>{itype}</code>\n"
                f"🚫 <b>Pattern:</b> <code>{pat}</code>"
            )
        except Exception:
            pass

    await message.reply_text(
        f"✅ <b>ᴀᴅᴅᴇᴅ ᴛᴏ ʙʟᴀᴄᴋʟɪsᴛ ({itype.upper()}):</b> <code>{pat}</code>\n\n"
        f"<i>ᴀɴʏ ᴛᴀsᴋ ᴀᴛᴛᴇᴍᴘᴛɪɴɢ ᴛᴏ ғᴏʀᴡᴀʀᴅ ᴛʜɪs ᴄᴏɴᴛᴇɴᴛ ᴡɪʟʟ ʙᴇ ᴀᴜᴛᴏᴍᴀᴛɪᴄᴀʟʟʏ ɪɴᴛᴇʀᴄᴇᴘᴛᴇᴅ.</i>"
    )


@Client.on_message(filters.command(["delblacklist", "blacklistdel", "rmblacklist"]))
async def del_blacklist_cmd(client: Client, message: Message):
    user_id = message.from_user.id if message.from_user else message.chat.id
    if not await db.is_admin(user_id):
        return await message.reply_text("⛔ <b>ᴛʜɪs ᴄᴏᴍᴍᴀɴᴅ ɪs ʀᴇsᴛʀɪᴄᴛᴇᴅ ᴛᴏ ʙᴏᴛ ᴀᴅᴍɪɴɪsᴛʀᴀᴛᴏʀs.</b>")

    if len(message.command) < 2:
        return await message.reply_text("<b>ᴜsᴀɢᴇ:</b> <code>/delblacklist &lt;pattern&gt;</code>")

    pat = " ".join(message.command[1:]).strip()
    await db.remove_blacklist(pat)

    if Config.LOG_CHANNEL:
        try:
            await client.send_message(
                Config.LOG_CHANNEL,
                f"🛡️ <b>#BlacklistRemoved</b>\n\n"
                f"👮 <b>Admin:</b> <code>{user_id}</code>\n"
                f"🚫 <b>Pattern:</b> <code>{pat}</code>"
            )
        except Exception:
            pass

    await message.reply_text(f"✅ <b>ʀᴇᴍᴏᴠᴇᴅ ғʀᴏᴍ ʙʟᴀᴄᴋʟɪsᴛ:</b> <code>{pat}</code>")


# ── Channel Surveillance & Oversight (/allchannels, /userchannels, /checkchannel) ──

@Client.on_message(filters.command(["allchannels", "channels"]))
async def all_channels_cmd(client: Client, message: Message):
    user_id = message.from_user.id if message.from_user else message.chat.id
    if not await db.is_admin(user_id):
        return await message.reply_text("⛔ <b>ᴛʜɪs ᴄᴏᴍᴍᴀɴᴅ ɪs ʀᴇsᴛʀɪᴄᴛᴇᴅ ᴛᴏ ʙᴏᴛ ᴀᴅᴍɪɴɪsᴛʀᴀᴛᴏʀs.</b>")

    cursor = db.chl.find({})
    channels = [c async for c in cursor]
    if not channels:
        return await message.reply_text("✨ <b>ɴᴏ ᴜsᴇʀ ᴄʜᴀɴɴᴇʟs ʀᴇɢɪsᴛᴇʀᴇᴅ ɪɴ ʙᴏᴛ.</b>")

    text = f"<blockquote><b>📡 <u>ᴀʟʟ ʀᴇɢɪsᴛᴇʀᴇᴅ ᴜsᴇʀ ᴄʜᴀɴɴᴇʟs ({len(channels)})</u></b></blockquote>\n\n"
    for idx, c in enumerate(channels[:20], start=1):
        uid = c.get("user_id")
        cid = c.get("chat_id")
        title = c.get("title") or "Unknown Channel"
        uname = c.get("username")
        link_str = f" (@{uname.lstrip('@')})" if uname and uname != "private" else ""
        text += (
            f"<b>{idx}. {title}</b>{link_str}\n"
            f"  🆔 <code>{cid}</code> | 👤 <b>User:</b> <code>{uid}</code>\n"
        )
    if len(channels) > 20:
        text += f"\n<i>...and {len(channels) - 20} more channels.</i>"

    await message.reply_text(text, disable_web_page_preview=True)


@Client.on_message(filters.command(["userchannels", "uchannels"]))
async def user_channels_cmd(client: Client, message: Message):
    user_id = message.from_user.id if message.from_user else message.chat.id
    if not await db.is_admin(user_id):
        return await message.reply_text("⛔ <b>ᴛʜɪs ᴄᴏᴍᴍᴀɴᴅ ɪs ʀᴇsᴛʀɪᴄᴛᴇᴅ ᴛᴏ ʙᴏᴛ ᴀᴅᴍɪɴɪsᴛʀᴀᴛᴏʀs.</b>")

    if len(message.command) < 2:
        return await message.reply_text("<b>ᴜsᴀɢᴇ:</b> <code>/userchannels &lt;user_id&gt;</code>")

    try:
        target_uid = int(message.command[1].strip())
    except ValueError:
        return await message.reply_text("⚠️ <b>ɪɴᴠᴀʟɪᴅ ᴜsᴇʀ ɪᴅ.</b>")

    channels = await db.get_user_channels(target_uid)
    if not channels:
        return await message.reply_text(f"✨ <b>ᴜsᴇʀ <code>{target_uid}</code> ʜᴀs ɴᴏ ᴄᴏɴғɪɢᴜʀᴇᴅ ᴄʜᴀɴɴᴇʟs.</b>")

    text = f"<blockquote><b>📡 <u>ᴄᴏɴғɪɢᴜʀᴇᴅ ᴄʜᴀɴɴᴇʟs ғᴏʀ {target_uid} ({len(channels)})</u></b></blockquote>\n\n"
    for idx, c in enumerate(channels, start=1):
        cid = c.get("chat_id")
        title = c.get("title") or "Unknown Channel"
        uname = c.get("username")
        link_str = f" (@{uname.lstrip('@')})" if uname and uname != "private" else ""
        text += f"<b>{idx}. {title}</b>{link_str}\n  🆔 <code>{cid}</code>\n"

    await message.reply_text(text, disable_web_page_preview=True)


@Client.on_message(filters.command(["checkchannel", "probechannel"]))
async def check_channel_cmd(client: Client, message: Message):
    user_id = message.from_user.id if message.from_user else message.chat.id
    if not await db.is_admin(user_id):
        return await message.reply_text("⛔ <b>ᴛʜɪs ᴄᴏᴍᴍᴀɴᴅ ɪs ʀᴇsᴛʀɪᴄᴛᴇᴅ ᴛᴏ ʙᴏᴛ ᴀᴅᴍɪɴɪsᴛʀᴀᴛᴏʀs.</b>")

    if len(message.command) < 2:
        return await message.reply_text("<b>ᴜsᴀɢᴇ:</b> <code>/checkchannel &lt;channel_id_or_username&gt;</code>")

    raw_target = message.command[1].strip()
    target = int(raw_target) if raw_target.lstrip("-").isdigit() else raw_target

    try:
        chat = await client.get_chat(target)
        title = chat.title or "Unknown"
        c_type = getattr(chat.type, "value", str(chat.type))
        uname = f"@{chat.username}" if chat.username else "Private"
        members = chat.members_count or "Unknown"
        desc = chat.description or "None"

        # Check against blacklist
        is_bl, bl_match = await db.check_blacklisted(text=f"{title} {desc}", channel=chat.id)
        bl_flag = f"🚨 <b>ʙʟᴀᴄᴋʟɪsᴛᴇᴅ ({bl_match})</b>" if is_bl else "🟢 <b>ᴄʟᴇᴀɴ</b>"

        text = (
            f"<blockquote><b>🔍 <u>ᴄʜᴀɴɴᴇʟ ɪɴsᴘᴇᴄᴛɪᴏɴ ʀᴇᴘᴏʀᴛ</u></b></blockquote>\n\n"
            f"🏷 <b>ᴛɪᴛʟᴇ:</b> <b>{title}</b>\n"
            f"🆔 <b>ᴄʜᴀᴛ ɪᴅ:</b> <code>{chat.id}</code>\n"
            f"🔗 <b>ᴜsᴇʀɴᴀᴍᴇ:</b> <code>{uname}</code>\n"
            f"📂 <b>ᴛʏᴘᴇ:</b> <code>{c_type}</code>\n"
            f"👥 <b>ᴍᴇᴍʙᴇʀs:</b> <code>{members}</code>\n"
            f"🛡️ <b>ᴍᴏᴅᴇʀᴀᴛɪᴏɴ sᴛᴀᴛᴜs:</b> {bl_flag}\n"
            f"📝 <b>ᴅᴇsᴄʀɪᴘᴛɪᴏɴ:</b> <code>{desc[:100]}</code>\n"
        )
        await message.reply_text(text, disable_web_page_preview=True)
    except Exception as e:
        await message.reply_text(
            f"⚠️ <b>ᴄᴏᴜʟᴅ ɴᴏᴛ ɪɴsᴘᴇᴄᴛ ᴄʜᴀɴɴᴇʟ:</b> <code>{e}</code>\n\n"
            f"<i>ᴛᴇʟᴇɢʀᴀᴍ ᴏɴʟʏ ᴀʟʟᴏᴡs ɪɴsᴘᴇᴄᴛɪɴɢ ᴘᴜʙʟɪᴄ ᴄʜᴀɴɴᴇʟs ᴏʀ ᴘʀɪᴠᴀᴛᴇ ᴄʜᴀɴɴᴇʟs ᴡʜᴇʀᴇ ᴛʜᴇ ʙᴏᴛ ɪs ᴀ ᴍᴇᴍʙᴇʀ/ᴀᴅᴍɪɴ.</i>"
        )
