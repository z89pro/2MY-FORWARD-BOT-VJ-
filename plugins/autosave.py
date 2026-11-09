import re
import asyncio
import logging
from config import Config, temp
from database import db
from translation import Translation
from .test import CLIENT, start_clone_bot
from .regix import custom_caption, copy
from pyrogram import Client, filters, enums
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery, Message
from pyrogram.errors import ListenerTimeout
from buttons import colored_markup

logger = logging.getLogger("SkinetAutoSave")

def get_autosave_markup(is_running: bool, count: int):
    status_btn = InlineKeyboardButton("⏹️ sᴛᴏᴘ ᴍᴏɴɪᴛᴏʀ", callback_data="autosave#toggle_monitor") if is_running else InlineKeyboardButton("▶️ sᴛᴀʀᴛ ᴍᴏɴɪᴛᴏʀ", callback_data="autosave#toggle_monitor")
    buttons = [
        [status_btn],
        [
            InlineKeyboardButton("➕ ᴀᴅᴅ ᴄʜᴀɴɴᴇʟ", callback_data="autosave#add_channel"),
            InlineKeyboardButton(f"📋 ᴄʜᴀɴɴᴇʟs ({count})", callback_data="autosave#list_channels")
        ],
        [
            InlineKeyboardButton("🎯 sᴍᴀʀᴛ ᴍᴇᴅɪᴀ ғɪʟᴛᴇʀs", callback_data="autosave#filters"),
            InlineKeyboardButton("📤 ᴜᴘʟᴏᴀᴅ ᴅᴇsᴛɪɴᴀᴛɪᴏɴ", callback_data="autosave#destinations")
        ],
        [
            InlineKeyboardButton("• ʙᴀᴄᴋ", callback_data="settings#main"),
            InlineKeyboardButton("❌ ᴄʟᴏsᴇ", callback_data="close_btn")
        ]
    ]
    return colored_markup(buttons)

def get_monitored_channels_markup(channels):
    buttons = []
    for ch in channels:
        cid = str(ch.get('_id', ''))
        title = ch.get('from_title', str(ch.get('from_chat')))
        active = "🟢" if ch.get('active', True) else "🔴"
        cb_toggle = f"autosave#tch_{cid}" if cid else f"autosave#toggle_chan_{str(ch.get('from_chat'))[:20]}"
        cb_del = f"autosave#dch_{cid}" if cid else f"autosave#del_chan_{str(ch.get('from_chat'))[:20]}"
        buttons.append([
            InlineKeyboardButton(f"{active} {title}", callback_data=cb_toggle),
            InlineKeyboardButton("🗑️", callback_data=cb_del)
        ])
    buttons.append([
        InlineKeyboardButton("• ʙᴀᴄᴋ", callback_data="autosave#main"),
        InlineKeyboardButton("❌ ᴄʟᴏsᴇ", callback_data="close_btn")
    ])
    return colored_markup(buttons)

