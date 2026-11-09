import os
import re 
import sys
import typing
import asyncio 
import logging 
from database import db 
from config import Config, temp
from pyrogram import Client, filters, types
from pyrogram.raw.all import layer
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery, Message 
from pyrogram.errors.exceptions.bad_request_400 import AccessTokenExpired, AccessTokenInvalid
from pyrogram.errors import (
    FloodWait,
    PhoneNumberInvalid,
    PhoneCodeInvalid,
    PhoneCodeExpired,
    SessionPasswordNeeded,
    PasswordHashInvalid,
    ListenerTimeout,
    PhoneNumberBanned,
    PhoneCodeEmpty,
    PhoneNumberUnoccupied,
    BadRequest
)
from config import Config
from translation import Translation
from typing import Union, Optional, AsyncGenerator

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

BTN_URL_REGEX = re.compile(r"(\[([^\[]+?)]\[buttonurl:/{0,2}(.+?)(:same)?])")
BOT_TOKEN_TEXT = "<b>1) ᴄʀᴇᴀᴛᴇ ᴀ ʙᴏᴛ ᴜsɪɴɢ @BotFather\n2) ᴛʜᴇɴ ʏᴏᴜ ᴡɪʟʟ ɢᴇᴛ ᴀ ᴍᴇssᴀɢᴇ ᴡɪᴛʜ ʙᴏᴛ ᴛᴏᴋᴇɴ\n3) ғᴏʀᴡᴀʀᴅ ᴛʜᴀᴛ ᴍᴇssᴀɢᴇ ᴛᴏ ᴍᴇ</b>"
SESSION_STRING_SIZE = 351

async def start_clone_bot(FwdBot, data=None):
   await FwdBot.start()

   async def iter_messages(
      self, 
      chat_id: Union[int, str], 
      limit: int, 
      offset: int = 0,
      search: str = None,
      filter: "types.TypeMessagesFilter" = None,
      ) -> Optional[AsyncGenerator["types.Message", None]]:
        current = max(1, int(offset or 0))
        limit = int(limit or 0)
        while current <= limit:
            new_diff = min(200, limit - current + 1)
            if new_diff <= 0:
                return
            ids = list(range(current, current + new_diff))
            current += new_diff
            try:
                messages = await self.get_messages(chat_id, ids)
            except FloodWait as fw:
                await asyncio.sleep(fw.value + 1)
                try:
                    messages = await self.get_messages(chat_id, ids)
                except Exception:
                    messages = []
            except Exception:
                messages = []
            if not messages:
                continue
            valid_messages = [m for m in messages if m and not getattr(m, 'empty', False)]
            valid_messages.sort(key=lambda m: getattr(m, 'id', 0))
            for message in valid_messages:
                yield message

   FwdBot.iter_messages = iter_messages
   Client.iter_messages = iter_messages
   return FwdBot

