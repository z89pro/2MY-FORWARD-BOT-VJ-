import asyncio 
from database import db
from config import Config
from translation import Translation
from pyrogram import Client, filters
from pyrogram.errors import ListenerTimeout
from .test import get_configs, update_configs, CLIENT, parse_buttons
from pyrogram.types import InlineKeyboardButton
from buttons import StyledMarkup as InlineKeyboardMarkup, btn, btn_url, row, markup, colored_markup

CLIENT = CLIENT()

# label shown in the panel for each transfer mode, in cycle order
TRANSFER_MODES = {
    'auto': 'AUTO (sᴍᴀʀᴛ)',
    'forward': 'FORWARD (ɴᴀᴛɪᴠᴇ)',
    'copy': 'COPY (sᴇʀᴠᴇʀ-sɪᴅᴇ)',
    'upload': 'UPLOAD (ᴅᴏᴡɴʟᴏᴀᴅ+ᴜᴘ)',
}
TRANSFER_MODE_ORDER = ['auto', 'forward', 'copy', 'upload']


@Client.on_message(filters.command('settings') & filters.private)
async def settings(client, message):
   text = (
      "<blockquote><b>⚙️ <u>sᴋɪɴᴇᴛ ᴠᴇʀsᴇ — ᴄᴏɴᴛʀᴏʟ ᴘᴀɴᴇʟ & sᴇᴛᴛɪɴɢs</u></b></blockquote>\n\n"
      "Customize your bots, destinations, captions, speed limits, and content sanitization filters.\n\n"
      "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
      "👇 <i>Choose a module below to configure:</i>"
   )
   is_adm = await db.is_admin(message.from_user.id)
   await message.reply_text(
     text,
     reply_markup=main_buttons(message.from_user.id, is_admin=is_adm),
     quote=True
   )
    
