"""
broadcast.py — Advanced Multi-Format Broadcast & Notification Engine for Skinet Verse
──────────────────────────────────────────────────────────────────────────────────────
Features:
  • Multi-Format: Supports replying to ANY message (Media, Text, Stickers, Documents, Polls)
  • Direct Argument: Send direct text via /broadcast <message>
  • Interactive Wizard: Prompts the admin if invoked without reply or arguments
  • Pin Support: Add -pin flag to automatically pin the message in user chats
  • Live Telemetry Card: Real-time progress bar, speed (msgs/sec), ETA, and counters
  • Instant Cancellation: Stop broadcast via /cancelbroadcast or interactive inline button
  • Smart DB Hygiene: Automatically deletes deactivated users and records blocked users
  • Restart Broadcast: /broadcastrestart for one-click system online notifications
"""

import time
import asyncio
from datetime import timedelta
from pyrogram import Client, filters
from pyrogram.types import Message, CallbackQuery
from pyrogram.errors import InputUserDeactivated, FloodWait, UserIsBlocked
from config import Config
from database import db
from buttons import colored_markup, btn, btn_url

BROADCAST_STATE = {
    "is_running": False,
    "should_cancel": False,
    "started_by": None,
    "start_time": 0.0,
}


def _get_progress_bar(completed: int, total: int, length: int = 12) -> str:
    if total <= 0:
        return "░" * length
    fraction = min(1.0, max(0.0, completed / total))
    filled = int(fraction * length)
    return "█" * filled + "░" * (length - filled)


def _format_time(seconds: float) -> str:
    s = int(seconds)
    if s < 60:
        return f"{s}s"
    m, s = divmod(s, 60)
    if m < 60:
        return f"{m}m {s:02d}s"
    h, m = divmod(m, 60)
    return f"{h}h {m:02d}m"



from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

