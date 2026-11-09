import os
import sys
import html
import asyncio
import logging
from config import Config, temp
from database import db
from pyrogram import Client, filters, enums
from pyrogram.types import InlineKeyboardButton, CallbackQuery, Message
from pyrogram.errors import MessageIdInvalid, MessageNotModified, RPCError, ListenerTimeout
from buttons import StyledMarkup as InlineKeyboardMarkup, btn, btn_url, row, markup, colored_markup

logger = logging.getLogger("SkinetConfig")

async def get_admin_display_name(client: Client, user_id: int) -> tuple:
    """Resolves (name, username) for an admin or authorized user."""
    name, username = "", ""
    try:
        u = await db.get_user(user_id)
        if u:
            from plugins.usertrack import display_name
            dname = display_name(u)
            if dname and not dname.startswith("User "):
                name = dname
            username = u.get("username") or ""
    except Exception:
        pass

    if not name:
        try:
            tg_u = await client.get_users(user_id)
            if tg_u:
                first = tg_u.first_name or ""
                last = f" {tg_u.last_name}" if tg_u.last_name else ""
                full = f"{first}{last}".strip()
                name = full or tg_u.username or f"User {user_id}"
                username = tg_u.username or username
        except Exception:
            pass

    return name or f"User {user_id}", username

async def safe_edit_message(message: Message, text: str, reply_markup=None, disable_web_page_preview: bool = True):
    try:
        return await message.edit_text(text, reply_markup=reply_markup, disable_web_page_preview=disable_web_page_preview)
    except MessageNotModified:
        return message
    except (MessageIdInvalid, RPCError):
        try:
            return await message.reply_text(text, reply_markup=reply_markup, disable_web_page_preview=disable_web_page_preview)
        except Exception:
            return None
    except Exception:
        return None

async def is_admin(user_id: int) -> bool:
    return await db.is_admin(user_id)

def mask_secret(s: str) -> str:
    if not s or not isinstance(s, str):
        return "N/A"
    s = s.strip()
    if len(s) <= 8:
        return "•" * len(s)
    return s[:4] + "•" * 8 + s[-4:]

async def build_config_view() -> str:
    fsub_status = "🟢 <b>ᴇɴᴀʙʟᴇᴅ</b>" if Config.FORCE_SUB_ON else "🔴 <b>ᴅɪsᴀʙʟᴇᴅ</b>"
    fsub_chan = f"<code>{Config.FORCE_SUB_CHANNEL}</code>" if Config.FORCE_SUB_CHANNEL else "<i>ɴᴏɴᴇ (ɴᴏᴛ sᴇᴛ)</i>"
    log_chan = f"<code>{Config.LOG_CHANNEL}</code>" if (Config.LOG_CHANNEL and Config.LOG_CHANNEL != 0) else "<code>0</code> <i>(ᴅɪsᴀʙʟᴇᴅ)</i>"
    dump_chan = f"<code>{Config.DUMP_CHANNEL}</code>" if (Config.DUMP_CHANNEL and Config.DUMP_CHANNEL != 0) else "<code>0</code> <i>(ᴅɪsᴀʙʟᴇᴅ)</i>"
    all_admins = await db.get_all_admins()
    admins_str = " ".join([f"<code>{x}</code>" for x in all_admins]) if all_admins else "<i>ɴᴏɴᴇ</i>"
    masked_token = mask_secret(Config.BOT_TOKEN)
    masked_hash = mask_secret(Config.API_HASH)
    fast_delay = getattr(Config, 'FAST_DELAY', 1.0)
    vcfg = await db.get_verify_config()
    v_status = "🟢 <b>ᴇɴᴀʙʟᴇᴅ</b>" if vcfg.get('enabled') else "🔴 <b>ᴅɪsᴀʙʟᴇᴅ</b>"
    v_info = f"{vcfg.get('duration', 24)}ʜ ({vcfg.get('steps', 1)} sᴛᴇᴘ)"
    upi_val = getattr(Config, 'UPI_ID', '') or "<i>ɴᴏᴛ sᴇᴛ</i>"
    active_tasks = await db.get_active_tasks()
    blacklist = await db.get_blacklist()
    banned = await db.get_banned()
    
    text = (
        "<blockquote><b>⚙️ <u>sᴋɪɴᴇᴛ ᴠᴇʀsᴇ — sʏsᴛᴇᴍ ᴄᴏɴғɪɢᴜʀᴀᴛɪᴏɴ</u></b></blockquote>\n\n"
        "<i>ᴍᴏᴅɪғʏ ɢʟᴏʙᴀʟ ʙᴏᴛ ᴇɴᴠɪʀᴏɴᴍᴇɴᴛ ᴠᴀʟᴜᴇs ᴅʏɴᴀᴍɪᴄᴀʟʟʏ ғʀᴏᴍ ᴛᴇʟᴇɢʀᴀᴍ. ᴄʜᴀɴɢᴇs ᴘᴇʀsɪsᴛ ɪɴ ᴍᴏɴɢᴏᴅʙ ᴀᴄʀᴏss sᴇʀᴠᴇʀ ʀᴇsᴛᴀʀᴛs!</i>\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👑 <b>ᴀᴜᴛʜᴏʀɪᴢᴇᴅ ᴀᴅᴍɪɴs ({len(all_admins)}):</b> {admins_str}\n"
        f"📡 <b>ʟᴏɢ ᴄʜᴀɴɴᴇʟ ɪᴅ:</b> {log_chan}\n"
        f"📦 <b>ᴅᴜᴍᴘ ᴄʜᴀɴɴᴇʟ ɪᴅ:</b> {dump_chan}\n"
        f"📢 <b>ғᴏʀᴄᴇ sᴜʙ ᴄʜᴀɴɴᴇʟ:</b> {fsub_chan}\n"
        f"🔒 <b>ғᴏʀᴄᴇ sᴜʙ ᴇɴғᴏʀᴄᴇᴅ:</b> {fsub_status}\n"
        f"🛡️ <b>ᴛᴏᴋᴇɴ ᴠᴇʀɪғɪᴄᴀᴛɪᴏɴ:</b> {v_status} (<code>{v_info}</code>)\n"
        f"💳 <b>ᴜᴘɪ ᴘᴀʏᴍᴇɴᴛ ɪᴅ:</b> <code>{upi_val}</code>\n"
        f"📊 <b>ʟɪᴠᴇ ᴛᴀsᴋs ʀᴜɴɴɪɴɢ:</b> <code>{len(active_tasks)}</code>\n"
        f"🛡️ <b>ʙʟᴀᴄᴋʟɪsᴛ ʀᴜʟᴇs:</b> <code>{len(blacklist)}</code>\n"
        f"🚫 <b>ʙᴀɴɴᴇᴅ ᴜsᴇʀs:</b> <code>{len(banned)}</code>\n"
        f"🤖 <b>ʙᴏᴛ ᴛᴏᴋᴇɴ:</b> <code>{masked_token}</code>\n"
        f"🔑 <b>ᴀᴘɪ ɪᴅ / ʜᴀsʜ:</b> <code>{Config.API_ID}</code> / <code>{masked_hash}</code>\n"
        f"⚡️ <b>ᴅᴇғᴀᴜʟᴛ sᴘᴇᴇᴅ ᴅᴇʟᴀʏ:</b> <code>{fast_delay}s</code>\n"
        f"🗄 <b>ᴅᴀᴛᴀʙᴀsᴇ ɴᴀᴍᴇ:</b> <code>{Config.DATABASE_NAME}</code>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "👇 <b>sᴇʟᴇᴄᴛ ᴀɴʏ ᴘᴀʀᴀᴍᴇᴛᴇʀ ʙᴇʟᴏᴡ ᴛᴏ ᴜᴘᴅᴀᴛᴇ ɪᴛs ᴠᴀʟᴜᴇ:</b>"
    )
    return text

