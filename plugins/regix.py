import os
import re
import sys 
import html
import math
import time
import random
import datetime
import asyncio
import logging
from .utils import STS
from database import db 
from .test import CLIENT , start_clone_bot

def human_delay(base: float) -> float:
    """Add ±30% random jitter to mimic human timing (reference from Fast-Forward-bot)"""
    jitter = base * 0.3
    return max(0.1, base + random.uniform(-jitter, jitter))

from config import Config, temp
from translation import Translation
from pyrogram import Client, filters 
from pyrogram.errors import FloodWait, MessageNotModified, RPCError
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery, Message 
from buttons import colored_markup 

CLIENT = CLIENT()
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
TEXT = Translation.TEXT

@Client.on_callback_query(filters.regex(r'^start_public'))
async def pub_(bot, message):
    try:
        await message.answer()
    except Exception:
        pass
    user = message.from_user.id
    from plugins.verify import is_user_verified, send_verify_prompt
    if not await is_user_verified(user):
        await message.answer("⚠️ ᴠᴇʀɪғɪᴄᴀᴛɪᴏɴ ʀᴇǫᴜɪʀᴇᴅ! ᴘʟᴇᴀsᴇ ᴄᴏᴍᴘʟᴇᴛᴇ ᴠᴇʀɪғɪᴄᴀᴛɪᴏɴ.", show_alert=True)
        return await send_verify_prompt(bot, message.message, user)
    frwd_id = message.data.split("_")[2]
    if temp.lock.get(user) and str(temp.lock.get(user))=="True":
      return await message.answer("ᴘʟᴇᴀsᴇ ᴡᴀɪᴛ ᴜɴᴛɪʟʟ ᴘʀᴇᴠɪᴏᴜs ᴛᴀsᴋ ᴄᴏᴍᴘʟᴇᴛᴇᴅ.", show_alert=True)
    # Claim the lock here rather than in execute_forward_task: several awaits
    # sit between the guard above and that assignment, so a double-tap would
    # pass both checks and run two forwards over the same range. pub_ awaits the
    # whole task, so clearing it in the finally below is enough.
    temp.lock[user] = True
    # Cleared only after the lock is held. Doing it at the top meant a second
    # tap on a stale button wiped a *running* task's cancel flag, so /stop did
    # nothing.
    temp.CANCEL[user] = False
    try:
        sts = STS(frwd_id)
        if not sts.verify():
          await message.answer("ʏᴏᴜ ᴀʀᴇ ᴄʟɪᴄᴋɪɴɢ ᴏɴ ᴍʏ ᴏɴᴇ ᴏғ ᴏʟᴅ ʙᴜᴛᴛᴏɴ.", show_alert=True)
          return await message.message.delete()
        sts.data[sts.id]['user_id'] = user
        temp.PAUSE[user] = False
        i = sts.get(full=True)
        if i.TO in temp.IS_FRWD_CHAT:
          return await message.answer("ɪɴ ᴛᴀʀɢᴇᴛ ᴄʜᴀᴛ ᴛᴀsᴋ ɪs ɪɴ ᴘʀᴏɢʀᴇss. ᴘʟᴇᴀsᴇ ᴡᴀɪᴛ ᴜɴᴛɪʟʟ ᴘʀᴇᴠɪᴏᴜs ᴛᴀsᴋ ɪs ᴄᴏᴍᴘʟᴇᴛᴇᴅ.", show_alert=True)
        m = await msg_edit(message.message, "<i><b>vᴇʀɪғʏɪɴɢ ʏᴏᴜʀ ᴅᴀᴛᴀ ᴘʟᴇᴀsᴇ ᴡᴀɪᴛ.</b></i>")
        _bot, caption, forward_tag, data, protect, button = await sts.get_data(user)
        if not _bot:
          return await msg_edit(m, "<code>ʏᴏᴜ ᴅɪᴅ ɴᴏᴛ ᴀᴅᴅᴇᴅ ᴀɴʏ ʙᴏᴛ ʏᴇᴛ ᴜsᴇ /settings</code>", wait=True)
        try:
          client = await start_clone_bot(CLIENT.client(_bot))
        except Exception as e:  
          return await m.edit(e)
        await msg_edit(m, "<b>ᴘʀᴏᴄᴇssɪɴɢ..</b>")
        who = "ᴜsᴇʀʙᴏᴛ" if not _bot.get('is_bot') else "ʙᴏᴛ"

        # ── Source chat probe with automatic userbot fallback ──
        source_ok = False
        try:
           await client.get_chat(sts.get("FROM"))
           source_ok = True
        except FloodWait as e:
           await msg_edit(m, f"⏳ **ᴛᴇʟᴇɢʀᴀᴍ ʀᴀᴛᴇ ʟɪᴍɪᴛ — ᴡᴀɪᴛ <code>{e.value}s</code>, ᴛʜᴇɴ ᴛᴀᴘ ʀᴇᴛʀʏ.**", retry_btn(frwd_id), True)
           return await stop(client, user)
        except Exception as src_err:
           # Primary worker can't read source — try userbot fallback
           if _bot.get('is_bot'):
               _userbot = await db.get_userbot(user)
               if _userbot:
                   await msg_edit(m, "<b>🔄 ʙᴏᴛ ᴄᴀɴ'ᴛ ᴀᴄᴄᴇss sᴏᴜʀᴄᴇ — sᴡɪᴛᴄʜɪɴɢ ᴛᴏ ᴜsᴇʀʙᴏᴛ...</b>")
                   try:
                       await stop(client, user)
                   except Exception:
                       pass
                   try:
                       client = await start_clone_bot(CLIENT.client(_userbot))
                       await client.get_chat(sts.get("FROM"))
                       _bot = _userbot
                       who = "ᴜsᴇʀʙᴏᴛ"
                       source_ok = True
                       logger.info(f"User {user}: auto-switched to userbot for private source {sts.get('FROM')}")
                   except FloodWait as e:
                       await msg_edit(m, f"⏳ **ᴛᴇʟᴇɢʀᴀᴍ ʀᴀᴛᴇ ʟɪᴍɪᴛ — ᴡᴀɪᴛ <code>{e.value}s</code>, ᴛʜᴇɴ ᴛᴀᴘ ʀᴇᴛʀʏ.**", retry_btn(frwd_id), True)
                       return await stop(client, user)
                   except Exception as ub_err:
                       await msg_edit(m,
                          f"**❌ ᴜsᴇʀʙᴏᴛ ᴀʟsᴏ ᴄᴀɴ'ᴛ ʀᴇᴀᴅ ᴛʜᴇ sᴏᴜʀᴄᴇ ᴄʜᴀᴛ.**\n\n"
                          f"<b>ʙᴏᴛ ᴇʀʀᴏʀ:</b> <code>{type(src_err).__name__}: {src_err}</code>\n"
                          f"<b>ᴜsᴇʀʙᴏᴛ ᴇʀʀᴏʀ:</b> <code>{type(ub_err).__name__}: {ub_err}</code>\n\n"
                          f"<i>ᴍᴀᴋᴇ sᴜʀᴇ ʏᴏᴜʀ ᴜsᴇʀʙᴏᴛ ᴀᴄᴄᴏᴜɴᴛ ʜᴀs ᴊᴏɪɴᴇᴅ ᴛʜᴇ sᴏᴜʀᴄᴇ ᴄʜᴀɴɴᴇʟ.</i>**",
                          retry_btn(frwd_id), True)
                       return await stop(client, user)

           if not source_ok:
               # No userbot available or this IS the userbot and it failed
               add_ub_btn = InlineKeyboardMarkup([
                   [InlineKeyboardButton("➕ ᴀᴅᴅ ᴜsᴇʀʙᴏᴛ", callback_data="settings#adduserbot")],
                   [InlineKeyboardButton("🔑 ʟᴏɢɪɴ ᴠɪᴀ ᴏᴛᴘ", callback_data="settings#addlogin")],
                   [
                       InlineKeyboardButton("♻️ ʀᴇᴛʀʏ", callback_data=f"start_public_{frwd_id}"),
                       InlineKeyboardButton("❌ ᴄʟᴏsᴇ", callback_data="close_btn")
                   ]
               ])
               if who == "ᴜsᴇʀʙᴏᴛ":
                   worker_line = f"👤 <b>ᴡᴏʀᴋᴇʀ ᴜsᴇᴅ:</b> <code>ᴜsᴇʀʙᴏᴛ</code> ({_bot.get('name', 'UserBot')})"
                   fix_lines = (
                       f"• <b>ʏᴏᴜʀ ᴜsᴇʀʙᴏᴛ (<code>{_bot.get('name', 'UserBot')}</code>) ʜᴀs ɴᴏᴛ ᴊᴏɪɴᴇᴅ ᴛʜɪs ᴄʜᴀɴɴᴇʟ:</b>\n"
                       f"  ᴘʟᴇᴀsᴇ ᴊᴏɪɴ ᴛʜᴇ sᴏᴜʀᴄᴇ ᴄʜᴀɴɴᴇʟ ᴡɪᴛʜ ʏᴏᴜʀ ᴜsᴇʀʙᴏᴛ ᴛᴇʟᴇɢʀᴀᴍ ᴀᴄᴄᴏᴜɴᴛ ғɪʀsᴛ, ᴛʜᴇɴ ᴛᴀᴘ ʀᴇᴛʀʏ.\n"
                       f"• <b>ɪғ ɪᴛ's ʀᴇsᴛʀɪᴄᴛᴇᴅ:</b> ᴍᴀᴋᴇ sᴜʀᴇ ʏᴏᴜʀ ᴀᴄᴄᴏᴜɴᴛ ɪs ɴᴏᴛ ʀᴇsᴛʀɪᴄᴛᴇᴅ ᴏʀ ʙᴀɴɴᴇᴅ ɪɴ ᴛʜᴀᴛ ᴄʜᴀɴɴᴇʟ."
                   )
               else:
                   worker_line = f"🤖 <b>ᴡᴏʀᴋᴇʀ ᴜsᴇᴅ:</b> <code>ʙᴏᴛ</code> (@{_bot.get('username', '?')})"
                   fix_lines = (
                       f"• <b>ɪғ ɪᴛ's ᴀ ᴘʀɪᴠᴀᴛᴇ ᴄʜᴀɴɴᴇʟ:</b> ᴀᴅᴅ ᴀ <b>ᴜsᴇʀʙᴏᴛ</b> (ʏᴏᴜʀ ᴘᴇʀsᴏɴᴀʟ ᴀᴄᴄᴏᴜɴᴛ ᴛʜᴀᴛ ᴊᴏɪɴᴇᴅ ᴛʜᴇ ᴄʜᴀɴɴᴇʟ) ᴠɪᴀ ʙᴜᴛᴛᴏɴs ʙᴇʟᴏᴡ, ᴏʀ ᴀᴅᴅ <b>@{_bot.get('username', 'bot')}</b> ᴀs ᴀɴ ᴀᴅᴍɪɴ ɪɴ ᴛʜᴇ ᴄʜᴀɴɴᴇʟ.\n"
                       f"• <b>ɪғ ɪᴛ's ʀᴇsᴛʀɪᴄᴛᴇᴅ:</b> ᴀ ᴜsᴇʀʙᴏᴛ sᴇssɪᴏɴ ɪs ʀᴇǫᴜɪʀᴇᴅ ᴛᴏ ʙʏᴘᴀss ᴄᴏᴘʏ ᴘʀᴏᴛᴇᴄᴛɪᴏɴ."
                   )

               await msg_edit(m,
                  f"<blockquote><b>❌ <u>ᴄᴀɴ'ᴛ ʀᴇᴀᴅ ᴛʜᴇ sᴏᴜʀᴄᴇ ᴄʜᴀᴛ</u></b></blockquote>\n\n"
                  f"{worker_line}\n"
                  f"⚠️ <b>ᴇʀʀᴏʀ:</b> <code>{type(src_err).__name__}: {src_err}</code>\n\n"
                  f"💡 <b><u>ʜᴏᴡ ᴛᴏ ғɪx ᴛʜɪs:</u></b>\n"
                  f"{fix_lines}",
                  add_ub_btn, True)
               return await stop(client, user)

        # ── Target chat probe ──
        try:
           k = await client.send_message(i.TO, "Testing")
           await k.delete()
        except FloodWait as e:
           await msg_edit(m, f"⏳ **ᴛᴇʟᴇɢʀᴀᴍ ʀᴀᴛᴇ ʟɪᴍɪᴛ — ᴡᴀɪᴛ <code>{e.value}s</code>, ᴛʜᴇɴ ᴛᴀᴘ ʀᴇᴛʀʏ.**", retry_btn(frwd_id), True)
           return await stop(client, user)
        except Exception as e:
           await msg_edit(m,
              f"**❌ ᴄᴀɴ'ᴛ ᴘᴏsᴛ ɪɴ ᴛʜᴇ ᴛᴀʀɢᴇᴛ ᴄʜᴀɴɴᴇʟ.**\n\n"
              f"<b>ᴡᴏʀᴋᴇʀ ᴜsᴇᴅ:</b> <code>{who}</code> (@{_bot.get('username', '?')})\n"
              f"<b>ᴇʀʀᴏʀ:</b> <code>{type(e).__name__}: {e}</code>\n\n"
              f"<i>ᴍᴀᴋᴇ ᴛʜᴀᴛ ᴡᴏʀᴋᴇʀ ᴀɴ ᴀᴅᴍɪɴ ɪɴ ᴛʜᴇ ᴛᴀʀɢᴇᴛ ᴄʜᴀɴɴᴇʟ ᴡɪᴛʜ ᴘᴏsᴛ ᴘᴇʀᴍɪssɪᴏɴs.</i>**",
              retry_btn(frwd_id), True)
           return await stop(client, user)
        task_id = f"fwd_{user}_{frwd_id}"
        user_configs = await db.get_configs(user)
        return await execute_forward_task(
            client=client,
            user=user,
            m=m,
            sts=sts,
            task_id=task_id,
            _bot=_bot,
            caption=caption,
            forward_tag=forward_tag,
            protect=protect,
            button=button,
            user_configs=user_configs,
            is_resumed=False,
        )
    finally:
        temp.lock[user] = False


