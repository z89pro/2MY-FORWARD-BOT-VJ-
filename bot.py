"""
bot.py — Advanced Telegram Forward Bot
Features:
  • Interactive Forwarding with Live Progress Bar & Pause / Resume / Cancel
  • Smart AutoSave Mode with real-time channel monitoring & media filtering
  • Speed Control (Extreme 0.5s, Fast 1.0s, Normal 3.0s, Safe 5.0s, Anti-Ban Jitter)
  • Channel Duplicate Cleaner (/unequify)
  • Stealth Dump Channel & Telemetry Log Channel Dual-Architecture
  • Resilient Startup (prevents Koyeb/Render crash loop on expired tokens)
  • Built-in Web Server for 24/7 keep-alive & health checks
"""
import os
import re
import sys
import json
import asyncio
import logging
from datetime import datetime, timezone, timedelta
from platform import python_version
from pyrogram import Client, __version__ as pyrogram_version
from pyrogram.raw.all import layer
from pyrogram.enums import ParseMode
from pyrogram.errors import FloodWait, RPCError
from pyrogram.errors.exceptions.bad_request_400 import AccessTokenExpired, AccessTokenInvalid
from pyrogram.types import BotCommand
from config import Config, temp
from database import db
from keep_alive import keep_alive
from font_styler import patch_pyrogram_font
from translation import Translation
from buttons import colored_markup, btn
import plugins.listener

# Initialize Universal Small Caps Font Engine
patch_pyrogram_font()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logging.getLogger("pyrogram").setLevel(logging.ERROR)
logger = logging.getLogger("ForwardBot")


