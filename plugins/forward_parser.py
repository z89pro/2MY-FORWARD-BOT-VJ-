"""
plugins/forward_parser.py — Universal Forward Message & Channel ID Parsing Engine
Accurately extracts channel/chat IDs, message IDs, titles, usernames, and types
across Pyrogram v1/v2 (forward_from_chat, forward_origin, forward_from, sender_chat).
"""
import re
import asyncio
import logging
from datetime import datetime, timezone
from pyrogram import Client, enums
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import RPCError, ChannelPrivate, ChatAdminRequired, PeerIdInvalid
from buttons import markup, row, btn
from database import db
from config import Config

logger = logging.getLogger("ForwardParser")

LINK_REGEX = re.compile(
    r"(?:https?://)?(?:t\.me|telegram\.me|telegram\.dog)/(?:c/(\d+)|([a-zA-Z0-9_]{4,}))/(\d+)/?",
    re.IGNORECASE
)

CHANNEL_LINK_REGEX = re.compile(
    r"(?:https?://)?(?:t\.me|telegram\.me|telegram\.dog)/(?:joinchat/|c/(\d+)|([a-zA-Z0-9_]{4,}))/?",
    re.IGNORECASE
)


def extract_forward_info(message: Message) -> dict:
    """
    Robustly extracts forward metadata across classic Pyrogram flat fields
    (forward_from_chat, forward_from, forward_from_message_id, forward_date),
    Pyrogram v2 / Bot API 7.0+ MessageOrigin objects (forward_origin),
    and anonymous sender_chat.
    """
    if not message:
        return {"is_forward": False}

    info = {
        "is_forward": False,
        "chat_id": None,
        "chat_title": "Unknown",
        "chat_username": None,
        "chat_type": "unknown",
        "message_id": None,
        "forward_date": None,
        "forward_date_str": "",
        "sender_id": None,
        "sender_name": None,
        "sender_username": None,
        "sender_is_bot": False,
        "author_signature": None,
        "link": None,
        "origin_type": None,
    }

    # 1. Inspect message.forward_origin (Pyrogram v2+ / MTProto MessageOrigin)
    origin = getattr(message, "forward_origin", None)
    if origin is not None:
        info["is_forward"] = True
        info["forward_date"] = getattr(origin, "date", None)
        origin_type_val = getattr(origin, "type", None)
        info["origin_type"] = str(origin_type_val).split(".")[-1].lower() if origin_type_val else "unknown"

        # Case A: MessageOriginChannel
        if hasattr(origin, "chat") and origin.chat:
            chat = origin.chat
            info["chat_id"] = getattr(chat, "id", None)
            info["chat_title"] = getattr(chat, "title", None) or getattr(chat, "first_name", "Channel")
            info["chat_username"] = getattr(chat, "username", None)
            ctype = getattr(chat, "type", None)
            info["chat_type"] = str(ctype).split(".")[-1].lower() if ctype else "channel"
            info["message_id"] = getattr(origin, "message_id", None)
            info["author_signature"] = getattr(origin, "author_signature", None)

        # Case B: MessageOriginChat
        elif hasattr(origin, "sender_chat") and origin.sender_chat:
            chat = origin.sender_chat
            info["chat_id"] = getattr(chat, "id", None)
            info["chat_title"] = getattr(chat, "title", "Group")
            info["chat_username"] = getattr(chat, "username", None)
            ctype = getattr(chat, "type", None)
            info["chat_type"] = str(ctype).split(".")[-1].lower() if ctype else "supergroup"
            info["author_signature"] = getattr(origin, "author_signature", None)

        # Case C: MessageOriginUser
        elif hasattr(origin, "sender_user") and origin.sender_user:
            user = origin.sender_user
            info["sender_id"] = getattr(user, "id", None)
            fname = getattr(user, "first_name", "") or ""
            lname = getattr(user, "last_name", "") or ""
            info["sender_name"] = f"{fname} {lname}".strip() or "User"
            info["sender_username"] = getattr(user, "username", None)
            info["sender_is_bot"] = getattr(user, "is_bot", False)
            info["chat_type"] = "bot" if info["sender_is_bot"] else "user"
            info["chat_title"] = info["sender_name"]
            info["chat_id"] = info["sender_id"]

        # Case D: MessageOriginHiddenUser
        elif hasattr(origin, "sender_user_name"):
            info["sender_name"] = getattr(origin, "sender_user_name", "Hidden User")
            info["chat_title"] = info["sender_name"]
            info["chat_type"] = "hidden_user"

    # 2. Inspect classic Pyrogram forward fields
    fwd_chat = getattr(message, "forward_from_chat", None)
    if fwd_chat:
        info["is_forward"] = True
        info["chat_id"] = getattr(fwd_chat, "id", None) or info["chat_id"]
        info["chat_title"] = getattr(fwd_chat, "title", None) or info["chat_title"]
        info["chat_username"] = getattr(fwd_chat, "username", None) or info["chat_username"]
        ctype = getattr(fwd_chat, "type", None)
        if ctype:
            info["chat_type"] = str(ctype).split(".")[-1].lower()
        if not info["message_id"]:
            info["message_id"] = getattr(message, "forward_from_message_id", None)
        if not info["origin_type"]:
            info["origin_type"] = "channel"

    fwd_user = getattr(message, "forward_from", None)
    if fwd_user:
        info["is_forward"] = True
        info["sender_id"] = getattr(fwd_user, "id", None) or info["sender_id"]
        fname = getattr(fwd_user, "first_name", "") or ""
        lname = getattr(fwd_user, "last_name", "") or ""
        sname = f"{fname} {lname}".strip() or "User"
        info["sender_name"] = sname
        info["sender_username"] = getattr(fwd_user, "username", None) or info["sender_username"]
        info["sender_is_bot"] = getattr(fwd_user, "is_bot", False)
        if not info["chat_id"] and info["sender_id"]:
            info["chat_id"] = info["sender_id"]
            info["chat_title"] = info["sender_name"]
            info["chat_type"] = "bot" if info["sender_is_bot"] else "user"

    fwd_sender_name = getattr(message, "forward_sender_name", None)
    if fwd_sender_name:
        info["is_forward"] = True
        if not info["sender_name"]:
            info["sender_name"] = fwd_sender_name
        if not info["chat_title"] or info["chat_title"] == "Unknown":
            info["chat_title"] = fwd_sender_name
            info["chat_type"] = "hidden_user"

    if getattr(message, "forward_date", None):
        info["is_forward"] = True
        if not info["forward_date"]:
            info["forward_date"] = message.forward_date

    # 3. Inspect sender_chat (e.g. channel broadcast or anonymous admin in supergroup)
    sender_chat = getattr(message, "sender_chat", None)
    if sender_chat and not info["chat_id"]:
        info["chat_id"] = getattr(sender_chat, "id", None)
        info["chat_title"] = getattr(sender_chat, "title", "Channel")
        info["chat_username"] = getattr(sender_chat, "username", None)
        ctype = getattr(sender_chat, "type", None)
        if ctype:
            info["chat_type"] = str(ctype).split(".")[-1].lower()

    # Format forward date string
    if info["forward_date"]:
        try:
            if isinstance(info["forward_date"], (int, float)):
                dt = datetime.fromtimestamp(info["forward_date"], tz=timezone.utc)
                info["forward_date_str"] = dt.strftime("%Y-%m-%d %H:%M:%S UTC")
            elif hasattr(info["forward_date"], "strftime"):
                info["forward_date_str"] = info["forward_date"].strftime("%Y-%m-%d %H:%M:%S UTC")
        except Exception:
            info["forward_date_str"] = str(info["forward_date"])

    # 4. Construct direct Telegram link
    cid = info["chat_id"]
    mid = info["message_id"]
    u = info["chat_username"]
    if u and mid:
        info["link"] = f"https://t.me/{u}/{mid}"
    elif u:
        info["link"] = f"https://t.me/{u}"
    elif cid and mid:
        clean_cid = str(cid)
        if clean_cid.startswith("-100"):
            clean_cid = clean_cid[4:]
        elif clean_cid.startswith("-"):
            clean_cid = clean_cid[1:]
        info["link"] = f"https://t.me/c/{clean_cid}/{mid}"

    return info