def build_config_buttons(vcfg=None) -> InlineKeyboardMarkup:
    fsub_mark = "✅ ᴏɴ" if Config.FORCE_SUB_ON else "❌ ᴏғғ"
    v_enabled = vcfg.get("enabled", True) if vcfg else Config.VERIFY_ENABLED
    v_mark = "✅ ᴏɴ" if v_enabled else "❌ ᴏғғ"
    buttons = [
        [
            InlineKeyboardButton("📡 ʟᴏɢ ᴄʜᴀɴɴᴇʟ", callback_data="config#set_log"),
            InlineKeyboardButton("📦 ᴅᴜᴍᴘ ᴄʜᴀɴɴᴇʟ", callback_data="config#set_dump")
        ],
        [
            InlineKeyboardButton("📢 ғᴏʀᴄᴇ sᴜʙ ᴄʜᴀɴɴᴇʟ", callback_data="config#set_fsub"),
            InlineKeyboardButton(f"🔒 ғ-sᴜʙ: {fsub_mark}", callback_data="config#toggle_fsub")
        ],
        [
            InlineKeyboardButton(f"🛡️ ᴠᴇʀɪғʏ: {v_mark}", callback_data="config#toggle_verify"),
            InlineKeyboardButton("⚙️ ᴠᴇʀɪғʏ sᴇᴛᴛɪɴɢs", callback_data="config#verify_settings")
        ],
        [
            InlineKeyboardButton("📈 ᴜsᴇʀ ᴛʀᴀᴄᴋɪɴɢ", callback_data="utr_overview"),
            InlineKeyboardButton("🛡️ ᴛᴀsᴋ sᴜʀᴠᴇɪʟʟᴀɴᴄᴇ", callback_data="config#tasks")
        ],
        [
            InlineKeyboardButton("🚫 ᴄᴏɴᴛᴇɴᴛ ʙʟᴀᴄᴋʟɪsᴛ", callback_data="config#blacklist"),
            InlineKeyboardButton("🔨 ʙᴀɴɴᴇᴅ ᴜsᴇʀs", callback_data="config#banned")
        ],
        [
            InlineKeyboardButton("👑 ᴍᴀɴᴀɢᴇ ᴀᴅᴍɪɴs", callback_data="config#manage_admins"),
            InlineKeyboardButton("💎 ᴠɪᴘ ᴍᴀɴᴀɢᴇʀ", callback_data="vipadmin_main")
        ],
        [
            InlineKeyboardButton("💳 ᴜᴘɪ ᴘᴀʏᴍᴇɴᴛ ɪᴅ", callback_data="config#set_upi"),
            InlineKeyboardButton("⚡️ sᴘᴇᴇᴅ ᴅᴇʟᴀʏ", callback_data="config#set_speed")
        ],
        [
            InlineKeyboardButton("🤖 ʙᴏᴛ ᴛᴏᴋᴇɴ", callback_data="config#set_token"),
            InlineKeyboardButton("🔑 ᴀᴘɪ ɪᴅ / ʜᴀsʜ", callback_data="config#set_api")
        ],
        [
            InlineKeyboardButton("🔄 ʀᴇsᴛᴀʀᴛ ʙᴏᴛ ɴᴏᴡ", callback_data="config#restart"),
            InlineKeyboardButton("⚙️ ᴏᴘᴇɴ sᴇᴛᴛɪɴɢs", callback_data="settings#main")
        ],
        [
            InlineKeyboardButton("• ʙᴀᴄᴋ", callback_data="back"),
            InlineKeyboardButton("❌ ᴄʟᴏsᴇ", callback_data="close_btn")
        ]
    ]
    return InlineKeyboardMarkup(buttons)


# ================= COMMAND /config & /env =================

@Client.on_message(filters.private & filters.command(["config", "env", "vars"]))
async def config_cmd(bot: Client, message: Message):
    user_id = message.from_user.id
    if not await is_admin(user_id):
        return await message.reply_text(
            "⚠️ <b>ᴀᴄᴄᴇss ᴅᴇɴɪᴇᴅ:</b> ᴛʜɪs ᴄᴏɴғɪɢᴜʀᴀᴛɪᴏɴ ᴅᴀsʜʙᴏᴀʀᴅ ɪs sᴛʀɪᴄᴛʟʏ ʀᴇsᴛʀɪᴄᴛᴇᴅ ᴛᴏ ʙᴏᴛ ᴀᴅᴍɪɴs & ᴏᴡɴᴇʀs.",
            quote=True
        )
    text = await build_config_view()
    vcfg = await db.get_verify_config()
    await message.reply_text(text, reply_markup=build_config_buttons(vcfg), disable_web_page_preview=True, quote=True)


# ================= CALLBACK QUERY ROUTER =================