@Client.on_callback_query(filters.regex(r'^settings'))
async def settings_query(bot, query):
  user_id = query.from_user.id
  i, type = query.data.split("#")
  buttons = [[InlineKeyboardButton('• ʙᴀᴄᴋ', callback_data="settings#main"), InlineKeyboardButton('❌ ᴄʟᴏsᴇ', callback_data="close_btn")]]
  
  if type=="main":
     text = (
        "<blockquote><b>⚙️ <u>sᴋɪɴᴇᴛ ᴠᴇʀsᴇ — ᴄᴏɴᴛʀᴏʟ ᴘᴀɴᴇʟ & sᴇᴛᴛɪɴɢs</u></b></blockquote>\n\n"
        "Customize your bots, destinations, captions, speed limits, and content sanitization filters.\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "👇 <i>Choose a module below to configure:</i>"
     )
     is_adm = await db.is_admin(user_id)
     await query.message.edit_text(
       text,
       reply_markup=main_buttons(user_id, is_admin=is_adm))

  elif type=="speed":
     configs = await get_configs(user_id)
     speed_cfg = configs.get('speed_cfg') or {'mode': 'fast', 'delay': 1.0, 'jitter': True, 'batch_size': 100}
     await query.message.edit_text(
        speed_text(speed_cfg),
        reply_markup=speed_buttons(speed_cfg))

  elif type.startswith("speed_mode_"):
     mode = type.replace("speed_mode_", "")
     configs = await get_configs(user_id)
     speed_cfg = configs.get('speed_cfg') or {'mode': 'fast', 'delay': 1.0, 'jitter': True, 'batch_size': 100}
     speed_cfg['mode'] = mode
     if mode == 'extreme':
        speed_cfg['delay'] = 0.5
        speed_cfg['batch_size'] = 100
     elif mode == 'fast':
        speed_cfg['delay'] = 1.0
        speed_cfg['batch_size'] = 100
     elif mode == 'normal':
        speed_cfg['delay'] = 3.0
        speed_cfg['batch_size'] = 50
     elif mode == 'safe':
        speed_cfg['delay'] = 5.0
        speed_cfg['batch_size'] = 20
     await update_configs(user_id, 'speed_cfg', speed_cfg)
     await query.message.edit_text(
        speed_text(speed_cfg),
        reply_markup=speed_buttons(speed_cfg))

  elif type.startswith("speed_adj_"):
     adj = float(type.replace("speed_adj_", ""))
     configs = await get_configs(user_id)
     speed_cfg = configs.get('speed_cfg') or {'mode': 'fast', 'delay': 1.0, 'jitter': True, 'batch_size': 100}
     new_delay = round(max(0.2, min(30.0, float(speed_cfg.get('delay', 1.0)) + adj)), 1)
     speed_cfg['delay'] = new_delay
     speed_cfg['mode'] = 'custom'
     await update_configs(user_id, 'speed_cfg', speed_cfg)
     await query.message.edit_text(
        speed_text(speed_cfg),
        reply_markup=speed_buttons(speed_cfg))

  elif type == "speed_toggle_jitter":
     configs = await get_configs(user_id)
     speed_cfg = configs.get('speed_cfg') or {'mode': 'fast', 'delay': 1.0, 'jitter': True, 'batch_size': 100}
     speed_cfg['jitter'] = not speed_cfg.get('jitter', True)
     await update_configs(user_id, 'speed_cfg', speed_cfg)
     await query.message.edit_text(
        speed_text(speed_cfg),
        reply_markup=speed_buttons(speed_cfg))
       
  elif type=="bots":
     buttons = []
     _custom_bot = await db.get_custom_bot(user_id)
     _userbot = await db.get_userbot(user_id)
     status_lines = []
     if _custom_bot:
        buttons.append([InlineKeyboardButton(f"🤖 {_custom_bot['name']}",
                         callback_data=f"settings#editbot_token")])
        status_lines.append(f"🤖 <b>ʙᴏᴛ:</b> <code>{_custom_bot['name']}</code> (@{_custom_bot.get('username', '?')})")
     if _userbot:
        buttons.append([InlineKeyboardButton(f"👤 {_userbot['name']}",
                         callback_data=f"settings#editbot_session")])
        status_lines.append(f"👤 <b>ᴜsᴇʀʙᴏᴛ:</b> <code>{_userbot['name']}</code> (@{_userbot.get('username', '?')})")
     if not status_lines:
        status_lines.append("<i>ɴᴏ ʙᴏᴛs ᴄᴏɴɴᴇᴄᴛᴇᴅ ʏᴇᴛ. ᴀᴅᴅ ᴏɴᴇ ʙᴇʟᴏᴡ!</i>")
     # Always offered: a connected userbot must not hide the option to add a bot token.
     buttons.append([InlineKeyboardButton('✚ ᴀᴅᴅ ʙᴏᴛ ✚',
                      callback_data="settings#addbot")])
     buttons.append([InlineKeyboardButton('✚ ᴀᴅᴅ ᴜsᴇʀ ʙᴏᴛ ✚',
                      callback_data="settings#adduserbot")])
     buttons.append([InlineKeyboardButton('✚ ʟᴏɢɪɴ ᴜsᴇʀ ʙᴏᴛ ✚',
                      callback_data="settings#addlogin")])
     buttons.append([InlineKeyboardButton('• ʙᴀᴄᴋ',
                      callback_data="settings#main")])
     await query.message.edit_text(
       "<blockquote><b>🤖 <u>ᴍʏ ᴄᴏɴɴᴇᴄᴛᴇᴅ ʙᴏᴛs & ᴜsᴇʀʙᴏᴛs</u></b></blockquote>\n\n"
       + "\n".join(status_lines) + "\n\n"
       "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
       "<i>ʙᴏᴛ ᴛᴏᴋᴇɴ = ᴘᴜʙʟɪᴄ ᴄʜᴀɴɴᴇʟs | ᴜsᴇʀʙᴏᴛ = ᴘʀɪᴠᴀᴛᴇ ᴄʜᴀɴɴᴇʟs\n"
       "ʏᴏᴜ ᴄᴀɴ ᴀᴅᴅ ʙᴏᴛʜ! ᴛʜᴇ ʙᴏᴛ ᴀᴜᴛᴏ-sᴡɪᴛᴄʜᴇs ᴛᴏ ᴜsᴇʀʙᴏᴛ ғᴏʀ ᴘʀɪᴠᴀᴛᴇ sᴏᴜʀᴄᴇs.</i>\n\n"
       "👇 <i>sᴇʟᴇᴄᴛ ᴀ ʙᴏᴛ ᴛᴏ ᴇᴅɪᴛ ᴏʀ ᴀᴅᴅ ᴀ ɴᴇᴡ ᴏɴᴇ:</i>",
       reply_markup=InlineKeyboardMarkup(buttons))
  
  elif type=="addbot":
     try:
        await query.message.delete()
     except Exception:
        pass
     res = await CLIENT.add_bot(bot, query)
     if res != True: return
     await bot.send_message(
        user_id,
        "<b>ʙᴏᴛ ᴛᴏᴋᴇɴ sᴜᴄᴄᴇssғᴜʟʟʏ ᴀᴅᴅᴇᴅ ᴛᴏ ᴅʙ ✅</b>",
        reply_markup=InlineKeyboardMarkup(buttons))
  
  elif type == "addlogin":
     try:
        await query.message.delete()
     except Exception:
        pass
     user = await CLIENT.add_login(bot, query)
     if user is None: return    
     await bot.send_message(
        user_id,
        "<b>sᴜᴄᴄᴇssғᴜʟʟʏ ʟᴏɢɪɴ ᴛᴏ ᴅʙ ✅</b>",
        reply_markup=InlineKeyboardMarkup(buttons))
        

  elif type=="adduserbot":
     try:
        await query.message.delete()
     except Exception:
        pass
     res = await CLIENT.add_session(bot, query)
     if res != True: return
     await bot.send_message(
        user_id,
        "<b>sᴇssɪᴏɴ sᴜᴄᴄᴇss ғᴜʟʟʏ ᴀᴅᴅᴇᴅ ᴛᴏ ᴅʙ ✅</b>",
        reply_markup=InlineKeyboardMarkup(buttons))
      
  elif type=="channels":
     buttons = []
     channels = await db.get_user_channels(user_id)
     for channel in channels:
        buttons.append([InlineKeyboardButton(f"{channel['title']}",
                         callback_data=f"settings#editchannels_{channel['chat_id']}")])
     buttons.append([InlineKeyboardButton('✚ ᴀᴅᴅ ᴄʜᴀɴɴᴇʟ ✚', 
                      callback_data="settings#addchannel")])
     buttons.append([InlineKeyboardButton('• ʙᴀᴄᴋ', 
                      callback_data="settings#main")])
     await query.message.edit_text( 
       "<blockquote><b>🏷 <u>ʏᴏᴜʀ ᴛᴀʀɢᴇᴛ & sᴏᴜʀᴄᴇ ᴄʜᴀɴɴᴇʟs</u></b></blockquote>\n\n"
       "Manage your connected channels, groups, and target destinations.\n\n"
       "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
       "👇 <i>Select a channel below to view details or add new:</i>",
       reply_markup=InlineKeyboardMarkup(buttons))
   
  elif type=="addchannel":  
      await query.message.delete()
      try:
          text = await bot.send_message(user_id, "<b>sᴇᴛ ᴛᴀʀɢᴇᴛ ᴄʜᴀɴɴᴇʟ\n\nғᴏʀᴡᴀʀᴅ ᴀ ᴍᴇssᴀɢᴇ ғʀᴏᴍ ᴛᴀʀɢᴇᴛ ᴄʜᴀɴɴᴇʟ, ᴏʀ sᴇɴᴅ ᴄʜᴀɴɴᴇʟ ɪᴅ / ʟɪɴᴋ.\n/cancel - ᴛᴏ ᴄᴀɴᴄᴇʟ ᴛʜɪs ᴘʀᴏᴄᴇss</b>")
          chat_ids = await bot.listen(chat_id=user_id, timeout=300)
          if chat_ids.text=="/cancel":
             await chat_ids.delete()
             return await text.edit_text(
                   "<b>ᴘʀᴏᴄᴇss ᴄᴀɴᴄᴇʟʟᴇᴅ</b>",
                   reply_markup=InlineKeyboardMarkup(buttons))
          from plugins.forward_parser import resolve_channel_input
          res = await resolve_channel_input(chat_ids, bot)
          if not res.get("chat_id"):
             await chat_ids.delete()
             return await text.edit_text(f"❌ <b>ɪɴᴠᴀʟɪᴅ ᴄʜᴀɴɴᴇʟ:</b> {res.get('error', 'Could not resolve channel')}", reply_markup=InlineKeyboardMarkup(buttons))
          chat_id = res["chat_id"]
          title = res.get("chat_title") or str(chat_id)
          username = res.get("chat_username") or "private"
          if username and not username.startswith("@") and username != "private":
              username = "@" + username
          chat = await db.add_channel(user_id, chat_id, title, username)
          try:
              await chat_ids.delete()
          except Exception:
              pass
          await text.edit_text(
             "<b>sᴜᴄᴄᴇssғᴜʟʟʏ ᴜᴘᴅᴀᴛᴇᴅ ✅</b>" if chat else "<b>ᴛʜɪs ᴄʜᴀɴɴᴇʟ ɪs ᴀʟʀᴇᴀᴅʏ ᴀᴅᴅᴇᴅ</b>",
             reply_markup=InlineKeyboardMarkup(buttons))
      except (asyncio.exceptions.TimeoutError, ListenerTimeout):
          await text.edit_text('ᴘʀᴏᴄᴇss ʜᴀs ʙᴇᴇɴ ᴀᴜᴛᴏᴍᴀᴛɪᴄᴀʟʟʏ ᴄᴀɴᴄᴇʟʟᴇᴅ.', reply_markup=InlineKeyboardMarkup(buttons))

  
  elif type in ("editbot", "editbot_token", "editbot_session"):
     # Determine which bot to show based on callback type
     if type == "editbot_session":
        bot_doc = await db.get_userbot(user_id)
     elif type == "editbot_token":
        bot_doc = await db.get_custom_bot(user_id)
     else:
        bot_doc = await db.get_bot(user_id)
     if not bot_doc:
        return await query.answer("ɴᴏ ʙᴏᴛ ғᴏᴜɴᴅ.", show_alert=True)
     TEXT = Translation.BOT_DETAILS if bot_doc.get('is_bot') else Translation.USER_DETAILS
     remove_cb = "settings#removebot_session" if not bot_doc.get('is_bot') else "settings#removebot_token"
     buttons = [[InlineKeyboardButton('❌ ʀᴇᴍᴏᴠᴇ ❌', callback_data=remove_cb)
               ],
               [InlineKeyboardButton('• ʙᴀᴄᴋ', callback_data="settings#bots")]]
     await query.message.edit_text(
        TEXT.format(bot_doc['name'], bot_doc['id'], bot_doc['username']),
        reply_markup=InlineKeyboardMarkup(buttons))
                                             
  elif type in ("removebot", "removebot_token", "removebot_session"):
     if type == "removebot_session":
        await db.remove_bot(user_id, is_bot=False)
     elif type == "removebot_token":
        await db.remove_bot(user_id, is_bot=True)
     else:
        await db.remove_bot(user_id)
     await query.message.edit_text(
        "<b>sᴜᴄᴄᴇssғᴜʟʟʏ ᴜᴘᴅᴀᴛᴇᴅ ✅</b>",
        reply_markup=InlineKeyboardMarkup(buttons))
                                             
  elif type.startswith("editchannels"): 
     chat_id = type.split('_')[1]
     chat = await db.get_channel_details(user_id, chat_id)
     buttons = [[InlineKeyboardButton('❌ ʀᴇᴍᴏᴠᴇ ❌', callback_data=f"settings#removechannel_{chat_id}")
               ],
               [InlineKeyboardButton('• ʙᴀᴄᴋ', callback_data="settings#channels")]]
     await query.message.edit_text(
        f"<b><u>📄 ᴄʜᴀɴɴᴇʟ ᴅᴇᴛᴀɪʟs</b></u>\n\n<b>- ᴛɪᴛʟᴇ:</b> <code>{chat['title']}</code>\n<b>- ᴄʜᴀɴɴᴇʟ ɪᴅ: </b> <code>{chat['chat_id']}</code>\n<b>- ᴜsᴇʀɴᴀᴍᴇ:</b> {chat['username']}",
        reply_markup=InlineKeyboardMarkup(buttons))
        
  elif type.startswith("removechannel"):
     chat_id = type.split('_')[1]
     await db.remove_channel(user_id, chat_id)
     await query.message.edit_text(
        "<b>sᴜᴄᴄᴇssғᴜʟʟʏ ᴜᴘᴅᴀᴛᴇᴅ ✅</b>",
        reply_markup=InlineKeyboardMarkup(buttons))
                               
  elif type=="caption":
     buttons = []
     data = await get_configs(user_id)
     caption = data['caption']
     clean_caption = data.get('clean_caption', False)
     clean_mark = "✅ ᴏɴ" if clean_caption else "❌ ᴏғғ"
     if caption is None:
        buttons.append([InlineKeyboardButton('✚ ᴀᴅᴅ ᴄᴀᴘᴛɪᴏɴ ✚', 
                      callback_data="settings#addcaption")])
     else:
        buttons.append([InlineKeyboardButton('sᴇᴇ ᴄᴀᴘᴛɪᴏɴ', 
                      callback_data="settings#seecaption")])
        buttons[-1].append(InlineKeyboardButton('🗑️ ᴅᴇʟᴇᴛᴇ ᴄᴀᴘᴛɪᴏɴ', 
                      callback_data="settings#deletecaption"))
     buttons.append([InlineKeyboardButton(f"🧹 ᴀᴜᴛᴏ-ᴄʟᴇᴀɴ ᴄᴀᴘᴛɪᴏɴ: {clean_mark}", 
                   callback_data="settings#toggle_cleancaption")])
     buttons.append([InlineKeyboardButton('• ʙᴀᴄᴋ', 
                      callback_data="settings#main")])
     await query.message.edit_text(
        "<blockquote><b>🖋️ <u>ᴄᴜsᴛᴏᴍ ᴄᴀᴘᴛɪᴏɴ & ᴀᴜᴛᴏ-sᴀɴɪᴛɪᴢᴇʀ</u></b></blockquote>\n\n"
        "Configure custom message captions or enable auto-cleaning to automatically strip competitor links, usernames & promotional ads.\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "<b><u>AVAILABLE FILLINGS:</u></b>\n"
        "• <code>{filename}</code> : File Name\n"
        "• <code>{size}</code> : Formatted File Size\n"
        "• <code>{caption}</code> : Original Caption",
        reply_markup=InlineKeyboardMarkup(buttons))
                                
  elif type=="toggle_cleancaption":
     data = await get_configs(user_id)
     curr = data.get('clean_caption', False)
     await update_configs(user_id, 'clean_caption', not curr)
     await query.answer(f"Auto-Clean: {'Enabled' if not curr else 'Disabled'}")
     data = await get_configs(user_id)
     caption = data['caption']
     clean_caption = data.get('clean_caption', False)
     clean_mark = "✅ ᴏɴ" if clean_caption else "❌ ᴏғғ"
     buttons = []
     if caption is None:
        buttons.append([InlineKeyboardButton('✚ ᴀᴅᴅ ᴄᴀᴘᴛɪᴏɴ ✚', 
                      callback_data="settings#addcaption")])
     else:
        buttons.append([InlineKeyboardButton('sᴇᴇ ᴄᴀᴘᴛɪᴏɴ', 
                      callback_data="settings#seecaption")])
        buttons[-1].append(InlineKeyboardButton('🗑️ ᴅᴇʟᴇᴛᴇ ᴄᴀᴘᴛɪᴏɴ', 
                      callback_data="settings#deletecaption"))
     buttons.append([InlineKeyboardButton(f"🧹 ᴀᴜᴛᴏ-ᴄʟᴇᴀɴ ᴄᴀᴘᴛɪᴏɴ: {clean_mark}", 
                   callback_data="settings#toggle_cleancaption")])
     buttons.append([InlineKeyboardButton('• ʙᴀᴄᴋ', 
                      callback_data="settings#main")])
     await query.message.edit_text(
        "<blockquote><b>🖋️ <u>ᴄᴜsᴛᴏᴍ ᴄᴀᴘᴛɪᴏɴ & ᴀᴜᴛᴏ-sᴀɴɪᴛɪᴢᴇʀ</u></b></blockquote>\n\n"
        "Configure custom message captions or enable auto-cleaning to automatically strip competitor links, usernames & promotional ads.\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "<b><u>AVAILABLE FILLINGS:</u></b>\n"
        "• <code>{filename}</code> : File Name\n"
        "• <code>{size}</code> : Formatted File Size\n"
        "• <code>{caption}</code> : Original Caption",
        reply_markup=InlineKeyboardMarkup(buttons))
                                
  elif type=="seecaption":   
     data = await get_configs(user_id)
     buttons = [[InlineKeyboardButton('🖋️ ᴇᴅɪᴛ ᴄᴀᴘᴛɪᴏɴ', 
                  callback_data="settings#addcaption")
               ],[
               InlineKeyboardButton('• ʙᴀᴄᴋ', 
                 callback_data="settings#caption")]]
     await query.message.edit_text(
        f"<b><u>YOUR CUSTOM CAPTION</b></u>\n\n<code>{data['caption']}</code>",
        reply_markup=InlineKeyboardMarkup(buttons))
    
  elif type=="deletecaption":
     await update_configs(user_id, 'caption', None)
     await query.message.edit_text(
        "<b>successfully updated</b>",
        reply_markup=InlineKeyboardMarkup(buttons))
                              
  elif type=="addcaption":
     await query.message.delete()
     try:
         text = await bot.send_message(query.message.chat.id, "Send your custom caption\n/cancel - <code>cancel this process</code>")
         caption = await bot.listen(chat_id=user_id, timeout=300)
         if caption.text=="/cancel":
            await caption.delete()
            return await text.edit_text(
                  "<b>process canceled !</b>",
                  reply_markup=InlineKeyboardMarkup(buttons))
         try:
            caption.text.format(filename='', size='', caption='')
         except KeyError as e:
            await caption.delete()
            return await text.edit_text(
               f"<b>wrong filling {e} used in your caption. change it</b>",
               reply_markup=InlineKeyboardMarkup(buttons))
         await update_configs(user_id, 'caption', caption.text)
         await caption.delete()
         await text.edit_text(
            "<b>Successfully Updated</b>",
            reply_markup=InlineKeyboardMarkup(buttons))
     except (asyncio.exceptions.TimeoutError, ListenerTimeout):
         await text.edit_text('Process has been automatically cancelled', reply_markup=InlineKeyboardMarkup(buttons))
  
  elif type=="button":
     buttons = []
     button = (await get_configs(user_id))['button']
     if button is None:
        buttons.append([InlineKeyboardButton('✚ ᴀᴅᴅ ʙᴜᴛᴛᴏɴ ✚', 
                      callback_data="settings#addbutton")])
     else:
        buttons.append([InlineKeyboardButton('👀 sᴇᴇ ʙᴜᴛᴛᴏɴ', 
                      callback_data="settings#seebutton")])
        buttons[-1].append(InlineKeyboardButton('🗑️ ʀᴇᴍᴏᴠᴇ ʙᴜᴛᴛᴏɴ ', 
                      callback_data="settings#deletebutton"))
     buttons.append([InlineKeyboardButton('↩ Back', 
                      callback_data="settings#main")])
     await query.message.edit_text(
         "<blockquote><b>⏹ <u>ᴄᴜsᴛᴏᴍ ɪɴʟɪɴᴇ ʙᴜᴛᴛᴏɴ</u></b></blockquote>\n\n"
         "Attach interactive buttons to all your forwarded messages.\n\n"
         "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
         "<b><u>FORMAT SPECIFICATION:</u></b>\n"
         "• <code>[Button Text][buttonurl:https://t.me/yourlink]</code>\n"
         "• <code>[Row 1][buttonurl:link1] | [Row 1 Col 2][buttonurl:link2]</code>",
         reply_markup=InlineKeyboardMarkup(buttons))
  
  elif type=="addbutton":
     await query.message.delete()
     try:
         txt = await bot.send_message(user_id, text="**Send your custom button.\n\nFORMAT:**\n`[Button Name][buttonurl:https://t.me/your_link]`\n\n/cancel - `cancel this process`")
         ask = await bot.listen(chat_id=user_id, timeout=300)
         if not ask or not ask.text or ask.text == '/cancel':
            return await txt.edit_text("<b>Process cancelled !</b>", reply_markup=InlineKeyboardMarkup(buttons))
         button = parse_buttons(ask.text)
         if not button:
            try: await ask.delete()
            except Exception: pass
            return await txt.edit_text("**INVALID BUTTON FORMAT**", reply_markup=InlineKeyboardMarkup(buttons))
         await update_configs(user_id, 'button', ask.text)
         try: await ask.delete()
         except Exception: pass
         await txt.edit_text("**Successfully button added**",
            reply_markup=InlineKeyboardMarkup(buttons))
     except Exception as e:
         await txt.edit_text(f'Process cancelled or timed out ({e})', reply_markup=InlineKeyboardMarkup(buttons))
  
  elif type=="seebutton":
      button = (await get_configs(user_id))['button']
      button = parse_buttons(button, markup=False)
      button.append([InlineKeyboardButton("↩ ʙᴀᴄᴋ", callback_data="settings#button")])
      await query.message.edit_text(
         "<blockquote><b>✨ <u>ʏᴏᴜʀ ᴄᴜsᴛᴏᴍ ʙᴜᴛᴛᴏɴ</u></b></blockquote>",
         reply_markup=InlineKeyboardMarkup(button))
      
  elif type=="deletebutton":
     await update_configs(user_id, 'button', None)
     await query.message.edit_text(
        "**Successfully button deleted**",
        reply_markup=InlineKeyboardMarkup(buttons))
   
  elif type=="database":
     buttons = []
     db_uri = (await get_configs(user_id))['db_uri']
     if db_uri is None:
        buttons.append([InlineKeyboardButton('✚ ᴀᴅᴅ ᴜʀʟ ✚', 
                      callback_data="settings#addurl")])
     else:
        buttons.append([InlineKeyboardButton('👀 sᴇᴇ ᴜʀʟ', 
                      callback_data="settings#seeurl")])
        buttons[-1].append(InlineKeyboardButton('🗑️ ʀᴇᴍᴏᴠᴇ ᴜʀʟ ', 
                      callback_data="settings#deleteurl"))
     buttons.append([InlineKeyboardButton('• ʙᴀᴄᴋ', 
                      callback_data="settings#main")])
     await query.message.edit_text(
         "<blockquote><b>🗃 <u>ᴍᴏɴɢᴏᴅʙ ᴅᴀᴛᴀʙᴀsᴇ ᴄᴏɴɴᴇᴄᴛɪᴏɴ</u></b></blockquote>\n\n"
         "Database is required to store duplicate message signatures permanently. Without MongoDB, duplicate tracking resets when the bot restarts.\n\n"
         "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
         "👇 <i>Configure your custom MongoDB cluster URI below:</i>",
         reply_markup=InlineKeyboardMarkup(buttons))
  elif type=="addurl":
     await query.message.delete()
     try:
        uri = await bot.ask(user_id, "<b>please send your mongodb url.</b>\n\n<i>get your Mongodb url from [here](https://mongodb.com)</i>", disable_web_page_preview=True, timeout=120)
     except Exception:
        return await query.message.reply_text("⏰ <b>ᴛɪᴍᴇᴏᴜᴛ: ɴᴏ ʀᴇsᴘᴏɴsᴇ ʀᴇᴄᴇɪᴠᴇᴅ.</b>", reply_markup=InlineKeyboardMarkup(buttons))
     if not uri or not uri.text or uri.text.lower() == "/cancel":
        return await query.message.reply_text(
                  "<b>process canceled !</b>",
                  reply_markup=InlineKeyboardMarkup(buttons))
     if not uri.text.startswith("mongodb+srv://") and not uri.text.endswith("majority"):
        return await uri.reply("<b>Invalid Mongodb Url</b>",
                   reply_markup=InlineKeyboardMarkup(buttons))
     await update_configs(user_id, 'db_uri', uri.text)
     await uri.reply("**Successfully database url added**",
             reply_markup=InlineKeyboardMarkup(buttons))
  
  elif type=="seeurl":
     db_uri = (await get_configs(user_id))['db_uri']
     await query.answer(f"DATABASE URL: {db_uri}", show_alert=True)
  
  elif type=="deleteurl":
     await update_configs(user_id, 'db_uri', None)
     await query.message.edit_text(
        "**Successfully your database url deleted**",
        reply_markup=InlineKeyboardMarkup(buttons))
      
  elif type=="dump":
     if not await db.is_admin(user_id):
        return await query.answer("⚠️ Dump Channel settings are restricted to Bot Admins only!", show_alert=True)
     dump_chan, dump_enabled = await db.get_admin_dump()
     state_mark = "✅ ᴏɴ" if dump_enabled else "❌ ᴏғғ"
     current_info = f"<code>{dump_chan}</code>" if dump_chan else "Not Set"
     
     btn = [
        [InlineKeyboardButton(f"📦 ᴍᴇᴅɪᴀ ᴅᴜᴍᴘ: {state_mark}", callback_data="settings#toggledump")],
        [InlineKeyboardButton("➕ sᴇᴛ ᴅᴜᴍᴘ ᴄʜᴀɴɴᴇʟ", callback_data="settings#setdump")]
     ]
     if dump_chan:
        btn[1].append(InlineKeyboardButton("🗑️ ʀᴇᴍᴏᴠᴇ", callback_data="settings#deletedump"))
     btn.append([InlineKeyboardButton("• ʙᴀᴄᴋ", callback_data="settings#main")])
     
     await query.message.edit_text(
        "<blockquote><b>📦 <u>ᴍᴇᴅɪᴀ ᴅᴜᴍᴘ / ʙᴀᴄᴋᴜᴘ ᴄʜᴀɴɴᴇʟ (ᴀᴅᴍɪɴ)</u></b></blockquote>\n\n"
        "A dedicated backup channel where all forwarded media/files from all users are mirrored and saved permanently.\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"• <b>ᴄᴜʀʀᴇɴᴛ ᴅᴜᴍᴘ ᴛᴀʀɢᴇᴛ:</b> {current_info}\n"
        f"• <b>ᴍᴇᴅɪᴀ ᴅᴜᴍᴘ sᴛᴀᴛᴜs:</b> <code>{state_mark}</code>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "👑 <i>Only bot admins can configure this channel.</i>",
        reply_markup=InlineKeyboardMarkup(btn)
     )

  elif type=="toggledump":
     if not await db.is_admin(user_id):
        return await query.answer("⚠️ Dump Channel settings are restricted to Bot Admins only!", show_alert=True)
     dump_chan, dump_enabled = await db.get_admin_dump()
     await db.update_admin_dump(dump_chan, not dump_enabled)
     await query.answer(f"Media Dump: {'Enabled' if not dump_enabled else 'Disabled'}")
     dump_chan, dump_enabled = await db.get_admin_dump()
     state_mark = "✅ ᴏɴ" if dump_enabled else "❌ ᴏғғ"
     current_info = f"<code>{dump_chan}</code>" if dump_chan else "Not Set"
     btn = [
        [InlineKeyboardButton(f"📦 ᴍᴇᴅɪᴀ ᴅᴜᴍᴘ: {state_mark}", callback_data="settings#toggledump")],
        [InlineKeyboardButton("➕ sᴇᴛ ᴅᴜᴍᴘ ᴄʜᴀɴɴᴇʟ", callback_data="settings#setdump")]
     ]
     if dump_chan:
        btn[1].append(InlineKeyboardButton("🗑️ ʀᴇᴍᴏᴠᴇ", callback_data="settings#deletedump"))
     btn.append([InlineKeyboardButton("• ʙᴀᴄᴋ", callback_data="settings#main")])
     await query.message.edit_text(
        "<blockquote><b>📦 <u>ᴍᴇᴅɪᴀ ᴅᴜᴍᴘ / ʙᴀᴄᴋᴜᴘ ᴄʜᴀɴɴᴇʟ (ᴀᴅᴍɪɴ)</u></b></blockquote>\n\n"
        "A dedicated backup channel where all forwarded media/files from all users are mirrored and saved permanently.\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"• <b>ᴄᴜʀʀᴇɴᴛ ᴅᴜᴍᴘ ᴛᴀʀɢᴇᴛ:</b> {current_info}\n"
        f"• <b>ᴍᴇᴅɪᴀ ᴅᴜᴍᴘ sᴛᴀᴛᴜs:</b> <code>{state_mark}</code>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "👑 <i>Only bot admins can configure this channel.</i>",
        reply_markup=InlineKeyboardMarkup(btn)
     )

  elif type=="setdump":
      if not await db.is_admin(user_id):
         return await query.answer("⚠️ Dump Channel settings are restricted to Bot Admins only!", show_alert=True)
      await query.message.delete()
      try:
          txt = await bot.send_message(
              user_id,
              "<blockquote><b>📦 <u>sᴇᴛ ɢʟᴏʙᴀʟ ᴅᴜᴍᴘ ᴄʜᴀɴɴᴇʟ</u></b></blockquote>\n\n"
              "ғᴏʀᴡᴀʀᴅ ᴀ ᴍᴇssᴀɢᴇ ғʀᴏᴍ ʏᴏᴜʀ ᴅᴜᴍᴘ ᴄʜᴀɴɴᴇʟ, ᴏʀ sᴇɴᴅ ɪᴛs ɪᴅ / ʟɪɴᴋ.\n\n"
              "• <b>ғᴏʀᴡᴀʀᴅ:</b> <i>ғᴏʀᴡᴀʀᴅ ᴀɴʏ ᴍᴇssᴀɢᴇ ғʀᴏᴍ ᴛʜᴇ ᴄʜᴀɴɴᴇʟ (ʀᴇᴄᴏᴍᴍᴇɴᴅᴇᴅ)</i>\n"
              "• <b>ɪᴅ:</b> <code>-1001234567890</code>\n"
              "• <b>ʟɪɴᴋ:</b> <code>https://t.me/c/...</code> ᴏʀ <code>@my_channel</code>\n\n"
              "⚠️ <b>ɪᴍᴘᴏʀᴛᴀɴᴛ:</b> <i>ᴍᴀᴋᴇ sᴜʀᴇ ᴛʜᴇ ʙᴏᴛ ɪs ᴀᴅᴅᴇᴅ ᴀs ᴀɴ ᴀᴅᴍɪɴ ɪɴ ᴛʜᴇ ᴅᴜᴍᴘ ᴄʜᴀɴɴᴇʟ!</i>\n\n"
              "/cancel — <code>ᴄᴀɴᴄᴇʟ ᴘʀᴏᴄᴇss</code>"
          )
          ask = await bot.listen(chat_id=user_id, timeout=300)
          if not ask or (ask.text and ask.text == '/cancel'):
              return await txt.edit_text("<b>ᴘʀᴏᴄᴇss ᴄᴀɴᴄᴇʟʟᴇᴅ !</b>", reply_markup=InlineKeyboardMarkup(buttons))
          from plugins.forward_parser import resolve_channel_input
          res = await resolve_channel_input(ask, bot, verify_access=True)
          if not res.get("chat_id"):
              err_msg = res.get("error") or "Could not parse channel from input."
              return await txt.edit_text(f"❌ <b>ᴇʀʀᴏʀ:</b>\n\n{err_msg}", reply_markup=InlineKeyboardMarkup(buttons))
          c_id = res["chat_id"]
          c_title = res.get("chat_title") or str(c_id)
          Config.DUMP_CHANNEL = c_id
          await db.update_system_config("DUMP_CHANNEL", c_id)
          await db.update_admin_dump(c_id, True)
          try:
              await ask.delete()
          except Exception:
              pass
          await txt.edit_text(
              f"<blockquote><b>✅ <u>ɢʟᴏʙᴀʟ ᴅᴜᴍᴘ ᴄʜᴀɴɴᴇʟ sᴇᴛ</u></b></blockquote>\n\n"
              f"📢 <b>ᴄʜᴀɴɴᴇʟ:</b> <code>{c_title}</code>\n"
              f"🆔 <b>ɪᴅ:</b> <code>{c_id}</code>\n"
              f"📦 <b>sᴛᴀᴛᴜs:</b> <code>✅ ᴏɴ (ᴀᴄᴛɪᴠᴇ)</code>\n\n"
              f"<i>ᴀʟʟ ғᴏʀᴡᴀʀᴅᴇᴅ ᴍᴇᴅɪᴀ ᴡɪʟʟ ɴᴏᴡ ʙᴇ ᴍɪʀʀᴏʀᴇᴅ ᴛᴏ ᴛʜɪs ᴄʜᴀɴɴᴇʟ!</i>",
              reply_markup=InlineKeyboardMarkup(buttons)
          )
      except Exception as e:
          await bot.send_message(user_id, f"Process error: {e}", reply_markup=InlineKeyboardMarkup(buttons))

  elif type=="deletedump":
     if not await db.is_admin(user_id):
        return await query.answer("⚠️ Dump Channel settings are restricted to Bot Admins only!", show_alert=True)
     await db.update_admin_dump(None, False)
     await query.answer("Dump Channel removed!", show_alert=True)
     btn = [
        [InlineKeyboardButton("📦 ᴍᴇᴅɪᴀ ᴅᴜᴍᴘ: ❌ ᴏғғ", callback_data="settings#toggledump")],
        [InlineKeyboardButton("➕ sᴇᴛ ᴅᴜᴍᴘ ᴄʜᴀɴɴᴇʟ", callback_data="settings#setdump")],
        [InlineKeyboardButton("• ʙᴀᴄᴋ", callback_data="settings#main")]
     ]
     await query.message.edit_text(
        "<blockquote><b>📦 <u>ᴍᴇᴅɪᴀ ᴅᴜᴍᴘ / ʙᴀᴄᴋᴜᴘ ᴄʜᴀɴɴᴇʟ (ᴀᴅᴍɪɴ)</u></b></blockquote>\n\n"
        "A dedicated backup channel where all forwarded media/files from all users are mirrored and saved permanently.\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "• <b>ᴄᴜʀʀᴇɴᴛ ᴅᴜᴍᴘ ᴛᴀʀɢᴇᴛ:</b> Not Set\n"
        "• <b>ᴍᴇᴅɪᴀ ᴅᴜᴍᴘ sᴛᴀᴛᴜs:</b> <code>❌ ᴏғғ</code>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "👑 <i>Only bot admins can configure this channel.</i>",
        reply_markup=InlineKeyboardMarkup(btn)
     )
      
  elif type=="filters":
     await query.message.edit_text(
        "<blockquote><b>🕵‍♀ <u>ᴄᴜsᴛᴏᴍ ᴍᴇssᴀɢᴇ ғɪʟᴛᴇʀs</u> 🕵‍♀</b></blockquote>\n\n"
        "Configure which media and message formats to transfer or ignore.\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "👇 <i>Click any filter below to toggle ON / OFF:</i>",
        reply_markup=await filters_buttons(user_id))
  elif type=="nextfilters":
     await query.edit_message_reply_markup( 
        reply_markup=await next_filters_buttons(user_id))
   
  elif type.startswith("updatefilter"):
     i, key, value = type.split('-')
     if value=="True":
        await update_configs(user_id, key, False)
     else:
        await update_configs(user_id, key, True)
     if key in ['poll', 'protect']:
        return await query.edit_message_reply_markup(
           reply_markup=await next_filters_buttons(user_id)) 
     await query.edit_message_reply_markup(
        reply_markup=await filters_buttons(user_id))
   
  elif type.startswith("alert_"):
     alert_msg = type.replace("alert_", "")
     if alert_msg == "toggle":
        alert_msg = "ℹ️ ᴛᴀᴘ ᴛʜᴇ ✅ / ❌ ʙᴜᴛᴛᴏɴ ᴛᴏ ᴛᴏɢɢʟᴇ"
     return await query.answer(alert_msg, show_alert=True)

  elif type.startswith("file_size"):
    settings = await get_configs(user_id)
    size = settings.get('file_size', 0)
    i, limit = size_limit(settings['size_limit'])
    await query.message.edit_text(
       f'<b><u>SIZE LIMIT</b></u><b>\n\nyou can set file size limit to forward\n\nStatus: files with {limit} `{size} MB` will forward</b>',
       reply_markup=size_button(size))
  elif type.startswith("update_size"):
    try:
      size = int(query.data.split('-')[1])
    except (IndexError, ValueError):
      size = 0
    if size > 2000 or size < 0:
      return await query.answer("⚠️ sɪᴢᴇ ʟɪᴍɪᴛ ᴇxᴄᴇᴇᴅᴇᴅ (0 - 2000 ᴍʙ)", show_alert=True)
    await update_configs(user_id, 'file_size', size)
    i, limit = size_limit((await get_configs(user_id))['size_limit'])
    await query.message.edit_text(
       f'<b><u>sɪᴢᴇ ʟɪᴍɪᴛ</b></u><b>\n\nʏᴏᴜ ᴄᴀɴ sᴇᴛ ғɪʟᴇ sɪᴢᴇ ʟɪᴍɪᴛ ᴛᴏ ғᴏʀᴡᴀʀᴅ\n\nsᴛᴀᴛᴜs: ғɪʟᴇs ᴡɪᴛʜ {limit} `{size} ᴍʙ` ᴡɪʟʟ ғᴏʀᴡᴀʀᴅ</b>',
       reply_markup=size_button(size))
  
  elif type.startswith('update_limit'):
    i, limit, size = type.split('-')
    limit, sts = size_limit(limit)
    await update_configs(user_id, 'size_limit', limit) 
    await query.message.edit_text(
       f'<b><u>SIZE LIMIT</b></u><b>\n\nyou can set file size limit to forward\n\nStatus: files with {sts} `{size} MB` will forward</b>',
       reply_markup=size_button(int(size)))
  elif type == "add_extension":
    await query.message.delete() 
    try:
       ext = await bot.ask(user_id, text="**please send your extensions (seperete by space)**", timeout=120)
    except Exception:
       return await query.message.reply_text("⏰ <b>ᴛɪᴍᴇᴏᴜᴛ: ɴᴏ ʀᴇsᴘᴏɴsᴇ ʀᴇᴄᴇɪᴠᴇᴅ.</b>", reply_markup=InlineKeyboardMarkup(buttons))
    if not ext or not ext.text or ext.text.lower() == '/cancel':
       return await query.message.reply_text(
                  "<b>process canceled</b>",
                  reply_markup=InlineKeyboardMarkup(buttons))
    extensions = ext.text.split(" ")
    extension = (await get_configs(user_id))['extension']
    if extension:
        for extn in extensions:
            extension.append(extn)
    else:
        extension = extensions
    await update_configs(user_id, 'extension', extension)
    await ext.reply_text(
        f"**successfully updated**",
        reply_markup=InlineKeyboardMarkup(buttons))
  elif type == "get_extension":
    extensions = (await get_configs(user_id))['extension']
    btn = extract_btn(extensions)
    btn.append([InlineKeyboardButton('✚ ᴀᴅᴅ ✚', callback_data='settings#add_extension')])
    btn.append([InlineKeyboardButton('🗑️ ʀᴇᴍᴏᴠᴇ ᴀʟʟ', callback_data='settings#rmve_all_extension')])
    btn.append([InlineKeyboardButton('• ʙᴀᴄᴋ', callback_data='settings#main')])
    await query.message.edit_text(
        text='<b><u>ᴇxᴛᴇɴsɪᴏɴs</u></b>\n\n<i>ғɪʟᴇs ᴡɪᴛʜ ᴛʜᴇsᴇ ᴇxᴛᴇɴsɪᴏɴs ᴡɪʟʟ ɴᴏᴛ ʙᴇ ғᴏʀᴡᴀʀᴅᴇᴅ.</i>',
        reply_markup=InlineKeyboardMarkup(btn))
  
  elif type == "rmve_all_extension":
    await update_configs(user_id, 'extension', None)
    await query.message.edit_text(text="<b>✅ sᴜᴄᴄᴇssғᴜʟʟʏ ᴅᴇʟᴇᴛᴇᴅ</b>",
                                   reply_markup=InlineKeyboardMarkup(buttons))
  elif type == "add_keyword":
    await query.message.delete()
    try:
        ask = await bot.ask(user_id, text="<b>ᴘʟᴇᴀsᴇ sᴇɴᴅ ᴋᴇʏᴡᴏʀᴅs (sᴇᴘᴀʀᴀᴛᴇᴅ ʙʏ sᴘᴀᴄᴇ)\n/cancel - ᴄᴀɴᴄᴇʟ</b>", timeout=120)
    except Exception:
        return await query.message.reply_text("⏰ <b>ᴛɪᴍᴇᴏᴜᴛ: ɴᴏ ʀᴇsᴘᴏɴsᴇ ʀᴇᴄᴇɪᴠᴇᴅ.</b>", reply_markup=InlineKeyboardMarkup(buttons))
    if not ask or not ask.text or ask.text.lower() == '/cancel':
        return await query.message.reply_text(
                   "<b>ᴘʀᴏᴄᴇss ᴄᴀɴᴄᴇʟʟᴇᴅ ✅</b>",
                   reply_markup=InlineKeyboardMarkup(buttons))
    keywords = ask.text.split(" ")
    keyword = (await get_configs(user_id))['keywords']
    if keyword:
        for word in keywords:
            keyword.append(word)
    else:
        keyword = keywords
    await update_configs(user_id, 'keywords', keyword)
    await ask.reply_text(
        "<b>✅ sᴜᴄᴄᴇssғᴜʟʟʏ ᴜᴘᴅᴀᴛᴇᴅ</b>",
        reply_markup=InlineKeyboardMarkup(buttons))
  
  elif type == "get_keyword":
    keywords = (await get_configs(user_id))['keywords']
    btn = extract_btn(keywords)
    btn.append([InlineKeyboardButton('✚ ᴀᴅᴅ ✚', callback_data='settings#add_keyword')])
    btn.append([InlineKeyboardButton('🗑️ ʀᴇᴍᴏᴠᴇ ᴀʟʟ', callback_data='settings#rmve_all_keyword')])
    btn.append([InlineKeyboardButton('• ʙᴀᴄᴋ', callback_data='settings#main')])
    await query.message.edit_text(
        text='<b><u>ᴋᴇʏᴡᴏʀᴅs</u></b>\n\n<i>ғɪʟᴇs ᴡɪᴛʜ ᴛʜᴇsᴇ ᴋᴇʏᴡᴏʀᴅs ɪɴ ғɪʟᴇ ɴᴀᴍᴇ ᴡɪʟʟ ʙᴇ ғᴏʀᴡᴀʀᴅᴇᴅ.</i>',
        reply_markup=InlineKeyboardMarkup(btn))
      
  elif type == "rmve_all_keyword":
    await update_configs(user_id, 'keywords', None)
    await query.message.edit_text(text="**sᴜᴄᴄᴇssғᴜʟʟʏ ᴅᴇʟᴇᴛᴇᴅ**",
                                   reply_markup=InlineKeyboardMarkup(buttons))

  elif type == "courseseller":
     configs = await get_configs(user_id)
     await query.message.edit_text(
        course_seller_text(configs),
        reply_markup=course_seller_buttons(configs)
     )

  elif type == "cs_toggle_mode":
     configs = await get_configs(user_id)
     curr = bool(configs.get('course_seller_mode', False))
     new_val = not curr
     configs['course_seller_mode'] = new_val
     if new_val:
        configs['auto_course_list'] = True
        configs['auto_numbering'] = True
        configs['username_remover'] = True
        configs['link_remover'] = True
        configs['hidden_link_remover'] = True
        configs['forward_tag'] = False
     await db.update_configs(user_id, configs)
     await query.answer(f"Course Seller Mode: {'Activated ⚡️' if new_val else 'Disabled'}")
     await query.message.edit_text(
        course_seller_text(configs),
        reply_markup=course_seller_buttons(configs)
     )

  elif type == "cs_toggle_list":
     configs = await get_configs(user_id)
     curr = bool(configs.get('auto_course_list', False))
     configs['auto_course_list'] = not curr
     await db.update_configs(user_id, configs)
     await query.answer(f"Course List Maker: {'ON' if not curr else 'OFF'}")
     await query.message.edit_text(course_seller_text(configs), reply_markup=course_seller_buttons(configs))

  elif type == "cs_toggle_num":
     configs = await get_configs(user_id)
     curr = bool(configs.get('auto_numbering', False))
     configs['auto_numbering'] = not curr
     await db.update_configs(user_id, configs)
     await query.answer(f"Lecture Numbering: {'ON' if not curr else 'OFF'}")
     await query.message.edit_text(course_seller_text(configs), reply_markup=course_seller_buttons(configs))

  elif type == "cs_toggle_user":
     configs = await get_configs(user_id)
     curr = bool(configs.get('username_remover', False))
     configs['username_remover'] = not curr
     await db.update_configs(user_id, configs)
     await query.answer(f"Username Remover: {'ON' if not curr else 'OFF'}")
     await query.message.edit_text(course_seller_text(configs), reply_markup=course_seller_buttons(configs))

  elif type == "cs_toggle_link":
     configs = await get_configs(user_id)
     curr = bool(configs.get('link_remover', False))
     configs['link_remover'] = not curr
     await db.update_configs(user_id, configs)
     await query.answer(f"Link Remover: {'ON' if not curr else 'OFF'}")
     await query.message.edit_text(course_seller_text(configs), reply_markup=course_seller_buttons(configs))

  elif type == "cs_toggle_hidden":
     configs = await get_configs(user_id)
     curr = bool(configs.get('hidden_link_remover', False))
     configs['hidden_link_remover'] = not curr
     await db.update_configs(user_id, configs)
     await query.answer(f"Hidden Link Sanitizer: {'ON' if not curr else 'OFF'}")
     await query.message.edit_text(course_seller_text(configs), reply_markup=course_seller_buttons(configs))

  elif type == "cs_cycle_style":
     configs = await get_configs(user_id)
     styles = ['bracket', 'lecture', 'part', 'lec', 'dot']
     cur = configs.get('course_number_style', 'bracket')
     nxt = styles[(styles.index(cur) + 1) % len(styles)] if cur in styles else 'bracket'
     configs['course_number_style'] = nxt
     await db.update_configs(user_id, configs)
     await query.answer(f"Style: {nxt}")
     await query.message.edit_text(course_seller_text(configs), reply_markup=course_seller_buttons(configs))

  elif type == "cs_toggle_missing":
     configs = await get_configs(user_id)
     curr = bool(configs.get('course_detect_missing', True))
     configs['course_detect_missing'] = not curr
     await db.update_configs(user_id, configs)
     await query.answer(f"Gap Check: {'ON' if not curr else 'OFF'}")
     await query.message.edit_text(course_seller_text(configs), reply_markup=course_seller_buttons(configs))

  elif type == "cs_toggle_export":
     configs = await get_configs(user_id)
     curr = bool(configs.get('course_export_txt', True))
     configs['course_export_txt'] = not curr
     await db.update_configs(user_id, configs)
     await query.answer(f"Auto TXT Export: {'ON' if not curr else 'OFF'}")
     await query.message.edit_text(course_seller_text(configs), reply_markup=course_seller_buttons(configs))

  elif type == "cs_toggle_tele":
     configs = await get_configs(user_id)
     curr = bool(configs.get('course_telegraph_export', True))
     configs['course_telegraph_export'] = not curr
     await db.update_configs(user_id, configs)
     await query.answer(f"Telegraph Syllabus: {'ON' if not curr else 'OFF'}")
     await query.message.edit_text(course_seller_text(configs), reply_markup=course_seller_buttons(configs))

  elif type == "cs_toggle_flood":
     configs = await get_configs(user_id)
     curr = bool(configs.get('adaptive_flood_enabled', True))
     configs['adaptive_flood_enabled'] = not curr
     await db.update_configs(user_id, configs)
     await query.answer(f"Adaptive Anti-Flood: {'ON' if not curr else 'OFF'}")
     await query.message.edit_text(course_seller_text(configs), reply_markup=course_seller_buttons(configs))

  elif type == "cs_view_branding":
     configs = await get_configs(user_id)
     hdr = configs.get('course_brand_header') or "<i>Not configured</i>"
     ftr = configs.get('course_brand_footer') or "<i>Not configured</i>"
     btn_raw = configs.get('course_sticky_button') or "<i>Not configured</i>"
     await query.message.reply_text(
        f"🏷️ <b><u>ᴄᴜʀʀᴇɴᴛ ʙʀᴀɴᴅɪɴɢ sᴜɪᴛᴇ</u></b>\n\n"
        f"📌 <b>ʜᴇᴀᴅᴇʀ ʙᴀɴɴᴇʀ:</b>\n<blockquote>{hdr}</blockquote>\n\n"
        f"📌 <b>ғᴏᴏᴛᴇʀ ʙᴀɴɴᴇʀ:</b>\n<blockquote>{ftr}</blockquote>\n\n"
        f"🔘 <b>sᴛɪᴄᴋʏ ʙᴜᴛᴛᴏɴ:</b>\n<blockquote><code>{btn_raw}</code></blockquote>\n\n"
        f"✏️ <i>ᴜsᴇ <code>/setbanner</code>, <code>/setfooter</code>, <code>/setcoursebutton</code> ᴛᴏ ᴍᴏᴅɪғʏ.</i>",
        quote=True
     )
     await query.answer()

  elif type == "cs_set_offset":
     try:
        ask = await query.message.chat.ask(
           "🔢 <b><u>sᴇᴛ sᴛᴀʀᴛɪɴɢ ʟᴇᴄᴛᴜʀᴇ ɴᴜᴍʙᴇʀ</u></b>\n\n"
           "Send the starting number (e.g. <code>1</code> or <code>15</code> or <code>101</code>).\n"
           "Send /cancel to abort.",
           filters=filters.text,
           timeout=60
        )
        if ask.text and not ask.text.startswith('/'):
           try:
              val = max(1, int(ask.text.strip()))
              configs = await get_configs(user_id)
              configs['course_start_offset'] = val
              await db.update_configs(user_id, configs)
              await ask.reply_text(f"✅ Starting lecture index set to: <b>{val}</b>", quote=True)
           except ValueError:
              await ask.reply_text("❌ Invalid integer! Please send a valid number.", quote=True)
     except Exception:
        pass
     configs = await get_configs(user_id)
     await query.message.reply_text(course_seller_text(configs), reply_markup=course_seller_buttons(configs))

  elif type == "cs_set_btn":
     try:
        ask = await query.message.chat.ask(
           "🔘 <b><u>sᴇᴛ sᴛɪᴄᴋʏ ᴄᴏᴜʀsᴇ ʙᴜᴛᴛᴏɴ</u></b>\n\n"
           "Send your button text and URL separated by <code>|</code>:\n"
           "Example: <code>💬 Ask Doubts | https://t.me/MySupportBot</code>\n\n"
           "Send /cancel to abort.",
           filters=filters.text,
           timeout=60
        )
        if ask.text and not ask.text.startswith('/'):
           raw = ask.text.strip()
           if '|' in raw or ' - ' in raw:
              configs = await get_configs(user_id)
              configs['course_sticky_button'] = raw
              await db.update_configs(user_id, configs)
              await ask.reply_text("✅ Sticky Course Button saved!", quote=True)
           else:
              await ask.reply_text("❌ Invalid format! Please use: <code>Text | URL</code>", quote=True)
     except Exception:
        pass
     configs = await get_configs(user_id)
     await query.message.reply_text(course_seller_text(configs), reply_markup=course_seller_buttons(configs))

  elif type == "cs_clear_btn":
     configs = await get_configs(user_id)
     configs['course_sticky_button'] = None
     await db.update_configs(user_id, configs)
     await query.answer("Sticky Course Button cleared.")
     await query.message.edit_text(course_seller_text(configs), reply_markup=course_seller_buttons(configs))

  elif type == "ftm":
     configs = await get_configs(user_id)
     await query.message.edit_text(
        ftm_text(configs),
        reply_markup=ftm_buttons(configs)
     )

  elif type == "ftm_toggle_user":
     configs = await get_configs(user_id)
     curr = bool(configs.get('username_remover', False))
     configs['username_remover'] = not curr
     await db.update_configs(user_id, configs)
     await query.answer(f"Username Remover: {'ON' if not curr else 'OFF'}")
     await query.message.edit_text(ftm_text(configs), reply_markup=ftm_buttons(configs))

  elif type == "ftm_toggle_link":
     configs = await get_configs(user_id)
     curr = bool(configs.get('link_remover', False))
     configs['link_remover'] = not curr
     await db.update_configs(user_id, configs)
     await query.answer(f"Link Remover: {'ON' if not curr else 'OFF'}")
     await query.message.edit_text(ftm_text(configs), reply_markup=ftm_buttons(configs))

  elif type == "ftm_toggle_hidden":
     configs = await get_configs(user_id)
     curr = bool(configs.get('hidden_link_remover', False))
     configs['hidden_link_remover'] = not curr
     await db.update_configs(user_id, configs)
     await query.answer(f"Hidden Link Sanitizer: {'ON' if not curr else 'OFF'}")
     await query.message.edit_text(ftm_text(configs), reply_markup=ftm_buttons(configs))

  elif type == "ftm_toggle_tag":
     configs = await get_configs(user_id)
     curr = bool(configs.get('forward_tag', False))
     configs['forward_tag'] = not curr
     await db.update_configs(user_id, configs)
     await query.answer(f"Forward Tag: {'Preserved' if not curr else 'Removed (Clean)'}")
     await query.message.edit_text(ftm_text(configs), reply_markup=ftm_buttons(configs))

  elif type == "ftm_cycle_upload":
     configs = await get_configs(user_id)
     modes = ['media', 'video', 'document']
     curr_mode = configs.get('upload_type', 'media')
     next_mode = modes[(modes.index(curr_mode) + 1) % len(modes)] if curr_mode in modes else 'media'
     configs['upload_type'] = next_mode
     await db.update_configs(user_id, configs)
     await query.answer(f"Upload Type: {next_mode.upper()}")
     await query.message.edit_text(ftm_text(configs), reply_markup=ftm_buttons(configs))

  elif type == "ftm_cycle_transfer":
     configs = await get_configs(user_id)
     curr = str(configs.get('transfer_mode', 'auto')).lower()
     if curr not in TRANSFER_MODE_ORDER:
        curr = 'auto'
     nxt = TRANSFER_MODE_ORDER[(TRANSFER_MODE_ORDER.index(curr) + 1) % len(TRANSFER_MODE_ORDER)]
     configs['transfer_mode'] = nxt
     await db.update_configs(user_id, configs)
     await query.answer(f"Transfer Mode: {TRANSFER_MODES[nxt]}")
     await query.message.edit_text(ftm_text(configs), reply_markup=ftm_buttons(configs))

  elif type == "ftm_set_user_rep":
     await query.message.delete()
     try:
        ask = await bot.ask(user_id, text="<b>👤 Send your replacement username (e.g. <code>@MyBrandCourses</code>):</b>\n\nSend <code>none</code> to clear\n/cancel - Cancel", timeout=120)
     except (asyncio.exceptions.TimeoutError, ListenerTimeout):
        configs = await get_configs(user_id)
        return await bot.send_message(user_id, ftm_text(configs), reply_markup=ftm_buttons(configs))
     if ask.text and not ask.text.startswith('/'):
        val = None if ask.text.strip().lower() == 'none' else ask.text.strip()
        configs = await get_configs(user_id)
        configs['username_replacer'] = val
        await db.update_configs(user_id, configs)
        await bot.send_message(user_id, f"✅ Username replacer set to: <code>{val}</code>", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('• ʙᴀᴄᴋ', callback_data='settings#ftm')]]))

  elif type == "ftm_set_link_rep":
     await query.message.delete()
     try:
        ask = await bot.ask(user_id, text="<b>🔗 Send your replacement link (e.g. <code>https://t.me/MyChannel</code>):</b>\n\nSend <code>none</code> to clear\n/cancel - Cancel", timeout=120)
     except (asyncio.exceptions.TimeoutError, ListenerTimeout):
        configs = await get_configs(user_id)
        return await bot.send_message(user_id, ftm_text(configs), reply_markup=ftm_buttons(configs))
     if ask.text and not ask.text.startswith('/'):
        val = None if ask.text.strip().lower() == 'none' else ask.text.strip()
        configs = await get_configs(user_id)
        configs['link_replacer'] = val
        await db.update_configs(user_id, configs)
        await bot.send_message(user_id, f"✅ Link replacer set to: <code>{val}</code>", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('• ʙᴀᴄᴋ', callback_data='settings#ftm')]]))

  elif type == "ftm_add_word":
     await query.message.delete()
     try:
        ask = await bot.ask(user_id, text="<b>🔤 Send word replacement rule as <code>old_word:new_word</code>:</b>\n(Example: <code>@competitor:@mychannel</code> or <code>badword:</code> to delete word)\n/cancel - Cancel", timeout=120)
     except (asyncio.exceptions.TimeoutError, ListenerTimeout):
        configs = await get_configs(user_id)
        return await bot.send_message(user_id, ftm_text(configs), reply_markup=ftm_buttons(configs))
     if ask.text and ":" in ask.text and not ask.text.startswith('/'):
        parts = ask.text.split(":", 1)
        old, new = parts[0].strip(), parts[1].strip()
        configs = await get_configs(user_id)
        words = configs.get('replace_words', {})
        words[old] = new
        configs['replace_words'] = words
        await db.update_configs(user_id, configs)
        await bot.send_message(user_id, f"✅ Rule added: <code>'{old}' ➔ '{new}'</code>", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('• ʙᴀᴄᴋ', callback_data='settings#ftm')]]))

  elif type == "ftm_clear_words":
     configs = await get_configs(user_id)
     configs['replace_words'] = {}
     await db.update_configs(user_id, configs)
     await query.answer("All word replacement rules cleared!")
     await query.message.edit_text(ftm_text(configs), reply_markup=ftm_buttons(configs))

  elif type.startswith("alert"):
    alert = type.split('_')[1]
    await query.answer(alert, show_alert=True)

