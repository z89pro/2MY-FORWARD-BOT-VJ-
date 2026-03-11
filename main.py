# Don't Remove Credit Tg - @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01

import asyncio, logging
from config import Config
from pyrogram import Client as VJ, idle
from typing import Union, Optional, AsyncGenerator
from logging.handlers import RotatingFileHandler
from plugins.regix import restart_forwards

# Don't Remove Credit Tg - @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01

if __name__ == "__main__":
    VJBot = VJ(
        "VJ-Forward-Bot",
        bot_token=Config.BOT_TOKEN,
        api_id=Config.API_ID,
        api_hash=Config.API_HASH,
        sleep_threshold=120,
        plugins=dict(root="plugins")
    )  
    async def iter_messages(
        self,
        chat_id: Union[int, str],
        limit: int,
        offset: int = 0,
    ) -> Optional[AsyncGenerator["types.Message", None]]:
        """Iterate through a chat sequentially.
        This convenience method does the same as repeatedly calling :meth:`~pyrogram.Client.get_messages` in a loop, thus saving
        you from the hassle of setting up boilerplate code. It is useful for getting the whole chat messages with a
        single call.
        Parameters:
            chat_id (``int`` | ``str``):
                Unique identifier (int) or username (str) of the target chat.
                For your personal cloud (Saved Messages) you can simply use "me" or "self".
                For a contact that exists in your Telegram address book you can use his phone number (str).
                
            limit (``int``):
                Identifier of the last message to be returned.
                
            offset (``int``, *optional*):
                Identifier of the first message to be returned.
                Defaults to 0.
        Returns:
            ``Generator``: A generator yielding :obj:`~pyrogram.types.Message` objects.
        Example:
            .. code-block:: python
                for message in app.iter_messages("pyrogram", 1, 15000):
                    print(message.text)
        """
        current = offset
        while True:
            new_diff = min(200, limit - current)
            if new_diff <= 0:
                return
            messages = await self.get_messages(chat_id, list(range(current, current+new_diff+1)))
            for message in messages:
                yield message
                current += 1
               
    from plugins.unequeify import unpack_new_file_id
    from pyrogram.enums import MessagesFilter
    from pyrogram.errors import FloodWait, InputUserDeactivated, UserIsBlocked, PeerIdInvalid
    from database import db

    async def log_channel_cleaner(bot_client):
        while True:
            await asyncio.sleep(21600)  # Runs every 6 hour
            if Config.LOG_CHANNEL != 0:
                try:
                    MESSAGES = []
                    DUPLICATE = []
                    
                    async for message in bot_client.search_messages(chat_id=Config.LOG_CHANNEL, filter=MessagesFilter.DOCUMENT):
                        file = message.document
                        if not file: continue
                        
                        try:
                            file_id = unpack_new_file_id(file.file_id) 
                            
                            if file_id in MESSAGES:
                                DUPLICATE.append(message.id)
                            else:
                                MESSAGES.append(file_id)
                                
                            if len(DUPLICATE) >= 100:
                                await bot_client.delete_messages(Config.LOG_CHANNEL, DUPLICATE)
                                DUPLICATE = []
                        except Exception as file_e:
                            pass
                            
                    if DUPLICATE:
                        await bot_client.delete_messages(Config.LOG_CHANNEL, DUPLICATE)
                except Exception as e:
                    pass

    async def send_restart_notification(bot_client):
        users = await db.get_all_users()
        msg_text = "✅ **Bot restarted successfully!**\n\nAll systems are fully operational."
        async for user in users:
            try:
                await bot_client.send_message(chat_id=user['id'], text=msg_text)
            except FloodWait as e:
                await asyncio.sleep(e.value)
                try:
                    await bot_client.send_message(chat_id=user['id'], text=msg_text)
                except:
                    pass
            except InputUserDeactivated:
                await db.delete_user(int(user['id']))
            except UserIsBlocked:
                pass
            except PeerIdInvalid:
                await db.delete_user(int(user['id']))
            except Exception:
                pass

    async def main():
        await VJBot.start()
        bot_info  = await VJBot.get_me()
        await restart_forwards(VJBot)
        print("Bot Started.")
        
        # Start Log Channel Cleaner Task
        asyncio.create_task(log_channel_cleaner(VJBot))
        
        # Start Restart Notification Task
        asyncio.create_task(send_restart_notification(VJBot))
        
        await idle()

    asyncio.get_event_loop().run_until_complete(main())

# Don't Remove Credit Tg - @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01