async def _run_broadcast_loop(bot: Client, user_id: int, status_msg: Message, user_ids: list, b_msg=None, b_text=None, should_pin=False, state=None):
    if not state:
        state = {
            'current_index': 0, 'sent': 0, 'failed': 0, 'deleted': 0, 'blocked': 0
        }
    
    total_users = len(user_ids)
    done = state.get('current_index', 0)
    success = state.get('sent', 0)
    failed = state.get('failed', 0)
    deleted = state.get('deleted', 0)
    blocked = state.get('blocked', 0)
    
    start_time = time.time()
    last_edit = 0.0
    cancel_btn = colored_markup([[btn("❌ ᴄᴀɴᴄᴇʟ ʙʀᴏᴀᴅᴄᴀsᴛ", "bcast_cancel", "red")]])

    try:
        for uid in user_ids[done:]:
            if BROADCAST_STATE["should_cancel"]:
                break

            try:
                sent_obj = None
                if b_msg:
                    sent_obj = await b_msg.copy(chat_id=uid)
                elif b_text:
                    sent_obj = await bot.send_message(chat_id=uid, text=b_text)

                if should_pin and sent_obj:
                    try:
                        await sent_obj.pin(both_sides=True)
                    except Exception:
                        pass
                success += 1

            except FloodWait as e:
                await asyncio.sleep(e.value + 1)
                try:
                    if b_msg:
                        sent_obj = await b_msg.copy(chat_id=uid)
                    elif b_text:
                        sent_obj = await bot.send_message(chat_id=uid, text=b_text)
                    if should_pin and sent_obj:
                        try:
                            await sent_obj.pin(both_sides=True)
                        except Exception:
                            pass
                    success += 1
                except Exception:
                    failed += 1

            except InputUserDeactivated:
                deleted += 1
                try:
                    await db.delete_user(uid)
                except Exception:
                    pass

            except UserIsBlocked:
                blocked += 1

            except Exception:
                failed += 1

            done += 1
            await asyncio.sleep(0.08)

            if done % 50 == 0:
                await db.save_broadcast_state(user_id, {
                    'user_id': user_id,
                    'total': total_users,
                    'sent': success,
                    'failed': failed,
                    'deleted': deleted,
                    'blocked': blocked,
                    'current_index': done,
                    'message_id': b_msg.id if b_msg else None,
                    'chat_id': b_msg.chat.id if b_msg else None,
                    'text': b_text,
                    'pin': should_pin
                })

            now = time.time()
            if done % 25 == 0 or (now - last_edit >= 3.0) or done == total_users:
                last_edit = now
                elapsed = max(0.1, now - start_time)
                session_done = done - state.get('current_index', 0)
                speed = session_done / elapsed if elapsed > 0 else 0
                pct = int((done / total_users) * 100) if total_users > 0 else 100
                bar = _get_progress_bar(done, total_users, 10)
                eta = (total_users - done) / speed if speed > 0 else 0

                progress_text = (
                    f"<blockquote><b>📢 <u>sᴋɪɴᴇᴛ ᴠᴇʀsᴇ — ʙʀᴏᴀᴅᴄᴀsᴛ ɪɴ ᴘʀᴏɢʀᴇss</u></b></blockquote>\n\n"
                    f"📊 <b>ᴘʀᴏɢʀᴇss:</b> <code>{pct}% [{bar}]</code>\n"
                    f"👥 <b>ᴘʀᴏᴄᴇssᴇᴅ:</b> <code>{done} / {total_users}</code>\n"
                    f"✅ <b>ᴅᴇʟɪᴠᴇʀᴇᴅ:</b> <code>{success}</code>\n"
                    f"🚫 <b>ʙʟᴏᴄᴋᴇᴅ:</b> <code>{blocked}</code>\n"
                    f"🗑 <b>ᴅᴇʟᴇᴛᴇᴅ:</b> <code>{deleted}</code>\n"
                    f"⚠️ <b>ғᴀɪʟᴇᴅ:</b> <code>{failed}</code>\n\n"
                    f"⚡ <b>sᴘᴇᴇᴅ:</b> <code>{speed:.1f} ᴍsɢs/s</code>\n"
                    f"⏰ <b>ᴇʟᴀᴘsᴇᴅ:</b> <code>{_format_time(elapsed)}</code> | ⏳ <b>ᴇᴛᴀ:</b> <code>{_format_time(eta)}</code>"
                )
                try:
                    await status_msg.edit_text(progress_text, reply_markup=cancel_btn)
                except Exception:
                    pass

    finally:
        total_time = max(0.1, time.time() - start_time)
        session_done = done - state.get('current_index', 0)
        avg_speed = session_done / total_time if total_time > 0 else 0
        was_cancelled = BROADCAST_STATE["should_cancel"]
        BROADCAST_STATE["is_running"] = False
        BROADCAST_STATE["should_cancel"] = False

        status_title = "🛑 <u>ʙʀᴏᴀᴅᴄᴀsᴛ ᴄᴀɴᴄᴇʟʟᴇᴅ</u>" if was_cancelled else "✅ <u>ʙʀᴏᴀᴅᴄᴀsᴛ ᴄᴏᴍᴘʟᴇᴛᴇᴅ</u>"
        status_sub = "<i>ʙʀᴏᴀᴅᴄᴀsᴛ ʜᴀʟᴛᴇᴅ ʙʏ ᴀᴅᴍɪɴɪsᴛʀᴀᴛᴏʀ.</i>" if was_cancelled else "<i>ʙʀᴏᴀᴅᴄᴀsᴛ ᴅᴇʟɪᴠᴇʀᴇᴅ sᴜᴄᴄᴇssғᴜʟʟʏ ᴀᴄʀᴏss ᴀʟʟ ᴜsᴇʀs!</i>"

        final_text = (
            f"<blockquote><b>📢 {status_title}</b></blockquote>\n\n"
            f"{status_sub}\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"👥 <b>ᴛᴏᴛᴀʟ ᴛᴀʀɢᴇᴛ ᴜsᴇʀs:</b> <code>{total_users}</code>\n"
            f"📥 <b>ᴛᴏᴛᴀʟ ᴘʀᴏᴄᴇssᴇᴅ:</b> <code>{done}</code>\n"
            f"✅ <b>sᴜᴄᴄᴇssғᴜʟʟʏ ᴅᴇʟɪᴠᴇʀᴇᴅ:</b> <code>{success}</code>\n"
            f"🚫 <b>ʙʟᴏᴄᴋᴇᴅ ᴛʜᴇ ʙᴏᴛ:</b> <code>{blocked}</code>\n"
            f"🗑 <b>ᴅᴇʟᴇᴛᴇᴅ ᴀᴄᴄᴏᴜɴᴛs:</b> <code>{deleted}</code>\n"
            f"⚠️ <b>ғᴀɪʟᴇᴅ / ᴇʀʀᴏʀs:</b> <code>{failed}</code>\n"
            f"⏱ <b>sᴇssɪᴏɴ ᴛɪᴍᴇ ᴛᴀᴋᴇɴ:</b> <code>{_format_time(total_time)}</code>\n"
            f"⚡ <b>ᴀᴠᴇʀᴀɢᴇ ᴛʜʀᴏᴜɢʜᴘᴜᴛ:</b> <code>{avg_speed:.1f} ᴍsɢs/s</code>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"<i>⚡ sᴋɪɴᴇᴛ ᴠᴇʀsᴇ ᴀᴜᴛᴏᴍᴀᴛᴇᴅ ᴛᴇʟᴇᴍᴇᴛʀʏ</i>"
        )
        
        if not was_cancelled or done >= total_users:
            await db.delete_broadcast_state(user_id)
        else:
            await db.save_broadcast_state(user_id, {
                'user_id': user_id,
                'total': total_users,
                'sent': success,
                'failed': failed,
                'deleted': deleted,
                'blocked': blocked,
                'current_index': done,
                'message_id': b_msg.id if b_msg else None,
                'chat_id': b_msg.chat.id if b_msg else None,
                'text': b_text,
                'pin': should_pin
            })
            
        try:
            await status_msg.edit_text(final_text)
        except Exception:
            pass