class CLIENT: 
  def __init__(self):
     self.api_id = int(Config.API_ID) if (Config.API_ID and str(Config.API_ID).isdigit()) else Config.API_ID
     self.api_hash = Config.API_HASH
    
  def client(self, data, user=None):
     if user == None and data.get('is_bot') == False:
        return Client(f"USERBOT_{data.get('user_id', 'client')}", self.api_id, self.api_hash, session_string=data.get('session'), in_memory=True)
     elif user == True:
        return Client("USERBOT", self.api_id, self.api_hash, session_string=data, in_memory=True)
     elif user != False:
        data = data.get('token')
     return Client("BOT", self.api_id, self.api_hash, bot_token=data, in_memory=True)

  async def add_bot(self, bot, message):
     user_id = int(message.from_user.id)
     try:
        msg = await bot.ask(chat_id=user_id, text=BOT_TOKEN_TEXT, timeout=300)
     except (TimeoutError, asyncio.TimeoutError, ListenerTimeout):
        await bot.send_message(user_id, "ᴛɪᴍᴇ ʟɪᴍɪᴛ ʀᴇᴀᴄʜᴇᴅ (5 ᴍɪɴᴜᴛᴇs).\nᴘʟᴇᴀsᴇ sᴛᴀʀᴛ ᴀɢᴀɪɴ.")
        return None
     if not msg or not msg.text or msg.text=='/cancel':
        await bot.send_message(user_id, '<b>ᴘʀᴏᴄᴇss ᴄᴀɴᴄᴇʟʟᴇᴅ !</b>')
        return None
     else:
         from plugins.forward_parser import extract_forward_info
         fwd_check = extract_forward_info(msg)
         if not fwd_check.get("is_forward"):
             await bot.send_message(user_id, "<b>ᴛʜɪs ɪs ɴᴏᴛ ᴀ ғᴏʀᴡᴀʀᴅ ᴍᴇssᴀɢᴇ</b>")
             return None
         sender_id = str(fwd_check.get("sender_id") or fwd_check.get("chat_id") or "")
         if sender_id != "93372553":
             await bot.send_message(user_id, "<b>ᴛʜɪs ᴍᴇssᴀɢᴇ ᴡᴀs ɴᴏᴛ ғᴏʀᴡᴀʀᴅ ғʀᴏᴍ ʙᴏᴛ ғᴀᴛʜᴇʀ</b>")
             return None
     bot_token = re.findall(r'\d[0-9]{8,10}:[0-9A-Za-z_-]{35}', msg.text, re.IGNORECASE)
     bot_token = bot_token[0] if bot_token else None
     if not bot_token:
        await bot.send_message(user_id, "<b>ᴛʜᴇʀᴇ ɪs ɴᴏ ʙᴏᴛ ᴛᴏᴋᴇɴ ɪɴ ᴛʜᴀᴛ ᴍᴇssᴀɢᴇ</b>")
        return None
     try:
        _client = await start_clone_bot(self.client(bot_token, False), True)
     except Exception as e:
        await bot.send_message(user_id, f"<b>ʙᴏᴛ ᴇʀʀᴏʀ:</b> `{e}`")
        return None
     _bot = _client.me
     details = {
       'id': _bot.id,
       'is_bot': True,
       'user_id': user_id,
       'name': _bot.first_name,
       'token': bot_token,
       'username': _bot.username 
     }
     await db.add_bot(details)
     return True

  async def add_login(self, bot, message):
    user_id = int(message.from_user.id)
    api_id = self.api_id or Config.API_ID
    api_hash = self.api_hash or Config.API_HASH
    disclaimer_text = "<b><blockquote>**<u>⚠️ ᴡᴀʀɴɪɴɢ ⚠️</u>**:\n\n ɪғ ʏᴏᴜ ᴀʟʀᴇᴀᴅʏ ʜᴀᴠᴇ ᴀ sᴇssɪᴏɴ sᴛʀɪɴɢ, ᴘʟᴇᴀsᴇ ᴜsᴇ ᴛʜᴇ ᴀᴅᴅ ᴜsᴇʀ ʙᴏᴛ. ᴏᴛʜᴇʀᴡɪsᴇ, ʏᴏᴜ ᴄᴀɴ ᴜsᴇ ʟᴏɢɪɴ.</blockquote></b>"
    await bot.send_message(user_id, text=disclaimer_text)

    client = Client(name=f":memory:{user_id}", api_id=api_id, api_hash=api_hash, in_memory=True)
    try:
        await client.connect()
    except Exception as e:
        await bot.send_message(user_id, f"<b>ғᴀɪʟᴇᴅ ᴛᴏ ᴄᴏɴɴᴇᴄᴛ:</b> `{e}`")
        return None

    try:
        # Step 1: Phone number (up to 3 attempts)
        phone_number = None
        code = None
        max_phone_attempts = 3

        for p_attempt in range(1, max_phone_attempts + 1):
            p_attempts_left = max_phone_attempts - p_attempt
            if p_attempt == 1:
                t = (
                    "➫ ᴘʟᴇᴀsᴇ sᴇɴᴅ ʏᴏᴜʀ ᴘʜᴏɴᴇ ɴᴜᴍʙᴇʀ ᴡɪᴛʜ ᴄᴏᴜɴᴛʀʏ ᴄᴏᴅᴇ ғᴏʀ ᴡʜɪᴄʜ ʏᴏᴜ ᴡᴀɴᴛ ᴛᴏ ɢᴇɴᴇʀᴀᴛᴇ sᴇssɪᴏɴ\n"
                    "➫ ᴇxᴀᴍᴘʟᴇ: +910000000000\n"
                    "/cancel - ᴛᴏ ᴄᴀɴᴄᴇʟ ᴛʜɪs ᴘʀᴏᴄᴇss"
                )
            else:
                t = (
                    f"➫ ᴘʟᴇᴀsᴇ ᴇɴᴛᴇʀ ʏᴏᴜʀ ᴘʜᴏɴᴇ ɴᴜᴍʙᴇʀ ᴡɪᴛʜ ᴄᴏᴜɴᴛʀʏ ᴄᴏᴅᴇ.\n"
                    f"⚠️ ʏᴏᴜ ʜᴀᴠᴇ {p_attempts_left + 1} ᴀᴛᴛᴇᴍᴘᴛ(s) ʟᴇғᴛ.\n"
                    f"/cancel - ᴛᴏ ᴄᴀɴᴄᴇʟ"
                )

            try:
                phone_number_msg = await bot.ask(user_id, t, filters=filters.text, timeout=300)
            except (TimeoutError, asyncio.TimeoutError, ListenerTimeout):
                await bot.send_message(user_id, "ᴛɪᴍᴇ ʟɪᴍɪᴛ ʀᴇᴀᴄʜᴇᴅ (5 ᴍɪɴᴜᴛᴇs).\n\nᴘʟᴇᴀsᴇ sᴛᴀʀᴛ ɢᴇɴᴇʀᴀᴛɪɴɢ ʏᴏᴜʀ sᴇssɪᴏɴ ᴀɢᴀɪɴ.")
                return None

            if not phone_number_msg or not phone_number_msg.text or phone_number_msg.text.startswith('/'):
                await bot.send_message(user_id, "<b>ᴘʀᴏᴄᴇss ᴄᴀɴᴄᴇʟʟᴇᴅ!</b>")
                return None

            raw_phone = re.sub(r'[\s\-]', '', phone_number_msg.text)
            if not (raw_phone.startswith('+') or raw_phone.isdigit()):
                if p_attempts_left > 0:
                    await bot.send_message(user_id, f"<b>ɪɴᴠᴀʟɪᴅ ᴘʜᴏɴᴇ ɴᴜᴍʙᴇʀ ғᴏʀᴍᴀᴛ!</b> ᴘʟᴇᴀsᴇ ɪɴᴄʟᴜᴅᴇ ᴄᴏᴜɴᴛʀʏ ᴄᴏᴅᴇ (ᴇ.ɢ. +910000000000).\nᴀᴛᴛᴇᴍᴘᴛs ʟᴇғᴛ: {p_attempts_left}")
                    continue
                else:
                    await bot.send_message(user_id, "<b>ɪɴᴠᴀʟɪᴅ ᴘʜᴏɴᴇ ɴᴜᴍʙᴇʀ ғᴏʀᴍᴀᴛ!</b> ᴍᴀxɪᴍᴜᴍ ᴀᴛᴛᴇᴍᴘᴛs ʀᴇᴀᴄʜᴇᴅ.")
                    return None

            await bot.send_message(user_id, "ᴛʀʏɪɴɢ ᴛᴏ sᴇɴᴅ ᴏᴛᴩ ᴀᴛ ᴛʜᴇ ɢɪᴠᴇɴ ɴᴜᴍʙᴇʀ...")
            try:
                code = await client.send_code(raw_phone)
                phone_number = raw_phone
                break
            except PhoneNumberInvalid:
                if p_attempts_left > 0:
                    await bot.send_message(user_id, f"ᴛʜᴇ ᴘʜᴏɴᴇ ɴᴜᴍʙᴇʀ ʏᴏᴜ'ᴠᴇ sᴇɴᴛ ᴅᴏᴇsɴ'ᴛ ʙᴇʟᴏɴɢ ᴛᴏ ᴀɴʏ ᴛᴇʟᴇɢʀᴀᴍ ᴀᴄᴄᴏᴜɴᴛ.\n⚠️ ʏᴏᴜ ʜᴀᴠᴇ {p_attempts_left} ᴀᴛᴛᴇᴍᴘᴛ(s) ʟᴇғᴛ.")
                    continue
                else:
                    await bot.send_message(user_id, "ᴛʜᴇ ᴘʜᴏɴᴇ ɴᴜᴍʙᴇʀ ʏᴏᴜ'ᴠᴇ sᴇɴᴛ ᴅᴏᴇsɴ'ᴛ ʙᴇʟᴏɴɢ ᴛᴏ ᴀɴʏ ᴛᴇʟᴇɢʀᴀᴍ ᴀᴄᴄᴏᴜɴᴛ.\nᴍᴀxɪᴍᴜᴍ ᴀᴛᴛᴇᴍᴘᴛs ʀᴇᴀᴄʜᴇᴅ.")
                    return None
            except PhoneNumberBanned:
                await bot.send_message(user_id, "ᴛʜɪs ᴘʜᴏɴᴇ ɴᴜᴍʙᴇʀ ɪs ʙᴀɴɴᴇᴅ ᴏɴ ᴛᴇʟᴇɢʀᴀᴍ.")
                return None
            except FloodWait as e:
                await bot.send_message(user_id, f"ғʟᴏᴏᴅᴡᴀɪᴛ: ᴘʟᴇᴀsᴇ ᴡᴀɪᴛ {e.value} sᴇᴄᴏɴᴅs ʙᴇғᴏʀᴇ ᴛʀʏɪɴɢ ᴀɢᴀɪɴ.")
                return None
            except Exception as e:
                await bot.send_message(user_id, f"<b>ᴇʀʀᴏʀ sᴇɴᴅɪɴɢ ᴏᴛᴘ:</b> `{e}`")
                return None

        if not code or not phone_number:
            return None

        # Step 2: OTP verification (up to 3 attempts)
        max_otp_attempts = 3
        signed_in = False
        needs_2fa = False

        for otp_attempt in range(1, max_otp_attempts + 1):
            otp_attempts_left = max_otp_attempts - otp_attempt
            if otp_attempt == 1:
                otp_prompt = (
                    "ᴘʟᴇᴀsᴇ sᴇɴᴅ ᴛʜᴇ ᴏᴛᴘ ᴛʜᴀᴛ ʏᴏᴜ'ᴠᴇ ʀᴇᴄᴇɪᴠᴇᴅ ғʀᴏᴍ ᴛᴇʟᴇɢʀᴀᴍ ᴏɴ ʏᴏᴜʀ ᴀᴄᴄᴏᴜɴᴛ.\n"
                    "➫ ɪғ ᴏᴛᴘ ɪs 12345, ʏᴏᴜ ᴄᴀɴ sᴇɴᴅ ɪᴛ ᴀs 1 2 3 4 5 ᴏʀ 12345.\n"
                    "/cancel - ᴛᴏ ᴄᴀɴᴄᴇʟ."
                )
            else:
                otp_prompt = (
                    f"ᴘʟᴇᴀsᴇ ᴇɴᴛᴇʀ ᴛʜᴇ ᴄᴏʀʀᴇᴄᴛ ᴏᴛᴘ ʀᴇᴄᴇɪᴠᴇᴅ ᴏɴ ʏᴏᴜʀ ᴛᴇʟᴇɢʀᴀᴍ ᴀᴄᴄᴏᴜɴᴛ.\n"
                    f"⚠️ ᴀᴛᴛᴇᴍᴘᴛ {otp_attempt}/{max_otp_attempts} ({otp_attempts_left + 1} ᴀᴛᴛᴇᴍᴘᴛs ʟᴇғᴛ).\n"
                    f"/cancel - ᴛᴏ ᴄᴀɴᴄᴇʟ."
                )

            try:
                phone_code_msg = await bot.ask(
                    user_id,
                    otp_prompt,
                    filters=filters.text,
                    timeout=600
                )
            except (TimeoutError, asyncio.TimeoutError, ListenerTimeout):
                await bot.send_message(user_id, "ᴛɪᴍᴇ ʟɪᴍɪᴛ ʀᴇᴀᴄʜᴇᴅ ᴏғ 10 ᴍɪɴᴜᴛᴇs.\n\nᴘʟᴇᴀsᴇ sᴛᴀʀᴛ ɢᴇɴᴇʀᴀᴛɪɴɢ ʏᴏᴜʀ sᴇssɪᴏɴ ᴀɢᴀɪɴ.")
                return None

            if not phone_code_msg or not phone_code_msg.text or phone_code_msg.text.startswith('/'):
                await bot.send_message(user_id, "<b>ᴘʀᴏᴄᴇss ᴄᴀɴᴄᴇʟʟᴇᴅ!</b>")
                return None

            phone_code = phone_code_msg.text.replace(" ", "").replace("-", "").strip()

            try:
                await client.sign_in(phone_number, code.phone_code_hash, phone_code)
                signed_in = True
                break
            except (PhoneCodeInvalid, PhoneCodeEmpty):
                if otp_attempts_left > 0:
                    await bot.send_message(
                        user_id, 
                        f"❌ ᴛʜᴇ ᴏᴛᴘ ʏᴏᴜ'ᴠᴇ sᴇɴᴛ ɪs ᴡʀᴏɴɢ.\n⚠️ ʏᴏᴜ ʜᴀᴠᴇ {otp_attempts_left} ᴀᴛᴛᴇᴍᴘᴛ(s) ʟᴇғᴛ."
                    )
                    continue
                else:
                    await bot.send_message(
                        user_id, 
                        "❌ ᴛʜᴇ ᴏᴛᴘ ʏᴏᴜ'ᴠᴇ sᴇɴᴛ ɪs ᴡʀᴏɴɢ.\nᴍᴀxɪᴍᴜᴍ 3 ᴀᴛᴛᴇᴍᴘᴛs ʀᴇᴀᴄʜᴇᴅ. ᴘʟᴇᴀsᴇ sᴛᴀʀᴛ ᴀɢᴀɪɴ."
                    )
                    return None
            except PhoneCodeExpired:
                await bot.send_message(user_id, "ᴛʜᴇ ᴏᴛᴘ ʏᴏᴜ'ᴠᴇ sᴇɴᴛ ɪs ᴇxᴘɪʀᴇᴅ.\n\nᴘʟᴇᴀsᴇ sᴛᴀʀᴛ ɢᴇɴᴇʀᴀᴛɪɴɢ ʏᴏᴜʀ sᴇssɪᴏɴ ᴀɢᴀɪɴ.")
                return None
            except PhoneNumberUnoccupied:
                await bot.send_message(user_id, "ᴛʜɪs ᴘʜᴏɴᴇ ɴᴜᴍʙᴇʀ ɪs ɴᴏᴛ ʀᴇɢɪsᴛᴇʀᴇᴅ ᴏɴ ᴛᴇʟᴇɢʀᴀᴍ. ᴘʟᴇᴀsᴇ ʀᴇɢɪsᴛᴇʀ ɪᴛ ғɪʀsᴛ.")
                return None
            except SessionPasswordNeeded:
                needs_2fa = True
                break
            except FloodWait as e:
                await bot.send_message(user_id, f"ғʟᴏᴏᴅᴡᴀɪᴛ: ᴘʟᴇᴀsᴇ ᴡᴀɪᴛ {e.value} sᴇᴄᴏɴᴅs ʙᴇғᴏʀᴇ ᴛʀʏɪɴɢ ᴀɢᴀɪɴ.")
                return None
            except Exception as e:
                await bot.send_message(user_id, f"<b>sɪɢɴ ɪɴ ᴇʀʀᴏʀ:</b> `{e}`")
                return None

        if not signed_in and not needs_2fa:
            return None

        # Step 3: Two-Step Verification Password (up to 3 attempts)
        if needs_2fa:
            max_pwd_attempts = 3
            pwd_verified = False

            for pwd_attempt in range(1, max_pwd_attempts + 1):
                pwd_attempts_left = max_pwd_attempts - pwd_attempt
                if pwd_attempt == 1:
                    pwd_prompt = (
                        "ᴘʟᴇᴀsᴇ ᴇɴᴛᴇʀ ʏᴏᴜʀ ᴛᴡᴏ-sᴛᴇᴘ ᴠᴇʀɪғɪᴄᴀᴛɪᴏɴ ᴘᴀssᴡᴏʀᴅ ᴛᴏ ᴄᴏɴᴛɪɴᴜᴇ.\n"
                        "/cancel - ᴛᴏ ᴄᴀɴᴄᴇʟ."
                    )
                else:
                    pwd_prompt = (
                        f"ᴘʟᴇᴀsᴇ ᴇɴᴛᴇʀ ʏᴏᴜʀ ᴛᴡᴏ-sᴛᴇᴘ ᴠᴇʀɪғɪᴄᴀᴛɪᴏɴ ᴘᴀssᴡᴏʀᴅ.\n"
                        f"⚠️ ᴀᴛᴛᴇᴍᴘᴛ {pwd_attempt}/{max_pwd_attempts} ({pwd_attempts_left + 1} ᴀᴛᴛᴇᴍᴘᴛs ʟᴇғᴛ).\n"
                        f"/cancel - ᴛᴏ ᴄᴀɴᴄᴇʟ."
                    )

                try:
                    two_step_msg = await bot.ask(
                        user_id,
                        pwd_prompt,
                        filters=filters.text,
                        timeout=300
                    )
                except (TimeoutError, asyncio.TimeoutError, ListenerTimeout):
                    await bot.send_message(user_id, "ᴛɪᴍᴇ ʟɪᴍɪᴛ ʀᴇᴀᴄʜᴇᴅ ᴏғ 5 ᴍɪɴᴜᴛᴇs.\n\nᴘʟᴇᴀsᴇ sᴛᴀʀᴛ ɢᴇɴᴇʀᴀᴛɪɴɢ ʏᴏᴜʀ sᴇssɪᴏɴ ᴀɢᴀɪɴ.")
                    return None

                if not two_step_msg or not two_step_msg.text or two_step_msg.text.startswith('/'):
                    await bot.send_message(user_id, "<b>ᴘʀᴏᴄᴇss ᴄᴀɴᴄᴇʟʟᴇᴅ!</b>")
                    return None

                password = two_step_msg.text.strip()
                try:
                    await client.check_password(password=password)
                    pwd_verified = True
                    break
                except PasswordHashInvalid:
                    if pwd_attempts_left > 0:
                        await bot.send_message(
                            user_id, 
                            f"❌ ᴛʜᴇ ᴘᴀssᴡᴏʀᴅ ʏᴏᴜ'ᴠᴇ sᴇɴᴛ ɪs ᴡʀᴏɴɢ.\n⚠️ ʏᴏᴜ ʜᴀᴠᴇ {pwd_attempts_left} ᴀᴛᴛᴇᴍᴘᴛ(s) ʟᴇғᴛ."
                        )
                        continue
                    else:
                        await bot.send_message(
                            user_id, 
                            "❌ ᴛʜᴇ ᴘᴀssᴡᴏʀᴅ ʏᴏᴜ'ᴠᴇ sᴇɴᴛ ɪs ᴡʀᴏɴɢ.\nᴍᴀxɪᴍᴜᴍ 3 ᴀᴛᴛᴇᴍᴘᴛs ʀᴇᴀᴄʜᴇᴅ. ᴘʟᴇᴀsᴇ sᴛᴀʀᴛ ᴀɢᴀɪɴ."
                        )
                        return None
                except FloodWait as e:
                    await bot.send_message(user_id, f"ғʟᴏᴏᴅᴡᴀɪᴛ: ᴘʟᴇᴀsᴇ ᴡᴀɪᴛ {e.value} sᴇᴄᴏɴᴅs ʙᴇғᴏʀᴇ ᴛʀʏɪɴɢ ᴀɢᴀɪɴ.")
                    return None
                except Exception as e:
                    await bot.send_message(user_id, f"<b>ᴘᴀssᴡᴏʀᴅ ᴇʀʀᴏʀ:</b> `{e}`")
                    return None

            if not pwd_verified:
                return None

        # Step 4: Export session string and save
        string_session = await client.export_session_string()
        if not string_session or len(string_session) < 100:
            await bot.send_message(user_id, "<b>ɪɴᴠᴀʟɪᴅ sᴇssɪᴏɴ sᴛʀɪɴɢ.</b>")
            return None

        text = f"➫ ᴛʜɪs ɪs ʏᴏᴜʀ ᴘʏʀᴏɢʀᴀᴍ v2 sᴛʀɪɴɢ sᴇssɪᴏɴ:\n\n<code>{string_session}</code>\n\nɴᴏᴛᴇ: ᴅᴏɴ'ᴛ sʜᴀʀᴇ ɪᴛ ᴡɪᴛʜ ᴀɴʏᴏɴᴇ."
        await bot.send_message(user_id, text)
        user = await client.get_me()
        details = {
            'id': user.id,
            'is_bot': False,
            'user_id': user_id,
            'name': user.first_name,
            'session': string_session,
            'username': user.username
        }
        await db.add_bot(details)
        return details
    finally:
        try:
            await client.disconnect()
        except Exception:
            pass

  async def add_session(self, bot, message):
      user_id = int(message.from_user.id)
      text = "<b>⚠️ ᴅɪsᴄʟᴀɪᴍᴇʀ ⚠️</b>\n\n<code>ʏᴏᴜ ᴄᴀɴ ᴜsᴇ ʏᴏᴜʀ sᴇssɪᴏɴ ғᴏʀ ғᴏʀᴡᴀʀᴅ ᴍᴇssᴀɢᴇ ғʀᴏᴍ ᴘʀɪᴠᴀᴛᴇ ᴄʜᴀᴛ ᴛᴏ ᴀɴᴏᴛʜᴇʀ ᴄʜᴀᴛ.\nᴘʟᴇᴀsᴇ ᴀᴅᴅ ʏᴏᴜʀ ᴘʏʀᴏɢʀᴀᴍ sᴇssɪᴏɴ ᴡɪᴛʜ ʏᴏᴜʀ ᴏᴡɴ ʀɪsᴋ. ᴛʜᴇɪʀ ɪs ᴀ ᴄʜᴀɴᴄᴇ ᴛᴏ ʙᴀɴ ʏᴏᴜʀ ᴀᴄᴄᴏᴜɴᴛ. ᴍʏ ᴅᴇᴠᴇʟᴏᴘᴇʀ ɪs ɴᴏᴛ ʀᴇsᴘᴏɴsɪʙʟᴇ ɪғ ʏᴏᴜʀ ᴀᴄᴄᴏᴜɴᴛ ᴍᴀʏ ɢᴇᴛ ʙᴀɴɴᴇᴅ.</code>"
      await bot.send_message(user_id, text=text)
      try:
          msg = await bot.ask(chat_id=user_id, text="<b>sᴇɴᴅ ʏᴏᴜʀ ᴘʏʀᴏɢʀᴀᴍ sᴇssɪᴏɴ sᴛʀɪɴɢ.\n\n/cancel - ᴄᴀɴᴄᴇʟ ᴛʜᴇ ᴘʀᴏᴄᴇss</b>", timeout=300)
      except (TimeoutError, asyncio.TimeoutError, ListenerTimeout):
          await bot.send_message(user_id, "ᴛɪᴍᴇ ʟɪᴍɪᴛ ʀᴇᴀᴄʜᴇᴅ (5 ᴍɪɴᴜᴛᴇs).\nᴘʟᴇᴀsᴇ sᴛᴀʀᴛ ᴀɢᴀɪɴ.")
          return None
      if not msg or not msg.text or msg.text=='/cancel':
          await bot.send_message(user_id, '<b>ᴘʀᴏᴄᴇss ᴄᴀɴᴄᴇʟʟᴇᴅ !</b>')
          return None
      session_str = msg.text.strip()
      if len(session_str) < 100:
          await bot.send_message(user_id, '<b>ɪɴᴠᴀʟɪᴅ sᴇssɪᴏɴ sᴛʀɪɴɢ</b>')
          return None
      try:
          client = await start_clone_bot(self.client(session_str, True), True)
      except Exception as e:
          await bot.send_message(user_id, f"<b>ᴜsᴇʀ ʙᴏᴛ ᴇʀʀᴏʀ:</b> `{e}`")
          return None
      user = client.me
      details = {
          'id': user.id,
          'is_bot': False,
          'user_id': user_id,
          'name': user.first_name,
          'session': session_str,
          'username': user.username
      }
      await db.add_bot(details)
      try:
          await client.stop()
      except Exception:
          pass
      return True