def extract_requested_chat(message: Message):
    """Safely extracts (chat_id, chat_title) from a native Telegram request_chat button message."""
    if not message:
        return None, None
    cid = None
    title = None
    chats_shared = getattr(message, "chats_shared", None)
    if chats_shared and getattr(chats_shared, "chats", None):
        rc = chats_shared.chats[0]
        cid = rc.chat_id
        title = getattr(rc, "title", None) or getattr(rc, "name", None) or "Channel"
    else:
        chat_shared = getattr(message, "chat_shared", None)
        if chat_shared:
            cid = getattr(chat_shared, "chat_id", None)
            title = getattr(chat_shared, "title", None) or getattr(chat_shared, "name", None) or "Channel"

    if cid is not None:
        try:
            cid_int = int(cid)
            if cid_int > 0 and not str(cid_int).startswith("-100"):
                cid = int(f"-100{cid_int}")
            else:
                cid = cid_int
        except Exception:
            pass
        return cid, title
    return None, None


async def resolve_channel_input(input_obj, bot: Client = None, verify_access: bool = False) -> dict:
    """
    Universal channel input resolver across the entire bot.
    Seamlessly extracts and verifies channel/group targets from:
    1. Forwarded messages (forward_from_chat, forward_origin, sender_chat)
    2. Native Telegram RequestPeer button messages (chats_shared)
    3. Direct message links (t.me/c/12345/67, t.me/mychannel/67)
    4. Channel username links or @handles (@mychannel, https://t.me/mychannel)
    5. Raw numeric channel IDs (-1001234567890, 1234567890)
    """
    res = {
        "chat_id": None,
        "chat_title": "Channel",
        "chat_username": None,
        "last_msg_id": None,
        "chat_type": "channel",
        "link": None,
        "is_forward": False,
        "peer_invalid": False,
        "error": None
    }

    if input_obj is None:
        res["error"] = "Empty input provided."
        return res

    # 1. If input is a Message object, check native RequestPeer shared chat or forward headers
    if isinstance(input_obj, Message):
        req_id, req_title = extract_requested_chat(input_obj)
        if req_id:
            res["chat_id"] = req_id
            res["chat_title"] = req_title
            res["chat_type"] = "channel"
            res["is_forward"] = False
            return res

        fwd_info = extract_forward_info(input_obj)
        if fwd_info.get("is_forward") and fwd_info.get("chat_id"):
            res["chat_id"] = fwd_info["chat_id"]
            res["chat_title"] = fwd_info.get("chat_title") or "Channel"
            res["chat_username"] = fwd_info.get("chat_username")
            res["last_msg_id"] = fwd_info.get("message_id")
            res["chat_type"] = fwd_info.get("chat_type") or "channel"
            res["link"] = fwd_info.get("link")
            res["is_forward"] = True
            return res

    # 2. Parse text or caption if no forward headers found
    raw_text = ""
    if isinstance(input_obj, (int, float)):
        raw_text = str(int(input_obj))
    elif isinstance(input_obj, str):
        raw_text = input_obj.strip()
    elif isinstance(input_obj, Message):
        raw_text = (input_obj.text or input_obj.caption or "").strip()

    if not raw_text:
        res["error"] = "No message text or forward headers detected."
        return res

    # Check for direct message link: t.me/c/12345/67 or t.me/channel/67
    link_match = LINK_REGEX.search(raw_text.replace("?single", "").strip())
    if link_match:
        c_num = link_match.group(1)
        c_user = link_match.group(2)
        mid = int(link_match.group(3))
        res["last_msg_id"] = mid
        if c_num:
            res["chat_id"] = int(f"-100{c_num}")
            res["link"] = f"https://t.me/c/{c_num}/{mid}"
        elif c_user:
            res["chat_id"] = c_user
            res["chat_username"] = c_user
            res["link"] = f"https://t.me/{c_user}/{mid}"
    else:
        # Check for channel username link or raw username: @channel or t.me/channel
        chan_match = CHANNEL_LINK_REGEX.search(raw_text.strip())
        if chan_match:
            c_num = chan_match.group(1)
            c_user = chan_match.group(2)
            if c_num:
                res["chat_id"] = int(f"-100{c_num}")
            elif c_user:
                res["chat_id"] = c_user
                res["chat_username"] = c_user
        elif raw_text.startswith("@"):
            uname = raw_text.lstrip("@").strip()
            res["chat_id"] = uname
            res["chat_username"] = uname
        elif re.match(r"^-?\d+$", raw_text):
            val = int(raw_text)
            if str(val).startswith("-100"):
                res["chat_id"] = val
            elif val > 0:
                res["chat_id"] = int(f"-100{val}")
            else:
                body = raw_text.lstrip("-")
                res["chat_id"] = -int(f"100{body}")

    if not res["chat_id"]:
        res["error"] = "Could not parse channel ID, username, or message link from input."
        return res

    # 3. If bot client is available, attempt to enrich title and canonical numeric ID safely
    if bot:
        try:
            chat_obj = await bot.get_chat(res["chat_id"])
            if chat_obj:
                res["chat_id"] = chat_obj.id
                res["chat_title"] = chat_obj.title or chat_obj.first_name or res["chat_title"]
                res["chat_username"] = chat_obj.username or res["chat_username"]
                if hasattr(chat_obj, "type"):
                    res["chat_type"] = str(chat_obj.type).split(".")[-1].lower()
        except PeerIdInvalid:
            res["peer_invalid"] = True
            if verify_access:
                res["error"] = (
                    "<b>⚠️ ᴘᴇᴇʀ ɪᴅ ɪɴᴠᴀʟɪᴅ:</b> ᴛʜᴇ ʙᴏᴛ ɪs ɴᴏᴛ ᴀɴ ᴀᴅᴍɪɴɪsᴛʀᴀᴛᴏʀ ɪɴ ᴛʜɪs ᴄʜᴀɴɴᴇʟ!\n\n"
                    "👉 <b>sᴏʟᴜᴛɪᴏɴ:</b>\n"
                    "1. ᴀᴅᴅ ᴛʜɪs ʙᴏᴛ ᴛᴏ ʏᴏᴜʀ ᴄʜᴀɴɴᴇʟ ᴀs ᴀɴ <b>ᴀᴅᴍɪɴɪsᴛʀᴀᴛᴏʀ</b> (ᴡɪᴛʜ 'ᴘᴏsᴛ ᴍᴇssᴀɢᴇs' ᴘᴇʀᴍɪssɪᴏɴ).\n"
                    "2. sᴇɴᴅ ᴀɴʏ ᴛᴇsᴛ ᴍᴇssᴀɢᴇ ɪɴ ᴛʜᴀᴛ ᴄʜᴀɴɴᴇʟ.\n"
                    "3. <b>ғᴏʀᴡᴀʀᴅ</b> ᴛʜᴀᴛ ᴍᴇssᴀɢᴇ ʜᴇʀᴇ ᴛᴏ sᴇᴛ ɪᴛ ɪɴsᴛᴀɴᴛʟʏ!"
                )
        except (ChannelPrivate, ChatAdminRequired) as e:
            if verify_access:
                res["error"] = f"<b>⚠️ ᴀᴄᴄᴇss ᴅᴇɴɪᴇᴅ:</b> ʙᴏᴛ ᴄᴀɴɴᴏᴛ ᴀᴄᴄᴇss ᴛʜɪs ᴄʜᴀɴɴᴇʟ ({type(e).__name__}). ᴍᴀᴋᴇ sᴜʀᴇ ᴛʜᴇ ʙᴏᴛ ɪs ᴀɴ ᴀᴅᴍɪɴ!"
        except RPCError as e:
            if verify_access:
                res["error"] = f"<b>⚠️ ᴛᴇʟᴇɢʀᴀᴍ ᴇʀʀᴏʀ:</b> {e}"
        except Exception as e:
            logger.debug("Could not enrich chat metadata for %s: %s", res["chat_id"], e)

    return res