def course_seller_text(cfg):
    mode_status = "🟢 ᴀᴄᴛɪᴠᴇ" if cfg.get('course_seller_mode') else "🔴 ᴅɪsᴀʙʟᴇᴅ"
    list_status = "✅ ᴏɴ" if cfg.get('auto_course_list') else "❌ ᴏғғ"
    num_status = "✅ ᴏɴ" if cfg.get('auto_numbering') else "❌ ᴏғғ"
    style_names = {
        'bracket': '[01]',
        'lecture': 'Lecture 01 -',
        'part': 'Part 01:',
        'lec': 'Lec 01 |',
        'dot': '01.'
    }
    cur_style = style_names.get(cfg.get('course_number_style', 'bracket'), '[01]')
    offset_val = int(cfg.get('course_start_offset', 1) or 1)
    gap_status = "✅ ᴏɴ" if cfg.get('course_detect_missing', True) else "❌ ᴏғғ"
    export_status = "✅ ᴏɴ" if cfg.get('course_export_txt', True) else "❌ ᴏғғ"
    sticky_btn = cfg.get('course_sticky_button') or "None"
    user_rem = "✅ ᴏɴ" if cfg.get('username_remover') else "❌ ᴏғғ"
    link_rem = "✅ ᴏɴ" if cfg.get('link_remover') else "❌ ᴏғғ"
    hid_rem = "✅ ᴏɴ" if cfg.get('hidden_link_remover') else "❌ ᴏғғ"
    
    return (
        "<blockquote><b>🎓 <u>ᴄᴏᴜʀsᴇ sᴇʟʟᴇʀ & ᴅɪsᴛʀɪʙᴜᴛᴏʀ sᴜɪᴛᴇ ⚡️</u></b></blockquote>\n\n"
        "<b>Power tools engineered specifically for Course Sellers & Content Distributors:</b>\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"⚡️ <b>Master Seller Mode:</b> <code>{mode_status}</code>\n"
        f"📚 <b>Auto Course List Maker:</b> <code>{list_status}</code>\n"
        f"🔢 <b>Auto Lecture Numbering:</b> <code>{num_status}</code>\n"
        f"🎨 <b>Numbering Style:</b> <code>{cur_style}</code>\n"
        f"🎯 <b>Start Index Offset:</b> <code>{offset_val}</code>\n"
        f"🔍 <b>Missing Lecture Gap Check:</b> <code>{gap_status}</code>\n"
        f"📄 <b>Auto Syllabus TXT Export:</b> <code>{export_status}</code>\n"
        f"🌐 <b>Telegraph Web Syllabus:</b> <code>{'Enabled' if cfg.get('course_telegraph_export', True) else 'Disabled'}</code>\n"
        f"🛡️ <b>Adaptive Anti-Flood:</b> <code>{'Enabled' if cfg.get('adaptive_flood_enabled', True) else 'Disabled'}</code>\n"
        f"🔘 <b>Sticky Course Button:</b> <code>{sticky_btn}</code>\n"
        f"👤 <b>Competitor Username Remover:</b> <code>{user_rem}</code>\n"
        f"🔗 <b>Link Remover & Replacer:</b> <code>{link_rem}</code>\n"
        f"🔍 <b>Hidden Link Sanitizer:</b> <code>{hid_rem}</code>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "💡 <i>Commands: /setbanner | /setfooter | /viewbranding | /setlecstart</i>"
    )