@Client.on_message(filters.private & filters.command('reset'))
async def reset_cmd(bot, m):
    user_id = m.from_user.id
    # Preserve user's bot, channel, and db_uri credentials
    old_configs = await db.get_configs(user_id)
    preserved_keys = {
        'db_uri': old_configs.get('db_uri'),
    }

    confirm_markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ ʏᴇs, ʀᴇsᴇᴛ ᴀʟʟ", callback_data="reset_confirm")],
        [InlineKeyboardButton("❌ ᴄᴀɴᴄᴇʟ", callback_data="reset_cancel")]
    ])
    await m.reply_text(
        "<blockquote><b>⚠️ <u>ᴄᴏɴғɪʀᴍ sᴇᴛᴛɪɴɢs ʀᴇsᴇᴛ</u></b></blockquote>\n\n"
        "ᴛʜɪs ᴡɪʟʟ ʀᴇsᴇᴛ <b>ᴀʟʟ</b> ᴄᴏɴғɪɢᴜʀᴀᴛɪᴏɴs ᴛᴏ ᴅᴇғᴀᴜʟᴛ:\n\n"
        "• ᴄᴀᴘᴛɪᴏɴ, ғɪʟᴛᴇʀs, sᴘᴇᴇᴅ, ᴋᴇʏᴡᴏʀᴅs\n"
        "• ᴄᴏᴜʀsᴇ sᴇʟʟᴇʀ ᴍᴏᴅᴇ & sᴋɪɴᴇᴛ ᴍᴏᴅɪғɪᴇʀ\n"
        "• ᴅᴜᴍᴘ ᴄʜᴀɴɴᴇʟ, ʙᴜᴛᴛᴏɴs, ʀᴇᴘʟᴀᴄᴇᴍᴇɴᴛs\n\n"
        "🔒 <i>ʏᴏᴜʀ ʙᴏᴛ ᴛᴏᴋᴇɴ, ᴄʜᴀɴɴᴇʟs & ᴅᴀᴛᴀʙᴀsᴇ ᴜʀɪ ᴡɪʟʟ ʙᴇ ᴘʀᴇsᴇʀᴠᴇᴅ.</i>",
        reply_markup=confirm_markup,
        quote=True
    )