@Client.on_callback_query(filters.regex("^bcast_action_(resume|discard)$"))
async def bcast_action_callback(bot: Client, query: CallbackQuery):
    user_id = query.from_user.id
    if not await db.is_admin(user_id):
        return await query.answer("⚠️ ᴀᴄᴄᴇss ᴅᴇɴɪᴇᴅ", show_alert=True)
    
    action = query.matches[0].group(1)
    
    if action == "discard":
        await db.delete_broadcast_state(user_id)
        await query.message.edit_text("✅ <b>ᴘʀᴇᴠɪᴏᴜs ʙʀᴏᴀᴅᴄᴀsᴛ sᴛᴀᴛᴇ ᴅɪsᴄᴀʀᴅᴇᴅ.</b> ʏᴏᴜ ᴄᴀɴ sᴛᴀʀᴛ ᴀ ɴᴇᴡ ᴏɴᴇ.")
        return

    state = await db.get_broadcast_state(user_id)
    if not state:
        return await query.message.edit_text("⚠️ <b>ɴᴏ sᴀᴠᴇᴅ ʙʀᴏᴀᴅᴄᴀsᴛ sᴛᴀᴛᴇ ғᴏᴜɴᴅ.</b>")
        
    b_msg_id = state.get('message_id')
    b_chat_id = state.get('chat_id')
    b_text = state.get('text')
    should_pin = state.get('pin', False)
    
    b_msg = None
    if b_msg_id and b_chat_id:
        try:
            b_msg = await bot.get_messages(b_chat_id, b_msg_id)
        except Exception:
            pass
            
    users_cursor = await db.get_all_users()
    user_ids = [u['id'] async for u in users_cursor if 'id' in u and u['id']]
    user_ids = list(dict.fromkeys(user_ids))
    
    BROADCAST_STATE["is_running"] = True
    BROADCAST_STATE["should_cancel"] = False
    BROADCAST_STATE["started_by"] = user_id
    BROADCAST_STATE["start_time"] = time.time()
    
    await query.message.edit_text("▶️ <b>ʀᴇsᴜᴍɪɴɢ ʙʀᴏᴀᴅᴄᴀsᴛ...</b>")
    status_msg = await bot.send_message(user_id, "⏳ <b>sᴛᴀᴛᴜs:</b> <code>ʀᴇsᴜᴍɪɴɢ...</code>")
    
    await _run_broadcast_loop(bot, user_id, status_msg, user_ids, b_msg, b_text, should_pin, state)