def course_seller_buttons(cfg):
    mode_btn = "🛑 ᴅɪsᴀʙʟᴇ sᴇʟʟᴇʀ ᴍᴏᴅᴇ" if cfg.get('course_seller_mode') else "⚡ ᴇɴᴀʙʟᴇ sᴇʟʟᴇʀ ᴍᴏᴅᴇ"
    list_mark = "✅" if cfg.get('auto_course_list') else "❌"
    num_mark = "✅" if cfg.get('auto_numbering') else "❌"
    style_names = {
        'bracket': '[01]',
        'lecture': 'Lecture 01',
        'part': 'Part 01',
        'lec': 'Lec 01',
        'dot': '01.'
    }
    cur_style = style_names.get(cfg.get('course_number_style', 'bracket'), '[01]')
    offset_val = int(cfg.get('course_start_offset', 1) or 1)
    gap_mark = "✅" if cfg.get('course_detect_missing', True) else "❌"
    exp_mark = "✅" if cfg.get('course_export_txt', True) else "❌"
    tele_mark = "✅" if cfg.get('course_telegraph_export', True) else "❌"
    flood_mark = "✅" if cfg.get('adaptive_flood_enabled', True) else "❌"
    hdr_has = "✅" if cfg.get('course_brand_header') else "❌"
    ftr_has = "✅" if cfg.get('course_brand_footer') else "❌"
    has_btn = "✏️ ᴇᴅɪᴛ" if cfg.get('course_sticky_button') else "➕ sᴇᴛ"
    user_mark = "✅" if cfg.get('username_remover') else "❌"
    link_mark = "✅" if cfg.get('link_remover') else "❌"
    hid_mark = "✅" if cfg.get('hidden_link_remover') else "❌"
    
    buttons = [
        [InlineKeyboardButton(mode_btn, callback_data="settings#cs_toggle_mode")],
        [
            InlineKeyboardButton(f"📚 ᴄᴏᴜʀsᴇ ʟɪsᴛ {list_mark}", callback_data="settings#cs_toggle_list"),
            InlineKeyboardButton(f"🔢 ɴᴜᴍʙᴇʀɪɴɢ {num_mark}", callback_data="settings#cs_toggle_num")
        ],
        [
            InlineKeyboardButton(f"🎨 sᴛʏʟᴇ: {cur_style}", callback_data="settings#cs_cycle_style"),
            InlineKeyboardButton(f"🎯 sᴛᴀʀᴛ: {offset_val}", callback_data="settings#cs_set_offset")
        ],
        [
            InlineKeyboardButton(f"🔍 ɢᴀᴘ ᴄʜᴇᴄᴋ {gap_mark}", callback_data="settings#cs_toggle_missing"),
            InlineKeyboardButton(f"📄 ᴛxᴛ ᴇxᴘᴏʀᴛ {exp_mark}", callback_data="settings#cs_toggle_export")
        ],
        [
            InlineKeyboardButton(f"🌐 ᴛᴇʟᴇɢʀᴀᴘʜ {tele_mark}", callback_data="settings#cs_toggle_tele"),
            InlineKeyboardButton(f"🛡️ ᴀɴᴛɪ-ғʟᴏᴏᴅ {flood_mark}", callback_data="settings#cs_toggle_flood")
        ],
        [
            InlineKeyboardButton(f"🏷️ ʙʀᴀɴᴅɪɴɢ (ʜ:{hdr_has} ғ:{ftr_has})", callback_data="settings#cs_view_branding"),
            InlineKeyboardButton(f"🔘 sᴛɪᴄᴋʏ ʙᴜᴛᴛᴏɴ ({has_btn})", callback_data="settings#cs_set_btn")
        ],
        [
            InlineKeyboardButton("🗑 ᴄʟᴇᴀʀ ʙᴛɴ", callback_data="settings#cs_clear_btn"),
            InlineKeyboardButton(f"👤 ᴜsᴇʀ {user_mark}", callback_data="settings#cs_toggle_user"),
            InlineKeyboardButton(f"🔗 ʟɪɴᴋ {link_mark}", callback_data="settings#cs_toggle_link")
        ],
        [
            InlineKeyboardButton("🛠 sᴋɪɴᴇᴛ ᴍᴏᴅɪғɪᴇʀ", callback_data="settings#ftm"),
            InlineKeyboardButton("• ʙᴀᴄᴋ", callback_data="settings#main"),
            InlineKeyboardButton("❌ ᴄʟᴏsᴇ", callback_data="close_btn")
        ]
    ]
    return InlineKeyboardMarkup(buttons)

