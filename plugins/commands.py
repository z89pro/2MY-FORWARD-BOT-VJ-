import os
import re
import sys
import asyncio 
import datetime
try:
    import psutil
except ImportError:
    psutil = None
from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from buttons import btn, btn_url, row, markup, colored_markup
from database import db, mongodb_version
from config import Config, temp
from platform import python_version
from translation import Translation
from pyrogram import Client, filters, enums, __version__ as pyrogram_version
from pyrogram.errors import ListenerTimeout

def get_main_buttons(user_id=None, is_admin=False):
    is_admin = is_admin or bool(user_id and user_id in Config.BOT_OWNER_ID)
    rows = [
        row(
            btn('➕ ᴀᴅᴅ ʙᴏᴛ', 'settings#bots', 'green'),
            btn('📡 ᴀᴅᴅ ᴄʜᴀɴɴᴇʟ', 'settings#addchannel', 'green')
        ),
        row(
            btn('⚙️ sᴇᴛᴛɪɴɢs', 'settings#main', 'blue'),
            btn('🚀 sᴍᴀʀᴛ ᴀᴜᴛᴏsᴀᴠᴇ', 'autosave#main', 'green')
        ),
        row(
            btn('🎓 ᴄᴏᴜʀsᴇ sᴇʟʟᴇʀ', 'settings#courseseller', 'yellow'),
            btn('💎 ᴠɪᴘ ᴘʀᴇᴍɪᴜᴍ', 'prem_plans', 'green')
        ),
        row(
            btn('🎁 ʀᴇғᴇʀ & ᴇᴀʀɴ', 'referral#main', 'blue'),
            btn('📚 ᴛᴜᴛᴏʀɪᴀʟ ʜᴜʙ', 'tutorial#menu', 'blue')
        ),
        row(
            btn('🛡️ ᴠᴇʀɪғʏ ᴘᴀss', 'verify_menu_btn', 'green'),
            btn('📊 sᴛᴀᴛᴜs', 'status', 'blue')
        ),
        row(
            btn('🧭 ᴄᴏᴍᴍᴀɴᴅ ᴍᴇɴᴜ', 'cmd_tab_all', 'blue'),
            btn('📖 ʜᴏᴡ ᴛᴏ ᴜsᴇ', 'how_to_use', 'blue')
        )
    ]
    if is_admin:
        rows.append(row(
            btn('📈 ᴜsᴇʀ ᴛʀᴀᴄᴋɪɴɢ', 'utr_overview', 'blue'),
            btn('⚙️ sʏsᴛᴇᴍ ᴄᴏɴғɪɢ', 'config#main', 'green')
        ))
    rows.append(row(
        btn('❌ ᴄʟᴏsᴇ', 'close_btn', 'red')
    ))
    return markup(*rows)

main_buttons = get_main_buttons()

#===================Start Function===================#

@Client.on_message(filters.private & filters.command(['start']))
async def start(client, message):
    user = message.from_user
    is_banned, ban_reason = await db.is_user_banned(user.id)
    if is_banned:
        return await message.reply_text(
            f"<blockquote><b>🚫 <u>ᴀᴄᴄᴏᴜɴᴛ sᴜsᴘᴇɴᴅᴇᴅ</u></b></blockquote>\n\n"
            f"ʏᴏᴜ ʜᴀᴠᴇ ʙᴇᴇɴ ʙᴀɴɴᴇᴅ ғʀᴏᴍ ᴜsɪɴɢ ᴛʜɪs ʙᴏᴛ.\n"
            f"<b>ʀᴇᴀsᴏɴ:</b> {ban_reason}\n\n"
            f"<i>ɪғ ʏᴏᴜ ʙᴇʟɪᴇᴠᴇ ᴛʜɪs ɪs ᴀɴ ᴇʀʀᴏʀ, ᴄᴏɴᴛᴀᴄᴛ ᴛʜᴇ ᴀᴅᴍɪɴɪsᴛʀᴀᴛᴏʀ.</i>"
        )

    # Verification token deep-link: /start vrf_{token} or /start verify_{token}
    if len(message.command) > 1 and (message.command[1].startswith("verify_") or message.command[1].startswith("vrf_")):
        try:
            from plugins.verify import handle_verify_callback
            handled = await handle_verify_callback(client, message, message.command[1])
            if handled:
                return
        except Exception:
            pass

    if Config.FORCE_SUB_ON and Config.FORCE_SUB_CHANNEL:
        try:
            member = await client.get_chat_member(Config.FORCE_SUB_CHANNEL, user.id)
            if member.status in [enums.ChatMemberStatus.BANNED, "kicked"]:
                await client.send_message(
                    chat_id=message.chat.id,
                    text="You are banned from using this bot.",
                )
                return
        except Exception:
            channel_url = Config.FORCE_SUB_CHANNEL if Config.FORCE_SUB_CHANNEL.startswith("http") else f"https://t.me/{Config.FORCE_SUB_CHANNEL.lstrip('@')}"
            join_button = [
                [InlineKeyboardButton("ᴊᴏɪɴ ᴄʜᴀɴɴᴇʟ", url=channel_url)],
                [InlineKeyboardButton("↻ ᴛʀʏ ᴀɢᴀɪɴ", url=f"https://t.me/{client.username}?start=start")]
            ]
            await client.send_message(
                chat_id=message.chat.id,
                text="ᴘʟᴇᴀsᴇ ᴊᴏɪɴ ᴏᴜʀ ᴄʜᴀɴɴᴇʟ ᴛᴏ ᴜsᴇ ᴛʜɪs ʙᴏᴛ.",
                reply_markup=InlineKeyboardMarkup(join_button)
            )
            return

    # Parse referral payload if present (/start ref_123456)
    ref_id = None
    if len(message.command) > 1 and message.command[1].startswith("ref_"):
        try:
            parsed_ref = int(message.command[1].replace("ref_", ""))
            if parsed_ref != user.id:
                ref_id = parsed_ref
        except Exception:
            ref_id = None

    is_new = not await db.is_user_exist(user.id)
    if is_new:
        # Store plain text. `mention` is raw HTML (<a href="tg://user?id=...">) and
        # downstream panels escape+truncate the stored name, which rendered the tag literally.
        _plain_name = (message.from_user.first_name or message.from_user.username or str(user.id))
        await db.add_user(user.id, _plain_name, referred_by=ref_id)
        if ref_id:
            credited, pts = await db.handle_referral_join(user.id, ref_id)
            if credited:
                try:
                    await client.send_message(
                        ref_id,
                        f"🎉 <b>New Referral Joined!</b>\n\n"
                        f"👤 <b>{user.mention}</b> joined Skinet Verse using your invite link!\n"
                        f"💎 You earned <b>+{pts} Referral Points</b>!\n\n"
                        f"Check your balance and redeem perks in /referral."
                    )
                except Exception:
                    pass
        if Config.LOG_CHANNEL:
            try:
                ref_txt = f"\n🔗 Rᴇғᴇʀʀᴇᴅ Bʏ: <code>{ref_id}</code>" if ref_id else ""
                await client.send_message(
                    chat_id=Config.LOG_CHANNEL,
                    text=f"#NewUser\n\nIᴅ - {user.id}\nNᴀᴍᴇ - {message.from_user.mention}{ref_txt}"
                )
            except Exception:
                pass
    else:
        _plain_name = (message.from_user.first_name or message.from_user.username or str(user.id))
        await db.touch_user(user.id, _plain_name)

    # Guided first-run readiness check
    custom_b = await db.get_custom_bot(user.id)
    ubot = await db.get_userbot(user.id)
    chans = await db.get_user_channels(user.id)

    readiness = (
        f"\n\n<blockquote><b>🚀 <u>ғᴏʀᴡᴀʀᴅ ʀᴇᴀᴅɪɴᴇss</u></b>\n"
        f"• 🤖 <b>ʙᴏᴛ ᴛᴏᴋᴇɴ:</b> {('<code>' + custom_b['name'] + '</code> ✅') if custom_b else '<code>ɴᴏᴛ sᴇᴛ</code> ⚠️'}\n"
        f"• 👤 <b>ᴜsᴇʀʙᴏᴛ:</b> {('<code>' + ubot['name'] + '</code> ✅') if ubot else '<code>ɴᴏᴛ sᴇᴛ</code> ⚠️'}\n"
        f"• 🎯 <b>ᴛᴀʀɢᴇᴛ:</b> {f'<code>{len(chans)} ᴄʜᴀɴɴᴇʟ(s)</code> ✅' if chans else '<code>ɴᴏᴛ sᴇᴛ</code> ⚠️'}</blockquote>"
    )

    is_adm = await db.is_admin(user.id)
    reply_markup = get_main_buttons(user.id, is_admin=is_adm)
    extra_welcome = "\n\n🎁 <i>You joined via an invite link! Claim your welcome bonus in /referral!</i>" if (is_new and ref_id) else ""
    await message.reply_text(
        text=Translation.START_TXT.format(message.from_user.first_name) + extra_welcome + readiness,
        reply_markup=reply_markup,
        quote=True
    )

#==================Restart Function==================#