async def execute_forward_task(client, user, m, sts, task_id, _bot, caption, forward_tag, protect, button, user_configs, is_resumed=False):
    i = sts.get(full=True)
    temp.forwardings += 1
    await db.add_frwd(user)
    if not is_resumed:
        await send(client, user, "<b>🚥 ғᴏʀᴡᴀʀᴅɪɴɢ sᴛᴀʀᴛᴇᴅ</b>")
    sts.add(time=True)
    
    clean_caption = user_configs.get('clean_caption', False)
    replace_words = user_configs.get('replace_words', {})
    dump_target = await db.get_effective_dump_channel(user_id=user)
    upload_type = user_configs.get('upload_type', 'media')
    transfer_mode = str(user_configs.get('transfer_mode', 'auto')).lower()

    # ── Active Filter & Deduplication Configuration ──
    seen_unique_ids = set()
    seen_text_hashes = set()
    skip_duplicates = bool(user_configs.get('duplicate', True))

    cfg_filters = user_configs.get('filters') or {}
    disabled_media_types = {k for k, v in cfg_filters.items() if v is False}

    size_limit_bytes = int(user_configs.get('file_size', 0) or 0)
    size_limit_mode = str(user_configs.get('size_limit', 'max')).lower()

    raw_exts = user_configs.get('extension')
    allowed_exts = None
    if raw_exts:
        if isinstance(raw_exts, list):
            allowed_exts = {e.lstrip('.').lower() for e in raw_exts if e}
        else:
            allowed_exts = {e.strip().lstrip('.').lower() for e in str(raw_exts).split(',') if e.strip()}

    raw_kw = user_configs.get('keywords')
    required_keywords = None
    if raw_kw:
        if isinstance(raw_kw, list):
            required_keywords = [k.strip().lower() for k in raw_kw if k.strip()]
        else:
            required_keywords = [k.strip().lower() for k in str(raw_kw).split(',') if k.strip()]
    # 'forward' forces the native batched forward; 'copy'/'upload' force the
    # per-message path; 'auto' keeps the existing forward_tag behaviour and
    # falls back to a download+re-upload whenever Telegram refuses the transfer.
    if transfer_mode == 'forward':
        use_native_forward = True
    elif transfer_mode in ('copy', 'upload'):
        use_native_forward = False
    else:
        use_native_forward = bool(forward_tag)
    speed_cfg = user_configs.get('speed_cfg') or {'mode': 'fast', 'delay': 1.0, 'jitter': True, 'batch_size': 100}
    
    # ── SYSTEM OVERRIDE FOR FAST DELAY ──
    # The config_menu sets FAST_DELAY system-wide which should act as the minimum bound
    system_fast_delay = getattr(Config, 'FAST_DELAY', None)
    if system_fast_delay is not None:
        user_delay = float(speed_cfg.get('delay', 1.0 if _bot['is_bot'] else 5.0))
        base_delay = max(user_delay, float(system_fast_delay))
    else:
        base_delay = float(speed_cfg.get('delay', 1.0 if _bot['is_bot'] else 5.0))
    jitter_enabled = bool(speed_cfg.get('jitter', True))
    batch_size = int(speed_cfg.get('batch_size', 100 if base_delay <= 1.0 else 20))
    adaptive_enabled = bool(user_configs.get('adaptive_flood_enabled', True))
    adaptive_delay = base_delay
    success_streak = 0
    course_items = []

    # ── Moderation & Anti-Piracy Checks ──
    is_banned, ban_reason = await db.is_user_banned(user)
    if is_banned:
        if m:
            await edit(m, f"<blockquote><b>🚫 <u>ᴀᴄᴄᴏᴜɴᴛ sᴜsᴘᴇɴᴅᴇᴅ</u></b></blockquote>\n\nʏᴏᴜ ᴀʀᴇ ʙᴀɴɴᴇᴅ ғʀᴏᴍ ᴜsɪɴɢ ᴛʜɪs ʙᴏᴛ.\n<b>ʀᴇᴀsᴏɴ:</b> {ban_reason}", "ᴄᴀɴᴄᴇʟʟᴇᴅ", sts)
        return

    is_bl_source, pat_source = await db.check_blacklisted(channel=sts.get("FROM"))
    is_bl_target, pat_target = await db.check_blacklisted(channel=i.TO)
    if is_bl_source or is_bl_target:
        matched = pat_source if is_bl_source else pat_target
        if Config.LOG_CHANNEL:
            try:
                await send(client, Config.LOG_CHANNEL,
                    f"🚨 <b>#BlacklistBlockedTask</b>\n\n"
                    f"👤 <b>User:</b> <code>{user}</code>\n"
                    f"📡 <b>Source:</b> <code>{sts.get('FROM')}</code>\n"
                    f"🎯 <b>Target:</b> <code>{i.TO}</code>\n"
                    f"🚫 <b>Matched Blacklist:</b> <code>{matched}</code>"
                )
            except Exception:
                pass
        if m:
            await edit(m, f"<blockquote><b>⛔ <u>ᴄᴏɴᴛᴇɴᴛ ᴠɪᴏʟᴀᴛɪᴏɴ</u></b></blockquote>\n\nᴛʜɪs ᴄʜᴀɴɴᴇʟ ɪs ʙʟᴏᴄᴋʟɪsᴛᴇᴅ ʙʏ ʙᴏᴛ ᴍᴏᴅᴇʀᴀᴛɪᴏɴ (<code>{matched}</code>).", "ᴄᴀɴᴄᴇʟʟᴇᴅ", sts)
        return

    try:
        await db.touch_user(user)
    except Exception:
        pass

    # ── Save active task in MongoDB checkpoint store ──
    task_doc = {
        "task_id": str(task_id),
        "user_id": int(user),
        "from_chat": sts.get("FROM"),
        "to_chat": i.TO,
        "limit": int(sts.get("limit")),
        "skip": int(sts.get("skip")) if sts.get("skip") else 0,
        "current_offset": int(sts.get("skip")) if sts.get("skip") else 0,
        "fetched": sts.get("fetched") or 0,
        "total_files": sts.get("total_files") or 0,
        "duplicate": sts.get("duplicate") or 0,
        "deleted": sts.get("deleted") or 0,
        "filtered": sts.get("filtered") or 0,
        "forward_tag": forward_tag,
        "protect": protect,
        "caption": caption,
        # Persisted so resume can rebuild the exact spans. Without this the
        # worker fell back to one contiguous (offset, limit) range and
        # forwarded everything *between* the ranges the user picked.
        "ranges": sts.get("ranges"),
        "status": "running"
    }
    await db.save_active_task(task_id, task_doc)

    if Config.LOG_CHANNEL:
        try:
            tag = "#ForwardTaskResumed" if is_resumed else "#ForwardTaskStarted"
            await send(client, Config.LOG_CHANNEL,
                f"📊 <b>{tag}</b>\n\n"
                f"👤 <b>User:</b> <code>{user}</code>\n"
                f"📡 <b>Source:</b> <code>{sts.get('FROM')}</code>\n"
                f"🎯 <b>Target:</b> <code>{i.TO}</code>\n"
                f"📦 <b>Total / Limit:</b> <code>{sts.get('limit')}</code>\n"
                f"⏩ <b>Offset:</b> <code>{sts.get('skip') or 0}</code>\n"
                f"⚡ <b>Speed Mode:</b> <code>{speed_cfg.get('mode', 'fast')}</code>"
            )
        except Exception:
            pass

    if m:
        await msg_edit(m, "<code>ᴘʀᴏᴄᴇssɪɴɢ ...</code>") 
    if i.TO not in temp.IS_FRWD_CHAT:
        temp.IS_FRWD_CHAT.append(i.TO)
    temp.lock[user] = True

    try:
        MSG = []
        pling = 0
        checkpoint_counter = 0
        if m:
            await edit(m, 'ᴘʀᴏɢʀᴇssɪɴɢ', 10, sts)
        start_offset = int(sts.get('skip')) if sts.get('skip') else 0
        limit_target = int(sts.get('limit'))

        async def iter_all_ranges():
            ranges_to_fetch = sts.get('ranges') or [(start_offset, limit_target)]
            for r_start, r_end in ranges_to_fetch:
                if await is_cancelled(client, user, m, sts, task_id=task_id):
                    return
                async for msg in client.iter_messages(
                    client,
                    chat_id=sts.get('FROM'),
                    limit=r_end,
                    offset=r_start
                ):
                    yield msg

        async for message in iter_all_ranges():
            if await is_cancelled(client, user, m, sts, task_id=task_id):
                return
            while temp.PAUSE.get(user) is True:
                if await is_cancelled(client, user, m, sts, task_id=task_id):
                    return
                await asyncio.sleep(2)
            
            if m and (pling % 20 == 0): 
                await edit(m, 'ᴘʀᴏɢʀᴇssɪɴɢ', 10, sts)
            pling += 1
            sts.add('fetched')

            # Periodic MongoDB checkpoint for auto-resumption
            checkpoint_counter += 1
            if checkpoint_counter % 5 == 0:
                current_mid = getattr(message, 'id', None) or (start_offset + pling)
                await db.update_task_progress(
                    task_id,
                    fetched=sts.get('fetched') or 0,
                    total_files=sts.get('total_files') or 0,
                    current_offset=current_mid,
                    duplicate=sts.get('duplicate') or 0,
                    deleted=sts.get('deleted') or 0,
                    filtered=sts.get('filtered') or 0
                )

            if message.empty or message.service:
                sts.add('deleted')
                continue

            # ── 1. Media Type Filter ──
            m_type = None
            if message.media:
                m_type = getattr(message.media, 'value', str(message.media))
            elif message.text:
                m_type = 'text'
            elif message.poll:
                m_type = 'poll'

            if m_type and m_type in disabled_media_types:
                sts.add('filtered')
                continue

            # ── 2. Extract Media Metadata for Size/Extension/Dedupe ──
            media_obj = getattr(message, message.media.value, None) if message.media else None
            file_name = getattr(media_obj, 'file_name', '') if media_obj else ''
            file_size = getattr(media_obj, 'file_size', 0) if media_obj else 0
            file_unique_id = getattr(media_obj, 'file_unique_id', None) if media_obj else None

            # ── 3. File Size Filter ──
            if size_limit_bytes > 0 and file_size > 0:
                if size_limit_mode == 'max' and file_size > size_limit_bytes:
                    sts.add('filtered')
                    continue
                elif size_limit_mode == 'min' and file_size < size_limit_bytes:
                    sts.add('filtered')
                    continue

            # ── 4. Extension Filter ──
            if allowed_exts and file_name:
                f_ext = file_name.rsplit('.', 1)[-1].lower() if '.' in file_name else ''
                if f_ext not in allowed_exts:
                    sts.add('filtered')
                    continue

            # ── 5. Keyword Filter ──
            if required_keywords:
                search_blob = f"{file_name} {message.caption or ''} {message.text or ''}".lower()
                if not any(kw in search_blob for kw in required_keywords):
                    sts.add('filtered')
            # ── 5b. Content Moderation & Anti-Piracy / NSFW Filter ──
            text_to_scan = f"{file_name} {message.caption or ''} {message.text or ''}".strip()
            if text_to_scan:
                is_bl, bl_match = await db.check_blacklisted(text=text_to_scan)
                if is_bl:
                    sts.add('filtered')
                    if Config.LOG_CHANNEL:
                        try:
                            await send(client, Config.LOG_CHANNEL,
                                f"🚨 <b>#ContentViolationDetected</b>\n\n"
                                f"👤 <b>User:</b> <code>{user}</code>\n"
                                f"📡 <b>Source:</b> <code>{sts.get('FROM')}</code>\n"
                                f"🚫 <b>Matched Blacklist:</b> <code>{bl_match}</code>\n"
                                f"📄 <b>Content:</b> <code>{(text_to_scan[:100])}</code>"
                            )
                        except Exception:
                            pass
                    continue

            # ── 6. In-Memory Deduplication ──
            if skip_duplicates:
                if file_unique_id:
                    if file_unique_id in seen_unique_ids:
                        sts.add('duplicate')
                        continue
                    seen_unique_ids.add(file_unique_id)
                elif message.text:
                    t_hash = hash(message.text.strip())
                    if t_hash in seen_text_hashes:
                        sts.add('duplicate')
                        continue
                    seen_text_hashes.add(t_hash)

            if use_native_forward:
                MSG.append(message.id)
                notcompleted = len(MSG)
                completed = sts.get('total') - sts.get('fetched')
                if (notcompleted >= batch_size or completed <= batch_size):
                    await forward(client, MSG, m, sts, protect, dump_target=dump_target, upload_type=upload_type)
                    sts.add('total_files', notcompleted)
                    b_del = (adaptive_delay if adaptive_enabled else base_delay) * 2
                    b_sleep = human_delay(b_del) if jitter_enabled else b_del
                    await asyncio.sleep(max(1.0, b_sleep))
                    MSG = []
            else:
                lec_start = int(user_configs.get('course_start_offset', 1) or 1)
                lec_idx = lec_start + len(course_items)
                new_caption = custom_caption(message, caption, clean_caption=clean_caption, replace_words=replace_words, user_configs=user_configs, lecture_index=lec_idx)
                sticky_raw = user_configs.get('course_sticky_button')
                sticky_btn = build_universal_button(sticky_raw) if sticky_raw else None
                lec_button = merge_sticky_button(button, sticky_btn)
                details = {"msg_id": message.id, "media": media(message), "caption": new_caption, 'button': lec_button, "protect": protect, "upload_type": upload_type, "transfer_mode": transfer_mode}
                sent_id = await copy(client, details, m, sts, dump_target=dump_target)
                if sent_id:
                    sts.add('total_files')
                    media_obj = getattr(message, message.media.value, None) if message.media else None
                    fname = getattr(media_obj, 'file_name', '') if media_obj else ''
                    c_title = fname or ((message.caption or message.text or "")[:50].strip() if (message.caption or message.text) else f"Lecture {lec_idx:02d}")
                    course_items.append({'num': lec_idx, 'title': c_title, 'msg_id': sent_id})

                # ── Adaptive Anti-Flood Engine ──
                if adaptive_enabled and hasattr(sts, 'data') and sts.id in sts.data:
                    last_fl = sts.data[sts.id].pop('last_flood', 0)
                    if last_fl > 0:
                        adaptive_delay = min(15.0, max(adaptive_delay + 1.0, adaptive_delay * 1.5))
                        success_streak = 0
                        logger.info(f"Adaptive Anti-Flood: Backed off delay to {adaptive_delay:.2f}s (Telegram FloodWait {last_fl}s)")
                    else:
                        success_streak += 1
                        if success_streak >= 25 and adaptive_delay > base_delay:
                            adaptive_delay = max(base_delay, adaptive_delay - 0.25)
                            success_streak = 0
                            logger.info(f"Adaptive Anti-Flood: Smoothly recovered delay to {adaptive_delay:.2f}s")

                eff_del = adaptive_delay if adaptive_enabled else base_delay
                sleep_time = human_delay(eff_del) if jitter_enabled else eff_del
                await asyncio.sleep(sleep_time)

        # Flush any remaining messages in buffer for native forward_tag mode
        if use_native_forward and MSG:
            await forward(client, MSG, m, sts, protect, dump_target=dump_target)
            sts.add('total_files', len(MSG))
            MSG = []

    except Exception as e:
        if m:
            await msg_edit(m, f'<b>ERROR:</b>\n<code>{e}</code>', wait=True)
        if sts.TO in temp.IS_FRWD_CHAT:
            temp.IS_FRWD_CHAT.remove(sts.TO)
        await db.delete_active_task(task_id)
        return await stop(client, user, task_id=task_id)

    if sts.TO in temp.IS_FRWD_CHAT:
        temp.IS_FRWD_CHAT.remove(sts.TO)
    
    # Task completed normally - remove checkpoint
    await db.delete_active_task(task_id)

    # ── User Tracking Telemetry ──
    try:
        final_forwarded = sts.get('total_files') or 0
        if final_forwarded > 0:
            await db.increment_user_forwards(user, final_forwarded)
        await db.touch_user(user)
    except Exception:
        pass

    if Config.LOG_CHANNEL:
        try:
            await send(client, Config.LOG_CHANNEL,
                f"✅ <b>#ForwardTaskCompleted</b>\n\n"
                f"👤 <b>User:</b> <code>{user}</code>\n"
                f"📡 <b>Source:</b> <code>{sts.get('FROM')}</code>\n"
                f"🎯 <b>Target:</b> <code>{sts.get('TO')}</code>\n"
                f"📥 <b>Fetched:</b> <code>{sts.get('fetched') or 0}</code>\n"
                f"⚙️ <b>Forwarded:</b> <code>{sts.get('total_files') or 0}</code>\n"
                f"♻️ <b>Duplicate:</b> <code>{sts.get('duplicate') or 0}</code>\n"
                f"🗑️ <b>Deleted:</b> <code>{sts.get('deleted') or 0}</code>"
            )
        except Exception:
            pass

    # Course Seller Index
    if (user_configs.get('course_seller_mode') or user_configs.get('auto_course_list')) and course_items:
        try:
            await send_course_index_list(client, user, sts, course_items, user_configs=user_configs)
        except Exception as err:
            logger.warning(f"Error sending course list: {err}")

    await send(client, user, "<b>🎉 ғᴏʀᴡᴀᴅɪɴɢ ᴄᴏᴍᴘʟᴇᴛᴇᴅ</b>")
    if m:
        await edit(m, 'ᴄᴏᴍᴘʟᴇᴛᴇᴅ', "ᴄᴏᴍᴘʟᴇᴛᴇᴅ", sts) 
    await stop(client, user, task_id=task_id)