@Client.on_message(filters.private & filters.command(["broadcast", "bcast"]))
async def broadcast_handler(bot: Client, message: Message):
    user_id = message.from_user.id
    if not await db.is_admin(user_id):
        return await message.reply_text("⚠️ <b>ᴀᴄᴄᴇss ᴅᴇɴɪᴇᴅ:</b> ʀᴇsᴛʀɪᴄᴛᴇᴅ ᴛᴏ ʙᴏᴛ ᴀᴅᴍɪɴɪsᴛʀᴀᴛᴏʀs.", quote=True)

    if BROADCAST_STATE["is_running"]:
        return await message.reply_text(
            "<blockquote><b>⚠️ ᴀ ʙʀᴏᴀᴅᴄᴀsᴛ ɪs ᴀʟʀᴇᴀᴅʏ ʀᴜɴɴɪɴɢ!</b>\n\n"
            "ᴜsᴇ <code>/cancelbroadcast</code> ᴛᴏ ʜᴀʟᴛ ᴛʜᴇ ᴀᴄᴛɪᴠᴇ ᴘʀᴏᴄᴇss.</blockquote>",
            quote=True
        )

    saved_state = await db.get_broadcast_state(user_id)
    if saved_state:
        from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        resume_markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("▶️ ʀᴇsᴜᴍᴇ", callback_data="bcast_action_resume"),
             InlineKeyboardButton("🗑 ᴅɪsᴄᴀʀᴅ", callback_data="bcast_action_discard")]
        ])
        return await message.reply_text(
            f"⚠️ <b>ʏᴏᴜ ʜᴀᴠᴇ ᴀɴ ɪɴᴄᴏᴍᴘʟᴇᴛᴇ ʙʀᴏᴀᴅᴄᴀsᴛ!</b>\n\n"
            f"📊 <b>ᴘʀᴏɢʀᴇss:</b> <code>{saved_state.get('current_index', 0)} / {saved_state.get('total', 0)}</code>\n\n"
            f"ᴅᴏ ʏᴏᴜ ᴡᴀɴᴛ ᴛᴏ ʀᴇsᴜᴍᴇ ɪᴛ ᴏʀ ᴅɪsᴄᴀʀᴅ ɪᴛ ᴀɴᴅ sᴛᴀʀᴛ ᴀ ɴᴇᴡ ᴏɴᴇ?",
            reply_markup=resume_markup
        )

    b_msg = message.reply_to_message
    b_text = None
    should_pin = False

    cmd_parts = message.text.split(None, 1) if message.text else []
    if len(cmd_parts) > 1:
        raw_text = cmd_parts[1].strip()
        if "-pin" in raw_text:
            should_pin = True
            raw_text = raw_text.replace("-pin", "").strip()
        b_text = raw_text

    if b_msg:
        if b_msg.text and "-pin" in b_msg.text:
            should_pin = True
        elif b_msg.caption and "-pin" in b_msg.caption:
            should_pin = True

    if not b_msg and not b_text:
        try:
            prompt_msg = await bot.ask(
                chat_id=user_id,
                text=(
                    "<blockquote><b>📢 <u>sᴋɪɴᴇᴛ ᴠᴇʀsᴇ — ʙʀᴏᴀᴅᴄᴀsᴛ ᴄᴇɴᴛᴇʀ</u></b></blockquote>\n\n"
                    "ᴘʟᴇᴀsᴇ sᴇɴᴅ ᴏʀ ғᴏʀᴡᴀʀᴅ ᴛʜᴇ ᴍᴇssᴀɢᴇ ʏᴏᴜ ᴡɪsʜ ᴛᴏ ʙʀᴏᴀᴅᴄᴀsᴛ ᴛᴏ ᴀʟʟ ʀᴇɢɪsᴛᴇʀᴇᴅ ᴜsᴇʀs.\n\n"
                    "• <b>sᴜᴘᴘᴏʀᴛᴇᴅ:</b> ᴛᴇxᴛ, ᴘʜᴏᴛᴏs, ᴠɪᴅᴇᴏs, ᴅᴏᴄᴜᴍᴇɴᴛs, ᴀᴜᴅɪᴏ, ᴠᴏɪᴄᴇ, sᴛɪᴄᴋᴇʀs\n"
                    "• <b>ᴘɪɴ ᴏᴘᴛɪᴏɴ:</b> ɪɴᴄʟᴜᴅᴇ <code>-pin</code> ɪɴ ᴛᴇxᴛ/ᴄᴀᴘᴛɪᴏɴ ᴛᴏ ᴀᴜᴛᴏ-ᴘɪɴ\n"
                    "• <b>ᴄᴀɴᴄᴇʟ:</b> sᴇɴᴅ <code>/cancel</code> ᴛᴏ ᴀʙᴏʀᴛ."
                ),
                timeout=180
            )
        except Exception:
            return await message.reply_text("⏱ <b>ᴛɪᴍᴇᴏᴜᴛ:</b> ʙʀᴏᴀᴅᴄᴀsᴛ sᴇᴛᴜᴘ ᴄᴀɴᴄᴇʟʟᴇᴅ (3 ᴍɪɴᴜᴛᴇs ᴇʟᴀᴘsᴇᴅ).")

        if not prompt_msg or not prompt_msg.text or prompt_msg.text == "/cancel":
            return await message.reply_text("❌ <b>ʙʀᴏᴀᴅᴄᴀsᴛ sᴇᴛᴜᴘ ᴄᴀɴᴄᴇʟʟᴇᴅ.</b>")

        if prompt_msg.text and "-pin" in prompt_msg.text:
            should_pin = True
            prompt_msg.text = prompt_msg.text.replace("-pin", "").strip()
        elif prompt_msg.caption and "-pin" in prompt_msg.caption:
            should_pin = True
            prompt_msg.caption = prompt_msg.caption.replace("-pin", "").strip()

        b_msg = prompt_msg

    try:
        users_cursor = await db.get_all_users()
        user_ids = [u['id'] async for u in users_cursor if 'id' in u and u['id']]
        user_ids = list(dict.fromkeys(user_ids))
    except Exception as e:
        return await message.reply_text(f"❌ <b>ᴅᴀᴛᴀʙᴀsᴇ ᴇʀʀᴏʀ:</b> ғᴀɪʟᴇᴅ ᴛᴏ ғᴇᴛᴄʜ ᴜsᴇʀs: <code>{e}</code>")

    total_users = len(user_ids)
    if not total_users:
        return await message.reply_text("⚠️ <b>ɴᴏ ᴜsᴇʀs ғᴏᴜɴᴅ ɪɴ ᴅᴀᴛᴀʙᴀsᴇ ᴛᴏ ʙʀᴏᴀᴅᴄᴀsᴛ ᴛᴏ.</b>")

    BROADCAST_STATE["is_running"] = True
    BROADCAST_STATE["should_cancel"] = False
    BROADCAST_STATE["started_by"] = user_id
    BROADCAST_STATE["start_time"] = time.time()

    cancel_btn = colored_markup([[btn("❌ ᴄᴀɴᴄᴇʟ ʙʀᴏᴀᴅᴄᴀsᴛ", "bcast_cancel", "red")]])

    status_msg = await message.reply_text(
        f"<blockquote><b>📢 <u>sᴋɪɴᴇᴛ ᴠᴇʀsᴇ — ʙʀᴏᴀᴅᴄᴀsᴛ ɪɴɪᴛɪᴀᴛᴇᴅ</u></b></blockquote>\n\n"
        f"👥 <b>ᴛᴏᴛᴀʟ ᴛᴀʀɢᴇᴛ ᴜsᴇʀs:</b> <code>{total_users}</code>\n"
        f"📌 <b>ᴀᴜᴛᴏ-ᴘɪɴ:</b> <code>{'ᴇɴᴀʙʟᴇᴅ ✅' if should_pin else 'ᴅɪsᴀʙʟᴇᴅ ❌'}</code>\n"
        f"⏳ <b>sᴛᴀᴛᴜs:</b> <code>ᴅɪsᴘᴀᴛᴄʜɪɴɢ ᴍᴇssᴀɢᴇs...</code>",
        reply_markup=cancel_btn
    )

    await _run_broadcast_loop(bot, user_id, status_msg, user_ids, b_msg, b_text, should_pin)