@Client.on_message(filters.command(['restart', 'reboot', 'botrestart', 'restarr']))
async def restart(client, message):
    user_id = message.from_user.id if message.from_user else (message.sender_chat.id if message.sender_chat else 0)
    if not user_id or not await db.is_admin(user_id):
        return await message.reply_text("⚠️ <b>ᴀᴄᴄᴇss ᴅᴇɴɪᴇᴅ:</b> ᴛʜɪs ᴄᴏᴍᴍᴀɴᴅ ɪs ʀᴇsᴛʀɪᴄᴛᴇᴅ ᴛᴏ ʙᴏᴛ ᴀᴅᴍɪɴɪsᴛʀᴀᴛᴏʀs.", quote=True)

    from datetime import datetime, timezone, timedelta
    ist = timezone(timedelta(hours=5, minutes=30))
    stamp = datetime.now(ist).strftime("%d-%b-%Y %I:%M:%S %p")
    user_name = message.from_user.first_name if message.from_user else "Admin"

    msg = await message.reply_text(
        text=Translation.RESTART_TXT.format(user_name, stamp),
        quote=True
    )
    try:
        await db.set_restart_status(message.chat.id, msg.id)
    except Exception:
        pass
    try:
        import json
        with open('.restart_status.json', 'w') as f:
            json.dump({'chat_id': message.chat.id, 'message_id': msg.id}, f)
    except Exception:
        pass

    # Stop any background live monitors cleanly
    for uid, live_cl in list(temp.LIVE_TASKS.items()):
        try:
            await live_cl.stop()
        except Exception:
            pass

    try:
        sys.stdout.flush()
        sys.stderr.flush()
    except Exception:
        pass

    await asyncio.sleep(1.5)
    args = [sys.executable]
    if sys.argv and sys.argv[0].endswith('.py'):
        args.extend(sys.argv)
    else:
        args.append("bot.py")
    os.execl(sys.executable, *args)
    
def get_help_buttons():
    return markup(
        row(
            btn('🧭 ᴀʟʟ ᴄᴏᴍᴍᴀɴᴅs', 'cmd_tab_all', 'green'),
            btn('📖 ʜᴏᴡ ᴛᴏ ᴜsᴇ ᴍᴇ', 'how_to_use', 'blue')
        ),
        row(
            btn('📚 ᴛᴜᴛᴏʀɪᴀʟ ʜᴜʙ', 'tutorial#menu', 'blue'),
            btn('🚀 sᴍᴀʀᴛ ᴀᴜᴛᴏsᴀᴠᴇ', 'autosave#main', 'green')
        ),
        row(
            btn('🎓 ᴄᴏᴜʀsᴇ sᴇʟʟᴇʀ', 'settings#courseseller', 'yellow'),
            btn('⚙️ sᴇᴛᴛɪɴɢs', 'settings#main', 'blue')
        ),
        row(
            btn('📊 sᴛᴀᴛᴜs', 'status', 'blue'),
            btn('ℹ️ ᴀʙᴏᴜᴛ', 'about', 'blue')
        ),
        row(
            btn('📜 ᴛᴇʀᴍs', 'terms_btn', 'blue'),
            btn('🔒 ᴘʀɪᴠᴀᴄʏ', 'privacy_btn', 'blue')
        ),
        row(
            btn('🔙 ʙᴀᴄᴋ ᴛᴏ ʜᴏᴍᴇ', 'back', 'blue'),
            btn('❌ ᴄʟᴏsᴇ', 'close_btn', 'red')
        )
    )

#==================Help Command==================#

@Client.on_message(filters.private & filters.command(['help']))
async def help_command(client, message):
    await message.reply_text(
        text=Translation.HELP_TXT,
        reply_markup=get_help_buttons(),
        quote=True
    )

#==================Terms & Privacy Commands==================#

@Client.on_message(filters.private & filters.command(['terms', 'tos']))
async def terms_command(client, message):
    await message.reply_text(
        text=Translation.TERMS_TXT,
        reply_markup=markup(
            row(btn('🔒 ᴘʀɪᴠᴀᴄʏ ᴘᴏʟɪᴄʏ', 'privacy_btn', 'blue')),
            row(btn('🔙 ʙᴀᴄᴋ ᴛᴏ ʜᴏᴍᴇ', 'back', 'blue'), btn('❌ ᴄʟᴏsᴇ', 'close_btn', 'red'))
        ),
        disable_web_page_preview=True,
        quote=True
    )

@Client.on_message(filters.private & filters.command(['privacy']))
async def privacy_command(client, message):
    await message.reply_text(
        text=Translation.PRIVACY_TXT,
        reply_markup=markup(
            row(btn('📜 ᴛᴇʀᴍs ᴏғ sᴇʀᴠɪᴄᴇ', 'terms_btn', 'blue')),
            row(btn('🔙 ʙᴀᴄᴋ ᴛᴏ ʜᴏᴍᴇ', 'back', 'blue'), btn('❌ ᴄʟᴏsᴇ', 'close_btn', 'red'))
        ),
        disable_web_page_preview=True,
        quote=True
    )

#==================Callback Functions==================#

@Client.on_callback_query(filters.regex(r'^help'))
async def helpcb(bot, query):
    await query.message.edit_text(
        text=Translation.HELP_TXT,
        reply_markup=get_help_buttons()
    )

@Client.on_callback_query(filters.regex(r'^how_to_use'))
async def how_to_use(bot, query):
    await query.message.edit_text(
        text=Translation.HOW_USE_TXT,
        reply_markup=markup(
            row(btn('➕ ᴀᴅᴅ ʙᴏᴛ', 'settings#bots', 'green'),
                btn('📡 ᴀᴅᴅ ᴄʜᴀɴɴᴇʟ', 'settings#addchannel', 'green')),
            row(btn('▶️ sᴛᴀʀᴛ ғᴏʀᴡᴀʀᴅɪɴɢ', 'how_to_fwd', 'green')),
            row(btn('📚 ꜰᴜʟʟ ᴛᴜᴛᴏʀɪᴀʟ ʜᴜʙ', 'tutorial#menu', 'blue')),
            row(btn('🔙 ʙᴀᴄᴋ', 'help', 'blue'), btn('❌ ᴄʟᴏsᴇ', 'close_btn', 'red'))
        ),
        disable_web_page_preview=True
    )


@Client.on_callback_query(filters.regex(r'^how_to_fwd$'))
async def how_to_fwd(bot, query):
    await query.answer(
        "sᴇɴᴅ /forward ᴛᴏ sᴛᴀʀᴛ ᴛʜᴇ ᴡɪᴢᴀʀᴅ — ᴏʀ /fwd 10-20 ᴛᴏ sᴋɪᴘ sᴛʀᴀɪɢʜᴛ ᴛᴏ ɪᴛ.",
        show_alert=True
    )

@Client.on_callback_query(filters.regex(r'^back'))
async def back(bot, query):
    is_adm = await db.is_admin(query.from_user.id)
    reply_markup = get_main_buttons(query.from_user.id, is_admin=is_adm)
    await query.message.edit_text(
       reply_markup=reply_markup,
       text=Translation.START_TXT.format(
                query.from_user.first_name))

@Client.on_callback_query(filters.regex(r'^about'))
async def about(bot, query):
    await query.message.edit_text(
        text=Translation.ABOUT_TXT,
        reply_markup=markup(
            row(
                btn('📜 ᴛᴇʀᴍs', 'terms_btn', 'blue'),
                btn('🔒 ᴘʀɪᴠᴀᴄʏ', 'privacy_btn', 'blue')
            ),
            row(btn('🔙 ʙᴀᴄᴋ', 'back', 'blue'), btn('❌ ᴄʟᴏsᴇ', 'close_btn', 'red'))
        ),
        disable_web_page_preview=True,
        parse_mode=enums.ParseMode.HTML,
    )

@Client.on_callback_query(filters.regex(r'^terms_btn'))
async def terms_cb(bot, query):
    await query.message.edit_text(
        text=Translation.TERMS_TXT,
        reply_markup=markup(
            row(btn('🔒 ᴘʀɪᴠᴀᴄʏ ᴘᴏʟɪᴄʏ', 'privacy_btn', 'blue')),
            row(btn('🔙 ʙᴀᴄᴋ', 'about', 'blue'), btn('❌ ᴄʟᴏsᴇ', 'close_btn', 'red'))
        ),
        disable_web_page_preview=True
    )

@Client.on_callback_query(filters.regex(r'^privacy_btn'))
async def privacy_cb(bot, query):
    await query.message.edit_text(
        text=Translation.PRIVACY_TXT,
        reply_markup=markup(
            row(btn('📜 ᴛᴇʀᴍs ᴏғ sᴇʀᴠɪᴄᴇ', 'terms_btn', 'blue')),
            row(btn('🔙 ʙᴀᴄᴋ', 'about', 'blue'), btn('❌ ᴄʟᴏsᴇ', 'close_btn', 'red'))
        ),
        disable_web_page_preview=True
    )

@Client.on_callback_query(filters.regex(r'^donate'))
async def donate(bot, query):
    await query.message.edit_text(
        text=Translation.DONATE_TXT,
        reply_markup=markup(row(btn('• ʙᴀᴄᴋ', 'back', 'blue'), btn('❌ ᴄʟᴏsᴇ', 'close_btn', 'red'))),
        disable_web_page_preview=True,
        parse_mode=enums.ParseMode.HTML,
    )

START_TIME = datetime.datetime.now()

# Function to calculate and format bot uptime
def format_uptime():
    uptime = datetime.datetime.now() - START_TIME
    total_seconds = uptime.total_seconds()

    days, remainder = divmod(total_seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)

    uptime_components = []
    if int(days) > 0:
        uptime_components.append(f"{int(days)} D")
    if int(hours) > 0:
        uptime_components.append(f"{int(hours)} H")
    if int(minutes) > 0:
        uptime_components.append(f"{int(minutes)} M")
    if int(seconds) > 0:
        uptime_components.append(f"{int(seconds)} Sec")

    uptime_str = ', '.join(uptime_components) if uptime_components else "0 Sec"
    return uptime_str