def format_forward_card(info: dict, user_id: int = None) -> tuple:
    """
    Builds an interactive Telegram card formatted in Unicode Small Caps
    with clickable channel ID and actionable inline buttons.
    """
    chat_id = info.get("chat_id")
    msg_id = info.get("message_id")
    title = info.get("chat_title") or "Unknown"
    ctype = (info.get("chat_type") or "channel").upper()
    link = info.get("link")
    username = info.get("chat_username")
    date_str = info.get("forward_date_str")
    sender_name = info.get("sender_name")

    lines = [
        "<blockquote><b>📡 <u>ᴄʜᴀɴɴᴇʟ ɪɴғᴏʀᴍᴀᴛɪᴏɴ ᴇxᴛʀᴀᴄᴛᴇᴅ</u></b></blockquote>\n",
        f"📢 <b>ᴛɪᴛʟᴇ:</b> <code>{title}</code>",
    ]

    if chat_id:
        lines.append(f"🆔 <b>ᴄʜᴀɴɴᴇʟ ɪᴅ:</b> <code>{chat_id}</code>  <i>(ᴛᴀᴘ ᴛᴏ ᴄᴏᴘʏ)</i>")
    if msg_id:
        lines.append(f"🔢 <b>ᴍᴇssᴀɢᴇ ɪᴅ:</b> <code>{msg_id}</code>")
    if ctype:
        lines.append(f"🏷 <b>ᴛʏᴘᴇ:</b> <code>{ctype}</code>")
    if username:
        lines.append(f"👤 <b>ᴜsᴇʀɴᴀᴍᴇ:</b> @{username}")
    if link:
        lines.append(f"🔗 <b>ᴅɪʀᴇᴄᴛ ʟɪɴᴋ:</b> <a href=\"{link}\">{link}</a>")
    if sender_name and sender_name != title:
        lines.append(f"👤 <b>ᴏʀɪɢɪɴᴀʟ sᴇɴᴅᴇʀ:</b> <code>{sender_name}</code>")
    if date_str:
        lines.append(f"📅 <b>ғᴏʀᴡᴀʀᴅ ᴅᴀᴛᴇ:</b> <code>{date_str}</code>")

    lines.append("\n━━━━━━━━━━━━━━━━━━━━━")
    lines.append("<i>ᴄʜᴏᴏsᴇ ᴀɴ ᴀᴄᴛɪᴏɴ ʙᴇʟᴏᴡ ᴛᴏ ᴜsᴇ ᴛʜɪs ᴄʜᴀɴɴᴇʟ:</i>")

    card_text = "\n".join(lines)

    rows = []
    is_admin = bool(user_id and (user_id in Config.BOT_OWNER_ID))

    if chat_id:
        r1 = [btn("📥 ᴀᴅᴅ ᴛᴏ ᴛᴀʀɢᴇᴛs", f"fwd_add_{chat_id}", "green")]
        if msg_id:
            r1.append(btn("⚡ ғᴏʀᴡᴀʀᴅ ғʀᴏᴍ ʜᴇʀᴇ", f"fwd_start_{chat_id}_{msg_id}", "blue"))
        rows.append(row(*r1))

        r2 = [
            btn("🧹 ᴅᴜᴘʟɪᴄᴀᴛᴇ ᴄʟᴇᴀɴᴇʀ", f"fwd_clean_{chat_id}", "yellow"),
            btn("📋 ᴄᴏᴘʏ ɪᴅ", f"fwd_copy_{chat_id}", "blue")
        ]
        rows.append(row(*r2))

        # Admin controls: 1-click set as Dump Channel or Log Channel
        if is_admin:
            r_adm = [
                btn("📦 sᴇᴛ ᴀs ᴅᴜᴍᴘ", f"fwd_dump_{chat_id}", "yellow"),
                btn("📡 sᴇᴛ ᴀs ʟᴏɢ", f"fwd_log_{chat_id}", "blue")
            ]
            rows.append(row(*r_adm))

    elif info.get("sender_id"):
        sid = info["sender_id"]
        rows.append(row(btn("📋 ᴄᴏᴘʏ ᴜsᴇʀ ɪᴅ", f"fwd_copy_{sid}", "blue")))

    rows.append(row(btn("❌ ᴄʟᴏsᴇ", "close_btn", "red")))

    return card_text, markup(*rows)