def ftm_text(cfg):
    user_rem = "✅ ᴏɴ" if cfg.get('username_remover') else "❌ ᴏғғ"
    user_rep = cfg.get('username_replacer') or "None (Clean only)"
    link_rem = "✅ ᴏɴ" if cfg.get('link_remover') else "❌ ᴏғғ"
    link_rep = cfg.get('link_replacer') or "None (Clean only)"
    hid_rem = "✅ ᴏɴ" if cfg.get('hidden_link_remover') else "❌ ᴏғғ"
    replacements = cfg.get('replace_words', {})
    up_type = str(cfg.get('upload_type', 'media')).upper()
    tr_mode = TRANSFER_MODES.get(str(cfg.get('transfer_mode', 'auto')).lower(), TRANSFER_MODES['auto'])
    tag_status = "❌ ʀᴇᴍᴏᴠᴇᴅ (ᴄʟᴇᴀɴ)" if not cfg.get('forward_tag') else "✅ ᴘʀᴇsᴇʀᴠᴇᴅ"

    return (
        "<blockquote><b>🛠 <u>sᴋɪɴᴇᴛ ᴛᴇxᴛ & ᴍᴇᴅɪᴀ ᴍᴏᴅɪғɪᴇʀ ⚡️</u></b></blockquote>\n\n"
        "<b>Skinet Verse Content Sanitization & Re-Branding Suite:</b>\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 <b>Username Remover:</b> <code>{user_rem}</code>\n"
        f"👤 <b>Username Replacer:</b> <code>{user_rep}</code>\n"
        f"🔗 <b>Link Remover:</b> <code>{link_rem}</code>\n"
        f"🔗 <b>Link Replacer:</b> <code>{link_rep}</code>\n"
        f"🔍 <b>Hidden Link Sanitizer:</b> <code>{hid_rem}</code>\n"
        f"🔤 <b>Active Word Replacements:</b> <code>{len(replacements)} rules</code>\n"
        f"📦 <b>Upload Stream Mode:</b> <code>{up_type}</code>\n"
        f"🚚 <b>Transfer Mode:</b> <code>{tr_mode}</code>\n"
        f"🏷 <b>Forward Tag:</b> <code>{tag_status}</code>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "💡 <i>Transfer mode picks how content moves to the target:</i>\n"
        "• <b>FORWARD</b> — native forward, fastest, keeps the source header\n"
        "• <b>COPY</b> — server-side copy, no download, header removed\n"
        "• <b>UPLOAD</b> — always download &amp; re-upload (works on protected sources)\n"
        "• <b>AUTO</b> — server-side first, re-upload only if Telegram refuses\n\n"
        "⚠️ <i>Protected / forward-restricted sources refuse both forward and copy, "
        "so AUTO silently switches to download &amp; re-upload for those.</i>"
    )