@Client.on_callback_query(filters.regex(r"^config"))
async def config_callback(bot: Client, query: CallbackQuery):
    user_id = query.from_user.id
    if not await is_admin(user_id):
        return await query.answer("⚠️ ᴀᴄᴄᴇss ᴅᴇɴɪᴇᴅ! ʀᴇsᴛʀɪᴄᴛᴇᴅ ᴛᴏ ʙᴏᴛ ᴀᴅᴍɪɴs & ᴏᴡɴᴇʀs ᴏɴʟʏ.", show_alert=True)

    data = query.data.split("#")[1] if "#" in query.data else "main"

    if data == "main":
        text = await build_config_view()
        vcfg = await db.get_verify_config()
        await safe_edit_message(query.message, text, reply_markup=build_config_buttons(vcfg), disable_web_page_preview=True)

    elif data == "toggle_fsub":
        Config.FORCE_SUB_ON = not Config.FORCE_SUB_ON
        await db.update_system_config("FORCE_SUB_ON", Config.FORCE_SUB_ON)
        await db.log_audit(user_id, 'toggle_fsub', {'force_sub': Config.FORCE_SUB_ON})
        status_txt = "ᴇɴᴀʙʟᴇᴅ" if Config.FORCE_SUB_ON else "ᴅɪsᴀʙʟᴇᴅ"
        await query.answer(f"ғᴏʀᴄᴇ sᴜʙ ɪs ɴᴏᴡ {status_txt}!")
        text = await build_config_view()
        vcfg = await db.get_verify_config()
        await safe_edit_message(query.message, text, reply_markup=build_config_buttons(vcfg), disable_web_page_preview=True)

    elif data == "toggle_verify":
        vcfg = await db.get_verify_config()
        new_val = not vcfg.get("enabled", True)
        await db.update_verify_config("enabled", new_val)
        Config.VERIFY_ENABLED = new_val
        await db.log_audit(user_id, 'toggle_verify', {'enabled': new_val})
        status_txt = "ᴇɴᴀʙʟᴇᴅ" if new_val else "ᴅɪsᴀʙʟᴇᴅ"
        await query.answer(f"ᴛᴏᴋᴇɴ ᴠᴇʀɪғɪᴄᴀᴛɪᴏɴ ɪs ɴᴏᴡ {status_txt}!")
        text = await build_config_view()
        vcfg["enabled"] = new_val
        await safe_edit_message(query.message, text, reply_markup=build_config_buttons(vcfg), disable_web_page_preview=True)

    elif data == "verify_settings":
        await query.answer()
        vcfg = await db.get_verify_config()
        status_txt = "🟢 ᴇɴᴀʙʟᴇᴅ" if vcfg.get("enabled") else "🔴 ᴅɪsᴀʙʟᴇᴅ"
        s1 = f"{vcfg.get('shortener_url', 'ɴᴏɴᴇ')} (ᴀᴘɪ: {'sᴇᴛ' if vcfg.get('shortener_api') else 'ɴᴏɴᴇ'})"
        s2 = f"{vcfg.get('shortener_url2', 'ɴᴏɴᴇ')} (ᴀᴘɪ: {'sᴇᴛ' if vcfg.get('shortener_api2') else 'ɴᴏɴᴇ'})"
        s3 = f"{vcfg.get('shortener_url3', 'ɴᴏɴᴇ')} (ᴀᴘɪ: {'sᴇᴛ' if vcfg.get('shortener_api3') else 'ɴᴏɴᴇ'})"
        txt = (
            "<blockquote><b>🛡️ <u>ᴛᴏᴋᴇɴ ᴠᴇʀɪғɪᴄᴀᴛɪᴏɴ sᴇᴛᴛɪɴɢs</u></b></blockquote>\n\n"
            f"• <b>sᴛᴀᴛᴜs:</b> <code>{status_txt}</code>\n"
            f"• <b>ᴘᴀss ᴅᴜʀᴀᴛɪᴏɴ:</b> <code>{vcfg.get('duration', 24)} ʜᴏᴜʀs</code>\n"
            f"• <b>ᴠᴇʀɪғɪᴄᴀᴛɪᴏɴ sᴛᴇᴘs:</b> <code>{vcfg.get('steps', 1)} sᴛᴇᴘ(s)</code>\n"
            f"• <b>ʟɪɴᴋ ᴛɪᴍᴇᴏᴜᴛ:</b> <code>{vcfg.get('timeout', 30)} ᴍɪɴᴜᴛᴇs</code>\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"<b>sʜᴏʀᴛᴇɴᴇʀ 1:</b> <code>{s1}</code>\n"
            f"<b>sʜᴏʀᴛᴇɴᴇʀ 2:</b> <code>{s2}</code>\n"
            f"<b>sʜᴏʀᴛᴇɴᴇʀ 3:</b> <code>{s3}</code>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "<i>💡 ᴜsᴇ <code>/setverify</code> ɪɴ ᴄʜᴀᴛ ᴛᴏ ᴄʜᴀɴɢᴇ sᴛᴇᴘs, ᴅᴜʀᴀᴛɪᴏɴ, ᴀɴᴅ ᴀᴅᴅ sʜᴏʀᴛᴇɴᴇʀ ᴀᴘɪ ᴋᴇʏs.</i>"
        )
        await safe_edit_message(
            query.message,
            txt,
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("• ʙᴀᴄᴋ", callback_data="config#main"),
                    InlineKeyboardButton("❌ ᴄʟᴏsᴇ", callback_data="close_btn")
                ]
            ]),
            disable_web_page_preview=True
        )

    elif data == "set_log":
        await query.message.delete()
        curr_log = f"<code>{Config.LOG_CHANNEL}</code>" if (Config.LOG_CHANNEL and Config.LOG_CHANNEL != 0) else "<code>0</code> <i>(ᴅɪsᴀʙʟᴇᴅ)</i>"
        try:
            ask = await bot.ask(
                user_id,
                text=(
                    "<blockquote><b>📡 <u>sᴇᴛ ʟᴏɢ ᴄʜᴀɴɴᴇʟ ɪᴅ</u></b></blockquote>\n\n"
                    f"<b>ᴄᴜʀʀᴇɴᴛ ᴠᴀʟᴜᴇ:</b> {curr_log}\n\n"
                    "sᴇɴᴅ ᴛʜᴇ ᴛᴇʟᴇɢʀᴀᴍ ᴄʜᴀɴɴᴇʟ ɪᴅ ᴡʜᴇʀᴇ sʏsᴛᴇᴍ ᴛᴇʟᴇᴍᴇᴛʀʏ ᴀɴᴅ ʀᴇsᴛᴀʀᴛ ᴇᴠᴇɴᴛs ᴡɪʟʟ ʙᴇ ᴅᴜᴍᴘᴇᴅ.\n\n"
                    "• <b>ᴇxᴀᴍᴘʟᴇ:</b> <code>-1001234567890</code>\n"
                    "• <b>ᴅɪsᴀʙʟᴇ:</b> sᴇɴᴅ <code>0</code> ᴛᴏ ᴋᴇᴇᴘ ᴅɪsᴀʙʟᴇᴅ\n"
                    "• <b>ᴄᴀɴᴄᴇʟ:</b> sᴇɴᴅ <code>/cancel</code> ᴛᴏ ᴀʙᴏʀᴛ\n\n"
                    "⚠️ <i>ᴇɴsᴜʀᴇ ᴛʜᴇ ʙᴏᴛ ɪs ᴀᴅᴅᴇᴅ ᴀs ᴀɴ ᴀᴅᴍɪɴɪsᴛʀᴀᴛᴏʀ ɪɴ ᴛʜᴀᴛ ᴄʜᴀɴɴᴇʟ ғɪʀsᴛ!</i>"
                ),
                timeout=120
            )
        except (asyncio.exceptions.TimeoutError, ListenerTimeout):
            text = await build_config_view()
            return await bot.send_message(user_id, text, reply_markup=build_config_buttons(), disable_web_page_preview=True)
        if not ask.text or ask.text.startswith("/cancel"):
            text = await build_config_view()
            return await bot.send_message(user_id, text, reply_markup=build_config_buttons(), disable_web_page_preview=True)

        raw = ask.text.strip()
        if not (raw.lstrip("-").isdigit()):
            return await bot.send_message(
                user_id,
                "<b>❌ ɪɴᴠᴀʟɪᴅ ᴄʜᴀɴɴᴇʟ ɪᴅ! ᴍᴜsᴛ ʙᴇ ɴᴜᴍʙᴇʀs (ᴇ.ɢ. -1001234567890).</b>",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("• ʙᴀᴄᴋ ᴛᴏ ᴄᴏɴғɪɢ", callback_data="config#main")]])
            )

        new_val = int(raw)
        Config.LOG_CHANNEL = new_val
        await db.update_system_config("LOG_CHANNEL", new_val)

        # Test notification dispatch
        if new_val != 0:
            try:
                await bot.send_message(new_val, "📡 <b>ʟᴏɢ ᴄʜᴀɴɴᴇʟ ᴄᴏɴɴᴇᴄᴛᴇᴅ sᴜᴄᴄᴇssғᴜʟʟʏ!</b>\n<i>⚡️ ᴘᴏᴡᴇʀᴇᴅ ʙʏ sᴋɪɴᴇᴛ ᴠᴇʀsᴇ</i>")
            except Exception as e:
                logger.warning(f"Could not dispatch test ping to new log channel {new_val}: {e}")

        disp = f"<code>{new_val}</code>" if new_val != 0 else "<code>0</code> <i>(ᴅɪsᴀʙʟᴇᴅ)</i>"
        await bot.send_message(
            user_id,
            f"✅ <b>ʟᴏɢ ᴄʜᴀɴɴᴇʟ ᴜᴘᴅᴀᴛᴇᴅ ᴛᴏ:</b> {disp}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("• ʙᴀᴄᴋ ᴛᴏ ᴄᴏɴғɪɢ", callback_data="config#main")]])
        )

    elif data == "set_dump":
        await query.message.delete()
        curr_dump = f"<code>{Config.DUMP_CHANNEL}</code>" if (Config.DUMP_CHANNEL and Config.DUMP_CHANNEL != 0) else "<code>0</code> <i>(ᴅɪsᴀʙʟᴇᴅ)</i>"
        try:
            ask = await bot.ask(
                user_id,
                text=(
                    "<blockquote><b>📦 <u>sᴇᴛ ᴅᴜᴍᴘ ᴄʜᴀɴɴᴇʟ ɪᴅ</u></b></blockquote>\n\n"
                    f"<b>ᴄᴜʀʀᴇɴᴛ ᴠᴀʟᴜᴇ:</b> {curr_dump}\n\n"
                    "ғᴏʀᴡᴀʀᴅ ᴀ ᴍᴇssᴀɢᴇ ғʀᴏᴍ ʏᴏᴜʀ ᴅᴜᴍᴘ ᴄʜᴀɴɴᴇʟ, ᴏʀ sᴇɴᴅ ᴄʜᴀɴɴᴇʟ ɪᴅ / ʟɪɴᴋ.\n\n"
                    "• <b>ғᴏʀᴡᴀʀᴅ:</b> <i>ғᴏʀᴡᴀʀᴅ ᴀɴʏ ᴍᴇssᴀɢᴇ ғʀᴏᴍ ᴛʜᴇ ᴄʜᴀɴɴᴇʟ (ʀᴇᴄᴏᴍᴍᴇɴᴅᴇᴅ)</i>\n"
                    "• <b>ɪᴅ:</b> <code>-1001234567890</code>\n"
                    "• <b>ʟɪɴᴋ:</b> <code>https://t.me/c/...</code> ᴏʀ <code>@my_channel</code>\n"
                    "• <b>ᴅɪsᴀʙʟᴇ:</b> sᴇɴᴅ <code>0</code> ᴛᴏ ᴋᴇᴇᴘ ᴅɪsᴀʙʟᴇᴅ\n"
                    "• <b>ᴄᴀɴᴄᴇʟ:</b> sᴇɴᴅ <code>/cancel</code> ᴛᴏ ᴀʙᴏʀᴛ\n\n"
                    "⚠️ <i>ᴇɴsᴜʀᴇ ᴛʜᴇ ʙᴏᴛ ɪs ᴀᴅᴅᴇᴅ ᴀs ᴀɴ ᴀᴅᴍɪɴɪsᴛʀᴀᴛᴏʀ ɪɴ ᴛʜᴀᴛ ᴄʜᴀɴɴᴇʟ ғɪʀsᴛ!</i>"
                ),
                timeout=120
            )
        except (asyncio.exceptions.TimeoutError, ListenerTimeout):
            text = await build_config_view()
            return await bot.send_message(user_id, text, reply_markup=build_config_buttons(), disable_web_page_preview=True)
        if not ask or (ask.text and ask.text.startswith("/cancel")):
            text = await build_config_view()
            return await bot.send_message(user_id, text, reply_markup=build_config_buttons(), disable_web_page_preview=True)

        if ask.text and ask.text.strip() == "0":
            new_val = 0
            Config.DUMP_CHANNEL = new_val
            await db.update_system_config("DUMP_CHANNEL", new_val)
            await db.update_admin_dump(new_val, enabled=False)
            return await bot.send_message(
                user_id,
                "✅ <b>ᴅᴜᴍᴘ ᴄʜᴀɴɴᴇʟ ᴅɪsᴀʙʟᴇᴅ!</b>",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("• ʙᴀᴄᴋ ᴛᴏ ᴄᴏɴғɪɢ", callback_data="config#main")]])
            )

        from plugins.forward_parser import resolve_channel_input
        res = await resolve_channel_input(ask, bot, verify_access=True)
        if not res.get("chat_id"):
            err_msg = res.get("error") or "Could not parse channel from input."
            return await bot.send_message(
                user_id,
                f"❌ <b>ᴇʀʀᴏʀ:</b>\n\n{err_msg}",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("• ʙᴀᴄᴋ ᴛᴏ ᴄᴏɴғɪɢ", callback_data="config#main")]])
            )

        new_val = res["chat_id"]
        c_title = res.get("chat_title") or str(new_val)
        Config.DUMP_CHANNEL = new_val
        await db.update_system_config("DUMP_CHANNEL", new_val)
        await db.update_admin_dump(new_val, enabled=True)

        await bot.send_message(
            user_id,
            f"<blockquote><b>✅ <u>ɢʟᴏʙᴀʟ ᴅᴜᴍᴘ ᴄʜᴀɴɴᴇʟ ᴜᴘᴅᴀᴛᴇᴅ</u></b></blockquote>\n\n"
            f"📢 <b>ᴄʜᴀɴɴᴇʟ:</b> <code>{c_title}</code>\n"
            f"🆔 <b>ɪᴅ:</b> <code>{new_val}</code>\n"
            f"📦 <b>sᴛᴀᴛᴜs:</b> <code>✅ ᴏɴ (ᴀᴄᴛɪᴠᴇ)</code>",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("• ʙᴀᴄᴋ ᴛᴏ ᴄᴏɴғɪɢ", callback_data="config#main")]])
        )

    elif data == "set_fsub":
        await query.message.delete()
        try:
            ask = await bot.ask(
                user_id,
                text=(
                    "<b>📢 sᴇɴᴅ ɴᴇᴡ ғᴏʀᴄᴇ sᴜʙ ᴄʜᴀɴɴᴇʟ:</b>\n\n"
                    "ᴇxᴀᴍᴘʟᴇs:\n"
                    "• <code>@MyChannel</code>\n"
                    "• <code>https://t.me/MyChannel</code>\n"
                    "• <code>-1001234567890</code>\n"
                    "sᴇɴᴅ <code>none</code> ᴛᴏ ᴄʟᴇᴀʀ\n"
                    "<i>/cancel - ᴀʙᴏʀᴛ</i>"
                ),
                timeout=120
            )
        except (asyncio.exceptions.TimeoutError, ListenerTimeout):
            text = await build_config_view()
            return await bot.send_message(user_id, text, reply_markup=build_config_buttons(), disable_web_page_preview=True)
        if not ask.text or ask.text.startswith("/cancel"):
            text = await build_config_view()
            return await bot.send_message(user_id, text, reply_markup=build_config_buttons(), disable_web_page_preview=True)

        raw = ask.text.strip()
        val = "" if raw.lower() in ("none", "0", "off") else raw
        Config.FORCE_SUB_CHANNEL = val
        await db.update_system_config("FORCE_SUB_CHANNEL", val)

        await bot.send_message(
            user_id,
            f"✅ <b>ғᴏʀᴄᴇ sᴜʙ ᴄʜᴀɴɴᴇʟ sᴇᴛ ᴛᴏ:</b> <code>{val or 'ɴᴏɴᴇ'}</code>",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("• ʙᴀᴄᴋ ᴛᴏ ᴄᴏɴғɪɢ", callback_data="config#main")]])
        )

    elif data == "manage_admins":
        admins = await db.get_all_admins()
        primary_owner = Config.BOT_OWNER_ID[0] if Config.BOT_OWNER_ID else None
        admin_lines = []
        for a in admins:
            name, uname = await get_admin_display_name(bot, a)
            uname_str = f" (@{uname})" if uname else ""
            tag = " 👑 <b>ᴘʀɪᴍᴀʀʏ ᴏᴡɴᴇʀ</b>" if a == primary_owner else " 🛡️ <b>ᴀᴅᴍɪɴ</b>"
            admin_lines.append(f"• <b>{html.escape(name)}</b>{uname_str}\n  └ 🆔 <code>{a}</code> | {tag}")
        admins_body = "\n\n".join(admin_lines) if admin_lines else "<i>ɴᴏɴᴇ</i>"

        text = (
            "<blockquote><b>👑 <u>sᴋɪɴᴇᴛ ᴠᴇʀsᴇ — ᴍᴜʟᴛɪ-ᴀᴅᴍɪɴ ᴍᴀɴᴀɢᴇᴍᴇɴᴛ</u></b></blockquote>\n\n"
            f"<b>ᴛᴏᴛᴀʟ ᴀᴜᴛʜᴏʀɪᴢᴇᴅ ᴀᴅᴍɪɴs:</b> <code>{len(admins)}</code>\n\n"
            f"{admins_body}\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "<i>ᴀᴜᴛʜᴏʀɪᴢᴇᴅ ᴀᴅᴍɪɴɪsᴛʀᴀᴛᴏʀs ʜᴀᴠᴇ ғᴜʟʟ ᴀᴄᴄᴇss ᴛᴏ sʏsᴛᴇᴍ ᴄᴏɴғɪɢᴜʀᴀᴛɪᴏɴ, ᴘʀᴇᴍɪᴜᴍ ᴠɪᴘ ᴀᴘᴘʀᴏᴠᴀʟs, sʜᴏʀᴛᴇɴᴇʀ ᴍᴀɴᴀɢᴇᴍᴇɴᴛ, ᴀɴᴅ ʟɪᴠᴇ ʟᴏɢs.</i>\n\n"
            "👇 <b>sᴇʟᴇᴄᴛ ᴀɴ ᴀᴄᴛɪᴏɴ ʙᴇʟᴏᴡ:</b>"
        )
        btn_list = [
            [
                InlineKeyboardButton("➕ ᴀᴅᴅ ᴀᴅᴍɪɴ", callback_data="config#add_admin_prompt"),
                InlineKeyboardButton("➖ ʀᴇᴍᴏᴠᴇ ᴀᴅᴍɪɴ", callback_data="config#del_admin_prompt")
            ]
        ]
        if primary_owner and user_id == primary_owner:
            btn_list.append([InlineKeyboardButton("➕ ᴀᴅᴅ ᴀᴅᴍɪɴ (ʙᴀᴛᴄʜ)", callback_data="config#set_admins")])
        
        btn_list.append([
            InlineKeyboardButton("• ʙᴀᴄᴋ ᴛᴏ ᴄᴏɴғɪɢ", callback_data="config#main"),
            InlineKeyboardButton("❌ ᴄʟᴏsᴇ", callback_data="close_btn")
        ])
        btns = InlineKeyboardMarkup(btn_list)
        await safe_edit_message(query.message, text, reply_markup=btns)

    elif data == "add_admin_prompt":
        await query.message.delete()
        try:
            ask = await bot.ask(
                user_id,
                text=(
                    "<b>👑 sᴇɴᴅ ᴛʜᴇ ᴛᴇʟᴇɢʀᴀᴍ ᴜsᴇʀ ɪᴅ ᴛᴏ ᴘʀᴏᴍᴏᴛᴇ ᴀs ᴀᴅᴍɪɴ:</b>\n\n"
                    "ᴇxᴀᴍᴘʟᴇ: <code>987654321</code>\n"
                    "<i>ᴜsᴇʀ ɪᴅ ᴄᴀɴ ʙᴇ ғᴏᴜɴᴅ ᴠɪᴀ @userinfobot ᴏʀ /status.</i>\n\n"
                    "<i>/cancel - ᴀʙᴏʀᴛ</i>"
                ),
                timeout=120
            )
        except (asyncio.exceptions.TimeoutError, ListenerTimeout):
            text = await build_config_view()
            return await bot.send_message(user_id, text, reply_markup=build_config_buttons(), disable_web_page_preview=True)
        if not ask.text or ask.text.startswith("/cancel"):
            text = await build_config_view()
            return await bot.send_message(user_id, text, reply_markup=build_config_buttons(), disable_web_page_preview=True)

        val = ask.text.strip()
        if not val.isdigit():
            return await bot.send_message(
                user_id,
                "<b>❌ ɪɴᴠᴀʟɪᴅ ɪᴅ! ᴜsᴇʀ ɪᴅ ᴍᴜsᴛ ʙᴇ ɴᴜᴍʙᴇʀs ᴏɴʟʏ.</b>",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("• ʙᴀᴄᴋ", callback_data="config#manage_admins")]])
            )
        new_admin = int(val)
        await db.add_admin(new_admin)
        await db.log_audit(user_id, 'add_admin', {'admin_id': new_admin})
        await bot.send_message(
            user_id,
            f"✅ <b>sᴜᴄᴄᴇssғᴜʟʟʏ ᴀᴅᴅᴇᴅ ᴜsᴇʀ <code>{new_admin}</code> ᴛᴏ ᴀᴜᴛʜᴏʀɪᴢᴇᴅ ᴀᴅᴍɪɴɪsᴛʀᴀᴛᴏʀs!</b>",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("• ʙᴀᴄᴋ ᴛᴏ ᴀᴅᴍɪɴs", callback_data="config#manage_admins")]])
        )

    elif data == "del_admin_prompt":
        await query.message.delete()
        admins = await db.get_all_admins()
        primary_owner = Config.BOT_OWNER_ID[0] if Config.BOT_OWNER_ID else None
        try:
            ask = await bot.ask(
                user_id,
                text=(
                    f"👑 <b>ᴄᴜʀʀᴇɴᴛ ᴀᴅᴍɪɴs:</b> <code>{' '.join(str(x) for x in admins)}</code>\n\n"
                    "<b>sᴇɴᴅ ᴛʜᴇ ᴛᴇʟᴇɢʀᴀᴍ ᴜsᴇʀ ɪᴅ ᴛᴏ ʀᴇᴍᴏᴠᴇ ғʀᴏᴍ ᴀᴅᴍɪɴs:</b>\n"
                    "<i>ɴᴏᴛᴇ: ᴘʀɪᴍᴀʀʏ ᴏᴡɴᴇʀ ᴄᴀɴɴᴏᴛ ʙᴇ ʀᴇᴍᴏᴠᴇᴅ.</i>\n\n"
                    "<i>/cancel - ᴀʙᴏʀᴛ</i>"
                ),
                timeout=120
            )
        except (asyncio.exceptions.TimeoutError, ListenerTimeout):
            text = await build_config_view()
            return await bot.send_message(user_id, text, reply_markup=build_config_buttons(), disable_web_page_preview=True)
        if not ask.text or ask.text.startswith("/cancel"):
            text = await build_config_view()
            return await bot.send_message(user_id, text, reply_markup=build_config_buttons(), disable_web_page_preview=True)

        val = ask.text.strip()
        if not val.isdigit():
            return await bot.send_message(
                user_id,
                "<b>❌ ɪɴᴠᴀʟɪᴅ ɪᴅ! ᴍᴜsᴛ ʙᴇ ᴅɪɢɪᴛs ᴏɴʟʏ.</b>",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("• ʙᴀᴄᴋ", callback_data="config#manage_admins")]])
            )
        del_admin = int(val)
        if primary_owner and del_admin == primary_owner:
            return await bot.send_message(
                user_id,
                "<b>⚠️ ᴘʀɪᴍᴀʀʏ ʙᴏᴛ ᴏᴡɴᴇʀ ᴄᴀɴɴᴏᴛ ʙᴇ ʀᴇᴍᴏᴠᴇᴅ!</b>",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("• ʙᴀᴄᴋ", callback_data="config#manage_admins")]])
            )
        await db.remove_admin(del_admin)
        await db.log_audit(user_id, 'remove_admin', {'admin_id': del_admin})
        await bot.send_message(
            user_id,
            f"✅ <b>sᴜᴄᴄᴇssғᴜʟʟʏ ʀᴇᴍᴏᴠᴇᴅ <code>{del_admin}</code> ғʀᴏᴍ ᴀᴅᴍɪɴɪsᴛʀᴀᴛᴏʀs!</b>",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("• ʙᴀᴄᴋ ᴛᴏ ᴀᴅᴍɪɴs", callback_data="config#manage_admins")]])
        )

    elif data == "set_upi":
        await query.message.delete()
        curr_upi = getattr(Config, 'UPI_ID', '') or 'ɴᴏɴᴇ'
        try:
            ask = await bot.ask(
                user_id,
                text=(
                    f"💳 <b>ᴄᴜʀʀᴇɴᴛ ᴜᴘɪ ɪᴅ:</b> <code>{curr_upi}</code>\n\n"
                    "<b>sᴇɴᴅ ɴᴇᴡ ᴜᴘɪ ɪᴅ ғᴏʀ ʀᴇᴄᴇɪᴠɪɴɢ ᴘʀᴇᴍɪᴜᴍ ᴘᴀʏᴍᴇɴᴛs:</b>\n"
                    "ᴇxᴀᴍᴘʟᴇ: <code>yourname@upi</code> ᴏʀ <code>merchant@okhdfcbank</code>\n"
                    "sᴇɴᴅ <code>none</code> ᴛᴏ ʀᴇᴍᴏᴠᴇ.\n\n"
                    "<i>/cancel - ᴀʙᴏʀᴛ</i>"
                ),
                timeout=120
            )
        except (asyncio.exceptions.TimeoutError, ListenerTimeout):
            text = await build_config_view()
            return await bot.send_message(user_id, text, reply_markup=build_config_buttons(), disable_web_page_preview=True)
        if not ask.text or ask.text.startswith("/cancel"):
            text = await build_config_view()
            return await bot.send_message(user_id, text, reply_markup=build_config_buttons(), disable_web_page_preview=True)

        new_upi = ask.text.strip()
        if new_upi.lower() in ("none", "0", "off"):
            new_upi = ""
        Config.UPI_ID = new_upi
        await db.update_system_config("UPI_ID", new_upi)
        await bot.send_message(
            user_id,
            f"✅ <b>ᴜᴘɪ ᴘᴀʏᴍᴇɴᴛ ɪᴅ ᴜᴘᴅᴀᴛᴇᴅ ᴛᴏ:</b> <code>{new_upi or 'ɴᴏɴᴇ'}</code>",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("• ʙᴀᴄᴋ ᴛᴏ ᴄᴏɴғɪɢ", callback_data="config#main")]])
        )

    elif data == "set_admins":
        await query.message.delete()
        admins = await db.get_all_admins()
        curr = " ".join([str(x) for x in admins])
        try:
            ask = await bot.ask(
                user_id,
                text=(
                    f"👑 <b>ᴄᴜʀʀᴇɴᴛ ᴀᴅᴍɪɴ ɪᴅs:</b> <code>{curr}</code>\n\n"
                    "<b>sᴇɴᴅ sᴘᴀᴄᴇ-sᴇᴘᴀʀᴀᴛᴇᴅ ᴛᴇʟᴇɢʀᴀᴍ ᴜsᴇʀ ɪᴅs ᴛᴏ sᴇᴛ ᴀs ᴀᴜᴛʜᴏʀɪᴢᴇᴅ ᴀᴅᴍɪɴs:</b>\n"
                    "ᴇxᴀᴍᴘʟᴇ: <code>8349955493 987654321</code>\n\n"
                    "<i>ɴᴏᴛᴇ: ʏᴏᴜʀ ɪᴅ ᴡɪʟʟ ᴀʟᴡᴀʏs ʙᴇ ᴘʀᴇsᴇʀᴠᴇᴅ sᴏ ʏᴏᴜ ᴄᴀɴɴᴏᴛ ʟᴏᴄᴋ ʏᴏᴜʀsᴇʟғ ᴏᴜᴛ.</i>\n"
                    "<i>/cancel - ᴀʙᴏʀᴛ</i>"
                ),
                timeout=120
            )
        except (asyncio.exceptions.TimeoutError, ListenerTimeout):
            text = await build_config_view()
            return await bot.send_message(user_id, text, reply_markup=build_config_buttons(), disable_web_page_preview=True)
        if not ask.text or ask.text.startswith("/cancel"):
            text = await build_config_view()
            return await bot.send_message(user_id, text, reply_markup=build_config_buttons(), disable_web_page_preview=True)

        raw_ids = ask.text.strip().replace(",", " ").split()
        parsed = [int(x) for x in raw_ids if x.lstrip("-").isdigit()]
        if user_id not in parsed:
            parsed.append(user_id)
        
        for aid in parsed:
            await db.add_admin(aid)

        await bot.send_message(
            user_id,
            f"✅ <b>ᴀᴅᴍɪɴ ʟɪsᴛ ᴜᴘᴅᴀᴛᴇᴅ ᴛᴏ:</b> <code>{parsed}</code>",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("• ʙᴀᴄᴋ ᴛᴏ ᴄᴏɴғɪɢ", callback_data="config#main")]])
        )

    elif data == "set_speed":
        await query.message.delete()
        try:
            ask = await bot.ask(
                user_id,
                text=(
                    "<b>⚡️ sᴇɴᴅ ɴᴇᴡ ᴅᴇғᴀᴜʟᴛ ғᴏʀᴡᴀʀᴅ ᴅᴇʟᴀʏ (ɪɴ sᴇᴄᴏɴᴅs):</b>\n\n"
                    "ᴘʀᴇsᴇᴛs:\n"
                    "• <code>0.2</code> ᴏʀ <code>0.5</code> (ᴇxᴛʀᴇᴍᴇ ғᴀsᴛ)\n"
                    "• <code>1.0</code> (ғᴀsᴛ ᴅᴇғᴀᴜʟᴛ)\n"
                    "• <code>3.0</code> (ɴᴏʀᴍᴀʟ sᴀғᴇ)\n"
                    "• <code>5.0</code> (ᴀɴᴛɪ-ғʟᴏᴏᴅ sᴛʀɪᴄᴛ)\n\n"
                    "<i>/cancel - ᴀʙᴏʀᴛ</i>"
                ),
                timeout=120
            )
        except (asyncio.exceptions.TimeoutError, ListenerTimeout):
            text = await build_config_view()
            return await bot.send_message(user_id, text, reply_markup=build_config_buttons(), disable_web_page_preview=True)
        if not ask.text or ask.text.startswith("/cancel"):
            text = await build_config_view()
            return await bot.send_message(user_id, text, reply_markup=build_config_buttons(), disable_web_page_preview=True)

        try:
            val = float(ask.text.strip())
            if val < 0.1 or val > 60.0:
                raise ValueError()
        except ValueError:
            return await bot.send_message(
                user_id,
                "<b>❌ ɪɴᴠᴀʟɪᴅ ᴅᴇʟᴀʏ! ᴇɴᴛᴇʀ ᴀ ᴅᴇᴄɪᴍᴀʟ ɴᴜᴍʙᴇʀ ʙᴇᴛᴡᴇᴇɴ 0.1 ᴀɴᴅ 60.0</b>",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("• ʙᴀᴄᴋ ᴛᴏ ᴄᴏɴғɪɢ", callback_data="config#main")]])
            )

        Config.FAST_DELAY = val
        await db.log_audit(user_id, 'set_fast_delay', {'delay': val})
        await db.update_system_config("FAST_DELAY", val)

        await bot.send_message(
            user_id,
            f"✅ <b>ᴅᴇғᴀᴜʟᴛ ᴅᴇʟᴀʏ sᴇᴛ ᴛᴏ:</b> <code>{val}s</code>",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("• ʙᴀᴄᴋ ᴛᴏ ᴄᴏɴғɪɢ", callback_data="config#main")]])
        )

    elif data == "set_token":
        await query.message.delete()
        try:
            ask = await bot.ask(
                user_id,
                text=(
                    "<b>🤖 sᴇɴᴅ ɴᴇᴡ ᴛᴇʟᴇɢʀᴀᴍ ʙᴏᴛ ᴛᴏᴋᴇɴ:</b>\n\n"
                    "ғᴏʀᴍᴀᴛ: <code>1234567890:AAHxxxx...</code>\n\n"
                    "⚠️ <b>ɪᴍᴘᴏʀᴛᴀɴᴛ:</b> <i>ᴀғᴛᴇʀ sᴀᴠɪɴɢ ᴀ ɴᴇᴡ ʙᴏᴛ ᴛᴏᴋᴇɴ, ʏᴏᴜ ᴍᴜsᴛ ʀᴇsᴛᴀʀᴛ ᴛʜᴇ ʙᴏᴛ ғᴏʀ ᴛʜᴇ ᴄʜᴀɴɢᴇ ᴛᴏ ᴛᴀᴋᴇ ᴇғғᴇᴄᴛ!</i>\n"
                    "<i>/cancel - ᴀʙᴏʀᴛ</i>"
                ),
                timeout=180
            )
        except (asyncio.exceptions.TimeoutError, ListenerTimeout):
            text = await build_config_view()
            return await bot.send_message(user_id, text, reply_markup=build_config_buttons(), disable_web_page_preview=True)
        if not ask.text or ask.text.startswith("/cancel"):
            text = await build_config_view()
            return await bot.send_message(user_id, text, reply_markup=build_config_buttons(), disable_web_page_preview=True)

        token = ask.text.strip()
        if not (":" in token and token.split(":", 1)[0].isdigit()):
            return await bot.send_message(
                user_id,
                "<b>❌ ɪɴᴠᴀʟɪᴅ ʙᴏᴛ ᴛᴏᴋᴇɴ ғᴏʀᴍᴀᴛ! ᴍᴜsᴛ ʙᴇ numeric_id:string ғʀᴏᴍ @BotFather.</b>",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("• ʙᴀᴄᴋ ᴛᴏ ᴄᴏɴғɪɢ", callback_data="config#main")]])
            )

        Config.BOT_TOKEN = token
        await db.update_system_config("BOT_TOKEN", token)

        await bot.send_message(
            user_id,
            f"✅ <b>ʙᴏᴛ ᴛᴏᴋᴇɴ sᴀᴠᴇᴅ ᴛᴏ ᴅᴀᴛᴀʙᴀsᴇ!</b>\n\nᴛᴏᴋᴇɴ: <code>{mask_secret(token)}</code>\n\nᴄʟɪᴄᴋ ʙᴇʟᴏᴡ ᴛᴏ ʀᴇsᴛᴀʀᴛ ᴛʜᴇ ʙᴏᴛ ᴄʟɪᴇɴᴛ ᴡɪᴛʜ ᴛʜɪs ɴᴇᴡ ᴛᴏᴋᴇɴ:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 ʀᴇsᴛᴀʀᴛ ʙᴏᴛ ɴᴏᴡ", callback_data="config#restart")],
                [InlineKeyboardButton("• ʙᴀᴄᴋ ᴛᴏ ᴄᴏɴғɪɢ", callback_data="config#main")]
            ])
        )

    elif data == "set_api":
        await query.message.delete()
        try:
            ask_id = await bot.ask(
                user_id,
                text="<b>🔑 sᴇɴᴅ ʏᴏᴜʀ ᴛᴇʟᴇɢʀᴀᴍ ᴀᴘɪ ɪᴅ (ɴᴜᴍʙᴇʀs):</b>\n\n<i>/cancel - ᴀʙᴏʀᴛ</i>",
                timeout=120
            )
        except (asyncio.exceptions.TimeoutError, ListenerTimeout):
            text = await build_config_view()
            return await bot.send_message(user_id, text, reply_markup=build_config_buttons(), disable_web_page_preview=True)
        if not ask_id.text or ask_id.text.startswith("/cancel"):
            text = await build_config_view()
            return await bot.send_message(user_id, text, reply_markup=build_config_buttons(), disable_web_page_preview=True)

        if not ask_id.text.strip().isdigit():
            return await bot.send_message(user_id, "<b>❌ ᴀᴘɪ ɪᴅ ᴍᴜsᴛ ʙᴇ ᴅɪɢɪᴛs ᴏɴʟʏ!</b>", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("• ʙᴀᴄᴋ", callback_data="config#main")]]))
        
        api_id = int(ask_id.text.strip())

        try:
            ask_hash = await bot.ask(
                user_id,
                text="<b>🔑 sᴇɴᴅ ʏᴏᴜʀ ᴛᴇʟᴇɢʀᴀᴍ ᴀᴘɪ ʜᴀsʜ (ʜᴇx sᴛʀɪɴɢ):</b>\n\n<i>/cancel - ᴀʙᴏʀᴛ</i>",
                timeout=120
            )
        except (asyncio.exceptions.TimeoutError, ListenerTimeout):
            text = await build_config_view()
            return await bot.send_message(user_id, text, reply_markup=build_config_buttons(), disable_web_page_preview=True)
        if not ask_hash.text or ask_hash.text.startswith("/cancel"):
            text = await build_config_view()
            return await bot.send_message(user_id, text, reply_markup=build_config_buttons(), disable_web_page_preview=True)

        api_hash = ask_hash.text.strip()
        Config.API_ID = api_id
        Config.API_HASH = api_hash
        await db.update_system_config("API_ID", api_id)
        await db.update_system_config("API_HASH", api_hash)

        await bot.send_message(
            user_id,
            f"✅ <b>ᴀᴘɪ ᴄʀᴇᴅᴇɴᴛɪᴀʟs ᴜᴘᴅᴀᴛᴇᴅ!</b>\nᴀᴘɪ ɪᴅ: <code>{api_id}</code>\nᴀᴘɪ ʜᴀsʜ: <code>{mask_secret(api_hash)}</code>",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("• ʙᴀᴄᴋ ᴛᴏ ᴄᴏɴғɪɢ", callback_data="config#main")]])
        )

    elif data == "tasks":
        tasks = await db.get_active_tasks()
        if not tasks:
            await query.answer("No active tasks found.")
            return await query.message.edit_text(
                "<blockquote><b>🛡️ <u>ᴛᴀsᴋ sᴜʀᴠᴇɪʟʟᴀɴᴄᴇ ᴄᴇɴᴛᴇʀ</u></b></blockquote>\n\n"
                "✨ <b>ɴᴏ ᴀᴄᴛɪᴠᴇ ғᴏʀᴡᴀʀᴅ ᴛᴀsᴋs ʀᴜɴɴɪɴɢ ᴄᴜʀʀᴇɴᴛʟʏ.</b>\n"
                "<i>ᴀʟʟ ᴡᴏʀᴋᴇʀs ᴀʀᴇ ɪᴅʟᴇ ᴀɴᴅ sʏsᴛᴇᴍ ɪs ᴄʟᴇᴀɴ.</i>",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔄 ʀᴇғʀᴇsʜ", callback_data="config#tasks")],
                    [InlineKeyboardButton("• ʙᴀᴄᴋ ᴛᴏ ᴄᴏɴғɪɢ", callback_data="config#main")]
                ])
            )
        text = (
            f"<blockquote><b>🛡️ <u>ᴀᴄᴛɪᴠᴇ ғᴏʀᴡᴀʀᴅ ᴛᴀsᴋs ({len(tasks)})</u></b></blockquote>\n"
            f"<i>ᴍᴏɴɪᴛᴏʀɪɴɢ ᴀʟʟ ʟɪᴠᴇ ᴜsᴇʀ ᴊᴏʙs:</i>\n\n"
        )
        rows = []
        for idx, t in enumerate(tasks[:8], start=1):
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
                f"📊 <b>ᴘʀᴏɢʀᴇss:</b> <code>{fetched}/{tot}</code> (🚫: {flt})\n"
                "────────────────────────────\n"
            )
            rows.append([
                InlineKeyboardButton(f"🛑 sᴛᴏᴘ #{idx}", callback_data=f"mod_stop_{tid}"),
                InlineKeyboardButton(f"🚫 ʙᴀɴ ᴜsᴇʀ", callback_data=f"mod_ban_{uid}")
            ])
        rows.append([
            InlineKeyboardButton("🔄 ʀᴇғʀᴇsʜ", callback_data="config#tasks"),
            InlineKeyboardButton("• ʙᴀᴄᴋ ᴛᴏ ᴄᴏɴғɪɢ", callback_data="config#main"),
            InlineKeyboardButton("❌ ᴄʟᴏsᴇ", callback_data="close_btn")
        ])
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(rows), disable_web_page_preview=True)

    elif data == "blacklist":
        bl = await db.get_blacklist()
        if not bl:
            text = (
                "<blockquote><b>🛡️ <u>ᴄᴏɴᴛᴇɴᴛ ᴍᴏᴅᴇʀᴀᴛɪᴏɴ ʙʟᴀᴄᴋʟɪsᴛ</u></b></blockquote>\n\n"
                "✨ <b>ᴛʜᴇ ʙʟᴀᴄᴋʟɪsᴛ ɪs ᴄᴜʀʀᴇɴᴛʟʏ ᴇᴍᴘᴛʏ.</b>\n\n"
                "👉 <b>ᴜsᴇ:</b> <code>/addblacklist &lt;pattern&gt;</code> ᴛᴏ ʙʟᴏᴄᴋ ɪʟʟᴇɢᴀʟ/ɴsғᴡ ᴄᴏɴᴛᴇɴᴛ."
            )
        else:
            text = f"<blockquote><b>🛡️ <u>ᴄᴏɴᴛᴇɴᴛ ᴍᴏᴅᴇʀᴀᴛɪᴏɴ ʙʟᴀᴄᴋʟɪsᴛ ({len(bl)})</u></b></blockquote>\n\n"
            for b in bl[:12]:
                text += f"• <code>{b.get('pattern')}</code> (<i>{b.get('type', 'keyword')}</i>)\n"
            text += "\n👉 <i>ᴜsᴇ <code>/addblacklist</code> ᴏʀ <code>/delblacklist</code> ᴛᴏ ᴍᴀɴᴀɢᴇ.</i>"

        await query.message.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("• ʙᴀᴄᴋ ᴛᴏ ᴄᴏɴғɪɢ", callback_data="config#main"),
                    InlineKeyboardButton("❌ ᴄʟᴏsᴇ", callback_data="close_btn")
                ]
            ])
        )

    elif data == "banned":
        banned_docs = await db.get_banned_details()
        if not banned_docs:
            text = (
                "<blockquote><b>🚫 <u>ʙᴀɴɴᴇᴅ ᴜsᴇʀs</u></b></blockquote>\n\n"
                "✨ <b>ɴᴏ ᴜsᴇʀs ᴀʀᴇ ᴄᴜʀʀᴇɴᴛʟʏ ʙᴀɴɴᴇᴅ.</b>"
            )
            rows = [[
                InlineKeyboardButton("• ʙᴀᴄᴋ ᴛᴏ ᴄᴏɴғɪɢ", callback_data="config#main"),
                InlineKeyboardButton("❌ ᴄʟᴏsᴇ", callback_data="close_btn")
            ]]
        else:
            text = f"<blockquote><b>🚫 <u>ʙᴀɴɴᴇᴅ ᴜsᴇʀs ({len(banned_docs)})</u></b></blockquote>\n\n"
            rows = []
            for b in banned_docs[:10]:
                uid = b.get("id")
                reason = b.get("ban_status", {}).get("ban_reason", "No reason")
                text += f"• <code>{uid}</code>: <i>{reason}</i>\n"
                rows.append([InlineKeyboardButton(f"🔓 ᴜɴʙᴀɴ {uid}", callback_data=f"mod_unban_{uid}")])
            rows.append([
                InlineKeyboardButton("• ʙᴀᴄᴋ ᴛᴏ ᴄᴏɴғɪɢ", callback_data="config#main"),
                InlineKeyboardButton("❌ ᴄʟᴏsᴇ", callback_data="close_btn")
            ])

        await query.message.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup(rows)
        )

    elif data == "restart":
        msg = await query.message.edit_text(
            "<blockquote><b>🔄 ʀᴇsᴛᴀʀᴛɪɴɢ sᴋɪɴᴇᴛ ᴠᴇʀsᴇ ʙᴏᴛ ᴇɴɢɪɴᴇ...</b>\n\n<i>ᴀʟʟ sᴇʀᴠɪᴄᴇs ᴡɪʟʟ ʀᴇʟᴏᴀᴅ ᴡɪᴛʜ ʟᴀᴛᴇsᴛ ᴅᴀᴛᴀʙᴀsᴇ ᴄᴏɴғɪɢs ɪɴ 5 sᴇᴄᴏɴᴅs.</i></blockquote>"
        )
        try:
            await db.set_restart_status(query.message.chat.id, msg.id)
        except Exception:
            pass
        try:
            import json
            with open('.restart_status.json', 'w') as f:
                json.dump({'chat_id': query.message.chat.id, 'message_id': msg.id}, f)
        except Exception:
            pass
        await asyncio.sleep(2)
        os.execl(sys.executable, sys.executable, *sys.argv)


