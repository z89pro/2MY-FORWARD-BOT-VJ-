import re
import asyncio 
from .utils import STS
from database import db
from config import temp 
from translation import Translation
from pyrogram import Client, filters, enums
from pyrogram.errors import FloodWait 
from pyrogram.errors.exceptions.not_acceptable_406 import ChannelPrivate as PrivateChat
from pyrogram.errors.exceptions.bad_request_400 import ChannelInvalid, ChatAdminRequired, UsernameInvalid, UsernameNotModified, ChannelPrivate
from pyrogram.types import (
    InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery,
    KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
)
try:
    from pyrogram.types import RequestPeerTypeChannel, RequestPeerTypeChat
except ImportError:
    try:
        from pyrogram.types import KeyboardButtonRequestChat
        class RequestPeerTypeChannel:
            def __new__(cls, button_id=1, **kwargs):
                return KeyboardButtonRequestChat(button_id=button_id, chat_is_channel=True)
        class RequestPeerTypeChat:
            def __new__(cls, button_id=1, **kwargs):
                return KeyboardButtonRequestChat(button_id=button_id, chat_is_channel=False)
    except Exception:
        class RequestPeerTypeChannel:
            def __init__(self, *args, **kwargs): pass
        class RequestPeerTypeChat:
            def __init__(self, *args, **kwargs): pass
from buttons import btn, row, markup, colored_markup

#===================Run Function===================#

ADD_CHANNEL_BTN = "➕ ᴀᴅᴅ ᴄʜᴀɴɴᴇʟ"


async def resolve_and_add_target(bot, message, user_id, source_msg):
    """Resolve a link / ID / forwarded message into a target channel.

    Registers it as a target if it isn't one already. Returns
    (chat_id, title), or None when the input isn't a usable channel.
    """
    from plugins.forward_parser import resolve_channel_input
    res = await resolve_channel_input(source_msg, bot)
    if not res.get("chat_id"):
        return None
    chat_id = res["chat_id"]
    title = res.get("chat_title") or str(chat_id)
    username = res.get("chat_username") or "private"
    if username and not username.startswith("@") and username != "private":
        username = "@" + username
    try:
        if not await db.in_channel(user_id, chat_id):
            await db.add_channel(user_id, chat_id, title, username)
    except Exception:
        pass
    return chat_id, title


async def prompt_add_channel(bot, message, user_id):
    """Ask for a channel and register it. Returns (chat_id, title) or None."""
    try:
        reply_kb = ReplyKeyboardMarkup([
            [KeyboardButton("📢 ᴄʜᴏᴏsᴇ ᴄʜᴀɴɴᴇʟ", request_chat=RequestPeerTypeChannel(button_id=11))],
            [KeyboardButton("👥 ᴄʜᴏᴏsᴇ ɢʀᴏᴜᴘ", request_chat=RequestPeerTypeChat(button_id=12))],
            [KeyboardButton("cancel")]
        ], one_time_keyboard=True, resize_keyboard=True)
        reply = await bot.ask(
            message.chat.id,
            text=("<b>➕ ᴀᴅᴅ ᴀ ᴛᴀʀɢᴇᴛ ᴄʜᴀɴɴᴇʟ\n\n"
                  "ᴛᴀᴘ ᴀ ʙᴜᴛᴛᴏɴ ʙᴇʟᴏᴡ ᴛᴏ ᴘɪᴄᴋ ᴀ ᴄʜᴀɴɴᴇʟ/ɢʀᴏᴜᴘ, sᴇɴᴅ ᴀ ʟɪɴᴋ ᴏʀ ID, ᴏʀ ғᴏʀᴡᴀʀᴅ ᴀ ᴍᴇssᴀɢᴇ.\n\n"
                  "⚠️ <i>ᴍᴀᴋᴇ sᴜʀᴇ ʏᴏᴜʀ ʙᴏᴛ ɪs ᴀᴅᴍɪɴ ᴛʜᴇʀᴇ ᴡɪᴛʜ ᴘᴏsᴛ ᴘᴇʀᴍɪssɪᴏɴs.</i>\n"
                  "/cancel - ᴄᴀɴᴄᴇʟ ᴛʜɪs ᴘʀᴏᴄᴇss</b>"),
            reply_markup=reply_kb,
            timeout=180,
        )
    except Exception:
        await message.reply_text("⏰ <b>ᴛɪᴍᴇᴏᴜᴛ: ɴᴏ ʀᴇsᴘᴏɴsᴇ ʀᴇᴄᴇɪᴠᴇᴅ.</b>", reply_markup=ReplyKeyboardRemove())
        return None

    from plugins.forward_parser import extract_requested_chat
    shared_id, shared_title = extract_requested_chat(reply)
    if shared_id:
        chat_id = shared_id
        title = shared_title or str(chat_id)
        try:
            if not await db.in_channel(user_id, chat_id):
                await db.add_channel(user_id, chat_id, title, "private")
        except Exception:
            pass
        return chat_id, title

    text = (reply.text or "").strip() if reply else ""
    if not text or text.lower().startswith(('/', 'cancel')):
        await message.reply_text(Translation.CANCEL, reply_markup=ReplyKeyboardRemove())
        return None
    added = await resolve_and_add_target(bot, message, user_id, reply)
    if not added:
        await message.reply_text(
            "<b>❌ ᴄᴏᴜʟᴅ ɴᴏᴛ ʀᴇᴀᴅ ᴛʜᴀᴛ ᴄʜᴀɴɴᴇʟ.</b>\n"
            "<i>sᴇɴᴅ ᴀ ʟɪɴᴋ ʟɪᴋᴇ <code>https://t.me/mychannel</code>, "
            "ᴀɴ ID ʟɪᴋᴇ <code>-1001234567890</code>, "
            "ᴏʀ ғᴏʀᴡᴀʀᴅ ᴀ ᴍᴇssᴀɢᴇ ғʀᴏᴍ ɪᴛ.</i>",
            reply_markup=ReplyKeyboardRemove())
        return None
    return added