async def auto_resume_unfinished_tasks(bot_app):
    """
    Startup recovery worker: queries MongoDB active_tasks and seamlessly resumes
    interrupted forwarding jobs from their last recorded message checkpoint.
    """
    await asyncio.sleep(4)
    try:
        tasks = await db.get_active_tasks()
    except Exception as e:
        logger.warning(f"Error checking unfinished tasks for auto-resume: {e}")
        return

    if not tasks:
        logger.info("✅ No unfinished forward tasks to resume.")
        return

    logger.info(f"🔄 Auto-resume: Found {len(tasks)} unfinished forward task(s)...")
    for t in tasks:
        asyncio.create_task(_resume_single_task(bot_app, t))

async def _resume_single_task(bot_app, task_data):
    user_id = task_data.get('user_id')
    task_id = task_data.get('task_id')
    if not user_id or not task_id:
        return

    from_chat = task_data.get('from_chat')
    _bot = await db.get_worker_for_chat(user_id, from_chat, is_source=True)
    if not _bot:
        _bot = await db.get_userbot(user_id) or await db.get_custom_bot(user_id)
    if not _bot:
        logger.warning(f"Cannot resume task {task_id}: no bot found for user {user_id}")
        await db.delete_active_task(task_id)
        try:
            await bot_app.send_message(
                user_id,
                "<blockquote><b>⚠️ ᴛᴀsᴋ ʀᴇsᴜᴍᴘᴛɪᴏɴ ɴᴏᴛɪᴄᴇ</b>\n\n"
                "<i>ʏᴏᴜʀ ᴘʀᴇᴠɪᴏᴜs ғᴏʀᴡᴀʀᴅɪɴɢ ᴛᴀsᴋ ᴄᴏᴜʟᴅ ɴᴏᴛ ᴀᴜᴛᴏ-ʀᴇsᴜᴍᴇ ʙᴇᴄᴀᴜsᴇ ʏᴏᴜʀ ʙᴏᴛ/sᴇssɪᴏɴ ɪs ɴᴏᴛ ᴄᴏɴғɪɢᴜʀᴇᴅ. ᴘʟᴇᴀsᴇ ᴄʜᴇᴄᴋ /settings.</i></blockquote>"
            )
        except Exception:
            pass
        return

    try:
        client = await start_clone_bot(CLIENT.client(_bot))
        # Probe source access — if bot can't read, try userbot
        from_chat = task_data.get('from_chat')
        try:
            await client.get_chat(from_chat)
        except Exception:
            if _bot.get('is_bot'):
                _userbot = await db.get_userbot(user_id)
                if _userbot:
                    try:
                        await client.stop()
                    except Exception:
                        pass
                    client = await start_clone_bot(CLIENT.client(_userbot))
                    _bot = _userbot
                    logger.info(f"Auto-resume {task_id}: switched to userbot for source access")
    except Exception as e:
        logger.warning(f"Failed to start bot client for resumed task {task_id}: {e}")
        await db.delete_active_task(task_id)
        return

    from_chat = task_data.get('from_chat')
    to_chat = task_data.get('to_chat')
    limit = int(task_data.get('limit', 0))
    current_offset = int(task_data.get('current_offset') or task_data.get('skip', 0))

    if current_offset >= limit:
        logger.info(f"Task {task_id} was already at or past limit ({current_offset} >= {limit}), clearing.")
        await db.delete_active_task(task_id)
        try:
            await client.stop()
        except Exception:
            pass
        return

    user_configs = await db.get_configs(user_id)
    caption = task_data.get('caption') or user_configs.get('caption')
    forward_tag = task_data.get('forward_tag', user_configs.get('forward_tag', False))
    protect = task_data.get('protect', user_configs.get('protect', False))
    from .test import parse_buttons
    button = parse_buttons(user_configs.get('button') or '')

    sts = STS(task_id)
    # Rebuild the original spans. Falling back to a single (current_offset,
    # limit) range made a resumed multi-range job forward every message
    # *between* the ranges the user selected.
    ranges = task_data.get('ranges')
    if ranges:
        try:
            ranges = [[int(a), int(b)] for a, b in ranges]
        except (TypeError, ValueError):
            ranges = None
    if ranges:
        # Drop the part of the first range already done, then any span that
        # trimming emptied.
        resume_at = int(current_offset or 0)
        if resume_at > ranges[0][0]:
            ranges[0][0] = resume_at
        ranges = [r for r in ranges if r[1] >= r[0]]
        if not ranges:
            await db.delete_active_task(task_id)
            try:
                await client.stop()
            except Exception:
                pass
            return
        sts.store(from_chat, to_chat, ranges[0][0], ranges[-1][1], ranges=ranges)
    else:
        sts.store(from_chat, to_chat, current_offset, limit)
    sts.data[task_id]['fetched'] = task_data.get('fetched', current_offset)
    sts.data[task_id]['total_files'] = task_data.get('total_files', 0)
    sts.data[task_id]['duplicate'] = task_data.get('duplicate', 0)
    sts.data[task_id]['deleted'] = task_data.get('deleted', 0)
    sts.data[task_id]['filtered'] = task_data.get('filtered', 0)
    sts.data[task_id]['user_id'] = user_id

    # Send resume notification message to user
    try:
        resume_card = (
            "<blockquote><b>🔄 <u>ᴀᴜᴛᴏ-ʀᴇsᴜᴍɪɴɢ ɪɴᴛᴇʀʀᴜᴘᴛᴇᴅ ғᴏʀᴡᴀʀᴅ ᴛᴀsᴋ</u></b>\n\n"
            f"📡 <b>sᴏᴜʀᴄᴇ:</b> <code>{from_chat}</code>\n"
            f"🎯 <b>ᴛᴀʀɢᴇᴛ:</b> <code>{to_chat}</code>\n"
            f"📦 <b>ʀᴇsᴜᴍɪɴɢ ᴀᴛ ᴍᴇssᴀɢᴇ:</b> <code>{current_offset}</code> / <code>{limit}</code>\n"
            f"⚙️ <b>ᴘʀᴇᴠɪᴏᴜsʟʏ ғᴏʀᴡᴀʀᴅᴇᴅ:</b> <code>{task_data.get('total_files', 0)}</code>\n\n"
            "⚡ <i>ʙᴏᴛ ʀᴇᴄᴏᴠᴇʀᴇᴅ sᴜᴄᴄᴇssғᴜʟʟʏ ғʀᴏᴍ ʀᴇʙᴏᴏᴛ! ᴄᴏɴᴛɪɴᴜɪɴɢ ғᴏʀᴡᴀʀᴅ ᴊᴏʙ...</i></blockquote>"
        )
        m = await bot_app.send_message(user_id, resume_card)
    except Exception as err:
        logger.warning(f"Could not send resume card to user {user_id}: {err}")
        m = None

    temp.CANCEL[user_id] = False
    temp.PAUSE[user_id] = False
    temp.lock[user_id] = True

    try:
        await execute_forward_task(
            client=client,
            user=user_id,
            m=m,
            sts=sts,
            task_id=task_id,
            _bot=_bot,
            caption=caption,
            forward_tag=forward_tag,
            protect=protect,
            button=button,
            user_configs=user_configs,
            is_resumed=True
        )
    finally:
        temp.lock[user_id] = False