def ftm_buttons(cfg):
    user_mark = "✅ ᴏɴ" if cfg.get('username_remover') else "❌ ᴏғғ"
    link_mark = "✅ ᴏɴ" if cfg.get('link_remover') else "❌ ᴏғғ"
    hid_mark = "✅ ᴏɴ" if cfg.get('hidden_link_remover') else "❌ ᴏғғ"
    tag_mark = "✅ ᴄʟᴇᴀɴ" if not cfg.get('forward_tag') else "⚠️ ᴛᴀɢɢᴇᴅ"
    up_type = str(cfg.get('upload_type', 'media')).capitalize()
    
    buttons = [
        [
            InlineKeyboardButton(f"👤 ᴜsᴇʀɴᴀᴍᴇ: {user_mark}", callback_data="settings#ftm_toggle_user"),
            InlineKeyboardButton("✏️ sᴇᴛ ᴜsᴇʀɴᴀᴍᴇ ʀᴇᴘʟᴀᴄᴇʀ", callback_data="settings#ftm_set_user_rep")
        ],
        [
            InlineKeyboardButton(f"🔗 ʟɪɴᴋs: {link_mark}", callback_data="settings#ftm_toggle_link"),
            InlineKeyboardButton("✏️ sᴇᴛ ʟɪɴᴋ ʀᴇᴘʟᴀᴄᴇʀ", callback_data="settings#ftm_set_link_rep")
        ],
        [
            InlineKeyboardButton(f"🔍 ʜɪᴅᴅᴇɴ ʟɪɴᴋs: {hid_mark}", callback_data="settings#ftm_toggle_hidden"),
            InlineKeyboardButton(f"🏷 ᴛᴀɢ: {tag_mark}", callback_data="settings#ftm_toggle_tag")
        ],
        [
            InlineKeyboardButton("🔤 ᴀᴅᴅ ᴡᴏʀᴅ ʀᴇᴘʟᴀᴄᴇᴍᴇɴᴛ", callback_data="settings#ftm_add_word"),
            InlineKeyboardButton("🗑 ʀᴇsᴇᴛ ᴡᴏʀᴅs", callback_data="settings#ftm_clear_words")
        ],
        [
            InlineKeyboardButton(f"📦 ᴜᴘʟᴏᴀᴅ ᴛʏᴘᴇ: {up_type}", callback_data="settings#ftm_cycle_upload")
        ],
        [
            InlineKeyboardButton(f"🚚 ᴛʀᴀɴsғᴇʀ: {TRANSFER_MODES.get(str(cfg.get('transfer_mode', 'auto')).lower(), TRANSFER_MODES['auto'])}",
                                 callback_data="settings#ftm_cycle_transfer")
        ],
        [
            InlineKeyboardButton("• ʙᴀᴄᴋ", callback_data="settings#main"),
            InlineKeyboardButton("❌ ᴄʟᴏsᴇ", callback_data="close_btn")
        ]
    ]
    return InlineKeyboardMarkup(buttons)