@Client.on_callback_query(filters.regex(r'^status'))
async def status(bot, query):
    users_count, bots_count = await db.total_users_bots_count()
    total_channels = await db.total_channels()

    # Calculate bot uptime
    uptime_str = format_uptime()
    is_adm = await db.is_admin(query.from_user.id)

    status_rows = []
    if is_adm:
        status_rows.append(row(btn('🔄 ʀᴇsᴛᴀʀᴛ ʙᴏᴛ (ᴀᴅᴍɪɴ)', 'config#restart', 'red')))
    status_rows.append(
        row(
            btn('• ʙᴀᴄᴋ', 'help', 'blue'),
            btn('• sᴇʀᴠᴇʀ sᴛᴀᴛs', 'server_status', 'blue'),
            btn('❌ ᴄʟᴏsᴇ', 'close_btn', 'red')
        )
    )

    await query.message.edit_text(
        text=Translation.STATUS_TXT.format(users_count, bots_count, temp.forwardings, total_channels),
        reply_markup=markup(*status_rows),
        parse_mode=enums.ParseMode.HTML,
        disable_web_page_preview=True,
    )

@Client.on_message(filters.private & filters.command(['status', 'stats']))
async def status_command(client: Client, message: Message):
    users_count, bots_count = await db.total_users_bots_count()
    total_channels = await db.total_channels()
    is_adm = await db.is_admin(message.from_user.id)

    status_rows = []
    if is_adm:
        status_rows.append(row(btn('🔄 ʀᴇsᴛᴀʀᴛ ʙᴏᴛ (ᴀᴅᴍɪɴ)', 'config#restart', 'red')))
    status_rows.append(
        row(
            btn('🧭 ᴄᴏᴍᴍᴀɴᴅ ᴍᴇɴᴜ', 'cmd_tab_all', 'blue'),
            btn('• sᴇʀᴠᴇʀ sᴛᴀᴛs', 'server_status', 'blue')
        )
    )
    status_rows.append(row(btn('🔙 ʜᴏᴍᴇ', 'back', 'blue'), btn('❌ ᴄʟᴏsᴇ', 'close_btn', 'red')))

    await message.reply_text(
        text=Translation.STATUS_TXT.format(users_count, bots_count, temp.forwardings, total_channels),
        reply_markup=markup(*status_rows),
        parse_mode=enums.ParseMode.HTML,
        disable_web_page_preview=True,
        quote=True
    )

@Client.on_callback_query(filters.regex(r'^server_status'))
async def server_status(bot, query):
    ram = psutil.virtual_memory().percent if psutil else "N/A"
    cpu = psutil.cpu_percent() if psutil else "N/A"

    await query.message.edit_text(
        text=Translation.SERVER_TXT.format(cpu, ram),
        reply_markup=markup(row(btn('• ʙᴀᴄᴋ', 'status', 'blue'), btn('❌ ᴄʟᴏsᴇ', 'close_btn', 'red'))),
        parse_mode=enums.ParseMode.HTML,
        disable_web_page_preview=True,
    )

#===================Donate Function===================#

@Client.on_message(filters.private & filters.command(['donate']))
async def donate_cmd(client, message):
    await message.reply_text(
        text=Translation.DONATE_TXT,
        quote=True
    )

#===================Clone Command===================#

@Client.on_message(filters.private & filters.command(['clone']))
async def clone_cmd(client, message):
    user_id = message.from_user.id
    _bot = await db.get_bot(user_id)
    if not _bot:
        return await message.reply_text("<b>❌ Please add a bot or login a UserBot in /settings first!</b>", quote=True)
    channels = await db.get_user_channels(user_id)
    if not channels:
        return await message.reply_text("<b>❌ Please set a target channel in /settings first!</b>", quote=True)
    await message.reply_text(
        "<b>⚡ <u>ᴄʜᴀɴɴᴇʟ ᴄʟᴏɴɪɴɢ ɢᴜɪᴅᴇ:</u></b>\n\n"
        "ᴛᴏ ғᴏʀᴡᴀʀᴅ ᴏʀ ᴄʟᴏɴᴇ ᴍᴇssᴀɢᴇs ғʀᴏᴍ ᴀ sᴏᴜʀᴄᴇ ᴄʜᴀɴɴᴇʟ ᴛᴏ ʏᴏᴜʀ ᴛᴀʀɢᴇᴛ:\n"
        "• ᴜsᴇ <code>/forward</code> ғᴏʀ ɪɴᴛᴇʀᴀᴄᴛɪᴠᴇ ᴡɪᴢᴀʀᴅ\n"
        "• ᴜsᴇ <code>/fwd &lt;start_link&gt; &lt;end_link&gt;</code> ғᴏʀ ᴅɪʀᴇᴄᴛ ʀᴀɴɢᴇ ғᴏʀᴡᴀʀᴅ\n"
        "• ᴜsᴇ <code>/autosave</code> ᴛᴏ ᴀᴜᴛᴏᴍᴀᴛɪᴄᴀʟʟʏ ᴍᴏɴɪᴛᴏʀ ᴄʜᴀɴɴᴇʟs ɪɴ ʀᴇᴀʟ-ᴛɪᴍᴇ.",
        reply_markup=markup(
            row(
                btn("⚙️ sᴇᴛᴛɪɴɢs", "settings#main", "blue"),
                btn("📚 ᴛᴜᴛᴏʀɪᴀʟ", "tutorial#menu", "blue")
            )
        ),
        quote=True
    )

#===================Add Bot Command===================#

@Client.on_message(filters.private & filters.command(['addbot', 'connectbot']))
async def addbot_cmd(client: Client, message: Message):
    user_id = message.from_user.id
    _bot = await db.get_bot(user_id)
    if _bot:
        status_str = f"✅ <b>ᴄᴜʀʀᴇɴᴛ ʙᴏᴛ:</b> <code>{_bot['name']}</code> (@{_bot.get('username', 'bot')})"
    else:
        status_str = "❌ <b>ᴄᴜʀʀᴇɴᴛ ʙᴏᴛ:</b> <i>ɴᴏ ʙᴏᴛ ᴏʀ ᴜsᴇʀʙᴏᴛ ᴄᴏɴɴᴇᴄᴛᴇᴅ</i>"

    buttons = [
        [
            InlineKeyboardButton("🤖 ᴀᴅᴅ ʙᴏᴛ ᴛᴏᴋᴇɴ", callback_data="settings#addbot"),
            InlineKeyboardButton("⚡ ᴀᴅᴅ ᴜsᴇʀʙᴏᴛ (sᴇssɪᴏɴ)", callback_data="settings#adduserbot")
        ],
        [
            InlineKeyboardButton("📱 ʟᴏɢɪɴ ᴜsᴇʀʙᴏᴛ (ᴏᴛᴘ)", callback_data="settings#addlogin"),
            InlineKeyboardButton("⚙️ ᴍʏ ᴄᴏɴɴᴇᴄᴛᴇᴅ ʙᴏᴛs", callback_data="settings#bots")
        ],
        [
            InlineKeyboardButton("❌ ᴄʟᴏsᴇ", callback_data="close_btn")
        ]
    ]
    await message.reply_text(
        "<blockquote><b>🤖 <u>ᴄᴏɴɴᴇᴄᴛ ʏᴏᴜʀ ʙᴏᴛ ᴏʀ ᴜsᴇʀʙᴏᴛ</u></b></blockquote>\n\n"
        "<i>ᴄᴏɴɴᴇᴄᴛ ʏᴏᴜʀ ᴏᴡɴ ʙᴏᴛ ᴛᴏᴋᴇɴ ғʀᴏᴍ @BotFather ᴏʀ ᴀ ᴘʏʀᴏɢʀᴀᴍ ᴜsᴇʀʙᴏᴛ sᴇssɪᴏɴ ᴛᴏ ғᴏʀᴡᴀʀᴅ ᴍᴇssᴀɢᴇs ᴀᴛ ᴜʟᴛʀᴀ-ғᴀsᴛ sᴘᴇᴇᴅs!</i>\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"{status_str}\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "👇 <b>sᴇʟᴇᴄᴛ ʜᴏᴡ ʏᴏᴜ ᴡᴀɴᴛ ᴛᴏ ᴄᴏɴɴᴇᴄᴛ:</b>",
        reply_markup=InlineKeyboardMarkup(buttons),
        quote=True
    )

#===================Verify Menu Callback===================#

@Client.on_callback_query(filters.regex(r'^verify_menu_btn'))
async def verify_menu_callback(bot, query):
    user_id = query.from_user.id
    from plugins.verify import is_user_verified, send_verify_prompt, get_remaining_verify_time
    verified = await is_user_verified(user_id)
    if verified:
        rem_sec = get_remaining_verify_time(user_id)
        if rem_sec > 0:
            hrs = rem_sec // 3600
            mins = (rem_sec % 3600) // 60
            exp_text = f"{hrs}h {mins}m remaining"
        else:
            exp_text = "Permanent VIP / Admin Access"
        await query.answer(f"✅ Verified! ({exp_text})", show_alert=True)
    else:
        await query.answer()
        await send_verify_prompt(bot, query.message, user_id)


#===================Course Seller Fast Commands===================#