_RESTRICTED_NAMES = {
    "ChatForwardsRestricted", "MessageAuthorRequired", "ChatRestricted",
    "ChatWriteForbidden", "ChatAdminRequired",
}
_RESTRICTED_MARKERS = (
    "FORWARDS_RESTRICTED", "FORWARDSRESTRICTED", "AUTHOR_REQUIRED",
    "MESSAGE_AUTHOR_REQUIRED", "PROTECTED_CONTENT",
)

def is_restricted_error(e: BaseException) -> bool:
    """True when Telegram refused the transfer because the source is protected.

    Such a source refuses both forwardMessages and copyMessage, so the only way
    to move the file is to download it and upload it as a fresh file.
    """
    if type(e).__name__ in _RESTRICTED_NAMES:
        return True
    text = str(e).upper()
    return any(m in text for m in _RESTRICTED_MARKERS)

# media kind -> (send method, name of its file argument). send_video_note and
# send_sticker take no caption, handled by the caller.
_UPLOAD_METHOD = {
    "photo": ("send_photo", "photo"),
    "video": ("send_video", "video"),
    "animation": ("send_animation", "animation"),
    "audio": ("send_audio", "audio"),
    "voice": ("send_voice", "voice"),
    "video_note": ("send_video_note", "video_note"),
    "sticker": ("send_sticker", "sticker"),
    "document": ("send_document", "document"),
}
_NO_CAPTION = {"send_video_note", "send_sticker"}
_DOWNGRADE_TO_FILE = {"send_video", "send_audio", "send_animation", "send_voice"}