# ================= MULTI-ADMIN COMMANDS =================

@Client.on_message(filters.private & filters.command(["addadmin"]))
async def cmd_add_admin(bot: Client, message: Message):
    if not await db.is_admin(message.from_user.id):
        return await message.reply_text("⚠️ <b>ᴀᴄᴄᴇss ᴅᴇɴɪᴇᴅ:</b> ʀᴇsᴛʀɪᴄᴛᴇᴅ ᴛᴏ ʙᴏᴛ ᴀᴅᴍɪɴs & ᴏᴡɴᴇʀs.", quote=True)
    args = message.command[1:]
    if not args or not args[0].isdigit():
        return await message.reply_text("<b>ᴜsᴀɢᴇ:</b> <code>/addadmin &lt;user_id&gt;</code>\n\nᴇxᴀᴍᴘʟᴇ: <code>/addadmin 987654321</code>", quote=True)
    new_uid = int(args[0])
    await db.add_admin(new_uid)
    await message.reply_text(f"✅ ᴜsᴇʀ <code>{new_uid}</code> ʜᴀs ʙᴇᴇɴ ɢʀᴀɴᴛᴇᴅ ᴀᴅᴍɪɴɪsᴛʀᴀᴛᴏʀ ᴘʀɪᴠɪʟᴇɢᴇs.", quote=True)