@Client.on_message(filters.command(['setlecstart', 'lecstart']))
async def setlecstart_cmd(client: Client, message: Message):
    user_id = message.from_user.id if message.from_user else message.chat.id
    if len(message.command) < 2:
        return await message.reply_text(
            "🔢 <b><u>sᴇᴛ sᴛᴀʀᴛɪɴɢ ʟᴇᴄᴛᴜʀᴇ ɴᴜᴍʙᴇʀ</u></b>\n\n"
            "<b>Usage:</b> <code>/setlecstart &lt;number&gt;</code>\n"
            "<b>Example:</b> <code>/setlecstart 15</code> (Starts numbering from Lecture [15])",
            quote=True
        )
    try:
        val = max(1, int(message.command[1]))
        configs = await db.get_configs(user_id)
        configs['course_start_offset'] = val
        await db.update_configs(user_id, configs)
        await message.reply_text(f"✅ Starting lecture index set to: <b>{val}</b>", quote=True)
    except ValueError:
        await message.reply_text("❌ Please provide a valid integer (e.g. <code>/setlecstart 1</code>).", quote=True)

@Client.on_message(filters.command(['setcoursebutton', 'coursebutton']))
async def setcoursebutton_cmd(client: Client, message: Message):
    user_id = message.from_user.id if message.from_user else message.chat.id
    parts = (message.text or message.caption or "").split(None, 1)
    if len(parts) < 2 or not parts[1].strip():
        return await message.reply_text(
            "🔘 <b><u>sᴇᴛ sᴛɪᴄᴋʏ ᴄᴏᴜʀsᴇ ʙᴜᴛᴛᴏɴ</u></b>\n\n"
            "<b>Usage:</b> <code>/setcoursebutton &lt;Button Text | URL&gt;</code>\n"
            "<b>Example:</b> <code>/setcoursebutton 💬 Ask Doubts | https://t.me/MyHelpdesk</code>\n\n"
            "<i>To remove the button, send: <code>/setcoursebutton none</code></i>",
            quote=True
        )
    raw_arg = parts[1].strip()
    configs = await db.get_configs(user_id)
    if raw_arg.lower() in ('none', 'off', 'clear', 'delete', 'remove'):
        configs['course_sticky_button'] = None
        await db.update_configs(user_id, configs)
        return await message.reply_text("✅ Sticky Course Button cleared!", quote=True)

    if '|' in raw_arg or ' - ' in raw_arg:
        configs['course_sticky_button'] = raw_arg
        await db.update_configs(user_id, configs)
        await message.reply_text(f"✅ Sticky Course Button saved:\n<code>{raw_arg}</code>", quote=True)
    else:
        await message.reply_text("❌ Invalid format! Please use: <code>Text | URL</code>", quote=True)

@Client.on_message(filters.command(['setbanner', 'setheader']))
async def setbanner_cmd(client: Client, message: Message):
    user_id = message.from_user.id if message.from_user else message.chat.id
    parts = (message.text or message.caption or "").split(None, 1)
    if len(parts) < 2 or not parts[1].strip():
        return await message.reply_text(
            "🎨 <b><u>sᴇᴛ ʜᴇᴀᴅᴇʀ ʙʀᴀɴᴅɪɴɢ ʙᴀɴɴᴇʀ</u></b>\n\n"
            "<b>ᴜsᴀɢᴇ:</b> <code>/setbanner &lt;banner text&gt;</code>\n"
            "<b>ᴇxᴀᴍᴘʟᴇ:</b> <code>/setbanner 🎓 <b>Skinet Academy</b> | Premium Series</code>\n\n"
            "<i>ᴛʜɪs ʙᴀɴɴᴇʀ ɪs ᴀᴜᴛᴏᴍᴀᴛɪᴄᴀʟʟʏ ᴘʀᴇᴘᴇɴᴅᴇᴅ ᴛᴏ ᴇᴠᴇʀʏ ғᴏʀᴡᴀʀᴅᴇᴅ ᴍᴇssᴀɢᴇ & ᴡᴇʙ sʏʟʟᴀʙᴜs!</i>",
            quote=True
        )
    banner_text = parts[1].strip()
    configs = await db.get_configs(user_id)
    configs['course_brand_header'] = banner_text
    await db.update_configs(user_id, configs)
    await message.reply_text(
        f"✅ <b><u>ʜᴇᴀᴅᴇʀ ʙᴀɴɴᴇʀ sᴀᴠᴇᴅ:</u></b>\n\n"
        f"<blockquote>{banner_text}</blockquote>\n\n"
        f"<i>ᴛʜɪs ᴡɪʟʟ ʙᴇ ᴘʀᴇᴘᴇɴᴅᴇᴅ ᴛᴏ ᴀʟʟ ғᴏʀᴡᴀʀᴅs ᴀɴᴅ ᴛᴇʟᴇɢʀᴀᴘʜ ᴘᴀɢᴇs.</i>",
        quote=True
    )

@Client.on_message(filters.command(['delbanner', 'clearbanner', 'delheader']))
async def delbanner_cmd(client: Client, message: Message):
    user_id = message.from_user.id if message.from_user else message.chat.id
    configs = await db.get_configs(user_id)
    configs['course_brand_header'] = None
    await db.update_configs(user_id, configs)
    await message.reply_text("🗑️ <b>ʜᴇᴀᴅᴇʀ ʙʀᴀɴᴅɪɴɢ ʙᴀɴɴᴇʀ ᴄʟᴇᴀʀᴇᴅ!</b>", quote=True)

@Client.on_message(filters.command(['setfooter', 'setbrandfooter']))
async def setfooter_cmd(client: Client, message: Message):
    user_id = message.from_user.id if message.from_user else message.chat.id
    parts = (message.text or message.caption or "").split(None, 1)
    if len(parts) < 2 or not parts[1].strip():
        return await message.reply_text(
            "🎨 <b><u>sᴇᴛ ғᴏᴏᴛᴇʀ ʙʀᴀɴᴅɪɴɢ ʙᴀɴɴᴇʀ</u></b>\n\n"
            "<b>ᴜsᴀɢᴇ:</b> <code>/setfooter &lt;footer text&gt;</code>\n"
            "<b>ᴇxᴀᴍᴘʟᴇ:</b> <code>/setfooter 📢 <b>Join:</b> @SkinetCourses | 💬 <b>Support:</b> @SkinetHelp</code>\n\n"
            "<i>ᴛʜɪs ʙᴀɴɴᴇʀ ɪs ᴀᴜᴛᴏᴍᴀᴛɪᴄᴀʟʟʏ ᴀᴘᴘᴇɴᴅᴇᴅ ᴛᴏ ᴇᴠᴇʀʏ ғᴏʀᴡᴀʀᴅᴇᴅ ᴍᴇssᴀɢᴇ & ᴡᴇʙ sʏʟʟᴀʙᴜs!</i>",
            quote=True
        )
    footer_text = parts[1].strip()
    configs = await db.get_configs(user_id)
    configs['course_brand_footer'] = footer_text
    await db.update_configs(user_id, configs)
    await message.reply_text(
        f"✅ <b><u>ғᴏᴏᴛᴇʀ ʙᴀɴɴᴇʀ sᴀᴠᴇᴅ:</u></b>\n\n"
        f"<blockquote>{footer_text}</blockquote>\n\n"
        f"<i>ᴛʜɪs ᴡɪʟʟ ʙᴇ ᴀᴘᴘᴇɴᴅᴇᴅ ᴛᴏ ᴀʟʟ ғᴏʀᴡᴀʀᴅs ᴀɴᴅ ᴛᴇʟᴇɢʀᴀᴘʜ ᴘᴀɢᴇs.</i>",
        quote=True
    )

@Client.on_message(filters.command(['delfooter', 'clearfooter']))
async def delfooter_cmd(client: Client, message: Message):
    user_id = message.from_user.id if message.from_user else message.chat.id
    configs = await db.get_configs(user_id)
    configs['course_brand_footer'] = None
    await db.update_configs(user_id, configs)
    await message.reply_text("🗑️ <b>ғᴏᴏᴛᴇʀ ʙʀᴀɴᴅɪɴɢ ʙᴀɴɴᴇʀ ᴄʟᴇᴀʀᴇᴅ!</b>", quote=True)

@Client.on_message(filters.command(['viewbranding', 'branding']))
async def viewbranding_cmd(client: Client, message: Message):
    user_id = message.from_user.id if message.from_user else message.chat.id
    configs = await db.get_configs(user_id)
    hdr = configs.get('course_brand_header') or "<i>Not configured</i>"
    ftr = configs.get('course_brand_footer') or "<i>Not configured</i>"
    btn_raw = configs.get('course_sticky_button') or "<i>Not configured</i>"

    await message.reply_text(
        f"🏷️ <b><u>ᴄᴜʀʀᴇɴᴛ ʙʀᴀɴᴅɪɴɢ sᴜɪᴛᴇ ᴄᴏɴғɪɢᴜʀᴀᴛɪᴏɴ</u></b>\n\n"
        f"📌 <b>ʜᴇᴀᴅᴇʀ ʙᴀɴɴᴇʀ:</b>\n<blockquote>{hdr}</blockquote>\n\n"
        f"📌 <b>ғᴏᴏᴛᴇʀ ʙᴀɴɴᴇʀ:</b>\n<blockquote>{ftr}</blockquote>\n\n"
        f"🔘 <b>sᴛɪᴄᴋʏ ʙᴜᴛᴛᴏɴ:</b>\n<blockquote><code>{btn_raw}</code></blockquote>\n\n"
        f"✏️ <i>ᴜsᴇ <code>/setbanner</code>, <code>/setfooter</code>, <code>/setcoursebutton</code> ᴛᴏ ᴍᴏᴅɪғʏ.</i>",
        quote=True
    )