def main_buttons(user_id=None, is_admin=False):
  is_admin = is_admin or bool(user_id and user_id in Config.BOT_OWNER_ID)
  buttons = [[
       InlineKeyboardButton('➕ ᴀᴅᴅ ʙᴏᴛ',
                    callback_data=f'settings#bots'),
       InlineKeyboardButton('🏷 ᴄʜᴀɴɴᴇʟs',
                    callback_data=f'settings#channels')
       ],[
       InlineKeyboardButton('🖋️ ᴄᴀᴘᴛɪᴏɴ',
                    callback_data=f'settings#caption'),
       InlineKeyboardButton('🗃 ᴍᴏɴɢᴏ ᴅʙ',
                    callback_data=f'settings#database')
       ],[
       InlineKeyboardButton('🕵‍♀ ғɪʟᴛᴇʀs 🕵‍♀',
                    callback_data=f'settings#filters'),
       InlineKeyboardButton('⏹ ʙᴜᴛᴛᴏɴ',
                    callback_data=f'settings#button')
       ],[
       InlineKeyboardButton('⚡ sᴘᴇᴇᴅ ᴄᴏɴᴛʀᴏʟ ⚡',
                    callback_data='settings#speed'),
       InlineKeyboardButton('🚀 sᴍᴀʀᴛ ᴀᴜᴛᴏsᴀᴠᴇ 🚀',
                    callback_data='autosave#main')
       ],[
       InlineKeyboardButton('🎓 ᴄᴏᴜʀsᴇ sᴇʟʟᴇʀ ⚡️',
                    callback_data='settings#courseseller'),
       InlineKeyboardButton('🛠 sᴋɪɴᴇᴛ ᴍᴏᴅɪғɪᴇʀ 🛠',
                    callback_data='settings#ftm')
       ]]
  if is_admin:
      buttons.append([
          InlineKeyboardButton('📦 ᴅᴜᴍᴘ ᴄʜᴀɴɴᴇʟ (ᴀᴅᴍɪɴ)', callback_data='settings#dump'),
          InlineKeyboardButton('⚙️ ʙᴏᴛ ᴄᴏɴғɪɢ (ᴀᴅᴍɪɴ)', callback_data='config#main')
      ])
      buttons.append([
          InlineKeyboardButton('ᴇxᴛʀᴀ sᴇᴛᴛɪɴɢs 🧪', callback_data='settings#nextfilters')
      ])
  else:
      buttons.append([
          InlineKeyboardButton('ᴇxᴛʀᴀ sᴇᴛᴛɪɴɢs 🧪', callback_data='settings#nextfilters')
      ])
  buttons.append([
      InlineKeyboardButton('• ʙᴀᴄᴋ', callback_data='help'),
      InlineKeyboardButton('❌ ᴄʟᴏsᴇ', callback_data='close_btn')
  ])
  return InlineKeyboardMarkup(buttons)