@Client.on_message(filters.private & filters.command(["deladmin"]))
async def cmd_del_admin(bot: Client, message: Message):
    if not await db.is_admin(message.from_user.id):
        return await message.reply_text("⚠️ <b>ᴀᴄᴄᴇss ᴅᴇɴɪᴇᴅ:</b> ʀᴇsᴛʀɪᴄᴛᴇᴅ ᴛᴏ ʙᴏᴛ ᴀᴅᴍɪɴs & ᴏᴡɴᴇʀs.", quote=True)
    args = message.command[1:]
    if not args or not args[0].isdigit():
        return await message.reply_text("<b>ᴜsᴀɢᴇ:</b> <code>/deladmin &lt;user_id&gt;</code>\n\nᴇxᴀᴍᴘʟᴇ: <code>/deladmin 987654321</code>", quote=True)
    del_uid = int(args[0])
    primary_owner = Config.BOT_OWNER_ID[0] if Config.BOT_OWNER_ID else None
    if primary_owner and del_uid == primary_owner:
        return await message.reply_text("⚠️ <b>ᴄᴀɴɴᴏᴛ ʀᴇᴍᴏᴠᴇ ᴘʀɪᴍᴀʀʏ ʙᴏᴛ ᴏᴡɴᴇʀ.</b>", quote=True)
    await db.remove_admin(del_uid)
    await message.reply_text(f"✅ ᴜsᴇʀ <code>{del_uid}</code> ʀᴇᴍᴏᴠᴇᴅ ғʀᴏᴍ ᴀᴅᴍɪɴɪsᴛʀᴀᴛᴏʀ ᴘʀɪᴠɪʟᴇɢᴇs.", quote=True)