async def build_autosave_text(user_id: int):
    channels = await db.get_user_live_forwards(user_id)
    is_running = user_id in temp.LIVE_TASKS and temp.LIVE_TASKS[user_id].is_connected
    status_str = "🟢 <b>ᴀᴄᴛɪᴠᴇ & ᴍᴏɴɪᴛᴏʀɪɴɢ 24/7</b>" if is_running else "🔴 <b>sᴛᴏᴘᴘᴇᴅ</b>"
    user_channels = await db.get_user_channels(user_id)
    default_dest = user_channels[0]['title'] if user_channels else "ɴᴏɴᴇ (sᴇᴛ ɪɴ /settings)"
    
    text = (
        "🚀 <b><u>sᴍᴀʀᴛ ᴀᴜᴛᴏsᴀᴠᴇ & ʟɪᴠᴇ ᴍᴏɴɪᴛᴏʀ</u></b> ⚡️\n\n"
        "<i>ᴘᴏᴡᴇʀᴇᴅ ʙʏ sᴋɪɴᴇᴛ ᴠᴇʀsᴇ</i>\n\n"
        f"🔥 <b>sᴛᴀᴛᴜs:</b> {status_str}\n"
        f"📡 <b>ᴍᴏɴɪᴛᴏʀᴇᴅ ᴄʜᴀɴɴᴇʟs:</b> <code>{len(channels)}</code>\n"
        f"📤 <b>ᴅᴇғᴀᴜʟᴛ ᴅᴇsᴛɪɴᴀᴛɪᴏɴ:</b> <code>{default_dest}</code>\n\n"
        "<b>🌟 ʟɪᴠᴇ ᴍᴏɴɪᴛᴏʀɪɴɢ ʜɪɢʜʟɪɢʜᴛs:</b>\n"
        "✅ <b>ʀᴇᴀʟ-ᴛɪᴍᴇ ɪɴᴛᴇʀᴄᴇᴘᴛɪᴏɴ:</b> ᴄᴀᴘᴛᴜʀᴇs ɪɴᴄᴏᴍɪɴɢ ʟᴇᴄᴛᴜʀᴇs/ғɪʟᴇs ɪɴsᴛᴀɴᴛʟʏ.\n"
        "🎯 <b>sᴍᴀʀᴛ ғɪʟᴛᴇʀs:</b> ʀᴏᴜᴛᴇ ᴏɴʟʏ ᴠɪᴅᴇᴏs, ɴᴏᴛᴇs/PDFs, ᴀᴜᴅɪᴏs, ᴏʀ ᴘʜᴏᴛᴏs.\n"
        "🛠 <b>sᴋɪɴᴇᴛ ᴄʟᴇᴀɴ ᴇɴɢɪɴᴇ:</b> sᴛʀɪᴘs ᴄᴏᴍᴘᴇᴛɪᴛᴏʀ ʟɪɴᴋs, ʜᴀɴᴅʟᴇs & ᴀᴅs ᴀᴜᴛᴏᴍᴀᴛɪᴄᴀʟʟʏ.\n"
        "📤 <b>ᴍᴜʟᴛɪ-ᴄʜᴀɴɴᴇʟ ʀᴏᴜᴛɪɴɢ:</b> ᴅᴇᴅɪᴄᴀᴛᴇᴅ ᴛᴀʀɢᴇᴛ ᴄʜᴀɴɴᴇʟ ᴘᴇʀ sᴏᴜʀᴄᴇ.\n\n"
        "👇 <i>ᴍᴀɴᴀɢᴇ ʏᴏᴜʀ ʟɪᴠᴇ ᴍᴏɴɪᴛᴏʀs ᴜsɪɴɢ ᴛʜᴇ ʙᴜᴛᴛᴏɴs ʙᴇʟᴏᴡ:</i>"
    )
    return text, is_running, len(channels)

# ================= COMMAND /autosave =================

@Client.on_message(filters.private & filters.command(["autosave", "live", "monitor"]))
async def autosave_cmd(bot, message):
    user_id = message.from_user.id
    is_banned, ban_reason = await db.is_user_banned(user_id)
    if is_banned:
        return await message.reply_text(
            f"<blockquote><b>🚫 <u>ᴀᴄᴄᴏᴜɴᴛ sᴜsᴘᴇɴᴅᴇᴅ</u></b></blockquote>\n\n"
            f"ʏᴏᴜ ʜᴀᴠᴇ ʙᴇᴇɴ ʙᴀɴɴᴇᴅ ғʀᴏᴍ ᴜsɪɴɢ ᴛʜɪs ʙᴏᴛ.\n"
            f"<b>ʀᴇᴀsᴏɴ:</b> {ban_reason}",
            quote=True
        )
    text, is_running, count = await build_autosave_text(user_id)
    await message.reply_text(text, reply_markup=get_autosave_markup(is_running, count), quote=True)

# ================= CALLBACK HANDLER =================