@Client.on_message(filters.command(['exportindex']))
async def exportindex_cmd(client: Client, message: Message):
    user_id = message.from_user.id if message.from_user else message.chat.id
    configs = await db.get_configs(user_id)
    enabled = configs.get('course_export_txt', True)
    status_str = "🟢 <b>ᴇɴᴀʙʟᴇᴅ</b>" if enabled else "🔴 <b>ᴅɪsᴀʙʟᴇᴅ</b>"
    text = (
        "📄 <b><u>ᴄᴏᴜʀsᴇ sʏʟʟᴀʙᴜs / ɪɴᴅᴇx ᴇxᴘᴏʀᴛ</u></b>\n\n"
        f"• <b>ᴀᴜᴛᴏ .TXT ᴇxᴘᴏʀᴛ:</b> {status_str}\n\n"
        "<i>ᴡʜᴇɴ ᴇɴᴀʙʟᴇᴅ, ᴛʜᴇ ʙᴏᴛ ᴀᴜᴛᴏᴍᴀᴛɪᴄᴀʟʟʏ ɢᴇɴᴇʀᴀᴛᴇs ᴀɴᴅ sᴇɴᴅs ᴀ <code>.txt</code> sʏʟʟᴀʙᴜs "
        "ᴅᴏᴄᴜᴍᴇɴᴛ ᴡɪᴛʜ ᴅɪʀᴇᴄᴛ ʟᴇᴄᴛᴜʀᴇ ʟɪɴᴋs ᴀғᴛᴇʀ ᴇᴠᴇʀʏ ᴄᴏᴜʀsᴇ ғᴏʀᴡᴀʀᴅɪɴɢ ʙᴀᴛᴄʜ.</i>\n\n"
        "💡 <i>ʏᴏᴜ ᴄᴀɴ ᴛᴏɢɢʟᴇ ᴛʜɪs sᴇᴛᴛɪɴɢ ᴏʀ ᴄᴏɴғɪɢᴜʀᴇ ʏᴏᴜʀ ᴄᴏᴜʀsᴇ sᴇʟʟᴇʀ sᴜɪᴛᴇ ᴠɪᴀ <code>/courseseller</code>.</i>"
    )
    kb = markup(
        row(
            btn("🎓 ᴄᴏᴜʀsᴇ sᴇʟʟᴇʀ", "settings#courseseller", "yellow"),
            btn("⚙️ sᴇᴛᴛɪɴɢs", "settings#main", "blue")
        ),
        row(
            btn("❌ ᴄʟᴏsᴇ", "close_btn", "red")
        )
    )
    await message.reply_text(text, reply_markup=kb, quote=True)

#===================Interactive Commands & Menu Browser===================#

COMMAND_CATEGORIES = {
    "all": {
        "title": "🧭 <b><u>ᴀʟʟ sʏsᴛᴇᴍ ᴄᴏᴍᴍᴀɴᴅs</u></b>",
        "desc": (
            "⏣ <code>/start</code> — Start bot & view main card\n"
            "⏣ <code>/help</code> — Detailed feature guide\n"
            "⏣ <code>/commands</code> — Interactive command navigator\n"
            "⏣ <code>/menu</code> — Quick action menu\n"
            "⏣ <code>/addbot</code> — Connect your bot token or UserBot\n"
            "⏣ <code>/settings</code> — Complete bot customization menu\n"
            "⏣ <code>/status</code> — System & forward statistics\n"
            "⏣ <code>/forward</code> — Interactive channel forward wizard\n"
            "⏣ <code>/fwd</code> — Direct multi-range forward (e.g. 10-20 30-40)\n"
            "⏣ <code>/courseseller</code> — Master Course Seller Suite\n"
            "⏣ <code>/setbanner</code> — Set dynamic header branding banner\n"
            "⏣ <code>/setfooter</code> — Set dynamic footer branding banner\n"
            "⏣ <code>/viewbranding</code> — Preview active branding suite\n"
            "⏣ <code>/setlecstart</code> — Set starting lecture numbering\n"
            "⏣ <code>/setcoursebutton</code> — Set sticky interactive button\n"
            "⏣ <code>/autosave</code> — Real-time 24/7 channel monitoring\n"
            "⏣ <code>/tutorial</code> — 12-Module Master Knowledge Hub\n"
            "⏣ <code>/skinet</code> — Text & media modifier guide\n"
            "⏣ <code>/pause</code> / <code>/resume</code> — Pause & resume tasks\n"
            "⏣ <code>/stop</code> — Gracefully cancel ongoing tasks\n"
            "⏣ <code>/unequify</code> — Channel duplicate message cleaner\n"
            "⏣ <code>/reset</code> — Reset personal configs to default\n"
            "⏣ <code>/plans</code> — View VIP passes & pricing\n"
            "⏣ <code>/myplan</code> — Check your active VIP status\n"
            "⏣ <code>/referral</code> — Refer friends & earn VIP rewards\n"
            "⏣ <code>/topref</code> — Referral leaderboard\n"
            "⏣ <code>/verify</code> — Check token verification pass\n"
            "⏣ <code>/restart</code> — Reboot bot engine (Admin)\n"
            "⏣ <code>/broadcast</code> — Broadcast message to users (Admin)\n"
            "⏣ <code>/cancelbroadcast</code> — Cancel broadcast (Admin)\n"
            "⏣ <code>/vipadmin</code> — VIP management center (Admin)\n"
            "⏣ <code>/setverify</code> — Token verification config (Admin)\n"
            "⏣ <code>/userstats</code> — Admin user analytics (Admin)\n"
            "⏣ <code>/config</code> — Bot system configuration (Owner)\n"
            "⏣ <code>/admins</code> — List bot administrators (Owner)"
        )
    },
    "forward": {
        "title": "📤 <b><u>ғᴏʀᴡᴀʀᴅɪɴɢ sᴜɪᴛᴇ ᴄᴏᴍᴍᴀɴᴅs</u></b>",
        "desc": (
            "⏣ <code>/forward</code> — Interactive wizard to migrate channels\n"
            "⏣ <code>/fwd &lt;link1&gt; &lt;link2&gt;</code> — Range forward start to end\n"
            "⏣ <code>/fwd &lt;ranges...&gt;</code> — Multi-range batch forwarding\n"
            "   <i>Example: <code>/fwd 10-20, 30-40, 50-60</code></i>\n"
            "⏣ <code>/addbot</code> — Connect your bot token or UserBot session\n"
            "⏣ <code>/pause</code> — Temporarily pause current forwarding task\n"
            "⏣ <code>/resume</code> — Resume paused forwarding task\n"
            "⏣ <code>/stop</code> — Gracefully terminate running forward task\n"
            "⏣ <code>/unequify</code> — Scan & delete duplicate media in channel\n"
            "⏣ <code>/autosave</code> — Real-time continuous channel listener\n"
            "⏣ <code>/settings</code> — Configure delay, speed, and filters"
        )
    },
    "seller": {
        "title": "🎓 <b><u>ᴄᴏᴜʀsᴇ sᴇʟʟᴇʀ & ʙʀᴀɴᴅɪɴɢ ᴄᴏᴍᴍᴀɴᴅs</u></b>",
        "desc": (
            "⏣ <code>/courseseller</code> — Master control panel for sellers\n"
            "⏣ <code>/setbanner &lt;text&gt;</code> — Set dynamic top branding banner\n"
            "⏣ <code>/delbanner</code> — Clear top branding banner\n"
            "⏣ <code>/setfooter &lt;text&gt;</code> — Set dynamic bottom branding banner\n"
            "⏣ <code>/delfooter</code> — Clear bottom branding banner\n"
            "⏣ <code>/viewbranding</code> — Preview current header & footer banners\n"
            "⏣ <code>/setlecstart &lt;num&gt;</code> — Start numbering from lecture [N]\n"
            "⏣ <code>/setcoursebutton &lt;text | url&gt;</code> — Set sticky button\n"
            "⏣ <code>/exportindex</code> — Generate `.txt` index document\n"
            "⏣ <code>/skinet</code> — Open Text & Media Modifier Guide"
        )
    },
    "vip": {
        "title": "💎 <b><u>ᴠɪᴘ ᴘᴀssᴇs & ʀᴇғᴇʀʀᴀʟ ᴄᴏᴍᴍᴀɴᴅs</u></b>",
        "desc": (
            "⏣ <code>/plans</code> — View VIP subscription tiers and passes\n"
            "⏣ <code>/myplan</code> — View your remaining VIP validity & plan\n"
            "⏣ <code>/referral</code> — Get your referral link & invite stats\n"
            "⏣ <code>/topref</code> — Top 10 referral earners leaderboard\n"
            "⏣ <code>/verify</code> — Check your token verification status\n"
            "⏣ <code>/donate</code> — Support bot hosting & maintenance"
        )
    },
    "admin": {
        "title": "🛡️ <b><u>ᴀᴅᴍɪɴ & sʏsᴛᴇᴍ ᴄᴏᴍᴍᴀɴᴅs</u></b>",
        "desc": (
            "⏣ <code>/restart</code> — Gracefully reboot bot engine & workers\n"
            "⏣ <code>/broadcast</code> — Interactive broadcast wizard to all users\n"
            "⏣ <code>/cancelbroadcast</code> — Abort ongoing broadcast process\n"
            "⏣ <code>/vipadmin</code> — VIP management dashboard\n"
            "⏣ <code>/addpremium &lt;id&gt; &lt;days&gt;</code> — Grant VIP to user\n"
            "⏣ <code>/delpremium &lt;id&gt;</code> — Revoke VIP from user\n"
            "⏣ <code>/setverify</code> — Configure token shortener verification\n"
            "⏣ <code>/userstats</code> — User analytics & growth dashboard\n"
            "⏣ <code>/config</code> — View & modify system environment variables\n"
            "⏣ <code>/admins</code> — List authorized bot administrators\n"
            "⏣ <code>/addadmin &lt;id&gt;</code> — Add bot administrator\n"
            "⏣ <code>/deladmin &lt;id&gt;</code> — Remove bot administrator"
        )
    }
}