@Client.on_callback_query(filters.regex(r'^reset_confirm$'))
async def reset_confirm_cb(bot, query):
    user_id = query.from_user.id
    try:
        old_configs = await db.get_configs(user_id)
        preserved_db_uri = old_configs.get('db_uri')

        # Get fresh defaults from database
        default = await db.get_configs("01")
        # Restore preserved credentials
        default['db_uri'] = preserved_db_uri

        await db.update_configs(user_id, default)
        await query.message.edit_text(
            "<blockquote><b>✅ <u>sᴇᴛᴛɪɴɢs ʀᴇsᴇᴛ sᴜᴄᴄᴇssғᴜʟ</u></b></blockquote>\n\n"
            "ᴀʟʟ ᴄᴏɴғɪɢᴜʀᴀᴛɪᴏɴs ʜᴀᴠᴇ ʙᴇᴇɴ ʀᴇsᴛᴏʀᴇᴅ ᴛᴏ ᴅᴇғᴀᴜʟᴛ.\n\n"
            "🔒 <i>ʙᴏᴛ ᴛᴏᴋᴇɴ, ᴄʜᴀɴɴᴇʟs & ᴅᴀᴛᴀʙᴀsᴇ ᴜʀɪ ᴡᴇʀᴇ ᴘʀᴇsᴇʀᴠᴇᴅ.</i>",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⚙️ ᴏᴘᴇɴ sᴇᴛᴛɪɴɢs", callback_data="settings#main")],
                [InlineKeyboardButton("🔙 ʜᴏᴍᴇ", callback_data="back")]
            ])
        )
    except Exception as e:
        logger.error(f"Reset error for {user_id}: {e}")
        await query.message.edit_text(
            "❌ <b>ᴀɴ ᴇʀʀᴏʀ ᴏᴄᴄᴜʀʀᴇᴅ ᴡʜɪʟᴇ ʀᴇsᴇᴛᴛɪɴɢ.</b>\n\n"
            f"<code>{e}</code>\n\n"
            "<i>ᴘʟᴇᴀsᴇ ᴛʀʏ ᴀɢᴀɪɴ ʟᴀᴛᴇʀ.</i>"
        )