@Client.on_callback_query(filters.regex(r"^autosave"))
async def autosave_callback(bot, query: CallbackQuery):
    user_id = query.from_user.id
    is_banned, ban_reason = await db.is_user_banned(user_id)
    if is_banned:
        return await query.answer(f"🚫 Account Banned: {ban_reason}", show_alert=True)
    data = query.data.split("#")[1] if "#" in query.data else "main"

    if data == "main":
        text, is_running, count = await build_autosave_text(user_id)
        await query.message.edit_text(text, reply_markup=get_autosave_markup(is_running, count))

    elif data == "toggle_monitor":
        if user_id in temp.LIVE_TASKS and temp.LIVE_TASKS[user_id].is_connected:
            # Stop monitor
            client = temp.LIVE_TASKS.pop(user_id, None)
            if client:
                try:
                    await client.stop()
                except Exception:
                    pass
            await query.answer("🛑 ᴀᴜᴛᴏsᴀᴠᴇ ᴍᴏɴɪᴛᴏʀ sᴛᴏᴘᴘᴇᴅ!", show_alert=True)
        else:
            # Start monitor
            success, err = await start_autosave_monitor(user_id, bot)
            if success:
                await query.answer("🚀 ᴀᴜᴛᴏsᴀᴠᴇ ᴍᴏɴɪᴛᴏʀ sᴛᴀʀᴛᴇᴅ!", show_alert=True)
            else:
                await query.answer(f"ғᴀɪʟᴇᴅ ᴛᴏ sᴛᴀʀᴛ: {err}", show_alert=True)
        text, is_running, count = await build_autosave_text(user_id)
        await query.message.edit_text(text, reply_markup=get_autosave_markup(is_running, count))

    elif data == "add_channel":
        await query.message.delete()
        _bot = await db.get_bot(user_id)
        if not _bot:
            return await bot.send_message(
                user_id,
                "<b>❌ ᴘʟᴇᴀsᴇ ᴀᴅᴅ ᴀ ʙᴏᴛ ᴏʀ ᴜsᴇʀʙᴏᴛ ғɪʀsᴛ ɪɴ /settings ᴛᴏ ᴜsᴇ ᴀᴜᴛᴏsᴀᴠᴇ ᴍᴏɴɪᴛᴏʀɪɴɢ!</b>\n\n"
                "• <b>ᴜsᴇʀʙᴏᴛ (ʀᴇᴄᴏᴍᴍᴇɴᴅᴇᴅ):</b> ᴄᴀɴ ᴍᴏɴɪᴛᴏʀ ᴀɴʏ ᴘʀɪᴠᴀᴛᴇ ᴏʀ ʀᴇsᴛʀɪᴄᴛᴇᴅ ᴄʜᴀɴɴᴇʟ ʏᴏᴜ ᴀʀᴇ ɪɴ.\n"
                "• <b>ʙᴏᴛ ᴛᴏᴋᴇɴ:</b> ᴄᴀɴ ᴍᴏɴɪᴛᴏʀ ᴄʜᴀɴɴᴇʟs ᴡʜᴇʀᴇ ʏᴏᴜʀ ʙᴏᴛ ɪs ᴀɴ ᴀᴅᴍɪɴɪsᴛʀᴀᴛᴏʀ.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⚙️ ᴏᴘᴇɴ sᴇᴛᴛɪɴɢs", callback_data="settings#main")]])
            )
        
        try:
            src_msg = await bot.ask(
                user_id,
                text=(
                    "<b>📡 sᴇɴᴅ sᴏᴜʀᴄᴇ ᴄʜᴀɴɴᴇʟ ʟɪɴᴋ ᴏʀ ᴄʜᴀᴛ ID ᴛᴏ ᴍᴏɴɪᴛᴏʀ:</b>\n\n"
                    "ᴇxᴀᴍᴘʟᴇs:\n"
                    "• <code>https://t.me/c/1234567890</code> (ᴘʀɪᴠᴀᴛᴇ ᴄʜᴀɴɴᴇʟ)\n"
                    "• <code>https://t.me/public_channel</code> (ᴘᴜʙʟɪᴄ ᴄʜᴀɴɴᴇʟ)\n"
                    "• <code>-1001234567890</code> (ᴅɪʀᴇᴄᴛ ᴄʜᴀᴛ ID)\n\n"
                    "<i>sᴇɴᴅ /cancel ᴛᴏ ᴀʙᴏʀᴛ</i>"
                ),
                timeout=300
            )
        except (asyncio.exceptions.TimeoutError, ListenerTimeout):
            text, is_running, count = await build_autosave_text(user_id)
            return await bot.send_message(user_id, text, reply_markup=get_autosave_markup(is_running, count))
        if not src_msg.text or src_msg.text.startswith("/cancel"):
            return await bot.send_message(user_id, "**ᴘʀᴏᴄᴇss ᴄᴀɴᴄᴇʟʟᴇᴅ!**")
        
        src_raw = src_msg.text.strip()
        link_regex = re.compile(r"(https://)?(t\.me/|telegram\.me/|telegram\.dog/)(c/)?(\d+|[a-zA-Z_0-9]+)")
        match = link_regex.search(src_raw)
        if match:
            src_id = match.group(4)
            if src_id.isnumeric():
                src_id = int("-100" + src_id)
        elif src_raw.lstrip("-").isdigit():
            src_id = int(src_raw)
        else:
            src_id = src_raw

        # Ask destination
        channels = await db.get_user_channels(user_id)
        default_dest = channels[0]['chat_id'] if channels else None
        default_title = channels[0]['title'] if channels else "ɢʟᴏʙᴀʟ ᴅᴇғᴀᴜʟᴛ"

        try:
            dst_msg = await bot.ask(
                user_id,
                text=(
                    f"<b>📤 sᴇɴᴅ ᴅᴇsᴛɪɴᴀᴛɪᴏɴ ᴄʜᴀɴɴᴇʟ ʟɪɴᴋ/ID:</b>\n\n"
                    f"ᴏʀ sᴇɴᴅ <code>/skip</code> ᴛᴏ ᴜsᴇ ʏᴏᴜʀ ᴅᴇғᴀᴜʟᴛ ᴅᴇsᴛɪɴᴀᴛɪᴏɴ:\n"
                    f"👉 <b>ᴅᴇғᴀᴜʟᴛ:</b> <code>{default_title}</code>\n\n"
                    "<i>sᴇɴᴅ /cancel ᴛᴏ ᴀʙᴏʀᴛ</i>"
                ),
                timeout=300
            )
        except (asyncio.exceptions.TimeoutError, ListenerTimeout):
            text, is_running, count = await build_autosave_text(user_id)
            return await bot.send_message(user_id, text, reply_markup=get_autosave_markup(is_running, count))
        if not dst_msg.text or dst_msg.text.startswith("/cancel"):
            return await bot.send_message(user_id, "**ᴘʀᴏᴄᴇss ᴄᴀɴᴄᴇʟʟᴇᴅ!**")
        
        if dst_msg.text.lower() == "/skip":
            if not default_dest:
                return await bot.send_message(user_id, "**❌ ɴᴏ ᴅᴇғᴀᴜʟᴛ ᴅᴇsᴛɪɴᴀᴛɪᴏɴ ғᴏᴜɴᴅ! ᴘʟᴇᴀsᴇ sᴇᴛ ᴀ ᴄʜᴀɴɴᴇʟ ɪɴ /settings ғɪʀsᴛ.**")
            dst_id = default_dest
            dst_title = default_title
        else:
            dst_raw = dst_msg.text.strip()
            dst_match = link_regex.search(dst_raw)
            if dst_match:
                dst_id = dst_match.group(4)
                if dst_id.isnumeric():
                    dst_id = int("-100" + dst_id)
            elif dst_raw.lstrip("-").isdigit():
                dst_id = int(dst_raw)
            else:
                dst_id = dst_raw
            dst_title = str(dst_id)

        src_title = str(src_id)
        try:
            chat = await bot.get_chat(src_id)
            src_title = chat.title or str(src_id)
        except Exception:
            pass

        await db.add_live_forward(user_id, src_id, dst_id, src_title, dst_title)
        
        # If running, restart monitor with new channel
        if user_id in temp.LIVE_TASKS:
            await start_autosave_monitor(user_id, bot)

        await bot.send_message(
            user_id,
            f"<b>✅ ᴄʜᴀɴɴᴇʟ ᴀᴅᴅᴇᴅ ᴛᴏ ʟɪᴠᴇ ᴍᴏɴɪᴛᴏʀɪɴɢ!</b>\n\n"
            f"📡 <b>sᴏᴜʀᴄᴇ:</b> <code>{src_title}</code>\n"
            f"📤 <b>ᴅᴇsᴛɪɴᴀᴛɪᴏɴ:</b> <code>{dst_title}</code>\n"
            f"⚡️ <b>ᴇɴɢɪɴᴇ:</b> sᴋɪɴᴇᴛ ᴠᴇʀsᴇ ᴀᴜᴛᴏsᴀᴠᴇ\n\n"
            "<i>ᴄʟɪᴄᴋ 'sᴛᴀʀᴛ ᴍᴏɴɪᴛᴏʀ' ᴛᴏ ʙᴇɢɪɴ ʟɪsᴛᴇɴɪɴɢ ғᴏʀ ɴᴇᴡ ᴘᴏsᴛs ɪɴ ʀᴇᴀʟ-ᴛɪᴍᴇ.</i>",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("▶️ sᴛᴀʀᴛ ᴍᴏɴɪᴛᴏʀ", callback_data="autosave#toggle_monitor")],
                [InlineKeyboardButton("• ʙᴀᴄᴋ ᴛᴏ ᴀᴜᴛᴏsᴀᴠᴇ", callback_data="autosave#main")]
            ])
        )

    elif data == "list_channels":
        channels = await db.get_user_live_forwards(user_id)
        if not channels:
            return await query.answer("ɴᴏ ᴄʜᴀɴɴᴇʟs ᴄᴜʀʀᴇɴᴛʟʏ ᴍᴏɴɪᴛᴏʀᴇᴅ!", show_alert=True)
        await query.message.edit_text(
            "📋 **ᴍᴏɴɪᴛᴏʀᴇᴅ ᴄʜᴀɴɴᴇʟs**\n\nᴄʟɪᴄᴋ ᴏɴ ᴀ ᴄʜᴀɴɴᴇʟ ᴛᴏ ᴛᴏɢɢʟᴇ ON/OFF ᴏʀ ᴄʟɪᴄᴋ 🗑️ ᴛᴏ ᴅᴇʟᴇᴛᴇ:",
            reply_markup=get_monitored_channels_markup(channels)
        )

    elif data.startswith("del_chan_") or data.startswith("dch_"):
        target_id = data.split("del_chan_")[1] if data.startswith("del_chan_") else data.split("dch_")[1]
        await db.remove_live_forward(user_id, target_id)
        await query.answer("ᴄʜᴀɴɴᴇʟ ʀᴇᴍᴏᴠᴇᴅ ғʀᴏᴍ ᴍᴏɴɪᴛᴏʀɪɴɢ!", show_alert=True)
        if user_id in temp.LIVE_TASKS:
            await start_autosave_monitor(user_id, bot)
        channels = await db.get_user_live_forwards(user_id)
        if not channels:
            text, is_running, count = await build_autosave_text(user_id)
            return await query.message.edit_text(text, reply_markup=get_autosave_markup(is_running, count))
        await query.message.edit_text(
            "📋 **ᴍᴏɴɪᴛᴏʀᴇᴅ ᴄʜᴀɴɴᴇʟs**\n\nᴄʟɪᴄᴋ ᴏɴ ᴀ ᴄʜᴀɴɴᴇʟ ᴛᴏ ᴛᴏɢɢʟᴇ ON/OFF ᴏʀ ᴄʟɪᴄᴋ 🗑️ ᴛᴏ ᴅᴇʟᴇᴛᴇ:",
            reply_markup=get_monitored_channels_markup(channels)
        )

    elif data.startswith("toggle_chan_") or data.startswith("tch_"):
        target_id = data.split("toggle_chan_")[1] if data.startswith("toggle_chan_") else data.split("tch_")[1]
        await db.toggle_live_forward_active(user_id, target_id)
        if user_id in temp.LIVE_TASKS:
            await start_autosave_monitor(user_id, bot)
        channels = await db.get_user_live_forwards(user_id)
        await query.message.edit_text(
            "📋 **ᴍᴏɴɪᴛᴏʀᴇᴅ ᴄʜᴀɴɴᴇʟs**\n\nᴄʟɪᴄᴋ ᴏɴ ᴀ ᴄʜᴀɴɴᴇʟ ᴛᴏ ᴛᴏɢɢʟᴇ ON/OFF ᴏʀ ᴄʟɪᴄᴋ 🗑️ ᴛᴏ ᴅᴇʟᴇᴛᴇ:",
            reply_markup=get_monitored_channels_markup(channels)
        )

    elif data == "filters":
        user_filters = await db.get_user_live_filters(user_id)
        def mark(ftype):
            return "✅" if user_filters.get(ftype, True) else "❌"

        buttons = [
            [
                InlineKeyboardButton(f"🎥 ᴠɪᴅᴇᴏs {mark('video')}", callback_data="autosave#toggle_filter_video"),
                InlineKeyboardButton(f"📸 ᴘʜᴏᴛᴏs {mark('photo')}", callback_data="autosave#toggle_filter_photo")
            ],
            [
                InlineKeyboardButton(f"📁 ᴅᴏᴄᴜᴍᴇɴᴛs {mark('document')}", callback_data="autosave#toggle_filter_document"),
                InlineKeyboardButton(f"🎵 ᴀᴜᴅɪᴏs {mark('audio')}", callback_data="autosave#toggle_filter_audio")
            ],
            [
                InlineKeyboardButton(f"💬 ᴛᴇxᴛs {mark('text')}", callback_data="autosave#toggle_filter_text"),
                InlineKeyboardButton(f"🎞️ ɢɪғs {mark('animation')}", callback_data="autosave#toggle_filter_animation")
            ],
            [
                InlineKeyboardButton("• ʙᴀᴄᴋ", callback_data="autosave#main"),
                InlineKeyboardButton("❌ ᴄʟᴏsᴇ", callback_data="close_btn")
            ]
        ]
        await query.message.edit_text(
            "🎯 **sᴍᴀʀᴛ ᴍᴇᴅɪᴀ ғɪʟᴛᴇʀs**\n\nᴄʜᴏᴏsᴇ ᴡʜᴀᴛ ᴛʏᴘᴇs ᴏғ ᴍᴇᴅɪᴀ ʏᴏᴜ ᴡᴀɴᴛ ᴀᴜᴛᴏsᴀᴠᴇ ᴛᴏ ᴀᴜᴛᴏᴍᴀᴛɪᴄᴀʟʟʏ ᴄᴀᴘᴛᴜʀᴇ ᴀɴᴅ ғᴏʀᴡᴀʀᴅ:",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    elif data.startswith("toggle_filter_"):
        filter_key = data.split("toggle_filter_")[1]
        configs = await db.get_configs(user_id)
        filters_cfg = configs.get('filters', {})
        current = filters_cfg.get(filter_key, True)
        filters_cfg[filter_key] = not current
        configs['filters'] = filters_cfg
        await db.update_configs(user_id, configs)
        await query.answer(f"{filter_key.title()} ғɪʟᴛᴇʀ ᴜᴘᴅᴀᴛᴇᴅ!")

        def mark(key):
            return "✅" if filters_cfg.get(key, True) else "❌"

        buttons = [
            [
                InlineKeyboardButton(f"🎥 ᴠɪᴅᴇᴏs {mark('video')}", callback_data="autosave#toggle_filter_video"),
                InlineKeyboardButton(f"📸 ᴘʜᴏᴛᴏs {mark('photo')}", callback_data="autosave#toggle_filter_photo")
            ],
            [
                InlineKeyboardButton(f"📁 ᴅᴏᴄᴜᴍᴇɴᴛs {mark('document')}", callback_data="autosave#toggle_filter_document"),
                InlineKeyboardButton(f"🎵 ᴀᴜᴅɪᴏs {mark('audio')}", callback_data="autosave#toggle_filter_audio")
            ],
            [
                InlineKeyboardButton(f"💬 ᴛᴇxᴛs {mark('text')}", callback_data="autosave#toggle_filter_text"),
                InlineKeyboardButton(f"🎞️ ɢɪғs {mark('animation')}", callback_data="autosave#toggle_filter_animation")
            ],
            [
                InlineKeyboardButton("• ʙᴀᴄᴋ", callback_data="autosave#main"),
                InlineKeyboardButton("❌ ᴄʟᴏsᴇ", callback_data="close_btn")
            ]
        ]
        await query.message.edit_text(
            "🎯 **sᴍᴀʀᴛ ᴍᴇᴅɪᴀ ғɪʟᴛᴇʀs**\n\nᴄʜᴏᴏsᴇ ᴡʜᴀᴛ ᴛʏᴘᴇs ᴏғ ᴍᴇᴅɪᴀ ʏᴏᴜ ᴡᴀɴᴛ ᴀᴜᴛᴏsᴀᴠᴇ ᴛᴏ ᴀᴜᴛᴏᴍᴀᴛɪᴄᴀʟʟʏ ᴄᴀᴘᴛᴜʀᴇ ᴀɴᴅ ғᴏʀᴡᴀʀᴅ:",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    elif data == "destinations":
        channels = await db.get_user_live_forwards(user_id)
        text = "📤 **ᴄᴜsᴛᴏᴍ ᴜᴘʟᴏᴀᴅ ᴅᴇsᴛɪɴᴀᴛɪᴏɴs**\n\n"
        if not channels:
            text += "ɴᴏ ᴍᴏɴɪᴛᴏʀᴇᴅ ᴄʜᴀɴɴᴇʟs ʏᴇᴛ! ᴜsᴇ ➕ **ᴀᴅᴅ ᴄʜᴀɴɴᴇʟ** ғɪʀsᴛ."
        else:
            for ch in channels:
                text += f"• **{ch.get('from_title', 'sᴏᴜʀᴄᴇ')}** ➡️ `{ch.get('to_title', 'ᴛᴀʀɢᴇᴛ')}`\n"
        buttons = [[
            InlineKeyboardButton("• ʙᴀᴄᴋ", callback_data="autosave#main"),
            InlineKeyboardButton("❌ ᴄʟᴏsᴇ", callback_data="close_btn")
        ]]
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))