@Client.on_message(filters.private & filters.command(["cancelbroadcast", "bcastcancel"]))
async def cancel_broadcast_cmd(bot: Client, message: Message):
    user_id = message.from_user.id
    if not await db.is_admin(user_id):
        return await message.reply_text("⚠️ <b>ᴀᴄᴄᴇss ᴅᴇɴɪᴇᴅ:</b> ʀᴇsᴛʀɪᴄᴛᴇᴅ ᴛᴏ ʙᴏᴛ ᴀᴅᴍɪɴɪsᴛʀᴀᴛᴏʀs.", quote=True)

    if not BROADCAST_STATE["is_running"]:
        return await message.reply_text("ℹ️ <b>ɴᴏ ʙʀᴏᴀᴅᴄᴀsᴛ ɪs ᴄᴜʀʀᴇɴᴛʟʏ ʀᴜɴɴɪɴɢ.</b>", quote=True)

    BROADCAST_STATE["should_cancel"] = True
    await message.reply_text("🛑 <b>ᴄᴀɴᴄᴇʟʟᴀᴛɪᴏɴ sɪɢɴᴀʟ sᴇɴᴛ!</b> ᴛʜᴇ ʙʀᴏᴀᴅᴄᴀsᴛ ᴡɪʟʟ ʜᴀʟᴛ sʜᴏʀᴛʟʏ.", quote=True)