@Client.on_message(filters.private & filters.command(["admins"]))
async def cmd_admins(bot: Client, message: Message):
    if not await db.is_admin(message.from_user.id):
        return await message.reply_text("⚠️ <b>ᴀᴄᴄᴇss ᴅᴇɴɪᴇᴅ:</b> ʀᴇsᴛʀɪᴄᴛᴇᴅ ᴛᴏ ʙᴏᴛ ᴀᴅᴍɪɴs & ᴏᴡɴᴇʀs.", quote=True)
    admins = await db.get_all_admins()
    primary = Config.BOT_OWNER_ID[0] if Config.BOT_OWNER_ID else None
    lines = []
    for a in admins:
        name, uname = await get_admin_display_name(bot, a)
        uname_str = f" (@{uname})" if uname else ""
        tag = " 👑 <b>ᴘʀɪᴍᴀʀʏ ᴏᴡɴᴇʀ</b>" if a == primary else " 🛡️ <b>ᴀᴜᴛʜᴏʀɪᴢᴇᴅ ᴀᴅᴍɪɴ</b>"
        lines.append(f"• <b>{html.escape(name)}</b>{uname_str}\n  └ 🆔 <code>{a}</code> | {tag}")
    admin_text = (
        "<blockquote><b>👑 <u>sᴋɪɴᴇᴛ ᴠᴇʀsᴇ — ᴀᴜᴛʜᴏʀɪᴢᴇᴅ ᴀᴅᴍɪɴɪsᴛʀᴀᴛᴏʀs</u></b></blockquote>\n\n"
        f"<b>ᴛᴏᴛᴀʟ ᴄᴏᴜɴᴛ:</b> <code>{len(admins)}</code>\n\n" + "\n\n".join(lines)
    )
    await message.reply_text(admin_text, quote=True)