def get_commands_markup(current_tab="all"):
    # (label, callback, color)
    tabs = [
        ("🧭 ᴀʟʟ", "cmd_tab_all", "blue"),
        ("📤 ғᴏʀᴡᴀʀᴅ", "cmd_tab_forward", "green"),
        ("🎓 sᴇʟʟᴇʀ", "cmd_tab_seller", "blue"),
        ("💎 ᴠɪᴘ", "cmd_tab_vip", "green"),
        ("🛡️ ᴀᴅᴍɪɴ", "cmd_tab_admin", "red"),
    ]

    def tab_btn(title, code, color):
        active = code == f"cmd_tab_{current_tab}"
        return btn(f"▸ {title} ◂" if active else title, code, color)

    row1 = [tab_btn(t, c, col) for t, c, col in tabs[:3]]
    row2 = [tab_btn(t, c, col) for t, c, col in tabs[3:]]
    row3 = [
        btn("⚙️ sᴇᴛᴛɪɴɢs", "settings#main", "green"),
        btn("❌ ᴄʟᴏsᴇ", "close_btn", "red"),
    ]
    return markup(row1, row2, row3)

@Client.on_message(filters.command(['commands', 'menu', 'cmds']))
async def commands_menu_cmd(client: Client, message: Message):
    tab_data = COMMAND_CATEGORIES["all"]
    text = f"<blockquote>{tab_data['title']}</blockquote>\n\n{tab_data['desc']}"
    await message.reply_text(text, reply_markup=get_commands_markup("all"), disable_web_page_preview=True, quote=True)

@Client.on_callback_query(filters.regex(r"^cmd_tab_(\w+)$"))
async def cmd_tab_callback(client: Client, query: CallbackQuery):
    tab = query.matches[0].group(1)
    tab_data = COMMAND_CATEGORIES.get(tab, COMMAND_CATEGORIES["all"])
    text = f"<blockquote>{tab_data['title']}</blockquote>\n\n{tab_data['desc']}"
    try:
        await query.message.edit_text(text, reply_markup=get_commands_markup(tab), disable_web_page_preview=True)
    except Exception:
        pass
    await query.answer()

#===================Channel ID & Dump Channel Commands===================#

@Client.on_message(filters.command(['id']) & filters.private)
async def id_command(client: Client, message: Message):
    user_id = message.from_user.id if message.from_user else message.chat.id
    from plugins.forward_parser import extract_forward_info, format_forward_card, resolve_channel_input

    # 1. Replied to a message? Inspect replied message
    if message.reply_to_message:
        rep = message.reply_to_message
        fwd_info = extract_forward_info(rep)
        if fwd_info.get("is_forward"):
            text, kb = format_forward_card(fwd_info, user_id=user_id)
            return await message.reply_text(text, reply_markup=kb, disable_web_page_preview=True, quote=True)
        else:
            rep_user = rep.from_user
            r_uid = rep_user.id if rep_user else "Unknown"
            r_uname = f"@{rep_user.username}" if (rep_user and rep_user.username) else "None"
            r_name = rep_user.first_name if rep_user else "User"
            r_mid = rep.id
            text = (
                f"<blockquote><b>🆔 <u>ᴍᴇssᴀɢᴇ & ᴜsᴇʀ ɪᴅs</u></b></blockquote>\n\n"
                f"👤 <b>ᴜsᴇʀ:</b> <code>{r_name}</code>\n"
                f"🆔 <b>ᴜsᴇʀ ɪᴅ:</b> <code>{r_uid}</code>  <i>(ᴛᴀᴘ ᴛᴏ ᴄᴏᴘʏ)</i>\n"
                f"👤 <b>ᴜsᴇʀɴᴀᴍᴇ:</b> {r_uname}\n"
                f"🔢 <b>ᴍᴇssᴀɢᴇ ɪᴅ:</b> <code>{r_mid}</code>\n"
                f"💬 <b>ᴄʜᴀᴛ ɪᴅ:</b> <code>{message.chat.id}</code>"
            )
            kb = markup(
                row(btn("📋 ᴄᴏᴘʏ ᴜsᴇʀ ɪᴅ", f"fwd_copy_{r_uid}", "blue")),
                row(btn("❌ ᴄʟᴏsᴇ", "close_btn", "red"))
            )
            return await message.reply_text(text, reply_markup=kb, quote=True)

    # 2. Argument passed? e.g. /id -1001234567890 or /id @mychannel
    cmd_parts = (message.text or message.caption or "").split(None, 1)
    if len(cmd_parts) > 1 and cmd_parts[1].strip():
        arg = cmd_parts[1].strip()
        res = await resolve_channel_input(arg, client)
        if res.get("chat_id"):
            fwd_info = {
                "is_forward": True,
                "chat_id": res["chat_id"],
                "chat_title": res.get("chat_title") or "Channel",
                "chat_username": res.get("chat_username"),
                "chat_type": res.get("chat_type") or "channel",
                "message_id": res.get("last_msg_id"),
                "forward_date": None,
                "forward_date_str": "",
                "sender_id": None,
                "sender_name": None,
                "link": res.get("link"),
            }
            text, kb = format_forward_card(fwd_info, user_id=user_id)
            return await message.reply_text(text, reply_markup=kb, disable_web_page_preview=True, quote=True)
        else:
            return await message.reply_text(f"❌ <b>ᴇʀʀᴏʀ:</b> {res.get('error', 'Could not resolve channel ID')}", quote=True)

    # 3. Standalone /id
    u_name = message.from_user.first_name if message.from_user else "You"
    u_user = f"@{message.from_user.username}" if (message.from_user and message.from_user.username) else "None"
    text = (
        f"<blockquote><b>🆔 <u>ʏᴏᴜʀ ᴛᴇʟᴇɢʀᴀᴍ ɪᴅᴇɴᴛɪғɪᴇʀs</u></b></blockquote>\n\n"
        f"👤 <b>ɴᴀᴍᴇ:</b> <code>{u_name}</code>\n"
        f"🆔 <b>ʏᴏᴜʀ ᴜsᴇʀ ɪᴅ:</b> <code>{user_id}</code>  <i>(ᴛᴀᴘ ᴛᴏ ᴄᴏᴘʏ)</i>\n"
        f"👤 <b>ʏᴏᴜʀ ᴜsᴇʀɴᴀᴍᴇ:</b> {u_user}\n"
        f"💬 <b>ᴄᴜʀʀᴇɴᴛ ᴄʜᴀᴛ ɪᴅ:</b> <code>{message.chat.id}</code>\n\n"
        f"💡 <i>ᴛɪᴘ: ғᴏʀᴡᴀʀᴅ ᴀɴʏ ᴍᴇssᴀɢᴇ ғʀᴏᴍ ᴀ ᴄʜᴀɴɴᴇʟ ʜᴇʀᴇ ᴛᴏ ɪɴsᴛᴀɴᴛʟʏ ᴇxᴛʀᴀᴄᴛ ɪᴛs ᴄʜᴀɴɴᴇʟ ɪᴅ!</i>"
    )
    kb = markup(
        row(btn("📋 ᴄᴏᴘʏ ᴍʏ ɪᴅ", f"fwd_copy_{user_id}", "blue")),
        row(btn("❌ ᴄʟᴏsᴇ", "close_btn", "red"))
    )
    await message.reply_text(text, reply_markup=kb, quote=True)