@Client.on_callback_query(filters.regex("^bcast_cancel$"))
async def cancel_broadcast_callback(bot: Client, query: CallbackQuery):
    user_id = query.from_user.id
    if not await db.is_admin(user_id):
        return await query.answer("⚠️ ᴀᴄᴄᴇss ᴅᴇɴɪᴇᴅ: ᴀᴅᴍɪɴ ᴏɴʟʏ.", show_alert=True)

    if not BROADCAST_STATE["is_running"]:
        return await query.answer("ℹ️ ʙʀᴏᴀᴅᴄᴀsᴛ ɪs ɴᴏᴛ ᴄᴜʀʀᴇɴᴛʟʏ ᴀᴄᴛɪᴠᴇ.", show_alert=True)

    BROADCAST_STATE["should_cancel"] = True
    await query.answer("🛑 ʙʀᴏᴀᴅᴄᴀsᴛ ɪs ʙᴇɪɴɢ sᴛᴏᴘᴘᴇᴅ...", show_alert=True)


@Client.on_message(filters.private & filters.command(["broadcastrestart", "bcastrestart"]))
async def broadcast_restart_notice(bot: Client, message: Message):
    """Convenience command: One-click broadcast announcing system restart & resumption."""
    user_id = message.from_user.id
    if not await db.is_admin(user_id):
        return await message.reply_text("⚠️ <b>ᴀᴄᴄᴇss ᴅᴇɴɪᴇᴅ:</b> ʀᴇsᴛʀɪᴄᴛᴇᴅ ᴛᴏ ʙᴏᴛ ᴀᴅᴍɪɴɪsᴛʀᴀᴛᴏʀs.", quote=True)

    if BROADCAST_STATE["is_running"]:
        return await message.reply_text("⚠️ ᴀ ʙʀᴏᴀᴅᴄᴀsᴛ ɪs ᴀʟʀᴇᴀᴅʏ ɪɴ ᴘʀᴏɢʀᴇss.", quote=True)

    bot_user = getattr(bot, "username", "codexup_bot")
    notice_text = (
        f"<blockquote><b>🤖 <u>sᴋɪɴᴇᴛ ᴠᴇʀsᴇ — sʏsᴛᴇᴍ ᴜᴘᴅᴀᴛᴇ ɴᴏᴛɪᴄᴇ</u></b></blockquote>\n\n"
        f"⚡ <b>sᴛᴀᴛᴜs:</b> <code>ᴏɴʟɪɴᴇ & ғᴜʟʟʏ ᴏᴘᴇʀᴀᴛɪᴏɴᴀʟ ✅</code>\n\n"
        f"ᴛʜᴇ ʙᴏᴛ ʜᴀs ᴄᴏᴍᴘʟᴇᴛᴇᴅ ᴀ ᴄᴏʀᴇ sʏsᴛᴇᴍ ʀᴇʙᴏᴏᴛ & ᴍᴀɪɴᴛᴇɴᴀɴᴄᴇ ᴜᴘᴅᴀᴛᴇ.\n"
        f"ᴀʟʟ ᴀᴜᴛᴏ-ғᴏʀᴡᴀʀᴅɪɴɢ ᴘɪᴘᴇʟɪɴᴇs, ᴀᴜᴛᴏsᴀᴠᴇ ᴍᴏɴɪᴛᴏʀs, ᴀɴᴅ ᴄʜᴀɴɴᴇʟs ᴀʀᴇ ᴀᴄᴛɪᴠᴇ!\n\n"
        f"👇 <i>ᴄʟɪᴄᴋ ʙᴇʟᴏᴡ ᴛᴏ ᴏᴘᴇɴ ʏᴏᴜʀ ʙᴏᴛ ᴅᴀsʜʙᴏᴀʀᴅ:</i>"
    )
    bot_markup = colored_markup([[btn_url("🚀 ᴏᴘᴇɴ ʙᴏᴛ ᴅᴀsʜʙᴏᴀʀᴅ", f"https://t.me/{bot_user}?start=start", "green")]])

    users_cursor = await db.get_all_users()
    user_ids = [u['id'] async for u in users_cursor if 'id' in u and u['id']]
    user_ids = list(dict.fromkeys(user_ids))
    total_users = len(user_ids)

    if not total_users:
        return await message.reply_text("⚠️ ɴᴏ ᴜsᴇʀs ғᴏᴜɴᴅ ɪɴ ᴅᴀᴛᴀʙᴀsᴇ.")

    BROADCAST_STATE["is_running"] = True
    BROADCAST_STATE["should_cancel"] = False
    BROADCAST_STATE["started_by"] = user_id
    BROADCAST_STATE["start_time"] = time.time()

    cancel_btn = colored_markup([[btn("❌ ᴄᴀɴᴄᴇʟ", "bcast_cancel", "red")]])
    status_msg = await message.reply_text(
        f"<blockquote><b>📢 <u>ʙʀᴏᴀᴅᴄᴀsᴛɪɴɢ ʀᴇsᴛᴀʀᴛ ɴᴏᴛɪᴄᴇ</u></b></blockquote>\n\n"
        f"👥 <b>ᴛᴀʀɢᴇᴛ ᴜsᴇʀs:</b> <code>{total_users}</code>\n"
        f"⏳ <b>sᴛᴀᴛᴜs:</b> <code>ᴅɪsᴘᴀᴛᴄʜɪɴɢ ᴜᴘᴅᴀᴛᴇ ɴᴏᴛɪᴄᴇ...</code>",
        reply_markup=cancel_btn
    )

    done = 0
    success = 0
    start_time = time.time()

    try:
        for uid in user_ids:
            if BROADCAST_STATE["should_cancel"]:
                break
            try:
                await bot.send_message(chat_id=uid, text=notice_text, reply_markup=bot_markup)
                success += 1
            except FloodWait as e:
                await asyncio.sleep(e.value + 1)
                try:
                    await bot.send_message(chat_id=uid, text=notice_text, reply_markup=bot_markup)
                    success += 1
                except Exception:
                    pass
            except Exception:
                pass

            done += 1
            await asyncio.sleep(0.08)

            if done % 30 == 0 or done == total_users:
                pct = int((done / total_users) * 100)
                bar = _get_progress_bar(done, total_users, 10)
                try:
                    await status_msg.edit_text(
                        f"<blockquote><b>📢 <u>ʙʀᴏᴀᴅᴄᴀsᴛɪɴɢ ʀᴇsᴛᴀʀᴛ ɴᴏᴛɪᴄᴇ</u></b></blockquote>\n\n"
                        f"📊 <b>ᴘʀᴏɢʀᴇss:</b> <code>{pct}% [{bar}]</code>\n"
                        f"👥 <b>ᴅᴇʟɪᴠᴇʀᴇᴅ:</b> <code>{success} / {total_users}</code>",
                        reply_markup=cancel_btn
                    )
                except Exception:
                    pass
    finally:
        BROADCAST_STATE["is_running"] = False
        BROADCAST_STATE["should_cancel"] = False
        try:
            await status_msg.edit_text(
                f"<blockquote><b>✅ <u>ʀᴇsᴛᴀʀᴛ ɴᴏᴛɪᴄᴇ ʙʀᴏᴀᴅᴄᴀsᴛ ᴄᴏᴍᴘʟᴇᴛᴇ</u></b></blockquote>\n\n"
                f"ᴅᴇʟɪᴠᴇʀᴇᴅ ᴜᴘᴅᴀᴛᴇ ɴᴏᴛɪᴄᴇ ᴛᴏ <code>{success}</code> ᴜsᴇʀs ɪɴ <code>{_format_time(time.time() - start_time)}</code>."
            )
        except Exception:
            pass
