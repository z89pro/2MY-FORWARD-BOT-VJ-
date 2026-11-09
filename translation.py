import os
from config import Config

class Translation(object):
  START_TXT = """<blockquote><b>⚡️ <u>sᴋɪɴᴇᴛ ᴠᴇʀsᴇ — ᴜʟᴛʀᴀ ғᴏʀᴡᴀʀᴅ ʙᴏᴛ</u></b></blockquote>

👋 <b>Welcome, {}!</b>

An enterprise-grade Telegram channel cloning, media migration, and course distribution engine.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🚀 <b>Engine:</b> <code>🟢 Online & Ready</code>
⚡️ <b>Version:</b> <code>v2.5.0 Ultra Edition</code>
🛡 <b>Anti-Ban Core:</b> <code>Active Jitter & FloodWait Shield</code>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

👇 <i>Choose an action below to get started:</i>"""

  DONATE_TXT = """<blockquote><b>❤️ <u>sᴋɪɴᴇᴛ ᴠᴇʀsᴇ sᴜᴘᴘᴏʀᴛ</u></b></blockquote>\n\n<i>Thank you for using Skinet Verse! Your support keeps the servers fast and 100% free.</i>"""

  HELP_TXT = """<blockquote><b>🔆 <u>sᴋɪɴᴇᴛ ᴠᴇʀsᴇ — ᴍᴀsᴛᴇʀ ᴄᴏᴍᴍᴀɴᴅ ʜᴜʙ</u></b></blockquote>

<b>📚 Available Commands:</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⏣ <code>/start</code> — Start bot & view main card
⏣ <code>/addbot</code> — Connect your bot token or userbot
⏣ <code>/commands</code> — Interactive command navigator & categories
⏣ <code>/forward</code> — Interactive channel forward wizard
⏣ <code>/fwd &lt;links/ranges&gt;</code> — Multi-range batch forward (e.g. 10-20 30-40)
⏣ <code>/courseseller</code> — Master Course Seller Suite & settings
⏣ <code>/setbanner</code> / <code>/delbanner</code> — Dynamic branding header banner
⏣ <code>/setfooter</code> / <code>/delfooter</code> — Dynamic branding footer banner
⏣ <code>/viewbranding</code> — Preview current branding suite
⏣ <code>/setlecstart</code> — Set starting lecture number
⏣ <code>/setcoursebutton</code> — Set sticky interactive button
⏣ <code>/autosave</code> — Real-time 24/7 channel monitoring
⏣ <code>/tutorial</code> — 12-Module Master Knowledge Hub
⏣ <code>/skinet</code> — Skinet Text & Media Modifier Guide
⏣ <code>/referral</code> — Refer & Earn VIP rewards
⏣ <code>/verify</code> — Check verification pass status
⏣ <code>/topref</code> — Top 10 Referral Leaderboard
⏣ <code>/pause</code> / <code>/resume</code> — Pause & resume forward tasks
⏣ <code>/stop</code> — Gracefully cancel ongoing tasks
⏣ <code>/unequify</code> — Channel duplicate message cleaner
⏣ <code>/settings</code> — Complete bot customization menu
⏣ <code>/config</code> — Owner system configuration (Admin)
⏣ <code>/restart</code> — Reboot bot engine & reload configs (Admin)
⏣ <code>/broadcast</code> — Multi-format broadcast to all users (Admin)
⏣ <code>/setverify</code> — Token verification config (Admin)
⏣ <code>/userstats</code> — Admin user analytics dashboard
⏣ <code>/reset</code> — Reset configurations to default
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<b>✨ Key Highlights:</b>
• 🎓 <b>Course Seller Suite:</b> Auto numbering, gap alerts & Telegraph syllabus
• 🛡️ <b>Adaptive Anti-Flood:</b> Dynamic jitter & FloodWait auto-recovery
• 🏷️ <b>Branding Banners:</b> 1024-char safe headers & footers for media
• ⚡ <b>Multi-Range Forwarding:</b> Forward multiple ranges in one go
• 🛠 <b>Skinet Modifier:</b> Competitor username & link replacement
• 🚀 <b>Smart AutoSave:</b> Real-time channel listener & auto-post"""

  HOW_USE_TXT = """<blockquote><b>📖 <u>sᴇᴛᴜᴘ ɢᴜɪᴅᴇ — ʀᴇᴀᴅ ᴛʜɪs ғɪʀsᴛ</u></b></blockquote>

<b>ᴛʜɪs ʙᴏᴛ ᴄᴏᴘɪᴇs ᴍᴇssᴀɢᴇs ғʀᴏᴍ ᴏɴᴇ ᴄʜᴀɴɴᴇʟ ᴛᴏ ᴀɴᴏᴛʜᴇʀ.</b>
ʏᴏᴜ ɴᴇᴇᴅ ᴛᴡᴏ ᴛʜɪɴɢs ʙᴇғᴏʀᴇ ɪᴛ ᴄᴀɴ ᴡᴏʀᴋ:

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1️⃣ <b>ᴀ ᴡᴏʀᴋᴇʀ</b> — ᴛʜᴇ ᴀᴄᴄᴏᴜɴᴛ ᴛʜᴀᴛ ᴅᴏᴇs ᴛʜᴇ ᴄᴏᴘʏɪɴɢ

   • ᴛᴀᴘ <b>➕ ᴀᴅᴅ ʙᴏᴛ</b> ᴏɴ ᴛʜᴇ ᴍᴀɪɴ ᴍᴇɴᴜ, ᴏʀ sᴇɴᴅ /addbot
   • ᴏᴘᴇɴ @BotFather ➔ /newbot ➔ ᴄᴏᴘʏ ᴛʜᴇ ᴛᴏᴋᴇɴ ➔ sᴇɴᴅ ɪᴛ ʜᴇʀᴇ
   • ғᴏʀ <b>ᴘʀɪᴠᴀᴛᴇ</b> ᴄʜᴀɴɴᴇʟs ʏᴏᴜ ɴᴇᴇᴅ ᴀ ᴜsᴇʀʙᴏᴛ ɪɴsᴛᴇᴀᴅ (ᴛᴀᴘ ➕ ᴀᴅᴅ ʙᴏᴛ ➔ ᴜsᴇʀʙᴏᴛ)

2️⃣ <b>ᴀ ᴛᴀʀɢᴇᴛ ᴄʜᴀɴɴᴇʟ</b> — ᴡʜᴇʀᴇ ᴍᴇssᴀɢᴇs ɢᴏ

   • ᴛᴀᴘ <b>📡 ᴀᴅᴅ ᴄʜᴀɴɴᴇʟ</b> ᴏɴ ᴛʜᴇ ᴍᴀɪɴ ᴍᴇɴᴜ
   • ғᴏʀᴡᴀʀᴅ ᴀɴʏ ᴍᴇssᴀɢᴇ ғʀᴏᴍ ᴛʜᴀᴛ ᴄʜᴀɴɴᴇʟ, ᴏʀ sᴇɴᴅ ɪᴛs ʟɪɴᴋ / ID
   • ⚠️ <b>ᴍᴀᴋᴇ ʏᴏᴜʀ ʙᴏᴛ ᴀɴ ᴀᴅᴍɪɴ ᴛʜᴇʀᴇ</b> ᴡɪᴛʜ "ᴘᴏsᴛ ᴍᴇssᴀɢᴇs" ᴏɴ

3️⃣ <b>ᴀ sᴏᴜʀᴄᴇ</b> — ᴡʜᴇʀᴇ ᴍᴇssᴀɢᴇs ᴄᴏᴍᴇ ғʀᴏᴍ

   • ɴᴏ sᴇᴛᴜᴘ ɴᴇᴇᴅᴇᴅ — ʏᴏᴜ ᴘɪᴄᴋ ɪᴛ ᴡʜᴇɴ ʏᴏᴜ sᴛᴀʀᴛ ᴀ ᴛᴀsᴋ
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<b>ᴛʜᴇɴ sᴛᴀʀᴛ ᴀ ᴛᴀsᴋ:</b>

▶️ <code>/forward</code> — ᴡɪᴢᴀʀᴅ. ɪᴛ ᴀsᴋs ʏᴏᴜ ǫᴜᴇsᴛɪᴏɴs ᴏɴᴇ ʙʏ ᴏɴᴇ.
▶️ <code>/fwd 10-20 30-40</code> — ᴏɴᴇ-ʟɪɴᴇʀ ᴠᴇʀsɪᴏɴ ᴏғ ᴛʜᴇ sᴀᴍᴇ ᴛʜɪɴɢ.

<b>ᴅᴜʀɪɴɢ ᴀ ᴛᴀsᴋ:</b>
⏸ <code>/pause</code> — sᴛᴏᴘ ғᴏʀ ɴᴏᴡ, ᴋᴇᴇᴘ ᴘʟᴀᴄᴇ
▶️ <code>/resume</code> — ᴄᴀʀʀʏ ᴏɴ ғʀᴏᴍ ᴡʜᴇʀᴇ ʏᴏᴜ ᴘᴀᴜsᴇᴅ
⏹ <code>/stop</code> — ᴄᴀɴᴄᴇʟ ᴛʜᴇ ᴛᴀsᴋ ᴄᴏᴍᴘʟᴇᴛᴇʟʏ

<b>ᴄᴏᴍᴍᴏɴ ᴘʀᴏʙʟᴇᴍs:</b>
• <i>"ʙᴏᴛ ɪs ɴᴏᴛ ᴀᴅᴍɪɴ"</i> ➔ ᴀᴅᴅ ɪᴛ ᴛᴏ ᴛʜᴇ ᴛᴀʀɢᴇᴛ ᴄʜᴀɴɴᴇʟ ᴀs ᴀᴅᴍɪɴ.
• <i>"ᴄᴏᴜʟᴅ ɴᴏᴛ ʀᴇᴀᴅ ᴛʜᴀᴛ ᴄʜᴀɴɴᴇʟ"</i> ➔ sᴇɴᴅ ᴛʜᴇ ʟɪɴᴋ, ᴏʀ ғᴏʀᴡᴀʀᴅ ᴀ ᴍᴇssᴀɢᴇ ғʀᴏᴍ ɪᴛ.
• <i>ɴᴏᴛʜɪɴɢ ʜᴀᴘᴘᴇɴs</i> ➔ sᴇɴᴅ /addbot ᴀɴᴅ ᴀᴅᴅ ᴀ ᴡᴏʀᴋᴇʀ ғɪʀsᴛ.
• <i>ᴘʀɪᴠᴀᴛᴇ sᴏᴜʀᴄᴇ</i> ➔ ʏᴏᴜʀ ᴜsᴇʀʙᴏᴛ ᴍᴜsᴛ ʙᴇ ᴀ ᴍᴇᴍʙᴇʀ ᴛʜᴇʀᴇ.

👇 <i>ᴛᴀᴘ ᴀ ʙᴜᴛᴛᴏɴ ᴛᴏ sᴛᴀʀᴛ:</i>"""

  ABOUT_TXT = """<blockquote><b>ℹ️ <u>ᴀʙᴏᴜᴛ — sᴋɪɴᴇᴛ ᴠᴇʀsᴇ ғᴏʀᴡᴀʀᴅ ʙᴏᴛ</u></b></blockquote>

An enterprise automated media pipeline engineered for high-concurrency channel migration and seamless brand sanitization.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🤖 <b>Bot:</b> <code>Skinet Verse Forward Bot</code>
💎 <b>Edition:</b> <code>Ultra Pro Max v2.5</code>
🗣 <b>Language:</b> <code>Python 3.10+</code>
📚 <b>Framework:</b> <code>Pyrogram / Pyrofork Layer 223+</code>
⚡️ <b>Engine:</b> <code>AsyncIO Multi-Worker</code>
🛡 <b>Security:</b> <code>In-Memory Sessions & FloodWait Defense</code>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
<i>⚡️ Powered by Skinet Verse Official</i>"""

  STATUS_TXT = """<blockquote><b>📊 <u>sᴋɪɴᴇᴛ ᴠᴇʀsᴇ — sʏsᴛᴇᴍ sᴛᴀᴛᴜs</u></b></blockquote>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
👥 <b>Total Users:</b> <code>{}</code>
🤖 <b>Connected Bots:</b> <code>{}</code>
🔁 <b>Active Forward Tasks:</b> <code>{}</code>
🏷 <b>Connected Channels:</b> <code>{}</code>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━""" 

  SERVER_TXT = """<blockquote><b>⚙️ <u>sᴇʀᴠᴇʀ ʀᴇsᴏᴜʀᴄᴇ sᴛᴀᴛs</u></b></blockquote>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💻 <b>CPU Load:</b> <code>{}%</code>
🧠 <b>RAM Usage:</b> <code>{}%</code>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""
  
  FROM_MSG = "<b>❪ SET SOURCE CHAT ❫\n\nForward the last message or send message link of source chat.\n/cancel - Cancel this process</b>"

  TO_MSG = "<b>❪ CHOOSE TARGET CHAT ❫\n\nChoose your target chat from the buttons below.\n/cancel - Cancel this process</b>"

  SKIP_MSG = "<b><u>sᴇᴛ ɴᴏ. ᴏғ ᴍᴇssᴀɢᴇs ᴛᴏ sᴋɪᴘ 📃</u></b>\n\n<b>You can skip a certain number of messages and forward the rest.\n\nDefault Skip Number = 0</b>\n\n<b><i>Example: If you enter 0, no messages will be skipped.\nIf you enter 5, the first 5 messages will be skipped.</i></b>\n/cancel <b>- Cancel this process</b>"

  CANCEL = "<b>Process Cancelled Successfully!</b>"

  BOT_DETAILS = "<blockquote><b>🤖 <u>ᴄᴏɴɴᴇᴄᴛᴇᴅ ʙᴏᴛ ᴅᴇᴛᴀɪʟs</u></b></blockquote>\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n➣ <b>ɴᴀᴍᴇ:</b> <code>{}</code>\n➣ <b>ʙᴏᴛ ɪᴅ:</b> <code>{}</code>\n➣ <b>ᴜsᴇʀɴᴀᴍᴇ:</b> @{}\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

  USER_DETAILS = "<blockquote><b>👤 <u>ᴄᴏɴɴᴇᴄᴛᴇᴅ ᴜsᴇʀʙᴏᴛ ᴅᴇᴛᴀɪʟs</u></b></blockquote>\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n➣ <b>ɴᴀᴍᴇ:</b> <code>{}</code>\n➣ <b>ᴜsᴇʀ ɪᴅ:</b> <code>{}</code>\n➣ <b>ᴜsᴇʀɴᴀᴍᴇ:</b> @{}\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━"  
         
  TEXT = """<blockquote><b>⚡️ <u>sᴋɪɴᴇᴛ ᴠᴇʀsᴇ — ғᴏʀᴡᴀʀᴅ sᴛᴀᴛᴜs</u></b></blockquote>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📦 <b>ᴛᴏᴛᴀʟ ᴍᴇssᴀɢᴇs:</b> <code>{}</code>