# ================= BACKGROUND MONITOR ENGINE =================

async def start_autosave_monitor(user_id: int, bot_client: Client):
    _bot = await db.get_bot(user_id, prefer_userbot=True)
    if not _bot:
        return False, "ᴘʟᴇᴀsᴇ ᴀᴅᴅ ᴀ ʙᴏᴛ ᴏʀ ᴜsᴇʀʙᴏᴛ ɪɴ /settings ғɪʀsᴛ."

    monitored = await db.get_user_live_forwards(user_id)
    active_channels = [ch for ch in monitored if ch.get('active', True)]
    if not active_channels:
        return False, "ɴᴏ ᴀᴄᴛɪᴠᴇ ᴄʜᴀɴɴᴇʟs ᴛᴏ ᴍᴏɴɪᴛᴏʀ. ᴜsᴇ ➕ ᴀᴅᴅ ᴄʜᴀɴɴᴇʟ ғɪʀsᴛ."

    # Stop any existing monitor task
    if user_id in temp.LIVE_TASKS:
        old = temp.LIVE_TASKS.pop(user_id, None)
        if old:
            try:
                await old.stop()
            except Exception:
                pass

    try:
        userbot = await start_clone_bot(CLIENT().client(_bot))
    except Exception as e:
        logger.error(f"Failed to start client for autosave: {e}")
        return False, str(e)

    # Map monitored chat IDs to their destination info
    chat_map = {}
    for ch in active_channels:
        from_c = ch.get('from_chat')
        try:
            from_c_id = int(from_c)
        except Exception:
            from_c_id = from_c
        chat_map[from_c_id] = ch
        chat_map[str(from_c)] = ch

    # Register real-time incoming message handler
    @userbot.on_message()
    async def incoming_live_message(client: Client, message: Message):
        chat_id = message.chat.id
        match_info = chat_map.get(chat_id) or chat_map.get(str(chat_id)) or (chat_map.get(f"@{message.chat.username}") if message.chat.username else None)
        if not match_info:
            return

        # Check Smart Media Filters
        user_configs = await db.get_configs(user_id)
        filters_cfg = user_configs.get('filters', {})
        
        if message.video and not filters_cfg.get('video', True):
            return
        if message.photo and not filters_cfg.get('photo', True):
            return
        if message.document and not filters_cfg.get('document', True):
            return
        if message.audio and not filters_cfg.get('audio', True):
            return
        if message.text and not filters_cfg.get('text', True):
            return
        if message.animation and not filters_cfg.get('animation', True):
            return

        to_chat = match_info.get('to_chat')
        try:
            to_chat = int(to_chat)
        except Exception:
            pass

        try:
            clean_cap = user_configs.get('clean_caption', False)
            rep_words = user_configs.get('replace_words', {})
            cap = custom_caption(
                message, 
                user_configs.get('caption'), 
                clean_caption=clean_cap, 
                replace_words=rep_words,
                user_configs=user_configs
            )
            
            dump_target = await db.get_effective_dump_channel(user_id=user_id)

            if user_configs.get('forward_tag'):
                await client.forward_messages(
                    chat_id=to_chat,
                    from_chat_id=chat_id,
                    message_ids=message.id,
                    protect_content=user_configs.get('protect')
                )
                if dump_target and str(dump_target) != str(to_chat):
                    try:
                        await client.forward_messages(chat_id=dump_target, from_chat_id=chat_id, message_ids=message.id)
                    except Exception:
                        pass
            else:
                if message.media:
                    media_attr = getattr(message, message.media.value, None)
                    file_id = getattr(media_attr, 'file_id', None) if media_attr else None
                    if file_id and cap:
                        await client.send_cached_media(
                            chat_id=to_chat,
                            file_id=file_id,
                            caption=cap,
                            protect_content=user_configs.get('protect')
                        )
                        if dump_target and str(dump_target) != str(to_chat):
                            try:
                                await client.send_cached_media(chat_id=dump_target, file_id=file_id, caption=cap)
                            except Exception:
                                pass
                    else:
                        await client.copy_message(
                            chat_id=to_chat,
                            from_chat_id=chat_id,
                            message_id=message.id,
                            caption=cap,
                            protect_content=user_configs.get('protect')
                        )
                        if dump_target and str(dump_target) != str(to_chat):
                            try:
                                await client.copy_message(chat_id=dump_target, from_chat_id=chat_id, message_id=message.id, caption=cap)
                            except Exception:
                                pass
                elif message.text:
                    await client.send_message(
                        chat_id=to_chat,
                        text=cap or message.text,
                        protect_content=user_configs.get('protect')
                    )
                    if dump_target and str(dump_target) != str(to_chat):
                        try:
                            await client.send_message(chat_id=dump_target, text=cap or message.text)
                        except Exception:
                            pass
            logger.info(f"Skinet AutoSave: Forwarded new message {message.id} from {chat_id} to {to_chat}")
            if Config.LOG_CHANNEL:
                try:
                    await bot_client.send_message(
                        chat_id=Config.LOG_CHANNEL,
                        text=f"📡 <b>#AutoSaveCaptured</b>\n\n⚡️ <b>Engine:</b> Skinet Verse\n👤 <b>User:</b> <code>{user_id}</code>\n📡 <b>Source:</b> <code>{chat_id}</code>\n🎯 <b>Destination:</b> <code>{to_chat}</code>\n🆔 <b>Message ID:</b> <code>{message.id}</code>"
                    )
                except Exception:
                    pass
        except Exception as err:
            logger.error(f"AutoSave Error on message {message.id}: {err}")

    temp.LIVE_TASKS[user_id] = userbot
    return True, None

async def resume_all_autosave_monitors(bot_client: Client):
    try:
        active_forwards = await db.get_all_active_live_forwards()
        if not active_forwards:
            return
        user_ids = list(set([doc['user_id'] for doc in active_forwards if 'user_id' in doc]))
        logger.info(f"Resuming AutoSave live monitors for {len(user_ids)} users...")
        for uid in user_ids:
            try:
                success, err = await start_autosave_monitor(uid, bot_client)
                if success:
                    logger.info(f"✅ AutoSave monitor resumed for user {uid}")
                else:
                    logger.warning(f"⚠️ AutoSave resume failed for user {uid}: {err}")
            except Exception as e:
                logger.error(f"Error resuming autosave for user {uid}: {e}")
    except Exception as e:
        logger.error(f"AutoSave resume routine error: {e}")