async def download_and_reupload(bot, from_chat_id, message_id, to_chat, caption=None,
                                button=None, protect=None, upload_type="media"):
    """Move one message by downloading its media and uploading it fresh.

    Fallback for protected sources where forward_messages and copy_message are
    both refused. `upload_type` decides the wire format: 'document' downgrades
    video/audio to a plain file, 'video' promotes video documents back.
    """
    src = await bot.get_messages(from_chat_id, message_id)
    if src is None or getattr(src, 'empty', False):
        return None

    kind = src.media.value if src.media else None
    if not kind:
        return await bot.send_message(
            chat_id=to_chat,
            text=caption if caption is not None else (src.text or ""),
            reply_markup=button,
            protect_content=protect,
            disable_web_page_preview=True,
        )

    method_name, file_arg = _UPLOAD_METHOD.get(kind, ("send_document", "document"))
    if upload_type == "document" and method_name in _DOWNGRADE_TO_FILE:
        method_name, file_arg = "send_document", "document"
    elif upload_type == "video" and method_name == "send_document" and kind in ("video", "animation"):
        method_name, file_arg = "send_video", "video"

    path = None
    try:
        path = await bot.download_media(src)
        if not path:
            return None
        kwargs = {"chat_id": to_chat, "protect_content": protect}
        if method_name not in _NO_CAPTION:
            kwargs["caption"] = caption
            kwargs["reply_markup"] = button
        orig_media = getattr(src, src.media.value, None) if src.media else None
        orig_name = getattr(orig_media, 'file_name', None) if orig_media else None
        if orig_name and method_name == "send_document":
            kwargs["file_name"] = orig_name
        kwargs[file_arg] = path
        return await getattr(bot, method_name)(**kwargs)
    finally:
        if path:
            try:
                os.remove(path)
            except Exception:
                pass


async def _copy_once(bot, msg, from_chat_id, to_chat, protect):
   """One server-side transfer attempt. Never downloads anything."""
   if msg.get("media"):
      return await bot.send_cached_media(
            chat_id=to_chat,
            file_id=msg.get("media"),
            caption=msg.get("caption"),
            reply_markup=msg.get('button'),
            protect_content=protect)
   if msg.get("caption") and not msg.get("media"):
      return await bot.send_message(
            chat_id=to_chat,
            text=msg.get("caption"),
            reply_markup=msg.get('button'),
            protect_content=protect)
   return await bot.copy_message(
         chat_id=to_chat,
         from_chat_id=from_chat_id,
         caption=msg.get("caption"),
         message_id=msg.get("msg_id"),
         reply_markup=msg.get('button'),
         protect_content=protect)


async def _transfer(bot, msg, sts, to_chat, transfer_mode, upload_type, protect):
   if transfer_mode == "upload":
      return await download_and_reupload(
            bot, sts.get('FROM'), msg.get("msg_id"), to_chat,
            caption=msg.get("caption"), button=msg.get('button'),
            protect=protect, upload_type=upload_type)
   return await _copy_once(bot, msg, sts.get('FROM'), to_chat, protect)


async def copy(bot, msg, m, sts, dump_target=None):
   transfer_mode = str(msg.get("transfer_mode") or "auto").lower()
   upload_type = msg.get("upload_type") or "media"
   try:
     sent = await _transfer(bot, msg, sts, sts.get('TO'), transfer_mode, upload_type, msg.get("protect"))
     if dump_target and str(dump_target) != str(sts.get('TO')):
        try:
           await _transfer(bot, msg, sts, dump_target, transfer_mode, upload_type, False)
        except Exception:
           pass
     return getattr(sent, 'id', None)
   except FloodWait as e:
     sts.add('floodwaits', 1)
     if hasattr(sts, 'data') and sts.id in sts.data:
         sts.data[sts.id]['last_flood'] = e.value
     await edit(m, 'ᴘʀᴏɢʀᴇssɪɴɢ', e.value, sts)
     await asyncio.sleep(e.value + 1)
     await edit(m, 'ᴘʀᴏɢʀᴇssɪɴɢ', 10, sts)
     return await copy(bot, msg, m, sts, dump_target=dump_target)
   except Exception as e:
     if is_restricted_error(e) or "FILE_REFERENCE" in str(e).upper():
        # Protected source: Telegram refused the server-side transfer, so the
        # file has to be downloaded and uploaded as a fresh one.
        try:
           sent = await _transfer(bot, msg, sts, sts.get('TO'), "upload", upload_type, msg.get("protect"))
           if sent is not None:
              if dump_target and str(dump_target) != str(sts.get('TO')):
                 try:
                    await _transfer(bot, msg, sts, dump_target, "upload", upload_type, False)
                 except Exception:
                    pass
              return getattr(sent, 'id', None)
        except Exception as inner:
           logger.warning(f"Re-upload fallback failed for msg {msg.get('msg_id')}: {inner}")
     logger.warning(f"Copy failed for message {msg.get('msg_id')}: {e}")
     sts.add('deleted')
     return None

def build_universal_button(raw_str):
   if not raw_str or not isinstance(raw_str, str):
      return None
   raw = raw_str.strip()
   if not raw:
      return None
   try:
      if '|' in raw:
         parts = raw.split('|', 1)
         t = parts[0].strip()
         u = parts[1].strip()
         if t and u:
            return InlineKeyboardButton(t, url=u)
      elif ' - ' in raw:
         parts = raw.split(' - ', 1)
         t = parts[0].strip()
         u = parts[1].strip()
         if t and u:
            return InlineKeyboardButton(t, url=u)
   except Exception:
      pass
   return None

def merge_sticky_button(existing_button, sticky_btn):
   if not sticky_btn:
      return existing_button
   if not existing_button:
      return InlineKeyboardMarkup([[sticky_btn]])
   if isinstance(existing_button, InlineKeyboardMarkup):
      new_keyboard = [list(row) for row in existing_button.inline_keyboard]
      new_keyboard.append([sticky_btn])
      return InlineKeyboardMarkup(new_keyboard)
   return existing_button

def detect_missing_lectures(items):
   nums = []
   for it in items:
      title = it.get('title', '')
      m = re.search(r'(?:lec(?:ture)?|part|ch(?:apter)?|session|class)[\s_.:-]*(\d+)', title, re.IGNORECASE)
      if not m:
         m = re.search(r'^\s*(\d+)[\s_.:-]', title)
      if m:
         try:
            nums.append(int(m.group(1)))
         except Exception:
            pass
   if len(nums) >= 2:
      min_n = min(nums)
      max_n = max(nums)
      if 0 < (max_n - min_n) < 500:
         full_set = set(range(min_n, max_n + 1))
         missing = sorted(list(full_set - set(nums)))
         return missing
   return []