📥 <b>ғᴇᴛᴄʜᴇᴅ ᴍᴇssᴀɢᴇs:</b> <code>{}</code>
📤 <b>ғᴏʀᴡᴀʀᴅᴇᴅ ᴍᴇssᴀɢᴇs:</b> <code>{}</code>
♻️ <b>ᴅᴜᴘʟɪᴄᴀᴛᴇ ᴍᴇssᴀɢᴇs:</b> <code>{}</code>
🗑 <b>ᴅᴇʟᴇᴛᴇᴅ ᴍᴇssᴀɢᴇs:</b> <code>{}</code>
⏩ <b>sᴋɪᴘᴘᴇᴅ ᴍᴇssᴀɢᴇs:</b> <code>{}</code>
🚫 <b>ғɪʟᴛᴇʀᴇᴅ ᴍᴇssᴀɢᴇs:</b> <code>{}</code>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚡️ <b>sᴛᴀᴛᴜs:</b> <code>{}</code>
📊 <b>ᴘʀᴏɢʀᴇss:</b> <code>{}%</code>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
<blockquote><b>{}</b></blockquote>"""

  DUPLICATE_TEXT = """<blockquote><b>♻️ <u>sᴋɪɴᴇᴛ ᴠᴇʀsᴇ — ᴜɴᴇǫᴜɪғʏ sᴛᴀᴛᴜs</u></b></blockquote>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📥 <b>ғᴇᴛᴄʜᴇᴅ ғɪʟᴇs:</b> <code>{}</code>