@Client.on_callback_query(filters.regex(r'^reset_cancel$'))
async def reset_cancel_cb(bot, query):
    await query.message.edit_text(
        "✅ <b>ʀᴇsᴇᴛ ᴄᴀɴᴄᴇʟʟᴇᴅ.</b> ʏᴏᴜʀ sᴇᴛᴛɪɴɢs ʀᴇᴍᴀɪɴ ᴜɴᴄʜᴀɴɢᴇᴅ.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 ʜᴏᴍᴇ", callback_data="back")]
        ])
    )

@Client.on_message(filters.command('resetall'))
async def resetall(bot, message):
  user_id = message.from_user.id if message.from_user else message.chat.id
  if not await db.is_admin(user_id):
      return await message.reply_text("⛔ <b>ᴛʜɪs ᴄᴏᴍᴍᴀɴᴅ ɪs ᴏɴʟʏ ғᴏʀ ʙᴏᴛ ᴀᴅᴍɪɴɪsᴛʀᴀᴛᴏʀs.</b>", quote=True)
  users = await db.get_all_users()
  sts = await message.reply_text(
      "<blockquote><b>🔄 <u>ʀᴇsᴇᴛᴛɪɴɢ ᴀʟʟ ᴜsᴇʀs...</u></b></blockquote>",
      quote=True
  )
  TEXT = "<b>ᴛᴏᴛᴀʟ:</b> {}\n<b>sᴜᴄᴄᴇss:</b> {}\n<b>ғᴀɪʟᴇᴅ:</b> {}"
  total = success = failed = 0
  async for user in users:
      user_id = user['id']
      default = await get_configs(user_id)
      default['db_uri'] = None
      total += 1
      if total % 10 == 0:
         try:
            await sts.edit_text(TEXT.format(total, success, failed))
         except Exception:
            pass
      try: 
         await db.update_configs(user_id, default)
         success += 1
      except Exception:
         failed += 1
  await sts.edit_text(
      "<blockquote><b>✅ <u>ʀᴇsᴇᴛ ᴀʟʟ ᴄᴏᴍᴘʟᴇᴛᴇᴅ</u></b></blockquote>\n\n" +
      TEXT.format(total, success, failed)
  )
  