@Client.on_message(filters.command(['setdump', 'dump']) & filters.private)
async def setdump_command(client: Client, message: Message):
    user_id = message.from_user.id if message.from_user else message.chat.id
    if not await db.is_admin(user_id):
        return await message.reply_text("⚠️ <b>ᴀᴄᴄᴇss ᴅᴇɴɪᴇᴅ:</b> ʀᴇsᴛʀɪᴄᴛᴇᴅ ᴛᴏ ʙᴏᴛ ᴀᴅᴍɪɴɪsᴛʀᴀᴛᴏʀs.", quote=True)

    from plugins.forward_parser import resolve_channel_input

    # 1. Reply to forwarded message
    if message.reply_to_message:
        res = await resolve_channel_input(message.reply_to_message, client, verify_access=True)
        if res.get("chat_id"):
            c_id = res["chat_id"]
            c_title = res.get("chat_title") or str(c_id)
            Config.DUMP_CHANNEL = c_id
            await db.update_system_config("DUMP_CHANNEL", c_id)
            await db.update_admin_dump(c_id, True)
            return await message.reply_text(
                f"<blockquote><b>✅ <u>ɢʟᴏʙᴀʟ ᴅᴜᴍᴘ ᴄʜᴀɴɴᴇʟ sᴇᴛ</u></b></blockquote>\n\n"
                f"📢 <b>ᴄʜᴀɴɴᴇʟ:</b> <code>{c_title}</code>\n"
                f"🆔 <b>ɪᴅ:</b> <code>{c_id}</code>\n"
                f"📦 <b>sᴛᴀᴛᴜs:</b> <code>✅ ᴏɴ (ᴀᴄᴛɪᴠᴇ)</code>",
                quote=True
            )

    # 2. Command argument
    cmd_parts = (message.text or message.caption or "").split(None, 1)
    if len(cmd_parts) > 1 and cmd_parts[1].strip():
        arg = cmd_parts[1].strip()
        if arg == "0":
            Config.DUMP_CHANNEL = 0
            await db.update_system_config("DUMP_CHANNEL", 0)
            await db.update_admin_dump(0, False)
            return await message.reply_text("✅ <b>ɢʟᴏʙᴀʟ ᴅᴜᴍᴘ ᴄʜᴀɴɴᴇʟ ᴅɪsᴀʙʟᴇᴅ!</b>", quote=True)

        res = await resolve_channel_input(arg, client, verify_access=True)
        if res.get("chat_id"):
            c_id = res["chat_id"]
            c_title = res.get("chat_title") or str(c_id)
            Config.DUMP_CHANNEL = c_id
            await db.update_system_config("DUMP_CHANNEL", c_id)
            await db.update_admin_dump(c_id, True)
            return await message.reply_text(
                f"<blockquote><b>✅ <u>ɢʟᴏʙᴀʟ ᴅᴜᴍᴘ ᴄʜᴀɴɴᴇʟ sᴇᴛ</u></b></blockquote>\n\n"
                f"📢 <b>ᴄʜᴀɴɴᴇʟ:</b> <code>{c_title}</code>\n"
                f"🆔 <b>ɪᴅ:</b> <code>{c_id}</code>\n"
                f"📦 <b>sᴛᴀᴛᴜs:</b> <code>✅ ᴏɴ (ᴀᴄᴛɪᴠᴇ)</code>",
                quote=True
            )
        else:
            err = res.get("error") or "Could not resolve channel."
            return await message.reply_text(f"❌ <b>ᴇʀʀᴏʀ:</b>\n\n{err}", quote=True)

    # 3. Interactive prompt
    curr = f"<code>{Config.DUMP_CHANNEL}</code>" if Config.DUMP_CHANNEL != 0 else "<code>0 (Disabled)</code>"
    try:
        ask = await client.ask(
            user_id,
            text=(
                "<blockquote><b>📦 <u>sᴇᴛ ɢʟᴏʙᴀʟ ᴅᴜᴍᴘ ᴄʜᴀɴɴᴇʟ</u></b></blockquote>\n\n"
                f"<b>ᴄᴜʀʀᴇɴᴛ ᴠᴀʟᴜᴇ:</b> {curr}\n\n"
                "ғᴏʀᴡᴀʀᴅ ᴀ ᴍᴇssᴀɢᴇ ғʀᴏᴍ ʏᴏᴜʀ ᴅᴜᴍᴘ ᴄʜᴀɴɴᴇʟ, ᴏʀ sᴇɴᴅ ɪᴛs ɪᴅ / ʟɪɴᴋ.\n\n"
                "• <b>ғᴏʀᴡᴀʀᴅ:</b> <i>ғᴏʀᴡᴀʀᴅ ᴀɴʏ ᴍᴇssᴀɢᴇ ғʀᴏᴍ ᴛʜᴇ ᴄʜᴀɴɴᴇʟ (ʀᴇᴄᴏᴍᴍᴇɴᴅᴇᴅ)</i>\n"
                "• <b>ɪᴅ:</b> <code>-1001234567890</code>\n"
                "• <b>ʟɪɴᴋ:</b> <code>https://t.me/c/...</code> ᴏʀ <code>@my_channel</code>\n\n"
                "⚠️ <b>ɪᴍᴘᴏʀᴛᴀɴᴛ:</b> <i>ᴍᴀᴋᴇ sᴜʀᴇ ᴛʜᴇ ʙᴏᴛ ɪs ᴀᴅᴅᴇᴅ ᴀs ᴀɴ ᴀᴅᴍɪɴ ɪɴ ᴛʜᴇ ᴅᴜᴍᴘ ᴄʜᴀɴɴᴇʟ!</i>\n\n"
                "/cancel — <code>ᴄᴀɴᴄᴇʟ ᴘʀᴏᴄᴇss</code>"
            ),
            timeout=120
        )
    except (asyncio.exceptions.TimeoutError, ListenerTimeout):
        return await message.reply_text("⏰ <b>ᴛɪᴍᴇᴏᴜᴛ: ɴᴏ ʀᴇsᴘᴏɴsᴇ ʀᴇᴄᴇɪᴠᴇᴅ.</b>", quote=True)
    if not ask or (ask.text and ask.text.startswith("/cancel")):
        return await message.reply_text("<b>ᴘʀᴏᴄᴇss ᴄᴀɴᴄᴇʟʟᴇᴅ !</b>", quote=True)

    if ask.text and ask.text.strip() == "0":
        Config.DUMP_CHANNEL = 0
        await db.update_system_config("DUMP_CHANNEL", 0)
        await db.update_admin_dump(0, False)
        return await message.reply_text("✅ <b>ɢʟᴏʙᴀʟ ᴅᴜᴍᴘ ᴄʜᴀɴɴᴇʟ ᴅɪsᴀʙʟᴇᴅ!</b>", quote=True)

    res = await resolve_channel_input(ask, client, verify_access=True)
    if res.get("chat_id"):
        c_id = res["chat_id"]
        c_title = res.get("chat_title") or str(c_id)
        Config.DUMP_CHANNEL = c_id
        await db.update_system_config("DUMP_CHANNEL", c_id)
        await db.update_admin_dump(c_id, True)
        return await message.reply_text(
            f"<blockquote><b>✅ <u>ɢʟᴏʙᴀʟ ᴅᴜᴍᴘ ᴄʜᴀɴɴᴇʟ sᴇᴛ</u></b></blockquote>\n\n"
            f"📢 <b>ᴄʜᴀɴɴᴇʟ:</b> <code>{c_title}</code>\n"
            f"🆔 <b>ɪᴅ:</b> <code>{c_id}</code>\n"
            f"📦 <b>sᴛᴀᴛᴜs:</b> <code>✅ ᴏɴ (ᴀᴄᴛɪᴠᴇ)</code>",
            quote=True
        )
    else:
        err = res.get("error") or "Could not resolve channel."
        return await message.reply_text(f"❌ <b>ᴇʀʀᴏʀ:</b>\n\n{err}", quote=True)


#===================Non-Command & Forward Message Handler===================#

KNOWN_COMMANDS = {
    "start", "help", "settings", "forward", "fwd", "autosave", "live", "monitor",
    "commands", "menu", "cmds", "id", "setdump", "dump",
    "broadcast", "bcast", "cancelbroadcast", "bcastcancel", "broadcastrestart", "bcastrestart",
    "restart", "reboot", "botrestart", "restarr", "terms", "tos", "privacy", "donate", "clone", "plans",
    "premium", "buy", "vip", "myplan", "plan", "addpremium", "addvip", "delpremium",
    "delvip", "vipadmin", "premiumadmin", "referral", "refer", "earn", "topref", "leaderboard", "refadmin",
    "stop", "pause", "resume", "reset", "resetall", "tutorial", "guide", "skinet",
    "modifier", "ftm", "courseseller", "seller", "course", "courses", "setlecstart", "lecstart",
    "setcoursebutton", "coursebutton", "exportindex", "unequify", "userstats", "track",
    "admintrack", "verify", "setverify", "config", "env", "vars", "addadmin",
    "deladmin", "admins", "cancel", "yes", "no", "setbanner", "setheader", "delbanner",
    "clearbanner", "delheader", "setfooter", "setbrandfooter", "delfooter", "clearfooter",
    "viewbranding", "branding", "status", "stats", "addbot", "connectbot", "auditlog",
    "tasks", "alltasks", "canceltask", "ban", "unban", "banned", "blacklist",
    "addblacklist", "delblacklist", "blacklistadd", "blacklistdel", "rmblacklist",
    "allchannels", "channels", "userchannels", "uchannels", "checkchannel", "probechannel"
}