🗑 <b>ᴅᴜᴘʟɪᴄᴀᴛᴇ ᴅᴇʟᴇᴛᴇᴅ:</b> <code>{}</code>
⚡️ <b>sᴛᴀᴛᴜs:</b> <code>{}</code>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""

  DOUBLE_CHECK = """<blockquote><b>📋 <u>ғᴏʀᴡᴀʀᴅ ᴛᴀsᴋ ᴠᴇʀɪғɪᴄᴀᴛɪᴏɴ</u></b></blockquote>

<b>Review the task configuration before initiating migration:</b>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🤖 <b>Active Worker:</b> <code>{botname}</code>
📥 <b>Source Chat:</b> <code>{from_chat}</code>
📤 <b>Target Chat:</b> <code>{to_chat}</code>
⏩ <b>Skip Offset:</b> <code>{skip} msgs</code>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚠️ <i><b>Verification Checklist:</b>
• <code>{botname}</code> must be an Admin with post permissions in Target Chat ({to_chat}).
• If Source Chat is private, your UserBot must be a joined member or Admin.</i>

👇 <b>Click "Yes, Proceed" below to start forwarding!</b>""" 

  TERMS_TXT = """<blockquote><b>📜 <u>ᴛᴇʀᴍs ᴏғ sᴇʀᴠɪᴄᴇ — sᴋɪɴᴇᴛ ᴠᴇʀsᴇ</u></b></blockquote>

<b>Last Updated: September 2026</b>

By accessing or using <b>Skinet Verse</b>, you agree to comply with and be bound by the following terms:

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
<b>1. Purpose & Permitted Use:</b>
• This bot is provided strictly for educational, personal data migration, and authorized channel backup purposes.
• You must own or have explicit authorization from the channel administrators to migrate, clone, or mirror content.

<b>2. Prohibited Activities:</b>
• Unauthorized distribution of copyrighted media, intellectual property without rights, or proprietary paywalled content.
• Transmission of illicit material, malicious software, spam, mass unauthorized advertising, or content violating Telegram ToS.
• Attempting to reverse engineer, disrupt, or exploit the service infrastructure.

<b>3. Fair Usage & System Stability:</b>
• Strict rate-limiting and anti-flood delay mechanisms are enforced to maintain Telegram MTProto API compliance.
• Abusive automated requests or bypass attempts may result in permanent access revocation.

<b>4. Disclaimer of Warranty:</b>
• The service is provided on an <i>"as is"</i> and <i>"as available"</i> basis without warranties of any kind.
• Operators assume zero legal liability for user-transferred content or channel administrative actions.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<i>💡 Need help or clarification? Contact support or our administration team.</i>"""

  PRIVACY_TXT = """<blockquote><b>🔒 <u>ᴘʀɪᴠᴀᴄʏ ᴘᴏʟɪᴄʏ — sᴋɪɴᴇᴛ ᴠᴇʀsᴇ</u></b></blockquote>

<b>Last Updated: September 2026</b>

Your privacy, data confidentiality, and account security are our highest architectural priorities.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
<b>1. Zero Content Storage:</b>
• <b>We do not store your forwarded files or media.</b> All media streams transit transiently in-memory directly through official Telegram MTProto endpoints.
• No video, audio, document, or media files ever touch our physical server disks.

<b>2. Session & Credential Security:</b>
• UserBot session strings and Bot tokens are encrypted and isolated within secured MongoDB collections.
• Credentials are used solely to execute forward/autosave tasks initiated by you.
• You can delete your credentials anytime via <code>/settings</code> or <code>/reset</code>.

<b>3. Diagnostics & Telemetry:</b>
• Error diagnostics and task counters (message IDs, success/failure counts) are recorded to facilitate crash recovery and auto-resume.
• System log channels record anonymous event telemetry to troubleshoot Telegram FloodWaits.

<b>4. No Third-Party Sharing:</b>
• We never sell, lease, disclose, or share your Telegram identity, channels, or personal data with any third parties or advertisers.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<i>💡 You retain full sovereignty over your data and can reset your account at any moment.</i>"""

  RESTART_TXT = """<blockquote><b>🔄 <u>sᴋɪɴᴇᴛ ᴠᴇʀsᴇ — sʏsᴛᴇᴍ ʀᴇʙᴏᴏᴛ</u></b></blockquote>

⚡ <i>Rebooting core engine and reloading all configurations...</i>

⏳ <b>Status:</b> <code>Restarting... (5-10s)</code>
👤 <b>Initiated By:</b> <code>{}</code>
⏰ <b>Timestamp:</b> <code>{} IST</code>"""

  RESTARTED_TXT = """<blockquote><b>🤖 <u>sᴋɪɴᴇᴛ ᴠᴇʀsᴇ — ʙᴏᴛ ʜᴀs ʀᴇsᴛᴀʀᴛᴇᴅ!</u></b></blockquote>

✅ <i>System rebooted successfully and all core services are online!</i>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🤖 <b>Bot:</b> @{} (<code>{}</code>)
🚀 <b>Status:</b> <code>Online & Ready ✅</code>
⏰ <b>Time:</b> <code>{} IST</code>
⚡ <b>Engine:</b> <code>Skinet Verse v2.5 Ultra Edition</code>
📚 <b>Pyrogram:</b> <code>v{}</code> | 🐍 <b>Python:</b> <code>v{}</code>
🛡 <b>Database:</b> <code>MongoDB Connected & Operational</code>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
<i>⚡ Powered by Skinet Verse Official</i>"""


# ── Universal Small Caps Post-Processor ──────────────────────────────
from font_styler import to_small_caps

for _attr, _val in list(Translation.__dict__.items()):
    if isinstance(_val, str) and not _attr.startswith("__"):
        setattr(Translation, _attr, to_small_caps(_val))