async def send_course_index_list(client, user, sts, course_items, user_configs=None):
   user_configs = user_configs or {}
   to_chat = sts.get('TO')
   from_title = str(sts.get('FROM'))
   to_str = str(to_chat).strip()
   is_public = to_str.startswith("@") or not to_str.lstrip("-").isdigit()
   if is_public:
      chan_ref = to_str.lstrip("@")
      clean_chat = ""
   else:
      chan_ref = ""
      if to_str.startswith("-100"):
         clean_chat = to_str[4:]
      elif to_str.startswith("-"):
         clean_chat = to_str[1:]
      else:
         clean_chat = to_str

   sticky_raw = user_configs.get('course_sticky_button')
   sticky_btn = build_universal_button(sticky_raw) if sticky_raw else None

   # Pre-populate clickable direct message links for every lecture item
   for it in course_items:
      if it.get('msg_id') and not it.get('link'):
         it['link'] = f"https://t.me/{chan_ref}/{it['msg_id']}" if is_public else f"https://t.me/c/{clean_chat}/{it['msg_id']}"

   missing_lecs = []
   if user_configs.get('course_detect_missing', True):
      missing_lecs = detect_missing_lectures(course_items)

   missing_card = ""
   if missing_lecs:
      missing_str = ", ".join(f"[{x:02d}]" for x in missing_lecs[:15])
      if len(missing_lecs) > 15:
         missing_str += f" (+{len(missing_lecs) - 15} more)"
      missing_card = f"⚠️ <b>ᴍɪssɪɴɢ ʟᴇᴄᴛᴜʀᴇs ᴅᴇᴛᴇᴄᴛᴇᴅ:</b> <code>{missing_str}</code>\n"
   else:
      missing_card = "🎉 <b>ᴄᴏᴜʀsᴇ ᴄᴏᴍᴘʟᴇᴛᴇɴᴇss:</b> <code>100% (No gaps detected)</code>\n"

   # Instant Telegraph Syllabus Webpage Generator
   telegraph_url = None
   if user_configs.get('course_telegraph_export', True) and course_items:
      try:
         from plugins.telegraph_helper import create_telegraph_syllabus
         telegraph_url = await create_telegraph_syllabus(
            title=from_title,
            from_title=from_title,
            course_items=course_items,
            missing_lectures=missing_lecs,
            header_banner=user_configs.get('course_brand_header'),
            footer_banner=user_configs.get('course_brand_footer')
         )
      except Exception as tele_err:
         logger.warning(f"Failed to generate Telegraph syllabus: {tele_err}")

   telegraph_card = ""
   if telegraph_url:
      telegraph_card = f"🌐 <b>ᴡᴇʙ sʏʟʟᴀʙᴜs (ᴛᴇʟᴇɢʀᴀᴘʜ):</b> <a href='{telegraph_url}'>Click to View Online</a>\n"

   btn_rows = []
   if telegraph_url:
      btn_rows.append([InlineKeyboardButton("🌐 ᴠɪᴇᴡ ᴡᴇʙ sʏʟʟᴀʙᴜs (ᴛᴇʟᴇɢʀᴀᴘʜ)", url=telegraph_url)])
   if sticky_btn:
      btn_rows.append([sticky_btn])
   idx_markup = InlineKeyboardMarkup(btn_rows) if btn_rows else None

   header = (
      "📚 <b><u>ᴄᴏᴜʀsᴇ ʟᴇᴄᴛᴜʀᴇs ɪɴᴅᴇx / sʏʟʟᴀʙᴜs</u></b>\n"
      "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
      f"🎯 <b>sᴏᴜʀᴄᴇ:</b> <code>{from_title}</code>\n"
      f"📦 <b>ᴛᴏᴛᴀʟ ʟᴇᴄᴛᴜʀᴇs:</b> <code>{len(course_items)}</code>\n"
      f"{missing_card}"
      f"{telegraph_card}"
      "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
   )

   chunk_size = 25
   total_pages = (len(course_items) + chunk_size - 1) // chunk_size
   for chunk_idx in range(0, len(course_items), chunk_size):
      chunk = course_items[chunk_idx:chunk_idx + chunk_size]
      page_num = (chunk_idx // chunk_size) + 1
      page_str = f"📑 <b>ᴘᴀɢᴇ:</b> <code>{page_num}/{total_pages}</code>\n\n" if total_pages > 1 else ""
      lines = []
      for item in chunk:
         num_str = f"{item['num']:02d}"
         title = str(item['title']).replace("<", "&lt;").replace(">", "&gt;")
         if item.get('link'):
            lines.append(f"<b>[{num_str}]</b> <a href='{item['link']}'>{title}</a>")
         else:
            lines.append(f"<b>[{num_str}]</b> {title}")

      footer = "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n⚡️ <i>ɢᴇɴᴇʀᴀᴛᴇᴅ ʙʏ sᴋɪɴᴇᴛ ᴠᴇʀsᴇ (ᴄᴏᴜʀsᴇ sᴇʟʟᴇʀ ᴍᴏᴅᴇ)</i>"
      full_text = header + page_str + "\n".join(lines) + footer

      try:
         sent_idx = await client.send_message(to_chat, full_text, disable_web_page_preview=True, reply_markup=idx_markup)
         if chunk_idx == 0:
            try:
               await sent_idx.pin(disable_notification=True)
            except Exception:
               pass
      except Exception:
         pass

      try:
         await client.send_message(user, full_text, disable_web_page_preview=True, reply_markup=idx_markup)
      except Exception:
         pass

   # Auto Export Document (.txt)
   if user_configs.get('course_export_txt', True) and course_items:
      try:
         safe_name = re.sub(r'[^a-zA-Z0-9_-]', '_', from_title)[:25] or "Course"
         txt_content = (
            "====================================================\n"
            "📚 COURSE LECTURES INDEX & SYLLABUS\n"
            f"🎯 Source: {from_title}\n"
            f"📦 Total Forwarded Lectures: {len(course_items)}\n"
            f"🌐 Web Syllabus (Telegraph): {telegraph_url or 'N/A'}\n"
            f"📅 Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            "⚡ Generated by Skinet Verse (Course Seller Mode)\n"
            "====================================================\n\n"
         )
         for it in course_items:
            num_str = f"{it['num']:02d}"
            title = it['title']
            msg_link = it.get('link')
            if msg_link:
               txt_content += f"[{num_str}] {title}\n     Link: {msg_link}\n\n"
            else:
               txt_content += f"[{num_str}] {title}\n\n"

         txt_content += "====================================================\n"
         if missing_lecs:
            txt_content += f"⚠️ Missing Lectures Detected: {', '.join(f'[{x:02d}]' for x in missing_lecs)}\n"
         else:
            txt_content += "🎉 Course Completeness: 100% (No gaps detected!)\n"
         txt_content += "====================================================\n"

         doc_file = f"/tmp/{safe_name}_Syllabus_Index.txt"
         with open(doc_file, "w", encoding="utf-8") as f_out:
            f_out.write(txt_content)

         doc_btn = InlineKeyboardMarkup([[InlineKeyboardButton("🌐 ᴠɪᴇᴡ ᴡᴇʙ sʏʟʟᴀʙᴜs", url=telegraph_url)]]) if telegraph_url else None
         await client.send_document(
            chat_id=user,
            document=doc_file,
            caption=f"📄 <b><u>ᴄᴏᴜʀsᴇ sʏʟʟᴀʙᴜs ᴅᴏᴄᴜᴍᴇɴᴛ</u></b>\n\n"
                    f"📦 <b>ᴛᴏᴛᴀʟ ʟᴇᴄᴛᴜʀᴇs:</b> <code>{len(course_items)}</code>\n"
                    f"🎯 <b>sᴏᴜʀᴄᴇ:</b> <code>{from_title}</code>\n\n"
                    f"⚡ <i>ʏᴏᴜ ᴄᴀɴ sʜᴀʀᴇ ᴛʜɪs ᴄʟᴇᴀɴ ɪɴᴅᴇx ғɪʟᴇ ᴡɪᴛʜ ʏᴏᴜʀ sᴛᴜᴅᴇɴᴛs!</i>",
            reply_markup=doc_btn
         )
         if os.path.exists(doc_file):
            os.remove(doc_file)
      except Exception as exp_err:
         logger.warning(f"Failed to export course syllabus document: {exp_err}")


async def forward(bot, msg, m, sts, protect, dump_target=None, upload_type="media"):
   try:
     await bot.forward_messages(
           chat_id=sts.get('TO'),
           from_chat_id=sts.get('FROM'),
           protect_content=protect,
           message_ids=msg)
     if dump_target and str(dump_target) != str(sts.get('TO')):
        try:
           await bot.forward_messages(
                 chat_id=dump_target,
                 from_chat_id=sts.get('FROM'),
                 message_ids=msg)
        except Exception:
           pass
   except FloodWait as e:
      sts.add('floodwaits', 1)
      if hasattr(sts, 'data') and sts.id in sts.data:
          sts.data[sts.id]['last_flood'] = e.value
      await edit(m, 'ᴘʀᴏɢʀᴇssɪɴɢ', e.value, sts)
      await asyncio.sleep(e.value + 1)
      await edit(m, 'ᴘʀᴏɢʀᴇssɪɴɢ', 10, sts)
      await forward(bot, msg, m, sts, protect, dump_target=dump_target, upload_type=upload_type)
   except Exception as e:
      if is_restricted_error(e):
         # Protected source: forwardMessages is refused, so re-upload each message
         # in the batch. Text-only messages survive; media is downloaded and sent.
         for mid in (msg if isinstance(msg, (list, tuple)) else [msg]):
            try:
               await download_and_reupload(
                     bot, sts.get('FROM'), mid, sts.get('TO'),
                     protect=protect, upload_type=upload_type)
               if dump_target and str(dump_target) != str(sts.get('TO')):
                  try:
                     await download_and_reupload(
                           bot, sts.get('FROM'), mid, dump_target,
                           protect=False, upload_type=upload_type)
                  except Exception:
                     pass
            except FloodWait as fw:
               await asyncio.sleep(fw.value + 1)
               try:
                  await download_and_reupload(
                        bot, sts.get('FROM'), mid, sts.get('TO'),
                        protect=protect, upload_type=upload_type)
               except Exception:
                  sts.add('deleted')
            except Exception as inner:
               logger.warning(f"Re-upload fallback failed for msg {mid}: {inner}")
               sts.add('deleted')
      elif isinstance(msg, (list, tuple)) and len(msg) > 1:
         # Batch forward failed (e.g. invalid/deleted message ID in batch).
         # Fallback to forwarding messages individually so good messages succeed!
         for mid in msg:
            try:
               await bot.forward_messages(
                     chat_id=sts.get('TO'),
                     from_chat_id=sts.get('FROM'),
                     protect_content=protect,
                     message_ids=mid)
               if dump_target and str(dump_target) != str(sts.get('TO')):
                  try:
                     await bot.forward_messages(
                           chat_id=dump_target,
                           from_chat_id=sts.get('FROM'),
                           message_ids=mid)
                  except Exception:
                     pass
            except FloodWait as fe:
               await asyncio.sleep(fe.value + 1)
               try:
                  await bot.forward_messages(
                        chat_id=sts.get('TO'),
                        from_chat_id=sts.get('FROM'),
                        protect_content=protect,
                        message_ids=mid)
               except Exception:
                  sts.add('deleted')
            except Exception as single_err:
               if is_restricted_error(single_err):
                  try:
                     await download_and_reupload(
                           bot, sts.get('FROM'), mid, sts.get('TO'),
                           protect=protect, upload_type=upload_type)
                  except Exception:
                     sts.add('deleted')
               else:
                  logger.warning(f"Skipping failed message {mid}: {single_err}")
                  sts.add('deleted')
      else:
         logger.warning(f"Single message forward failed: {e}")
         sts.add('deleted')

PROGRESS = """
📈 ᴘᴇʀᴄᴇɴᴛᴀɢᴇ : {0} %

⭕ ғᴇᴛᴄʜᴇᴅ : {1}

⚙️ ғᴏʀᴡᴀʀᴅᴇᴅ : {2}

🗞️ ʀᴇᴍᴀɴɪɴɢ : {3}

♻️ sᴛᴀᴛᴜs : {4}

⏳️ ᴇᴛᴀ : {5}
"""

async def msg_edit(msg, text, button=None, wait=None):
    if not msg:
        return None
    try:
        return await msg.edit(text, reply_markup=button)
    except MessageNotModified:
        pass 
    except FloodWait as e:
        if wait:
           await asyncio.sleep(e.value)
           return await msg_edit(msg, text, button, wait)
    except Exception as e:
        logger.debug(f"msg_edit suppressed: {e}")
        return None

async def edit(msg, title, status, sts):
    if not msg:
        return
    try:
        i = sts.get(full=True)
        if not i:
            return
        owner = getattr(i, 'user_id', None) or (sts.verify().get('user_id') if isinstance(sts.verify(), dict) else None)
        is_paused = temp.PAUSE.get(owner, False)
        if is_paused:
            status = '⏸️ ᴘᴀᴜsᴇᴅ'
        elif status == 10:
            status = 'ғᴏʀᴡᴀʀᴅɪɴɢ'
        elif str(status).isnumeric():
            status = f"sʟᴇᴇᴘɪɴɢ {status} s"

        total_val = float(i.total) if i.total else 1.0
        fetched_val = float(i.fetched) if i.fetched else 0.0
        pct_val = min(100.0, max(0.0, (fetched_val * 100.0) / total_val)) if total_val > 0 else 0.0
        percentage = "{:.0f}".format(pct_val)

        now = time.time()
        diff = int(now - (i.start or now))
        speed = sts.divide(i.fetched, diff)
        elapsed_time = round(diff) * 1000
        time_to_completion = round(sts.divide(i.total - i.fetched, int(speed))) * 1000
        estimated_total_time = elapsed_time + time_to_completion  
        
        progress = "▰{0}{1}".format(
            ''.join(["▰" for _ in range(math.floor(int(percentage) / 10))]),
            ''.join(["▱" for _ in range(10 - math.floor(int(percentage) / 10))]))
        if hasattr(sts, 'data') and i.id in sts.data:
            sts.data[i.id]['status'] = status
            sts.data[i.id]['est_time'] = estimated_total_time
        button = [[InlineKeyboardButton(progress, callback_data=f'fstat#{percentage}#{i.id}')]]
        estimated_total_time = TimeFormatter(milliseconds=estimated_total_time)
        estimated_total_time = estimated_total_time if estimated_total_time != '' else '0 s'

        safe_title = html.escape(str(title or ''))
        text = TEXT.format(i.total, i.fetched, i.total_files, i.duplicate, i.deleted, i.skip, i.filtered, status, percentage, safe_title)
        if status in ["ᴄᴀɴᴄᴇʟʟᴇᴅ", "ᴄᴏᴍᴘʟᴇᴛᴇᴅ"]:
            button.append([InlineKeyboardButton('• ᴄʟᴏsᴇ', callback_data='close_btn')])
        else:
            pause_btn = InlineKeyboardButton('▶️ ʀᴇsᴜᴍᴇ', callback_data=f'resume_frwd#{i.id}') if is_paused else InlineKeyboardButton('⏸️ ᴘᴀᴜsᴇ', callback_data=f'pause_frwd#{i.id}')
            button.append([
                pause_btn,
                InlineKeyboardButton('🛑 ᴄᴀɴᴄᴇʟ', callback_data='terminate_frwd')
            ])
        await msg_edit(msg, text, colored_markup(button))
    except Exception as e:
        logger.warning(f"edit() error (ignored to keep task running): {e}")

async def is_cancelled(client, user, msg, sts, task_id=None):
   if temp.CANCEL.get(user) == True:
      if sts.TO in temp.IS_FRWD_CHAT:
          temp.IS_FRWD_CHAT.remove(sts.TO)
      if Config.LOG_CHANNEL:
         try:
            await send(client, Config.LOG_CHANNEL,
                f"🛑 <b>#ForwardTaskCancelled</b>\n\n"
                f"👤 <b>User:</b> <code>{user}</code>\n"
                f"📡 <b>Source:</b> <code>{sts.get('FROM')}</code>\n"
                f"🎯 <b>Target:</b> <code>{sts.get('TO')}</code>\n"
                f"⚙️ <b>Forwarded:</b> <code>{sts.get('total_files') or 0}</code>"
            )
         except Exception:
            pass
      if msg:
          try:
              await edit(msg, "ᴄᴀɴᴄᴇʟʟᴇᴅ", "ᴄᴀɴᴄᴇʟʟᴇᴅ", sts)
          except Exception:
              pass
      await send(client, user, "<b>❌ ғᴏʀᴡᴀʀᴅɪɴɢ ᴄᴀɴᴄᴇʟʟᴇᴅ</b>")
      await stop(client, user, task_id=task_id)
      return True 
   return False 

async def stop(client, user, task_id=None):
   try:
     await client.stop()
   except:
     pass 
   await db.rmve_frwd(user)
   if task_id:
     try:
       await db.delete_active_task(task_id)
     except Exception:
       pass
   else:
     try:
       t = await db.get_user_active_task(user)
       if t:
         await db.delete_active_task(t["task_id"])
     except Exception:
       pass
   temp.forwardings = max(0, temp.forwardings - 1)
   temp.lock[user] = False 
   temp.PAUSE[user] = False

async def send(bot, user, text):
   try:
      await bot.send_message(user, text=text)
   except:
      pass 

def clean_caption_advanced(text: str, user_configs: dict = None, lecture_index: int = None, file_name: str = "") -> str:
  if not text:
    text = ""
  user_configs = user_configs or {}
  is_seller = bool(user_configs.get('course_seller_mode', False))
  rem_user = is_seller or bool(user_configs.get('username_remover', False))
  rep_user = user_configs.get('username_replacer')
  rem_link = is_seller or bool(user_configs.get('link_remover', False))
  rep_link = user_configs.get('link_replacer')
  rem_hid = is_seller or bool(user_configs.get('hidden_link_remover', False))
  clean_cap = is_seller or bool(user_configs.get('clean_caption', False))
  replace_words = user_configs.get('replace_words', {})
  auto_num = is_seller or bool(user_configs.get('auto_numbering', False))

  # 1. Hidden link remover & replacer (HTML: <a href="url">text</a>)
  if rem_hid or rem_link:
    if rep_link:
      text = re.sub(r'<a\s+[^>]*href=["\'][^"\']+["\'][^>]*>(.*?)</a>', rf'<a href="{rep_link}">\1</a>', text, flags=re.DOTALL)
    else:
      text = re.sub(r'<a\s+[^>]*href=["\'][^"\']+["\'][^>]*>(.*?)</a>', r'\1', text, flags=re.DOTALL)

  # 2. Hidden link remover & replacer (Markdown: [text](url))
  if rem_hid or rem_link:
    if rep_link:
      text = re.sub(r'\[([^\]]+)\]\(https?://[^\)]+\)', rf'[\1]({rep_link})', text)
    else:
      text = re.sub(r'\[([^\]]+)\]\(https?://[^\)]+\)', r'\1', text)

  # 3. Direct links remover & replacer (do not match URLs inside HTML tag attributes)
  if rem_link or clean_cap:
    url_pattern = r'(?<!href=["\'])(?<!["\'=])(?:https?://|www\.)[^\s<>"\'\)]+'
    if rep_link:
      text = re.sub(url_pattern, rep_link, text)
    else:
      text = re.sub(url_pattern, '', text)

  # 4. Username remover & replacer (do not match inside email addresses)
  if rem_user or clean_cap:
    username_pattern = r'(?<![a-zA-Z0-9_.])@([a-zA-Z0-9_]{3,32})'
    if rep_user:
      text = re.sub(username_pattern, rep_user, text)
    else:
      text = re.sub(username_pattern, '', text)

  # 5. Word replacements
  if replace_words:
    for old, new in replace_words.items():
      if old:
        text = text.replace(old, new)

  # 6. Normalize whitespace
  text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text).strip()

  # 7. Lecture numbering prefix
  if auto_num and lecture_index is not None:
    num_style = user_configs.get('course_number_style', 'bracket')
    if num_style == 'lecture':
      prefix = f"<b>Lecture {lecture_index:02d} -</b> "
    elif num_style == 'part':
      prefix = f"<b>Part {lecture_index:02d}:</b> "
    elif num_style == 'lec':
      prefix = f"<b>Lec {lecture_index:02d} |</b> "
    elif num_style == 'dot':
      prefix = f"<b>{lecture_index:02d}.</b> "
    else:
      prefix = f"<b>[{lecture_index:02d}]</b> "

    if not any(text.startswith(p) for p in ("[", "<b>[", "<b>Lecture", "<b>Part", "<b>Lec")):
      text = prefix + (text if text else (file_name or f"Lecture {lecture_index:02d}"))

  # 8. Remove hashtags (#tag) if remove_tags enabled
  if user_configs.get('remove_tags', False):
    text = re.sub(r'#\w+', '', text).strip()

  # 9. Watermark text
  watermark = user_configs.get('watermark_text')
  if watermark and text:
    text = f"{text}\n\n{watermark}".strip()

  return text