@Client.on_message(filters.private & ~filters.service, group=100)
async def non_command_handler(client: Client, message: Message):
    user_id = message.from_user.id if message.from_user else message.chat.id

    # Check if user is banned
    is_banned, ban_reason = await db.is_user_banned(user_id)
    if is_banned:
        return await message.reply_text(
            f"<blockquote><b>🚫 <u>ᴀᴄᴄᴏᴜɴᴛ sᴜsᴘᴇɴᴅᴇᴅ</u></b></blockquote>\n\n"
            f"ʏᴏᴜ ʜᴀᴠᴇ ʙᴇᴇɴ ʙᴀɴɴᴇᴅ ғʀᴏᴍ ᴜsɪɴɢ ᴛʜɪs ʙᴏᴛ.\n"
            f"<b>ʀᴇᴀsᴏɴ:</b> {ban_reason}"
        )

    # 1. Skip if there is an active listener (like bot.ask) for this chat/user
    try:
        from pyrogram import enums
        if hasattr(client, "listeners") and isinstance(client.listeners, dict):
            msg_listeners = client.listeners.get(enums.ListenerTypes.MESSAGE, [])
            for l in msg_listeners:
                ident = getattr(l, "identifier", None)
                if ident:
                    c_id = getattr(ident, "chat_id", None)
                    u_id = getattr(ident, "from_user_id", None)
                    if (c_id and c_id == message.chat.id) or (u_id and u_id == user_id):
                        return
    except Exception:
        pass

    # 2. Skip if user is submitting payment proof
    try:
        from plugins.premium import _SUBMIT_STATE
        if user_id in _SUBMIT_STATE:
            return
    except Exception:
        pass

    # 3. Universal Forward Message Channel ID Parser
    from plugins.forward_parser import extract_forward_info, format_forward_card
    fwd_info = extract_forward_info(message)
    if fwd_info.get("is_forward"):
        card_text, card_kb = format_forward_card(fwd_info, user_id=user_id)
        return await message.reply_text(
            text=card_text,
            reply_markup=card_kb,
            disable_web_page_preview=True,
            quote=True
        )

    raw_text = (message.text or message.caption or "").strip()

    # 4. Check if it's a known command -> let registered handlers execute
    if raw_text.startswith("/"):
        cmd_word = raw_text.split()[0].lstrip("/").split("@")[0].lower()
        from plugins.utils import auto_delete
        asyncio.create_task(auto_delete(message, delay=5))
        if cmd_word in KNOWN_COMMANDS:
            return

        # Unknown command response
        unrec = await message.reply_text(
            f"<blockquote><b>❓ <u>ᴜɴᴋɴᴏᴡɴ ᴄᴏᴍᴍᴀɴᴅ: /{cmd_word}</u></b></blockquote>\n\n"
            f"ᴛʜᴇ ᴄᴏᴍᴍᴀɴᴅ <code>/{cmd_word}</code> ɪs ɴᴏᴛ ʀᴇᴄᴏɢɴɪᴢᴇᴅ ʙʏ sᴋɪɴᴇᴛ ᴠᴇʀsᴇ.\n\n"
            f"👉 ᴘʟᴇᴀsᴇ ᴄʜᴇᴄᴋ <code>/help</code> ᴛᴏ ᴠɪᴇᴡ ᴀʟʟ ᴀᴠᴀɪʟᴀʙʟᴇ ᴄᴏᴍᴍᴀɴᴅs!",
            quote=True,
            reply_markup=markup(
                row(btn("📖 ᴠɪᴇᴡ ᴄᴏᴍᴍᴀɴᴅs", "help", "blue"), btn("🔙 ʜᴏᴍᴇ", "back", "red"))
            )
        )
        asyncio.create_task(auto_delete(unrec, delay=15))
        return

    # 5. Check if it's a channel link or message link -> resolve channel metadata!
    if raw_text.startswith("https://t.me/") or raw_text.startswith("http://t.me/") or raw_text.startswith("t.me/"):
        from plugins.forward_parser import resolve_channel_input
        res = await resolve_channel_input(raw_text, client)
        if res.get("chat_id"):
            fwd_info = {
                "is_forward": True,
                "chat_id": res["chat_id"],
                "chat_title": res.get("chat_title") or "Channel",
                "chat_username": res.get("chat_username"),
                "chat_type": res.get("chat_type") or "channel",
                "message_id": res.get("last_msg_id"),
                "forward_date": None,
                "forward_date_str": "",
                "sender_id": None,
                "sender_name": None,
                "link": res.get("link"),
            }
            card_text, card_kb = format_forward_card(fwd_info, user_id=user_id)
            return await message.reply_text(
                text=card_text,
                reply_markup=card_kb,
                disable_web_page_preview=True,
                quote=True
            )

    # 6. Ignore other plain messages silently (prevents menu popups on random numbers/text)
    return


#===================Forward Card Interactive Callbacks===================#

@Client.on_callback_query(filters.regex(r"^fwd_copy_(-?\d+)$"))
async def fwd_copy_callback(client: Client, query: CallbackQuery):
    cid = query.matches[0].group(1)
    await query.answer(f"{cid}", show_alert=True)


@Client.on_callback_query(filters.regex(r"^fwd_add_(-?\d+)$"))
async def fwd_add_callback(client: Client, query: CallbackQuery):
    user_id = query.from_user.id
    cid = int(query.matches[0].group(1))
    if await db.in_channel(user_id, cid):
        return await query.answer("ℹ️ ᴛʜɪs ᴄʜᴀɴɴᴇʟ ɪs ᴀʟʀᴇᴀᴅʏ ɪɴ ʏᴏᴜʀ ᴛᴀʀɢᴇᴛs!", show_alert=True)

    title = "Target Channel"
    uname = "private"
    try:
        chat_obj = await client.get_chat(cid)
        if chat_obj:
            title = chat_obj.title or chat_obj.first_name or title
            if chat_obj.username:
                uname = "@" + chat_obj.username
    except Exception:
        pass
    await db.add_channel(user_id, cid, title, uname)
    await query.answer("✅ ᴄʜᴀɴɴᴇʟ sᴜᴄᴄᴇssғᴜʟʟʏ ᴀᴅᴅᴇᴅ ᴛᴏ ʏᴏᴜʀ ᴛᴀʀɢᴇᴛs!", show_alert=True)


@Client.on_callback_query(filters.regex(r"^fwd_dump_(-?\d+)$"))
async def fwd_dump_callback(client: Client, query: CallbackQuery):
    user_id = query.from_user.id
    if not await db.is_admin(user_id):
        return await query.answer("⚠️ Admin only!", show_alert=True)
    cid = int(query.matches[0].group(1))
    Config.DUMP_CHANNEL = cid
    await db.update_system_config("DUMP_CHANNEL", cid)
    await db.update_admin_dump(cid, True)
    await query.answer(f"✅ Dump Channel set to: {cid}", show_alert=True)


@Client.on_callback_query(filters.regex(r"^fwd_log_(-?\d+)$"))
async def fwd_log_callback(client: Client, query: CallbackQuery):
    user_id = query.from_user.id
    if not await db.is_admin(user_id):
        return await query.answer("⚠️ Admin only!", show_alert=True)
    cid = int(query.matches[0].group(1))
    Config.LOG_CHANNEL = cid
    await db.update_system_config("LOG_CHANNEL", cid)
    await query.answer(f"✅ Log Channel set to: {cid}", show_alert=True)


@Client.on_callback_query(filters.regex(r"^fwd_start_(-?\d+)_(\d+)$"))
async def fwd_start_callback(client: Client, query: CallbackQuery):
    user_id = query.from_user.id
    cid = int(query.matches[0].group(1))
    mid = int(query.matches[0].group(2))
    _bot = await db.get_userbot(user_id) or await db.get_custom_bot(user_id)
    if not _bot:
        return await query.answer("⚠️ Please add a bot or userbot in /settings first!", show_alert=True)
    channels = await db.get_user_channels(user_id)
    if not channels:
        return await query.answer("⚠️ Please set a target channel in /settings first!", show_alert=True)
    await query.answer()
    await query.message.reply_text(
        f"<blockquote><b>⚡ <u>ғᴏʀᴡᴀʀᴅ ʀᴀɴɢᴇ sᴇᴛᴜᴘ</u></b></blockquote>\n\n"
        f"📡 <b>sᴏᴜʀᴄᴇ ᴄʜᴀɴɴᴇʟ:</b> <code>{cid}</code>\n"
        f"🔢 <b>sᴛᴀʀᴛ ᴍᴇssᴀɢᴇ:</b> <code>{mid}</code>\n"
        f"🎯 <b>ᴛᴀʀɢᴇᴛ ᴄʜᴀɴɴᴇʟ:</b> <code>{channels[0]['title']}</code>\n\n"
        f"👉 <b>ᴛᴏ sᴛᴀʀᴛ ғᴏʀᴡᴀʀᴅɪɴɢ, sᴇɴᴅ:</b>\n"
        f"<code>/fwd {cid}/{mid} {cid}/&lt;end_id&gt;</code>\n\n"
        f"ᴏʀ ʟᴀᴜɴᴄʜ ᴛʜᴇ ғᴜʟʟ ᴡɪᴢᴀʀᴅ ᴡɪᴛʜ <code>/forward</code>!",
        quote=True
    )


@Client.on_callback_query(filters.regex(r"^fwd_clean_(-?\d+)$"))
async def fwd_clean_callback(client: Client, query: CallbackQuery):
    user_id = query.from_user.id
    cid = int(query.matches[0].group(1))
    _bot = await db.get_userbot(user_id)
    if not _bot:
        return await query.answer("⚠️ Need a userbot to clean duplicates. Add one in /settings!", show_alert=True)
    await query.answer()
    await query.message.reply_text(
        f"<blockquote><b>🧹 <u>ᴅᴜᴘʟɪᴄᴀᴛᴇ ᴄʟᴇᴀɴᴇʀ (/unequify)</u></b></blockquote>\n\n"
        f"🎯 <b>ᴛᴀʀɢᴇᴛ ᴄʜᴀɴɴᴇʟ:</b> <code>{cid}</code>\n\n"
        f"👉 <i>sᴇɴᴅ <code>/unequify</code> ᴛᴏ sᴛᴀʀᴛ ʀᴇᴍᴏᴠɪɴɢ ᴅᴜᴘʟɪᴄᴀᴛᴇs ɪɴ ᴛʜɪs ᴄʜᴀɴɴᴇʟ!</i>",
        quote=True
    )