@Client.on_message(filters.command("auditlog") & filters.private)
async def auditlog_cmd(client: Client, message: Message):
    user_id = message.from_user.id
    if Config.BOT_OWNER_ID and user_id != Config.BOT_OWNER_ID[0]:
        return await message.reply("⛔️ **ᴏɴʟʏ ᴛʜᴇ ᴘʀɪᴍᴀʀʏ ᴏᴡɴᴇʀ ᴄᴀɴ ᴠɪᴇᴡ ᴀᴜᴅɪᴛ ʟᴏɢs.**")
    
    from database import db
    logs = db.audit_log.find().sort("timestamp", -1).limit(20)
    lines = []
    async for log in logs:
        ts = log['timestamp'].strftime("%Y-%m-%d %H:%M:%S")
        lines.append(f"• <code>{ts}</code> - 👤 <code>{log['user_id']}</code>: <b>{log['action']}</b> <code>{log['details']}</code>")
    
    if not lines:
        return await message.reply("<b>📝 ᴀᴜᴅɪᴛ ʟᴏɢ ɪs ᴇᴍᴘᴛʏ.</b>")
    
    text = "<b>🛡️ <u>ʀᴇᴄᴇɴᴛ ᴀᴜᴅɪᴛ ʟᴏɢs</u> (ᴛᴏᴘ 20)</b>\n\n" + "\n".join(lines)
    await message.reply(text)