def clean_caption_text(text: str) -> str:
  return clean_caption_advanced(text, {'clean_caption': True})

def apply_word_replacements(text: str, replace_words: dict) -> str:
  if not text or not replace_words:
    return text
  for old, new in replace_words.items():
    text = text.replace(old, new)
  return text

def build_media_caption(header: str = None, body: str = None, footer: str = None, max_len: int = 1024) -> str:
    """
    Safely builds a caption within Telegram's hard limits (1024 for media, 4096 for text).
    Preserves branding header and footer banners intact, cleanly truncating the body
    with an ellipsis if total length exceeds max_len.
    """
    header = (header or "").strip()
    body = (body or "").strip()
    footer = (footer or "").strip()

    if not header and not footer:
        if len(body) > max_len:
            return body[:max_len - 3] + "..."
        return body

    sep = "\n\n"
    total_len = len(header) + len(body) + len(footer)
    if header and body:
        total_len += len(sep)
    if (header or body) and footer:
        total_len += len(sep)

    if total_len <= max_len:
        parts = [p for p in [header, body, footer] if p]
        return sep.join(parts)

    reserved = len(header) + len(footer)
    if header and footer:
        reserved += len(sep)
    if body and (header or footer):
        reserved += len(sep)

    if reserved >= max_len:
        half = (max_len - 4) // 2
        new_hdr = (header[:half] + "...") if len(header) > half else header
        new_ftr = (footer[:half] + "...") if len(footer) > half else footer
        return f"{new_hdr}\n\n{new_ftr}" if new_hdr and new_ftr else (new_hdr or new_ftr)

    avail_body = max_len - reserved
    if len(body) > avail_body:
        if avail_body > 3:
            body = body[:avail_body - 3] + "..."
        else:
            body = ""

    parts = [p for p in [header, body, footer] if p]
    return sep.join(parts)