def speed_buttons(cfg):
  mode = cfg.get('mode', 'fast')
  delay = float(cfg.get('delay', 1.0))
  jitter = cfg.get('jitter', True)

  extreme_mark = " ✅" if mode == "extreme" else ""
  fast_mark = " ✅" if mode == "fast" else ""
  normal_mark = " ✅" if mode == "normal" else ""
  safe_mark = " ✅" if mode == "safe" else ""
  jitter_mark = "✅ ᴏɴ" if jitter else "❌ ᴏғғ"

  buttons = [
    [
      InlineKeyboardButton(f"🚀 ᴇxᴛʀᴇᴍᴇ (0.5s){extreme_mark}", callback_data="settings#speed_mode_extreme"),
      InlineKeyboardButton(f"⚡ ғᴀsᴛ (1.0s){fast_mark}", callback_data="settings#speed_mode_fast"),
    ],
    [
      InlineKeyboardButton(f"🏃 ɴᴏʀᴍᴀʟ (3.0s){normal_mark}", callback_data="settings#speed_mode_normal"),
      InlineKeyboardButton(f"🐢 sᴀғᴇ (5.0s){safe_mark}", callback_data="settings#speed_mode_safe"),
    ],
    [
      InlineKeyboardButton("➖ 0.5s", callback_data="settings#speed_adj_-0.5"),
      InlineKeyboardButton(f"⏱️ ᴅᴇʟᴀʏ: {delay:.1f}s", callback_data=f"settings#alert_Current delay is {delay:.1f}s"),
      InlineKeyboardButton("➕ 0.5s", callback_data="settings#speed_adj_0.5"),
    ],
    [
      InlineKeyboardButton("➖ 1.0s", callback_data="settings#speed_adj_-1.0"),
      InlineKeyboardButton("➕ 1.0s", callback_data="settings#speed_adj_1.0"),
    ],
    [
      InlineKeyboardButton(f"🎲 ᴀɴᴛɪ-ʙᴀɴ ᴊɪᴛᴛᴇʀ: {jitter_mark}", callback_data="settings#speed_toggle_jitter"),
    ],
    [
      InlineKeyboardButton("• ʙᴀᴄᴋ", callback_data="settings#main"),
      InlineKeyboardButton("❌ ᴄʟᴏsᴇ", callback_data="close_btn")
    ]
  ]
  return InlineKeyboardMarkup(buttons)

def speed_text(cfg):
  mode = cfg.get('mode', 'fast')
  delay = float(cfg.get('delay', 1.0))
  jitter = cfg.get('jitter', True)
  batch_size = cfg.get('batch_size', 100)

  mode_names = {
    'extreme': '🚀 ᴇxᴛʀᴇᴍᴇ (0.5s)',
    'fast': '⚡ ғᴀsᴛ (1.0s)',
    'normal': '🏃 ɴᴏʀᴍᴀʟ (3.0s)',
    'safe': '🐢 sᴀғᴇ (5.0s - Anti-Ban)',
    'custom': '⚙️ ᴄᴜsᴛᴏᴍ'
  }
  mode_str = mode_names.get(mode, mode.title())
  jitter_str = "✅ ᴇɴᴀʙʟᴇᴅ (±30% random jitter)" if jitter else "❌ ᴅɪsᴀʙʟᴇᴅ"

  return (
    "<blockquote><b>⚡ <u>sᴘᴇᴇᴅ ᴄᴏɴᴛʀᴏʟ & ᴀɴᴛɪ-ʙᴀɴ sᴇᴛᴛɪɴɢs</u> ⚡</b></blockquote>\n\n"
    "Configure message forwarding speed, delay intervals, and anti-ban protections.\n\n"
    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    f"• <b>ᴄᴜʀʀᴇɴᴛ ᴍᴏᴅᴇ:</b> <code>{mode_str}</code>\n"
    f"• <b>ʙᴀsᴇ ᴅᴇʟᴀʏ:</b> <code>{delay:.1f} sec</code>\n"
    f"• <b>ʜᴜᴍᴀɴ ᴊɪᴛᴛᴇʀ:</b> <code>{jitter_str}</code>\n"
    f"• <b>ʙᴀᴛᴄʜ sɪᴢᴇ:</b> <code>{batch_size} msgs</code>\n"
    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    "💡 <b>Modes Reference:</b>\n"
    "• <b>⚡ Fast:</b> 1.0s delay (recommended for normal forwarding)\n"
    "• <b>🏃 Normal:</b> 3.0s delay (balanced speed & safety)\n"
    "• <b>🐢 Safe:</b> 5.0s delay (best for userbots to avoid bans)\n"
    "• <b>🚀 Extreme:</b> 0.5s delay (fastest transfer, recommended for bot tokens)\n"
    "• <b>🎲 Anti-Ban Jitter:</b> Randomizes delays like a human to evade Telegram automated pattern bans"
  )

def size_limit(limit):
   if str(limit) == "None":
      return None, ""
   elif str(limit) == "True":
      return True, "more than"
   else:
      return False, "less than"
def extract_btn(datas):
    i = 0
    btn = []
    if datas:
       prefix = b'settings#alert_'
       max_payload_bytes = 64 - len(prefix)  # 49 bytes
       for data in datas:
         if i >= 5:
            i = 0
         cb_data = (prefix + str(data).encode('utf-8')[:max_payload_bytes]).decode('utf-8', errors='ignore')
         if i == 0:
            btn.append([InlineKeyboardButton(data, callback_data=cb_data)])
            i += 1
            continue
         elif i > 0:
            btn[-1].append(InlineKeyboardButton(data, callback_data=cb_data))
            i += 1
    return btn 

def size_button(size):
  buttons = [[
       InlineKeyboardButton('+',
                    callback_data=f'settings#update_limit-True-{size}'),
       InlineKeyboardButton('=',
                    callback_data=f'settings#update_limit-None-{size}'),
       InlineKeyboardButton('-',
                    callback_data=f'settings#update_limit-False-{size}')
       ],[
       InlineKeyboardButton('+1',
                    callback_data=f'settings#update_size-{size + 1}'),
       InlineKeyboardButton('-1',
                    callback_data=f'settings#update_size-{max(0, size - 1)}')
       ],[
       InlineKeyboardButton('+5',
                    callback_data=f'settings#update_size-{size + 5}'),
       InlineKeyboardButton('-5',
                    callback_data=f'settings#update_size-{max(0, size - 5)}')
       ],[
       InlineKeyboardButton('+10',
                    callback_data=f'settings#update_size-{size + 10}'),
       InlineKeyboardButton('-10',
                    callback_data=f'settings#update_size-{max(0, size - 10)}')
       ],[
       InlineKeyboardButton('+50',
                    callback_data=f'settings#update_size-{size + 50}'),
       InlineKeyboardButton('-50',
                    callback_data=f'settings#update_size-{max(0, size - 50)}')
       ],[
       InlineKeyboardButton('+100',
                    callback_data=f'settings#update_size-{size + 100}'),
       InlineKeyboardButton('-100',
                    callback_data=f'settings#update_size-{max(0, size - 100)}')
       ],[
        InlineKeyboardButton('↩ ʙᴀᴄᴋ',
                     callback_data="settings#main"),
        InlineKeyboardButton('❌ ᴄʟᴏsᴇ',
                     callback_data="close_btn")
      ]]
  return InlineKeyboardMarkup(buttons)
async def filters_buttons(user_id):
  filter = await get_configs(user_id)
  filters = filter['filters']
  buttons = [[
       InlineKeyboardButton('🏷️ ғᴏʀᴡᴀʀᴅ ᴛᴀɢ',
                    callback_data='settings#alert_toggle'),
       InlineKeyboardButton('✅' if filter['forward_tag'] else '❌',
                    callback_data=f'settings#updatefilter-forward_tag-{filter["forward_tag"]}')
       ],[
       InlineKeyboardButton('🖍️ ᴛᴇxᴛ',
                    callback_data='settings#alert_toggle'),
       InlineKeyboardButton('✅' if filters['text'] else '❌',
                    callback_data=f'settings#updatefilter-text-{filters["text"]}')
       ],[
       InlineKeyboardButton('📁 ᴅᴏᴄᴜᴍᴇɴᴛs',
                    callback_data='settings#alert_toggle'),
       InlineKeyboardButton('✅' if filters['document'] else '❌',
                    callback_data=f'settings#updatefilter-document-{filters["document"]}')
       ],[
       InlineKeyboardButton('🎞️ ᴠɪᴅᴇᴏs',
                    callback_data='settings#alert_toggle'),
       InlineKeyboardButton('✅' if filters['video'] else '❌',
                    callback_data=f'settings#updatefilter-video-{filters["video"]}')
       ],[
       InlineKeyboardButton('📷 ᴘʜᴏᴛᴏs',
                    callback_data='settings#alert_toggle'),
       InlineKeyboardButton('✅' if filters['photo'] else '❌',
                    callback_data=f'settings#updatefilter-photo-{filters["photo"]}')
       ],[
       InlineKeyboardButton('🎧 ᴀᴜᴅɪᴏs',
                    callback_data='settings#alert_toggle'),
       InlineKeyboardButton('✅' if filters['audio'] else '❌',
                    callback_data=f'settings#updatefilter-audio-{filters["audio"]}')
       ],[
       InlineKeyboardButton('🎤 ᴠᴏɪᴄᴇs',
                    callback_data='settings#alert_toggle'),
       InlineKeyboardButton('✅' if filters['voice'] else '❌',
                    callback_data=f'settings#updatefilter-voice-{filters["voice"]}')
       ],[
       InlineKeyboardButton('🎭 ᴀɴɪᴍᴀᴛɪᴏɴs',
                    callback_data='settings#alert_toggle'),
       InlineKeyboardButton('✅' if filters['animation'] else '❌',
                    callback_data=f'settings#updatefilter-animation-{filters["animation"]}')
       ],[
       InlineKeyboardButton('🃏 sᴛɪᴄᴋᴇʀs',
                    callback_data='settings#alert_toggle'),
       InlineKeyboardButton('✅' if filters['sticker'] else '❌',
                    callback_data=f'settings#updatefilter-sticker-{filters["sticker"]}')
       ],[
       InlineKeyboardButton('▶️ sᴋɪᴘ ᴅᴜᴘʟɪᴄᴀᴛᴇ',
                    callback_data='settings#alert_toggle'),
       InlineKeyboardButton('✅' if filter['duplicate'] else '❌',
                    callback_data=f'settings#updatefilter-duplicate-{filter["duplicate"]}')
       ],[
       InlineKeyboardButton('• ʙᴀᴄᴋ',
                    callback_data="settings#main"),
       InlineKeyboardButton('❌ ᴄʟᴏsᴇ',
                    callback_data="close_btn")
       ]]
  return InlineKeyboardMarkup(buttons) 
async def next_filters_buttons(user_id):
  filter = await get_configs(user_id)
  filters = filter['filters']
  buttons = [[
       InlineKeyboardButton('📊 ᴘᴏʟʟ',
                    callback_data='settings#alert_toggle'),
       InlineKeyboardButton('✅' if filters['poll'] else '❌',
                    callback_data=f'settings#updatefilter-poll-{filters["poll"]}')
       ],[
       InlineKeyboardButton('🔒 sᴇᴄᴜʀᴇ ᴍᴇssᴀɢᴇs',
                    callback_data='settings#alert_toggle'),
       InlineKeyboardButton('✅' if filter['protect'] else '❌',
                    callback_data=f'settings#updatefilter-protect-{filter["protect"]}')
       ],[
       InlineKeyboardButton('🛑 sɪᴢᴇ ʟɪᴍɪᴛ',
                    callback_data='settings#file_size')
       ],[
       InlineKeyboardButton('💾 ᴇxᴛᴇɴsɪᴏɴ',
                    callback_data='settings#get_extension')
       ],[
       InlineKeyboardButton('♦️ ᴋᴇʏᴡᴏʀᴅ',
                    callback_data='settings#get_keyword')
       ],[
       InlineKeyboardButton('• ʙᴀᴄᴋ', 
                    callback_data="settings#main"),
       InlineKeyboardButton('❌ ᴄʟᴏsᴇ', 
                    callback_data="close_btn")
       ]]
  return InlineKeyboardMarkup(buttons) 
   