async def get_configs(user_id):
  configs = await db.get_configs(user_id)
  return configs
                          
async def update_configs(user_id, key, value):
  current = await db.get_configs(user_id)
  # All top-level config keys (includes course seller, FTM, and new fields)
  TOP_LEVEL_KEYS = {
      'caption', 'duplicate', 'db_uri', 'forward_tag', 'protect',
      'file_size', 'size_limit', 'extension', 'keywords', 'button',
      'speed_cfg', 'clean_caption', 'replace_words', 'dump_channel', 'dump_enabled',
      'course_seller_mode', 'auto_course_list', 'auto_numbering',
      'username_remover', 'username_replacer', 'link_remover', 'link_replacer',
      'hidden_link_remover', 'hidden_link_replacer', 'remove_tags',
      'upload_type', 'transfer_mode', 'watermark_text', 'autosave_unlocked',
      'course_start_offset', 'course_number_style', 'course_sticky_button',
      'course_detect_missing', 'course_export_txt', 'course_telegraph_export',
      'course_brand_header', 'course_brand_footer', 'adaptive_flood_enabled'
  }
  if key in TOP_LEVEL_KEYS:
     current[key] = value
  else: 
     current['filters'][key] = value
  await db.update_configs(user_id, current)
    
def parse_buttons(text, markup=True):
    buttons = []
    for match in BTN_URL_REGEX.finditer(text):
        n_escapes = 0
        to_check = match.start(1) - 1
        while to_check > 0 and text[to_check] == "\\":
            n_escapes += 1
            to_check -= 1

        if n_escapes % 2 == 0:
            if bool(match.group(4)) and buttons:
                buttons[-1].append(InlineKeyboardButton(
                    text=match.group(2),
                    url=match.group(3).replace(" ", "")))
            else:
                buttons.append([InlineKeyboardButton(
                    text=match.group(2),
                    url=match.group(3).replace(" ", ""))])
    if markup and buttons:
       buttons = InlineKeyboardMarkup(buttons)
    return buttons if buttons else None