class Bot(Client):
    def __init__(self):
        super().__init__(
            Config.BOT_SESSION,
            api_hash=Config.API_HASH,
            api_id=int(Config.API_ID) if Config.API_ID else 0,
            bot_token=Config.BOT_TOKEN,
            sleep_threshold=10,
            workers=200,
            plugins={"root": "plugins"}
        )
        self.log = logging

    async def start(self, *args, **kwargs):
        try:
            await super().start(*args, **kwargs)
        except (AccessTokenExpired, AccessTokenInvalid) as e:
            logger.critical("=" * 70)
            logger.critical("❌ CRITICAL: TELEGRAM BOT_TOKEN HAS EXPIRED OR IS INVALID!")
            logger.critical(f"Telegram error: {e}")
            logger.critical("")
            logger.critical("👉 HOW TO FIX ON KOYEB / RENDER:")
            logger.critical("1. Open Telegram and message @BotFather")
            logger.critical("2. Create a new bot or revoke/regenerate token (/newbot or /token)")
            logger.critical("3. Copy your fresh bot token")
            logger.critical("4. In your Koyeb / Render Dashboard -> App Settings -> Environment Variables:")
            logger.critical("   Set BOT_TOKEN = <your_new_token>")
            logger.critical("5. Redeploy your service.")
            logger.critical("=" * 70)
            logger.info("Keeping web health-check server alive to prevent Koyeb restart loop...")
            while True:
                await asyncio.sleep(3600)
        except Exception as e:
            # Everything else is a genuine fault — an unreachable Mongo, a
            # malformed config, a bad API_ID/HASH. Parking here turned it into
            # a permanently mute process that still passed the health check.
            # Exit non-zero so the platform's restart policy can act on it.
            logger.critical("=" * 70)
            logger.critical(f"❌ FATAL: could not start the bot client: {type(e).__name__}: {e}")
            logger.critical("Exiting so the supervisor can restart with a clean state.")
            logger.critical("=" * 70)
            raise

        me = await self.get_me()
        logger.info(f"✅ {me.first_name} (@{me.username}) started! Layer {layer} (Pyrogram {pyrogram_version})")

        # Register bot commands in Telegram Menu
        # Register all bot commands in Telegram Menu
        try:
            await self.set_bot_commands([
                # Main & Navigation
                BotCommand("start", "sᴛᴀʀᴛ ʙᴏᴛ & ᴠɪᴇᴡ ᴍᴀɪɴ ᴄᴀʀᴅ"),
                BotCommand("help", "ᴄᴏᴍᴘʟᴇᴛᴇ ғᴇᴀᴛᴜʀᴇ ɢᴜɪᴅᴇ & ʜᴇʟᴘ"),
                BotCommand("commands", "ɪɴᴛᴇʀᴀᴄᴛɪᴠᴇ ᴄᴏᴍᴍᴀɴᴅ ᴍᴇɴᴜ"),
                BotCommand("menu", "ǫᴜɪᴄᴋ ɴᴀᴠɪɢᴀᴛɪᴏɴ ᴍᴇɴᴜ"),
                BotCommand("addbot", "ᴄᴏɴɴᴇᴄᴛ ʏᴏᴜʀ ʙᴏᴛ ᴛᴏᴋᴇɴ ᴏʀ ᴜsᴇʀʙᴏᴛ"),
                BotCommand("id", "ᴠɪᴇᴡ ʏᴏᴜʀ ɪᴅ ᴏʀ ғᴏʀᴡᴀʀᴅᴇᴅ ᴄʜᴀɴɴᴇʟ ɪᴅ"),
                BotCommand("settings", "ᴄᴏɴғɪɢᴜʀᴇ ᴀʟʟ ʙᴏᴛ sᴇᴛᴛɪɴɢs"),
                BotCommand("status", "sʏsᴛᴇᴍ & ʙᴏᴛ sᴛᴀᴛɪsᴛɪᴄs"),

                # Forwarding Suite
                BotCommand("forward", "sᴛᴀʀᴛ ғᴏʀᴡᴀʀᴅɪɴɢ ᴡɪᴢᴀʀᴅ"),
                BotCommand("fwd", "ᴍᴜʟᴛɪ-ʀᴀɴɢᴇ ʙᴀᴛᴄʜ ғᴏʀᴡᴀʀᴅ"),
                BotCommand("autosave", "𝟸𝟺/𝟽 ʀᴇᴀʟ-ᴛɪᴍᴇ ᴀᴜᴛᴏsᴀᴠᴇ"),
                BotCommand("pause", "ᴘᴀᴜsᴇ ᴏɴɢᴏɪɴɢ ғᴏʀᴡᴀʀᴅɪɴɢ"),
                BotCommand("resume", "ʀᴇsᴜᴍᴇ ᴘᴀᴜsᴇᴅ ғᴏʀᴡᴀʀᴅɪɴɢ"),
                BotCommand("stop", "ᴄᴀɴᴄᴇʟ ᴏɴɢᴏɪɴɢ ғᴏʀᴡᴀʀᴅɪɴɢ"),
                BotCommand("unequify", "ᴄʟᴇᴀɴ ᴅᴜᴘʟɪᴄᴀᴛᴇs ɪɴ ᴄʜᴀɴɴᴇʟ"),
                BotCommand("reset", "ʀᴇsᴇᴛ sᴇᴛᴛɪɴɢs ᴛᴏ ᴅᴇғᴀᴜʟᴛ"),

                # Course Seller & Branding Suite
                BotCommand("courseseller", "ᴍᴀsᴛᴇʀ ᴄᴏᴜʀsᴇ sᴇʟʟᴇʀ sᴜɪᴛᴇ"),
                BotCommand("setbanner", "sᴇᴛ ʜᴇᴀᴅᴇʀ ʙʀᴀɴᴅɪɴɢ ʙᴀɴɴᴇʀ"),
                BotCommand("delbanner", "ᴄʟᴇᴀʀ ʜᴇᴀᴅᴇʀ ʙʀᴀɴᴅɪɴɢ ʙᴀɴɴᴇʀ"),
                BotCommand("setfooter", "sᴇᴛ ғᴏᴏᴛᴇʀ ʙʀᴀɴᴅɪɴɢ ʙᴀɴɴᴇʀ"),
                BotCommand("delfooter", "ᴄʟᴇᴀʀ ғᴏᴏᴛᴇʀ ʙʀᴀɴᴅɪɴɢ ʙᴀɴɴᴇʀ"),
                BotCommand("viewbranding", "ᴘʀᴇᴠɪᴇᴡ ʙʀᴀɴᴅɪɴɢ sᴜɪᴛᴇ"),
                BotCommand("setlecstart", "sᴇᴛ sᴛᴀʀᴛɪɴɢ ʟᴇᴄᴛᴜʀᴇ ɴᴜᴍʙᴇʀ"),
                BotCommand("setcoursebutton", "sᴇᴛ sᴛɪᴄᴋʏ ᴄᴏᴜʀsᴇ ʙᴜᴛᴛᴏɴ"),

                # Guides & Knowledge
                BotCommand("tutorial", "𝟷𝟸-ᴍᴏᴅᴜʟᴇ ᴍᴀsᴛᴇʀ ɢᴜɪᴅᴇ"),
                BotCommand("skinet", "ᴍᴏᴅɪғɪᴇʀ & ᴄʟᴇᴀɴᴇʀ ɢᴜɪᴅᴇ"),

                # VIP Passes & Referrals
                BotCommand("plans", "ᴠɪᴘ ᴘᴀssᴇs & ᴘᴜʀᴄʜᴀsᴇ"),
                BotCommand("myplan", "ᴄʜᴇᴄᴋ ᴀᴄᴛɪᴠᴇ ᴠɪᴘ sᴛᴀᴛᴜs"),
                BotCommand("referral", "ʀᴇғᴇʀ ғʀɪᴇɴᴅs & ᴇᴀʀɴ"),
                BotCommand("topref", "ʀᴇғᴇʀʀᴀʟ ʟᴇᴀᴅᴇʀʙᴏᴀʀᴅ"),
                BotCommand("verify", "ᴄʜᴇᴄᴋ ᴠᴇʀɪғɪᴄᴀᴛɪᴏɴ ᴘᴀss"),

                # Admin & Maintenance
                BotCommand("setdump", "sᴇᴛ ɢʟᴏʙᴀʟ ᴅᴜᴍᴘ ᴄʜᴀɴɴᴇʟ (ᴀᴅᴍɪɴ)"),
                BotCommand("restart", "ʀᴇʙᴏᴏᴛ ʙᴏᴛ ᴇɴɢɪɴᴇ (ᴀᴅᴍɪɴ)"),
                BotCommand("broadcast", "ʙʀᴏᴀᴅᴄᴀsᴛ ᴛᴏ ᴜsᴇʀs (ᴀᴅᴍɪɴ)"),
                BotCommand("cancelbroadcast", "ᴄᴀɴᴄᴇʟ ʙʀᴏᴀᴅᴄᴀsᴛ (ᴀᴅᴍɪɴ)"),
                BotCommand("vipadmin", "ᴠɪᴘ ᴀᴅᴍɪɴ ʜᴜʙ (ᴀᴅᴍɪɴ)"),
                BotCommand("addpremium", "ɢʀᴀɴᴛ ᴠɪᴘ ᴛᴏ ᴜsᴇʀ (ᴀᴅᴍɪɴ)"),
                BotCommand("delpremium", "ʀᴇᴠᴏᴋᴇ ᴠɪᴘ (ᴀᴅᴍɪɴ)"),
                BotCommand("setverify", "ᴠᴇʀɪғɪᴄᴀᴛɪᴏɴ sᴇᴛᴛɪɴɢs (ᴀᴅᴍɪɴ)"),
                BotCommand("userstats", "ᴜsᴇʀ ᴀɴᴀʟʏᴛɪᴄs (ᴀᴅᴍɪɴ)"),
                BotCommand("tasks", "sᴜʀᴠᴇɪʟʟᴀɴᴄᴇ: ᴀʟʟ ᴀᴄᴛɪᴠᴇ ᴛᴀsᴋs (ᴀᴅᴍɪɴ)"),
                BotCommand("ban", "ʙᴀɴ ᴜsᴇʀ ғʀᴏᴍ ʙᴏᴛ (ᴀᴅᴍɪɴ)"),
                BotCommand("unban", "ᴜɴʙᴀɴ ᴜsᴇʀ (ᴀᴅᴍɪɴ)"),
                BotCommand("blacklist", "ᴠɪᴇᴡ & ᴍᴀɴᴀɢᴇ ʙʟᴀᴄᴋʟɪsᴛ (ᴀᴅᴍɪɴ)"),
                BotCommand("config", "sʏsᴛᴇᴍ ᴄᴏɴғɪɢ (ᴏᴡɴᴇʀ)"),
                BotCommand("admins", "ʟɪsᴛ ʙᴏᴛ ᴀᴅᴍɪɴs (ᴏᴡɴᴇʀ)")
            ])
            logger.info("✅ Telegram bot command menu registered successfully (42 commands).")
        except Exception as e:
            logger.warning(f"Failed to set bot commands: {e}")

        # Ensure latest dynamic system configs are active in-memory
        try:
            await db.load_system_config_into_env()
            asyncio.create_task(db.sanitize_corrupted_user_names())
        except Exception as e:
            logger.debug(f"Load system config error: {e}")

        self.id = me.id
        self.username = me.username
        self.first_name = me.first_name
        self.set_parse_mode(ParseMode.DEFAULT)

        # ── 1. Process Pending Restart Status (from /restart or config menu) ──
        ist = timezone(timedelta(hours=5, minutes=30))
        stamp = datetime.now(ist).strftime("%d-%b-%Y %I:%M:%S %p")
        restarted_chat_id = None
        reboot_notice = None

        try:
            reboot_notice = await db.get_and_clear_restart_status()
        except Exception as e:
            logger.debug(f"DB restart status query error: {e}")

        if not reboot_notice and os.path.exists('.restart_status.json'):
            try:
                with open('.restart_status.json', 'r') as f:
                    reboot_notice = json.load(f)
                os.remove('.restart_status.json')
            except Exception as e:
                logger.debug(f"Local restart file cleanup error: {e}")

        restart_markup = colored_markup([
            [btn("🚀 sʏsᴛᴇᴍ sᴛᴀᴛᴜs", "status", "blue"), btn("⚙️ ᴄᴏɴғɪɢ", "config#main", "green")]
        ])

        reboot_done_text = Translation.RESTARTED_TXT.format(
            getattr(self, 'username', 'bot'),
            getattr(self, 'id', 0),
            stamp,
            pyrogram_version,
            python_version()
        )

        if reboot_notice:
            r_chat_id = reboot_notice.get('chat_id')
            r_msg_id = reboot_notice.get('message_id')
            if r_chat_id and r_msg_id:
                restarted_chat_id = r_chat_id
                try:
                    await self.edit_message_text(r_chat_id, r_msg_id, reboot_done_text, reply_markup=restart_markup)
                    logger.info(f"Updated restart status message for chat {r_chat_id}")
                except Exception:
                    try:
                        await self.send_message(r_chat_id, reboot_done_text, reply_markup=restart_markup)
                    except Exception:
                        pass

        # ── 2. Broadcast Restart Notice to LOG_CHANNEL ──
        if Config.LOG_CHANNEL:
            try:
                await self.send_message(Config.LOG_CHANNEL, reboot_done_text, reply_markup=restart_markup)
                logger.info(f"Sent restart notice to LOG_CHANNEL: {Config.LOG_CHANNEL}")
            except Exception as e:
                logger.warning(
                    f"Could not send restart notice to LOG_CHANNEL ({Config.LOG_CHANNEL}): {e}. "
                    f"Please ensure @{getattr(self, 'username', 'bot')} is added as an Admin with post permissions in that channel."
                )

        # ── 3. Notify Bot Owner(s) and Administrators ──
        try:
            admins_to_notify = await db.get_all_admins()
        except Exception:
            admins_to_notify = Config.BOT_OWNER_ID or []

        if reboot_notice:
            for aid in admins_to_notify:
                if aid != restarted_chat_id:
                    try:
                        await self.send_message(aid, reboot_done_text, reply_markup=restart_markup)
                    except Exception:
                        pass

        # ── 4. Auto-Resume Interrupted Forwarding Tasks from Checkpoint ──
        try:
            from plugins.regix import auto_resume_unfinished_tasks
            asyncio.create_task(auto_resume_unfinished_tasks(self))
            logger.info("✅ Auto-resume forward task recovery worker launched.")
        except Exception as e:
            logger.warning(f"Could not initialize forward auto-resumption: {e}")

        # ── 6. Periodic VIP Premium Expiry Sweep (every 6h) ──
        async def _expiry_sweep():
            import time
            while True:
                try:
                    now = time.time()
                    expired_cursor = db.premium.find({"expires_at": {"$lte": now, "$gt": 0}, "expiry_notified": {"$ne": True}})
                    async for doc in expired_cursor:
                        uid = doc.get("user_id")
                        if uid:
                            try:
                                await self.send_message(
                                    uid,
                                    "<blockquote><b>⚠️ <u>ᴠɪᴘ ᴘʟᴀɴ ᴇxᴘɪʀᴇᴅ</u></b></blockquote>\n\n"
                                    "<i>ʏᴏᴜʀ ᴠɪᴘ ᴘʀᴇᴍɪᴜᴍ ᴘʟᴀɴ ʜᴀs ᴇxᴘɪʀᴇᴅ. ʏᴏᴜʀ sᴘᴇᴇᴅ & ғᴇᴀᴛᴜʀᴇs ʜᴀᴠᴇ ʙᴇᴇɴ ʀᴇsᴇᴛ ᴛᴏ sᴛᴀɴᴅᴀʀᴅ.\n\n"
                                    "👉 ᴜsᴇ /plans ᴛᴏ ʀᴇɴᴇᴡ ʏᴏᴜʀ sᴜʙsᴄʀɪᴘᴛɪᴏɴ ᴀɴʏᴛɪᴍᴇ!</i>"
                                )
                            except Exception:
                                pass
                            await db.premium.update_one({"_id": doc["_id"]}, {"$set": {"expiry_notified": True}})
                except Exception as ex:
                    logger.debug(f"Expiry sweep error: {ex}")
                await asyncio.sleep(21600)  # 6 hours

        asyncio.create_task(_expiry_sweep())

    async def stop(self, *args, **kwargs):
        logger.info(f"🛑 Bot @{getattr(self, 'username', 'ForwardBot')} stopping...")
        await super().stop(*args, **kwargs)


if __name__ == "__main__":
    # Start web keep-alive server first on Koyeb/Render port
    keep_alive()

    # Explicit event loop setup for Python 3.10/3.11/3.12 compatibility
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    # Pre-load persistent system config from MongoDB before Pyrogram starts
    try:
        loop.run_until_complete(db.load_system_config_into_env())
    except Exception as e:
        logger.debug(f"Pre-load config error: {e}")

    app = Bot()
    try:
        app.run()
    except (KeyboardInterrupt, SystemExit):
        logger.info("🛑 Process terminated.")