def custom_caption(msg, caption, clean_caption=False, replace_words=None, user_configs=None, lecture_index=None):
  user_configs = dict(user_configs) if user_configs else {}
  if clean_caption:
    user_configs['clean_caption'] = True
  if replace_words:
    user_configs['replace_words'] = replace_words

  file_name = ''
  file_size = 0
  fcaption = ''

  if msg.media:
    media_val = getattr(msg.media, 'value', str(msg.media))
    media_obj = getattr(msg, media_val, None)
    if media_obj:
      file_name = getattr(media_obj, 'file_name', '') or ''
      file_size = getattr(media_obj, 'file_size', 0) or 0
    if msg.caption:
      fcaption = msg.caption.html if hasattr(msg.caption, 'html') else str(msg.caption)
  elif msg.text:
    fcaption = msg.text.html if hasattr(msg.text, 'html') else str(msg.text)

  cleaned = clean_caption_advanced(fcaption, user_configs, lecture_index=lecture_index, file_name=file_name)

  final_text = cleaned
  if caption:
    try:
      res = caption.format(
        filename=file_name,
        size=get_size(file_size),
        caption=cleaned or ""
      )
      final_text = res.strip() if res.strip() else None
    except Exception:
      final_text = cleaned

  header_banner = user_configs.get('course_brand_header')
  footer_banner = user_configs.get('course_brand_footer')
  max_len = 1024 if getattr(msg, 'media', None) else 4096

  if header_banner or footer_banner or (final_text and len(final_text) > max_len):
    final_text = build_media_caption(header=header_banner, body=final_text or "", footer=footer_banner, max_len=max_len)

  return final_text.strip() if final_text and final_text.strip() else None

def get_size(size):
  units = ["Bytes", "KB", "MB", "GB", "TB", "PB", "EB"]
  size = float(size)
  i = 0
  while size >= 1024.0 and i < len(units):
     i += 1
     size /= 1024.0
  return "%.2f %s" % (size, units[i]) 

def media(msg):
  if msg.media:
     media = getattr(msg, msg.media.value, None)
     if media:
        return getattr(media, 'file_id', None)
  return None 

def TimeFormatter(milliseconds: int) -> str:
    try:
        ms = int(float(milliseconds))
    except Exception:
        ms = 0
    seconds, ms = divmod(ms, 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    tmp = ((str(days) + "d, ") if days else "") + \
        ((str(hours) + "h, ") if hours else "") + \
        ((str(minutes) + "m, ") if minutes else "") + \
        ((str(seconds) + "s, ") if seconds else "") + \
        ((str(ms) + "ms, ") if ms else "")
    return tmp[:-2] if tmp else "0s"

def retry_btn(id):
    return colored_markup([
        [InlineKeyboardButton('♻️ ʀᴇᴛʀʏ ♻️', callback_data=f"start_public_{id}")],
        [InlineKeyboardButton('❌ ᴄʟᴏsᴇ', callback_data="close_btn")]
    ])

@Client.on_callback_query(filters.regex(r'^terminate_frwd$'))
async def terminate_frwding(bot, m):
    user_id = m.from_user.id 
    temp.lock[user_id] = False
    temp.CANCEL[user_id] = True 
    temp.PAUSE[user_id] = False
    await m.answer("ғᴏʀᴡᴀʀᴅɪɴɢ ᴄᴀɴᴄᴇʟʟᴇᴅ !", show_alert=True)

@Client.on_callback_query(filters.regex(r'^pause_frwd'))
async def pause_callback(bot, query):
    user_id = query.from_user.id
    temp.PAUSE[user_id] = True
    await query.answer("⏸️ Forwarding Paused!", show_alert=True)
    frwd_id = query.data.split("#")[1]
    sts = STS(frwd_id)
    if sts.verify():
        await edit(query.message, 'ᴘᴀᴜsᴇᴅ', '⏸️ ᴘᴀᴜsᴇᴅ', sts)

@Client.on_callback_query(filters.regex(r'^resume_frwd'))
async def resume_callback(bot, query):
    user_id = query.from_user.id
    temp.PAUSE[user_id] = False
    await query.answer("▶️ Forwarding Resumed!", show_alert=True)
    frwd_id = query.data.split("#")[1]
    sts = STS(frwd_id)
    if sts.verify():
        await edit(query.message, 'ᴘʀᴏɢʀᴇssɪɴɢ', 10, sts)

@Client.on_callback_query(filters.regex(r'^(fwrdstatus|fstat)'))
async def status_msg(bot, msg):
    parts = msg.data.split("#")
    if len(parts) == 5:
        _, status, est_time, percentage, frwd_id = parts
        try:
            est_time = int(est_time)
        except Exception:
            est_time = 0
    else:
        _, percentage, frwd_id = parts
        sts = STS(frwd_id)
        status = sts.get('status') or 'ғᴏʀᴡᴀʀᴅɪɴɢ'
        est_time = sts.get('est_time') or 0
    sts = STS(frwd_id)
    if not sts.verify():
       fetched = forwarded = remaining = skipped = 0
    else:
       total = sts.get('total') or 0
       skipped = sts.get('skip') or 0
       fetched, forwarded = sts.get('fetched') or 0, sts.get('total_files') or 0
       remaining = max(0, total - forwarded - skipped)
       if not est_time:
           est_time = sts.get('est_time') or 0
    try:
        est_time_str = TimeFormatter(milliseconds=int(est_time))
    except Exception:
        est_time_str = '0 s'
    est_time_str = est_time_str if (est_time_str != '' or str(status).lower() not in ['completed', 'cancelled', 'ᴄᴏᴍᴘʟᴇᴛᴇᴅ', 'ᴄᴀɴᴄᴇʟʟᴇᴅ']) else '0 s'
    return await msg.answer(PROGRESS.format(percentage, fetched, forwarded, remaining, status, est_time_str), show_alert=True)

@Client.on_message(filters.command("stop"))
async def stop_forwarding(bot, message):
    user_id = message.from_user.id
    if temp.lock.get(user_id):
        temp.lock[user_id] = False
        temp.CANCEL[user_id] = True
        temp.PAUSE[user_id] = False
        try:
            t = await db.get_user_active_task(user_id)
            if t:
                await db.delete_active_task(t["task_id"])
        except Exception:
            pass
        await message.reply("🛑 ғᴏʀᴡᴀʀᴅɪɴɢ ᴄᴀɴᴄᴇʟʟᴇᴅ !", quote=True)
    else:
        try:
            t = await db.get_user_active_task(user_id)
            if t:
                await db.delete_active_task(t["task_id"])
                return await message.reply("🛑 ᴀᴄᴛɪᴠᴇ ᴛᴀsᴋ ᴄʟᴇᴀʀᴇᴅ ғʀᴏᴍ ᴅᴀᴛᴀʙᴀsᴇ.", quote=True)
        except Exception:
            pass
        await message.reply("❌ ɴᴏ ᴏɴɢᴏɪɴɢ ғᴏʀᴡᴀʀᴅɪɴɢ ᴘʀᴏᴄᴇss ᴛᴏ ᴄᴀɴᴄᴇʟ.", quote=True)

@Client.on_message(filters.command("pause"))
async def pause_command(bot, message):
    user_id = message.from_user.id
    if temp.lock.get(user_id):
        temp.PAUSE[user_id] = True
        await message.reply("⏸️ **ғᴏʀᴡᴀʀᴅɪɴɢ ᴘᴀᴜsᴇᴅ!**\nUse /resume to continue or click the Resume button.", quote=True)
    else:
        await message.reply("❌ **No ongoing forwarding process to pause.**", quote=True)

@Client.on_message(filters.command("resume"))
async def resume_command(bot, message):
    user_id = message.from_user.id
    if temp.PAUSE.get(user_id):
        temp.PAUSE[user_id] = False
        await message.reply("▶️ **ғᴏʀᴡᴀʀᴅɪɴɢ ʀᴇsᴜᴍᴇᴅ!**", quote=True)
    else:
        await message.reply("❌ **Process is not paused or not running.**", quote=True)

@Client.on_callback_query(filters.regex(r'^(close_btn|close|close_data|cmd_close|close_menu)$'))
async def close(bot, update):
    try:
        await update.answer()
    except Exception:
        pass
    try:
        await update.message.delete()
    except Exception:
        pass

@Client.on_callback_query(filters.regex(r'^(noop|utr_noop)$'))
async def noop_callback(bot, update):
    try:
        await update.answer()
    except Exception:
        pass