@Client.on_message(filters.private & filters.command(["fwd", "forward"]))
async def run(bot, message):
    buttons = []
    user_id = message.from_user.id
    is_banned, ban_reason = await db.is_user_banned(user_id)
    if is_banned:
        return await message.reply_text(
            f"<blockquote><b>🚫 <u>ᴀᴄᴄᴏᴜɴᴛ sᴜsᴘᴇɴᴅᴇᴅ</u></b></blockquote>\n\n"
            f"ʏᴏᴜ ʜᴀᴠᴇ ʙᴇᴇɴ ʙᴀɴɴᴇᴅ ғʀᴏᴍ ᴜsɪɴɢ ᴛʜɪs ʙᴏᴛ.\n"
            f"<b>ʀᴇᴀsᴏɴ:</b> {ban_reason}",
            quote=True
        )

    if temp.lock.get(user_id):
        return await message.reply_text("⏳ <b>ᴀ ᴛᴀsᴋ ɪs ᴀʟʀᴇᴀᴅʏ ɪɴ ᴘʀᴏɢʀᴇss. ᴘʟᴇᴀsᴇ ᴡᴀɪᴛ ᴜɴᴛɪʟ ɪᴛ ᴄᴏᴍᴘʟᴇᴛᴇs ᴏʀ ᴜsᴇ /stop.</b>", quote=True)
    from plugins.verify import is_user_verified, send_verify_prompt
    if not await is_user_verified(user_id):
        return await send_verify_prompt(bot, message, user_id)
    _userbot = await db.get_userbot(user_id)
    _custom_bot = await db.get_custom_bot(user_id)
    if not _userbot and not _custom_bot:
      return await message.reply("<code>__**You didn't add any bot. Please add a bot using /settings !**__</code>")
    channels = await db.get_user_channels(user_id)
    if not channels:
       return await message.reply_text("Please set a target channel in /settings before forwarding")
    
    from plugins.range_parser import parse_multi_ranges, format_ranges_summary, calculate_total_messages

    # Direct multi-range or link forwarding: /fwd <link/ranges...>
    raw_args = ""
    cmd_parts = (message.text or message.caption or "").split(None, 1)
    if len(cmd_parts) > 1:
        raw_args = cmd_parts[1]
    if raw_args:
        try:
            parsed_chat, parsed_ranges = parse_multi_ranges(raw_args)
            if parsed_chat and parsed_ranges:
                toid = channels[0]['chat_id']
                to_title = channels[0]['title']

                is_bl_from, pat_from = await db.check_blacklisted(channel=parsed_chat)
                is_bl_to, pat_to = await db.check_blacklisted(channel=toid)
                if is_bl_from or is_bl_to:
                    matched = pat_from if is_bl_from else pat_to
                    return await message.reply_text(
                        f"<blockquote><b>⛔ <u>ᴄᴏɴᴛᴇɴᴛ ᴠɪᴏʟᴀᴛɪᴏɴ</u></b></blockquote>\n\n"
                        f"ᴛʜɪs ᴄʜᴀɴɴᴇʟ ɪs ʙʟᴏᴄᴋʟɪsᴛᴇᴅ ʙʏ ʙᴏᴛ ᴍᴏᴅᴇʀᴀᴛɪᴏɴ (<code>{matched}</code>).",
                        quote=True
                    )

                is_source_private = False
                s_cid = str(parsed_chat).strip()
                if s_cid.startswith("-100") or s_cid.isdigit() or "/c/" in s_cid or "/+" in s_cid or "joinchat" in s_cid:
                    is_source_private = True
                elif not s_cid.startswith("@") and not s_cid.startswith("http"):
                    is_source_private = True

                try:
                    title = (await bot.get_chat(parsed_chat)).title
                except Exception:
                    is_source_private = True
                    title = "Source"

                if is_source_private:
                    if _userbot:
                        active_worker = _userbot
                    else:
                        add_ub_btn = InlineKeyboardMarkup([
                            [InlineKeyboardButton("➕ ᴀᴅᴅ ᴜsᴇʀʙᴏᴛ", callback_data="settings#adduserbot")],
                            [InlineKeyboardButton("🔑 ʟᴏɢɪɴ ᴠɪᴀ ᴏᴛᴘ", callback_data="settings#addlogin")],
                            [InlineKeyboardButton("❌ ᴄʟᴏsᴇ", callback_data="close_btn")]
                        ])
                        return await message.reply_text(
                            f"<blockquote><b>⚠️ <u>ᴜsᴇʀʙᴏᴛ ʀᴇǫᴜɪʀᴇᴅ ғᴏʀ ᴘʀɪᴠᴀᴛᴇ ᴄʜᴀɴɴᴇʟ</u></b></blockquote>\n\n"
                            f"📡 <b>sᴏᴜʀᴄᴇ:</b> <code>{title}</code> (<code>{parsed_chat}</code>)\n\n"
                            f"ᴛʜɪs ɪs ᴀ <b>ᴘʀɪᴠᴀᴛᴇ ᴄʜᴀɴɴᴇʟ</b>. ᴛᴇʟᴇɢʀᴀᴍ ʙᴏᴛ ᴛᴏᴋᴇɴs ᴄᴀɴɴᴏᴛ ʀᴇᴀᴅ ᴘʀɪᴠᴀᴛᴇ ᴄʜᴀɴɴᴇʟs ᴜɴʟᴇss ᴛʜᴇʏ ᴀʀᴇ ᴀᴅᴍɪɴs.\n\n"
                            f"👉 <b>ᴘʟᴇᴀsᴇ ᴄᴏɴɴᴇᴄᴛ ʏᴏᴜʀ ᴜsᴇʀʙᴏᴛ sᴇssɪᴏɴ</b> (ʏᴏᴜʀ ᴛᴇʟᴇɢʀᴀᴍ ᴀᴄᴄᴏᴜɴᴛ ᴛʜᴀᴛ ʜᴀs ᴊᴏɪɴᴇᴅ ᴛʜɪs ᴄʜᴀɴɴᴇʟ) ᴠɪᴀ ᴛʜᴇ ʙᴜᴛᴛᴏɴs ʙᴇʟᴏᴡ ᴛᴏ ᴄᴏɴᴛɪɴᴜᴇ:",
                            reply_markup=add_ub_btn
                        )
                else:
                    active_worker = _userbot or _custom_bot

                worker_name_display = f"👤 <b>ᴜsᴇʀʙᴏᴛ:</b> <code>{active_worker['name']}</code>" if not active_worker.get('is_bot') else f"🤖 <b>ʙᴏᴛ:</b> <code>{active_worker['name']}</code> (@{active_worker.get('username', '?')})"
                
                total_msgs = calculate_total_messages(parsed_ranges)
                summary_str = format_ranges_summary(parsed_ranges)
                forward_id = f"{user_id}-{message.id}"
                reply_markup = markup(
                    row(
                        btn('✅ ʏᴇs, sᴛᴀʀᴛ', f"start_public_{forward_id}", "green"),
                        btn('❌ ɴᴏ, ᴄᴀɴᴄᴇʟ', "close_btn", "red")
                    )
                )
                await message.reply_text(
                    text=f"⚡ <b><u>ᴍᴜʟᴛɪ-ʀᴀɴɢᴇ ғᴏʀᴡᴀʀᴅ</u></b>\n\n"
                         f"{worker_name_display}\n"
                         f"📡 <b>ғʀᴏᴍ:</b> <code>{title}</code>\n"
                         f"🎯 <b>ᴛᴏ:</b> <code>{to_title}</code>\n"
                         f"📑 <b>ʀᴀɴɢᴇs:</b> <code>{summary_str}</code>\n"
                         f"📦 <b>ᴛᴏᴛᴀʟ ᴍᴇssᴀɢᴇs:</b> <code>{total_msgs}</code>\n\n"
                         f"<i>ᴅᴏ ʏᴏᴜ ᴡᴀɴᴛ ᴛᴏ sᴛᴀʀᴛ ғᴏʀᴡᴀʀᴅɪɴɢ ᴛʜᴇsᴇ ʀᴀɴɢᴇs?</i>",
                    disable_web_page_preview=True,
                    reply_markup=reply_markup
                )
                first_start = parsed_ranges[0][0]
                last_end = parsed_ranges[-1][1]
                STS(forward_id).store(parsed_chat, toid, skip=first_start, limit=last_end, ranges=parsed_ranges, worker=active_worker)
                return
        except Exception as parse_err:
            return await message.reply_text(f"⚠️ <b>ᴇʀʀᴏʀ ɪɴ ʀᴀɴɢᴇ ᴘᴀʀsɪɴɢ:</b> {parse_err}")

    target_map = {}
    buttons = [
        [KeyboardButton("📢 ᴘɪᴄᴋ ᴛᴀʀɢᴇᴛ ᴄʜᴀɴɴᴇʟ", request_chat=RequestPeerTypeChannel(button_id=101))],
        [KeyboardButton("👥 ᴘɪᴄᴋ ᴛᴀʀɢᴇᴛ ɢʀᴏᴜᴘ", request_chat=RequestPeerTypeChat(button_id=102))]
    ]
    for idx, channel in enumerate(channels, start=1):
        c_title = (channel.get('title') or '').strip()
        c_id = str(channel.get('chat_id', ''))
        label = f"{idx}. {c_title}"
        buttons.append([KeyboardButton(label)])

        target_map[label] = channel
        target_map[label.lower()] = channel
        target_map[str(idx)] = channel
        target_map[c_title] = channel
        target_map[c_title.lower()] = channel
        target_map[c_id] = channel
        try:
            from font_styler import style_button
            styled_l = style_button(label)
            target_map[styled_l] = channel
            target_map[styled_l.lower()] = channel
            styled_t = style_button(c_title)
            target_map[styled_t] = channel
            target_map[styled_t.lower()] = channel
        except Exception:
            pass
    buttons.append([KeyboardButton(ADD_CHANNEL_BTN)])
    buttons.append([KeyboardButton("cancel")])
    keyboard = ReplyKeyboardMarkup(buttons, one_time_keyboard=True, resize_keyboard=True)

    toid = to_title = None
    _worker = _userbot or _custom_bot
    w_name = _worker.get('name', 'Bot') if _worker else 'Bot'
    w_user = _worker.get('username', 'Bot') if _worker else 'Bot'
    try:
        prompt_txt = Translation.TO_MSG.format(w_name, w_user)
    except Exception:
        prompt_txt = Translation.TO_MSG
    if len(channels) == 1:
        prompt_txt += f"\n\n<i>🎯 ᴄᴜʀʀᴇɴᴛ ᴅᴇғᴀᴜʟᴛ:</i> <b>{channels[0]['title']}</b> (ᴛᴀᴘ ʙᴇʟᴏᴡ ᴛᴏ ᴜsᴇ ᴏʀ ᴘɪᴄᴋ ᴀɴᴏᴛʜᴇʀ)"

    for _attempt in range(3):
        try:
            _toid = await bot.ask(message.chat.id, prompt_txt, reply_markup=keyboard, timeout=180)
        except Exception:
            return await message.reply_text("⏰ <b>ᴛɪᴍᴇᴏᴜᴛ: ɴᴏ ʀᴇsᴘᴏɴsᴇ ʀᴇᴄᴇɪᴠᴇᴅ. ғᴏʀᴡᴀʀᴅɪɴɢ ᴄᴀɴᴄᴇʟʟᴇᴅ.</b>", reply_markup=ReplyKeyboardRemove())
        answer = (_toid.text or "").strip() if _toid else ""
        if answer and answer.lower().startswith(('/', 'cancel')):
            return await message.reply_text(Translation.CANCEL, reply_markup=ReplyKeyboardRemove())

        from plugins.forward_parser import extract_requested_chat
        shared_id, shared_title = extract_requested_chat(_toid)
        if shared_id:
            toid = shared_id
            to_title = shared_title or str(shared_id)
            try:
                if not await db.in_channel(user_id, toid):
                    await db.add_channel(user_id, toid, to_title, "private")
            except Exception:
                pass
            break

        if answer == ADD_CHANNEL_BTN:
            added = await prompt_add_channel(bot, message, user_id)
            if added:
                toid, to_title = added
                break
            continue

        picked = target_map.get(answer) or target_map.get(answer.lower())
        if not picked:
            # Not one of the buttons — maybe a link, an ID, or a forward.
            added = await resolve_and_add_target(bot, message, user_id, _toid)
            if added:
                toid, to_title = added
                break
            await message.reply_text(
                "<b>❌ ᴛʜᴀᴛ ᴡᴀsɴ'ᴛ ᴏɴᴇ ᴏғ ʏᴏᴜʀ ᴄʜᴀɴɴᴇʟs.</b>\n\n"
                "<i>ᴛᴀᴘ ᴀ ʙᴜᴛᴛᴏɴ ʙᴇʟᴏᴡ, ᴘɪᴄᴋ ᴀ ᴄʜᴀɴɴᴇʟ, sᴇɴᴅ ɪᴛs ɴᴜᴍʙᴇʀ, ᴏʀ sᴇɴᴅ ᴀ ᴄʜᴀɴɴᴇʟ ʟɪɴᴋ / ID.</i>")
            continue
        toid = picked['chat_id']
        to_title = picked['title']
        break

    if toid is None:
        return await message.reply_text(
            "<b>⛔ ᴛᴏᴏ ᴍᴀɴʏ ᴜɴʀᴇᴄᴏɢɴɪᴢᴇᴅ ᴀɴsᴡᴇʀs. ᴘʀᴏᴄᴇss ᴄᴀɴᴄᴇʟʟᴇᴅ.</b>\n"
            "<i>ᴛᴀᴘ /forward ᴛᴏ sᴛᴀʀᴛ ᴀɢᴀɪɴ.</i>",
            reply_markup=ReplyKeyboardRemove())

    target_confirm_msg = (
        f"<blockquote>🎯 <b><u>ᴛᴀʀɢᴇᴛ ᴄʜᴀɴɴᴇʟ ᴄᴏɴғɪʀᴍᴇᴅ</u></b></blockquote>\n\n"
        f"📤 <b>ᴛᴀʀɢᴇᴛ (ᴛᴏ):</b> <code>{to_title}</code>\n"
        f"🆔 <b>ᴄʜᴀᴛ ɪᴅ:</b> <code>{toid}</code>\n"
        f"✅ <b>sᴛᴀᴛᴜs:</b> Target channel selected and ready.\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👉 <b>ɴᴏᴡ sᴇʟᴇᴄᴛ ʏᴏᴜʀ sᴏᴜʀᴄᴇ (ғʀᴏᴍ):</b>\n"
        f"• <i>Forward any message from the Source Channel, OR</i>\n"
        f"• <i>Send message link (e.g. <code>https://t.me/c/12345/10</code>), OR</i>\n"
        f"• <i>Tap one of the buttons below to pick a channel/group:</i>\n\n"
        f"/cancel - Cancel this process"
    )

    src_kb = ReplyKeyboardMarkup([
        [KeyboardButton("📢 ᴘɪᴄᴋ sᴏᴜʀᴄᴇ ᴄʜᴀɴɴᴇʟ", request_chat=RequestPeerTypeChannel(button_id=201))],
        [KeyboardButton("👥 ᴘɪᴄᴋ sᴏᴜʀᴄᴇ ɢʀᴏᴜᴘ", request_chat=RequestPeerTypeChat(button_id=202))],
        [KeyboardButton("cancel")]
    ], one_time_keyboard=True, resize_keyboard=True)

    try:
        fromid = await bot.ask(
            message.chat.id,
            target_confirm_msg,
            reply_markup=src_kb,
            timeout=180
        )
    except Exception:
        return await message.reply_text("⏰ <b>ᴛɪᴍᴇᴏᴜᴛ: ɴᴏ ʀᴇsᴘᴏɴsᴇ ʀᴇᴄᴇɪᴠᴇᴅ. ғᴏʀᴡᴀʀᴅɪɴɢ ᴄᴀɴᴄᴇʟʟᴇᴅ.</b>", reply_markup=ReplyKeyboardRemove())

    answer_from = (fromid.text or "").strip() if fromid else ""
    if answer_from and answer_from.lower().startswith(('/', 'cancel')):
        return await message.reply(Translation.CANCEL, reply_markup=ReplyKeyboardRemove())

    detected_ranges = None
    res = {}
    chat_id = None
    last_msg_id = None
    title = "Source"

    from plugins.forward_parser import extract_requested_chat
    shared_src_id, shared_src_title = extract_requested_chat(fromid)
    if shared_src_id:
        chat_id = shared_src_id
        title = shared_src_title or "Source"
        try:
            async for probe_m in bot.get_chat_history(chat_id, limit=1):
                last_msg_id = probe_m.id
                break
        except Exception:
            pass

        if not last_msg_id:
            try:
                range_ask = await bot.ask(
                    message.chat.id,
                    f"✅ <b><u>sᴏᴜʀᴄᴇ ᴄʜᴏsᴇɴ:</u></b> <code>{title}</code>\n\n"
                    f"<i>ᴘʟᴇᴀsᴇ sᴇɴᴅ ᴛʜᴇ <b>ᴍᴇssᴀɢᴇ ʀᴀɴɢᴇ</b> (ᴇ.ɢ. <code>1-100</code>), ᴀ <b>ᴍᴇssᴀɢᴇ ʟɪɴᴋ</b>, ᴏʀ ᴛʜᴇ <b>ʟᴀsᴛ ᴍᴇssᴀɢᴇ ɪᴅ</b>:</i>\n\n"
                    f"/cancel - ᴄᴀɴᴄᴇʟ",
                    reply_markup=ReplyKeyboardRemove(),
                    timeout=180
                )
            except Exception:
                return await message.reply_text("⏰ <b>ᴛɪᴍᴇᴏᴜᴛ: ɴᴏ ʀᴇsᴘᴏɴsᴇ ʀᴇᴄᴇɪᴠᴇᴅ. ғᴏʀᴡᴀʀᴅɪɴɢ ᴄᴀɴᴄᴇʟʟᴇᴅ.</b>")
            if not range_ask or not range_ask.text or range_ask.text.lower().startswith(('/', 'cancel')):
                return await message.reply(Translation.CANCEL)

            r_text = range_ask.text.strip()
            p_c, p_r = parse_multi_ranges(r_text)
            if p_r:
                detected_ranges = p_r
                skip_count = p_r[0][0]
                last_msg_id = p_r[-1][1]
            elif r_text.isdigit():
                last_msg_id = int(r_text)
            else:
                from plugins.forward_parser import resolve_channel_input
                res = await resolve_channel_input(range_ask, bot)
                if res.get("last_msg_id"):
                    last_msg_id = res["last_msg_id"]
                else:
                    return await message.reply("❌ Invalid range or message link specified.", reply_markup=ReplyKeyboardRemove())
    elif fromid.text and not fromid.forward_date and not getattr(fromid, "forward_origin", None):
        try:
            p_chat, p_ranges = parse_multi_ranges(fromid.text)
            if p_chat and p_ranges and (len(p_ranges) > 1 or p_ranges[0][0] != p_ranges[0][1]):
                chat_id = p_chat
                detected_ranges = p_ranges
                last_msg_id = p_ranges[-1][1]
                skip_count = p_ranges[0][0]
            else:
                from plugins.forward_parser import resolve_channel_input
                res = await resolve_channel_input(fromid, bot)
                if not res.get("chat_id") or not res.get("last_msg_id"):
                    return await message.reply('Invalid link specified.', reply_markup=ReplyKeyboardRemove())
                chat_id = res["chat_id"]
                last_msg_id = res["last_msg_id"]
        except Exception:
            from plugins.forward_parser import resolve_channel_input
            res = await resolve_channel_input(fromid, bot)
            if not res.get("chat_id") or not res.get("last_msg_id"):
                return await message.reply('Invalid link specified.', reply_markup=ReplyKeyboardRemove())
            chat_id = res["chat_id"]
            last_msg_id = res["last_msg_id"]
    else:
        from plugins.forward_parser import resolve_channel_input
        res = await resolve_channel_input(fromid, bot)
        if not res.get("chat_id"):
            return await message.reply_text(f"❌ **Invalid source message!** {res.get('error', 'Please forward a message from a channel or send a message link.')}", reply_markup=ReplyKeyboardRemove())
        chat_id = res["chat_id"]
        last_msg_id = res.get("last_msg_id")
        if last_msg_id is None:
            return await message.reply_text("**This forwarded message has no message ID. Please send the direct message link instead.**", reply_markup=ReplyKeyboardRemove())

    is_source_private = False
    try:
        src_chat = await bot.get_chat(chat_id)
        if src_chat:
            if getattr(src_chat, "title", None):
                title = src_chat.title
            is_source_private = False
    except (PrivateChat, ChannelPrivate, ChannelInvalid, ChatAdminRequired):
        is_source_private = True
        title = res.get("chat_title") or title
    except (UsernameInvalid, UsernameNotModified):
        return await message.reply('Invalid Link specified.', reply_markup=ReplyKeyboardRemove())
    except Exception:
        is_source_private = True
        title = res.get("chat_title") or title

    if is_source_private:
        if _userbot:
            active_worker = _userbot
        else:
            add_ub_btn = InlineKeyboardMarkup([
                [InlineKeyboardButton("➕ ᴀᴅᴅ ᴜsᴇʀʙᴏᴛ", callback_data="settings#adduserbot")],
                [InlineKeyboardButton("🔑 ʟᴏɢɪɴ ᴠɪᴀ ᴏᴛᴘ", callback_data="settings#addlogin")],
                [InlineKeyboardButton("❌ ᴄʟᴏsᴇ", callback_data="close_btn")]
            ])
            return await message.reply_text(
                f"<blockquote><b>⚠️ <u>ᴜsᴇʀʙᴏᴛ ʀᴇǫᴜɪʀᴇᴅ ғᴏʀ ᴘʀɪᴠᴀᴛᴇ ᴄʜᴀɴɴᴇʟ</u></b></blockquote>\n\n"
                f"📡 <b>sᴏᴜʀᴄᴇ:</b> <code>{title}</code> (<code>{chat_id}</code>)\n\n"
                f"ᴛʜɪs ɪs ᴀ <b>ᴘʀɪᴠᴀᴛᴇ ᴄʜᴀɴɴᴇʟ</b>. ᴛᴇʟᴇɢʀᴀᴍ ʙᴏᴛ ᴛᴏᴋᴇɴs ᴄᴀɴɴᴏᴛ ʀᴇᴀᴅ ᴘʀɪᴠᴀᴛᴇ ᴄʜᴀɴɴᴇʟs ᴜɴʟᴇss ᴛʜᴇʏ ᴀʀᴇ ᴀᴅᴍɪɴs.\n\n"
                f"👉 <b>ᴘʟᴇᴀsᴇ ᴄᴏɴɴᴇᴄᴛ ʏᴏᴜʀ ᴜsᴇʀʙᴏᴛ sᴇssɪᴏɴ</b> (ʏᴏᴜʀ ᴛᴇʟᴇɢʀᴀᴍ ᴀᴄᴄᴏᴜɴᴛ ᴛʜᴀᴛ ʜᴀs ᴊᴏɪɴᴇᴅ ᴛʜɪs ᴄʜᴀɴɴᴇʟ) ᴠɪᴀ ᴛʜᴇ ʙᴜᴛᴛᴏɴs ʙᴇʟᴏᴡ ᴛᴏ ᴄᴏɴᴛɪɴᴜᴇ:",
                reply_markup=add_ub_btn
            )
    else:
        active_worker = _userbot or _custom_bot

    worker_name_display = f"👤 <b>ᴜsᴇʀʙᴏᴛ:</b> <code>{active_worker['name']}</code>" if not active_worker.get('is_bot') else f"🤖 <b>ʙᴏᴛ:</b> <code>{active_worker['name']}</code> (@{active_worker.get('username', '?')})"
    worker_label = active_worker['name'] if not active_worker.get('is_bot') else f"{active_worker['name']} (@{active_worker.get('username', '?')})"

    if detected_ranges:
        total_msgs = calculate_total_messages(detected_ranges)
        summary_str = format_ranges_summary(detected_ranges)
        forward_id = f"{user_id}-{fromid.id}"
        reply_markup = markup(
            row(
                btn('✅ ʏᴇs, sᴛᴀʀᴛ', f"start_public_{forward_id}", "green"),
                btn('❌ ɴᴏ, ᴄᴀɴᴄᴇʟ', "close_btn", "red")
            )
        )
        await message.reply_text(
            text=f"⚡ <b><u>ᴍᴜʟᴛɪ-ʀᴀɴɢᴇ ғᴏʀᴡᴀʀᴅ</u></b>\n\n"
                 f"{worker_name_display}\n"
                 f"📡 <b>ғʀᴏᴍ:</b> <code>{title}</code>\n"
                 f"🎯 <b>ᴛᴏ:</b> <code>{to_title}</code>\n"
                 f"📑 <b>ʀᴀɴɢᴇs:</b> <code>{summary_str}</code>\n"
                 f"📦 <b>ᴛᴏᴛᴀʟ ᴍᴇssᴀɢᴇs:</b> <code>{total_msgs}</code>\n\n"
                 f"<i>ᴅᴏ ʏᴏᴜ ᴡᴀɴᴛ ᴛᴏ sᴛᴀʀᴛ ғᴏʀᴡᴀʀᴅɪɴɢ ᴛʜᴇsᴇ ʀᴀɴɢᴇs?</i>",
            disable_web_page_preview=True,
            reply_markup=reply_markup
        )
        STS(forward_id).store(chat_id, toid, skip=skip_count, limit=last_msg_id, ranges=detected_ranges, worker=active_worker)
        return

    src_confirm_prompt = (
        f"<blockquote>📡 <b><u>sᴏᴜʀᴄᴇ ᴄʜᴀɴɴᴇʟ ᴄᴏɴғɪʀᴍᴇᴅ</u></b></blockquote>\n\n"
        f"📥 <b>sᴏᴜʀᴄᴇ (ғʀᴏᴍ):</b> <code>{title}</code>\n"
        f"🆔 <b>ᴄʜᴀᴛ ɪᴅ:</b> <code>{chat_id}</code>\n"
        f"🔢 <b>ʟᴀsᴛ ᴍsɢ ɪᴅ:</b> <code>{last_msg_id or 'Auto'}</code>\n"
        f"📤 <b>ᴛᴀʀɢᴇᴛ (ᴛᴏ):</b> <code>{to_title}</code> (<code>{toid}</code>)\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👉 <b>ɴᴏᴡ sᴇɴᴅ ɴᴜᴍʙᴇʀ ᴏғ ᴍᴇssᴀɢᴇs ᴛᴏ sᴋɪᴘ (ᴏғғsᴇᴛ):</b>\n"
        f"<i>(Send <code>0</code> to forward all messages from the beginning)</i>\n\n"
        f"/cancel - Cancel this process"
    )
    try:
        skipno = await bot.ask(message.chat.id, src_confirm_prompt, timeout=180)
    except Exception:
        return await message.reply_text("⏰ <b>ᴛɪᴍᴇᴏᴜᴛ: ɴᴏ ʀᴇsᴘᴏɴsᴇ ʀᴇᴄᴇɪᴠᴇᴅ. ғᴏʀᴡᴀʀᴅɪɴɢ ᴄᴀɴᴄᴇʟʟᴇᴅ.</b>")
    if not skipno or not skipno.text or skipno.text.lower().startswith(('/', 'cancel')):
        await message.reply(Translation.CANCEL)
        return
    skip_val = skipno.text.strip()
    if not skip_val.isdigit():
        await message.reply("Invalid number! Please enter digits only.")
        return
    skip_count = int(skip_val)
    forward_id = f"{user_id}-{skipno.id}"
    reply_markup = markup(
        row(
            btn('✅ ʏᴇs, sᴛᴀʀᴛ', f"start_public_{forward_id}", "green"),
            btn('❌ ɴᴏ, ᴄᴀɴᴄᴇʟ', "close_btn", "red")
        )
    )
    double_check_txt = (
        f"<blockquote>📋 <b><u>ғᴏʀᴡᴀʀᴅ ᴛᴀsᴋ ᴠᴇʀɪғɪᴄᴀᴛɪᴏɴ</u></b></blockquote>\n\n"
        f"<b>Please review your forward task before proceeding:</b>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📥 <b>sᴏᴜʀᴄᴇ (ғʀᴏᴍ):</b> <code>{title}</code> (<code>{chat_id}</code>)\n"
        f"📤 <b>ᴛᴀʀɢᴇᴛ (ᴛᴏ):</b> <code>{to_title}</code> (<code>{toid}</code>)\n"
        f"🤖 <b>ᴀᴄᴛɪᴠᴇ ᴡᴏʀᴋᴇʀ:</b> <code>{worker_label}</code>\n"
        f"⏩ <b>sᴋɪᴘ ᴏғғsᴇᴛ:</b> <code>{skip_count} messages</code>\n"
        f"🔢 <b>ʟᴀsᴛ ᴍsɢ ɪᴅ:</b> <code>{last_msg_id or 'Auto'}</code>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"⚠️ <i>Ensure <code>{worker_label}</code> is an Admin with post permissions in Target (<code>{to_title}</code>)!</i>\n\n"
        f"👇 <b>Tap below to begin forwarding:</b>"
    )
    await message.reply_text(
        text=double_check_txt,
        disable_web_page_preview=True,
        reply_markup=reply_markup
    )
    STS(forward_id).store(chat_id, toid, skip_count, int(last_msg_id) if last_msg_id else 0, worker=active_worker) 