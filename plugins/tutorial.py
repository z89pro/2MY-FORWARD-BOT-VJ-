import os
from pyrogram import Client, filters, enums
from pyrogram.types import InlineKeyboardButton, CallbackQuery, Message
from buttons import StyledMarkup as InlineKeyboardMarkup, btn, btn_url, row, markup, colored_markup

TUTORIAL_MODULES = {
    1: {
        "title": "🚀 1. ʙᴏᴛ ᴏᴠᴇʀᴠɪᴇᴡ & /start",
        "short": "ʙᴏᴛ ᴏᴠᴇʀᴠɪᴇᴡ",
        "text": (
            "<b><u>📚 MODULE 1: BOT OVERVIEW & GETTING STARTED</u></b>\n\n"
            "Welcome to <b>Skinet Verse Forward Bot</b> — an ultra-fast channel cloning, content migration, and automated distribution suite designed for Telegram channels and course creators!\n\n"
            "<b>🎯 Core Capabilities:</b>\n"
            "• <b>Full Channel Forwarding:</b> Copy thousands of lectures, videos, and PDFs with blazing speed.\n"
            "• <b>Smart AutoSave:</b> Monitor private & public channels and auto-forward new posts 24/7 in real-time.\n"
            "• <b>Course Seller Mode ⚡️:</b> Auto-number lectures, strip competitor tags, and build an automated syllabus table of contents.\n"
            "• <b>Skinet Modifier:</b> Remove and replace competitor usernames, links, and hidden hyperlinks.\n"
            "• <b>Anti-Ban Engine:</b> Human-like delay jitter and dynamic FloodWait absorption.\n\n"
            "<b>⚡ Essential Commands:</b>\n"
            "• <code>/start</code> - Activate and initialize your bot account.\n"
            "• <code>/settings</code> - Configure bots, channels, captions, and speed.\n"
            "• <code>/forward</code> - Interactive step-by-step forwarding wizard.\n"
            "• <code>/fwd &lt;link1&gt; &lt;link2&gt;</code> - Fast direct range forwarder.\n"
            "• <code>/autosave</code> - Real-time channel monitoring engine.\n"
            "• <code>/tutorial</code> - Access this comprehensive tutorial hub anytime!"
        ),
        "action_btn": InlineKeyboardButton("⚙️ ᴏᴘᴇɴ sᴇᴛᴛɪɴɢs", callback_data="settings#main")
    },
    2: {
        "title": "🤖 2. ʙᴏᴛғᴀᴛʜᴇʀ ᴛᴏᴋᴇɴ & sᴇᴛᴜᴘ",
        "short": "ʙᴏᴛғᴀᴛʜᴇʀ sᴇᴛᴜᴘ",
        "text": (
            "<b><u>📚 MODULE 2: BOTFATHER TOKEN & BOT SETUP</u></b>\n\n"
            "Before forwarding messages, you must connect a Telegram Bot to perform the heavy lifting on your behalf.\n\n"
            "<b>🛠 Step-by-Step Setup:</b>\n"
            "<b>1.</b> Open Telegram and search for <b>@BotFather</b>.\n"
            "<b>2.</b> Send <code>/newbot</code> and follow the prompts:\n"
            "   • Enter a name for your bot (e.g., <i>My Forwarder</i>).\n"
            "   • Choose a username ending in <code>bot</code> (e.g., <code>my_forwarder_xbot</code>).\n"
            "<b>3.</b> BotFather will give you an <b>HTTP API Token</b>:\n"
            "   • Example: <code>1234567890:AAHxxxxxx...</code>\n"
            "<b>4.</b> Open this bot and run <code>/settings</code>.\n"
            "<b>5.</b> Click on <b>🤖 ʙᴏᴛs</b> ➔ <b>✚ ᴀᴅᴅ ʙᴏᴛ ✚</b>.\n"
            "<b>6.</b> Paste or forward the BotFather token message to this bot.\n\n"
            "✅ <i>Once added, your bot is verified and ready to forward messages!</i>"
        ),
        "action_btn": InlineKeyboardButton("🤖 ᴍᴀɴᴀɢᴇ ʙᴏᴛs", callback_data="settings#bots")
    },
    3: {
        "title": "🏷 3. ᴛᴀʀɢᴇᴛ ᴄʜᴀɴɴᴇʟ sᴇᴛᴜᴘ",
        "short": "ᴛᴀʀɢᴇᴛ ᴄʜᴀɴɴᴇʟs",
        "text": (
            "<b><u>📚 MODULE 3: TARGET CHANNEL CONFIGURATION</u></b>\n\n"
            "Your <b>Target Channel</b> is where all forwarded files, videos, and course materials will be delivered.\n\n"
            "<b>🛠 How to Configure:</b>\n"
            "<b>1.</b> Create a new Telegram Channel (or open an existing one).\n"
            "<b>2.</b> Add your helper bot (from Module 2) to your target channel as an <b>Administrator</b>.\n"
            "   <i>Ensure it has 'Post Messages' & 'Edit Messages' privileges.</i>\n"
            "<b>3.</b> Open this bot, type <code>/settings</code> and tap <b>🏷 ᴄʜᴀɴɴᴇʟs</b>.\n"
            "<b>4.</b> Tap <b>✚ ᴀᴅᴅ ᴄʜᴀɴɴᴇʟ ✚</b>.\n"
            "<b>5.</b> Forward any message from your target channel to this bot, or enter the Channel ID (e.g., <code>-1001987654321</code>).\n\n"
            "💡 <i>Tip: You can add multiple target channels and switch between them whenever you start a forward task!</i>"
        ),
        "action_btn": InlineKeyboardButton("🏷 ᴍᴀɴᴀɢᴇ ᴄʜᴀɴɴᴇʟs", callback_data="settings#channels")
    },
    4: {
        "title": "⏩ 4. ғᴏʀᴡᴀʀᴅɪɴɢ (/forward & /fwd)",
        "short": "ғᴏʀᴡᴀʀᴅ & /fwd",
        "text": (
            "<b><u>📚 MODULE 4: FORWARDING ENGINE (/forward & /fwd)</u></b>\n\n"
            "The bot provides two flexible ways to copy and migrate channel content:\n\n"
            "<b>Method A: Interactive Wizard (<code>/forward</code>)</b>\n"
            "• Type <code>/forward</code> in the bot chat.\n"
            "• Forward the last message or send a message link from the source channel.\n"
            "• Select your target channel from the interactive inline buttons.\n"
            "• Set the number of messages to skip (send <code>0</code> for none).\n"
            "• The bot begins forwarding with real-time status, ETA, and Pause/Resume controls!\n\n"
            "<b>Method B: Instant Direct Range (<code>/fwd</code>)</b>\n"
            "• Forward an exact range of messages in one swift command:\n"
            "  <code>/fwd &lt;start_link&gt; &lt;end_link&gt;</code>\n"
            "• <b>Example:</b>\n"
            "  <code>/fwd https://t.me/c/12345/10 https://t.me/c/12345/150</code>\n"
            "• Starts immediately without asking interactive questions!"
        ),
        "action_btn": InlineKeyboardButton("⚙️ ғᴏʀᴡᴀʀᴅ sᴇᴛᴛɪɴɢs", callback_data="settings#main")
    },
    5: {
        "title": "💎 5. ғʀᴇᴇ ᴠs ᴘʀᴏ ᴛɪᴇʀ ғᴇᴀᴛᴜʀᴇs",
        "short": "ғʀᴇᴇ ᴠs ᴘʀᴏ ᴛɪᴇʀs",
        "text": (
            "<b><u>📚 MODULE 5: FREE vs PRO TIER COMPARISON</u></b>\n\n"
            "Choose the power level that fits your workflow:\n\n"
            "<b>🆓 FREE TIER:</b>\n"
            "• Standard forwarding speed (3s - 5s safe delay)\n"
            "• 1 Connected Target Channel\n"
            "• Basic Media Filters (Videos, Documents)\n"
            "• Standard Caption formatting\n\n"
            "<b>⚡ PRO / ULTRA TIER (Skinet Verse):</b>\n"
            "• 🚀 <b>Extreme Speed Mode:</b> 0.2s - 0.5s ultra-fast burst transfer\n"
            "• 🎓 <b>Course Seller Mode ⚡️:</b> Auto lecture numbering + Index Table of Contents\n"
            "• 🛠 <b>Skinet Modifier:</b> Username & Link Replacer + Hidden Link Sanitizer\n"
            "• 🔄 <b>Smart AutoSave:</b> Real-time channel monitoring & automatic forwarding\n"
            "• 👤 <b>UserBot Integration:</b> Clone from private/restricted channels\n"
            "• 📦 <b>Unlimited Channels & Batch Size:</b> Zero throttling and multi-admin support"
        ),
        "action_btn": InlineKeyboardButton("🎓 ᴄᴏᴜʀsᴇ sᴇʟʟᴇʀ ᴍᴏᴅᴇ", callback_data="settings#courseseller")
    },
    6: {
        "title": "🖋 6. ᴄᴜsᴛᴏᴍ ᴄᴀᴘᴛɪᴏɴ sᴇᴛᴛɪɴɢs",
        "short": "ᴄᴜsᴛᴏᴍ ᴄᴀᴘᴛɪᴏɴs",
        "text": (
            "<b><u>📚 MODULE 6: CUSTOM CAPTION ENGINE</u></b>\n\n"
            "Transform message captions automatically to feature your own branding, links, and styling!\n\n"
            "<b>🛠 How to Configure:</b>\n"
            "<b>1.</b> Run <code>/settings</code> and tap <b>🖋️ ᴄᴀᴘᴛɪᴏɴ</b>.\n"
            "<b>2.</b> Tap <b>✏️ sᴇᴛ ᴄᴀᴘᴛɪᴏɴ</b> to enter your template.\n\n"
            "<b>Dynamic Placeholders:</b>\n"
            "• <code>{filename}</code> - Original name of the document or video.\n"
            "• <code>{size}</code> - Human-readable file size (e.g., <code>150.4 MB</code>).\n"
            "• <code>{duration}</code> - Video or audio duration (e.g., <code>45m 12s</code>).\n\n"
            "<b>📝 Sample Template:</b>\n"
            "<code>🎬 &lt;b&gt;{filename}&lt;/b&gt;\n"
            "📦 Size: {size} | ⏳ {duration}\n\n"
            "🌟 &lt;i&gt;Uploaded by Skinet Verse&lt;/i&gt;</code>\n\n"
            "💡 <i>Enable 'Clean Caption' to wipe competitor headers/footers before applying your custom format!</i>"
        ),
        "action_btn": InlineKeyboardButton("🖋️ sᴇᴛ ᴄᴀᴘᴛɪᴏɴ", callback_data="settings#caption")
    },
    7: {
        "title": "🕵 7. ᴍᴇᴅɪᴀ ғɪʟᴛᴇʀ ᴛᴏɢɢʟᴇs",
        "short": "ᴍᴇᴅɪᴀ ғɪʟᴛᴇʀs",
        "text": (
            "<b><u>📚 MODULE 7: SMART MEDIA FILTERS</u></b>\n\n"
            "Never clutter your target channel with unwanted spam, stickers, or filler text!\n\n"
            "<b>🛠 Configurable Filters:</b>\n"
            "• 🎥 <b>Videos:</b> Lecture videos, webinars, tutorial recordings.\n"
            "• 📁 <b>Documents:</b> PDF notes, slides, code zips, assignments.\n"
            "• 🖼 <b>Photos:</b> Diagrams, mind maps, formula sheets.\n"
            "• 🎵 <b>Audios:</b> Podcasts, audio lectures, voice notes.\n"
            "• 💬 <b>Text:</b> Announcements, syllabus breakdowns, chat messages.\n"
            "• 🎞 <b>Animations:</b> GIFs and motion previews.\n\n"
            "<b>⚙️ How to Toggle:</b>\n"
            "Go to <code>/settings</code> ➔ <b>🕵‍♀ ғɪʟᴛᴇʀs 🕵‍♀</b> and toggle each media type ON/OFF with a single tap!"
        ),
        "action_btn": InlineKeyboardButton("🕵‍♀ ᴍᴀɴᴀɢᴇ ғɪʟᴛᴇʀs", callback_data="settings#filters")
    },
    8: {
        "title": "⚡️ 8. ᴀᴜᴛᴏ-ғᴏʀᴡᴀʀᴅɪɴɢ (ᴀᴜᴛᴏsᴀᴠᴇ)",
        "short": "sᴍᴀʀᴛ ᴀᴜᴛᴏsᴀᴠᴇ",
        "text": (
            "<b><u>📚 MODULE 8: SMART AUTOSAVE (AUTO-FORWARDING)</u></b>\n\n"
            "Tired of running manual forward commands every time a teacher drops a new lecture? <b>Smart AutoSave</b> monitors channels 24/7!\n\n"
            "<b>🌟 How It Works:</b>\n"
            "<b>1.</b> Type <code>/autosave</code> to launch the AutoSave Control Panel.\n"
            "<b>2.</b> Add source channels to your monitored list.\n"
            "<b>3.</b> Set specific target destinations or use your global target.\n"
            "<b>4.</b> Whenever the source channel posts a new file, video, or note:\n"
            "   • The bot captures the message in real-time.\n"
            "   • Applies your Skinet Modifier filters, cleans links, replaces usernames.\n"
            "   • Automatically pushes the cleaned post to your target channel!\n\n"
            "⚡️ <i>Runs seamlessly in the background with zero battery or CPU drain on your device!</i>"
        ),
        "action_btn": InlineKeyboardButton("🚀 ʟᴀᴜɴᴄʜ ᴀᴜᴛᴏsᴀᴠᴇ", callback_data="autosave#main")
    },
    9: {
        "title": "💧 9. ᴡᴀᴛᴇʀᴍᴀʀᴋs & ʙʀᴀɴᴅɪɴɢ",
        "short": "ᴡᴀᴛᴇʀᴍᴀʀᴋs & ʙʀᴀɴᴅ",
        "text": (
            "<b><u>📚 MODULE 9: WATERMARK SANITIZATION & BRANDING</u></b>\n\n"
            "Establish your own brand identity and eliminate competitor watermarks from forwarded materials:\n\n"
            "<b>🛡 Clean Forward Standard:</b>\n"
            "• <b>Remove 'Forwarded From' Tag:</b> Turn off forward tags so messages appear as original native uploads posted directly by you.\n"
            "• <b>Custom Header & Footer Watermarks:</b> Embed your channel link or brand signature on every video and document caption.\n"
            "• <b>Upload Type Cycling:</b> Convert raw media files into standard Streamable Videos or pure Documents via <b>🛠 sᴋɪɴᴇᴛ ᴍᴏᴅɪғɪᴇʀ ➔ 📦 ᴜᴘʟᴏᴀᴅ ᴛʏᴘᴇ</b>.\n\n"
            "💡 <i>Combine with Skinet Username Replacer for 100% white-label course distribution!</i>"
        ),
        "action_btn": InlineKeyboardButton("🛠 sᴋɪɴᴇᴛ ᴍᴏᴅɪғɪᴇʀ", callback_data="settings#ftm")
    },
    10: {
        "title": "🛠 10. sᴋɪɴᴇᴛ ʀᴇᴘʟᴀᴄᴇʀs & ʀᴇᴍᴏᴠᴇʀs",
        "short": "sᴋɪɴᴇᴛ ʀᴇᴘʟᴀᴄᴇʀ ɢᴜɪᴅᴇ",
        "text": (
            "<b><u>📚 MODULE 10: SKINET REMOVERS & REPLACERS (STEP-BY-STEP)</u></b>\n\n"
            "<b>Skinet Text & Media Modifier (Powered by Skinet Verse)</b> gives you complete control over competitor text, links, and tags.\n\n"
            "<b>1️⃣ Competitor Username Remover:</b>\n"
            "• Go to <code>/settings</code> ➔ <b>🛠 sᴋɪɴᴇᴛ ᴍᴏᴅɪғɪᴇʀ</b> ➔ Tap <b>👤 ᴜsᴇʀɴᴀᴍᴇ: [ON/OFF]</b>.\n"
            "• Automatically wipes all <code>@username</code> mentions from captions.\n\n"
            "<b>2️⃣ Competitor Username Replacer:</b>\n"
            "• Tap <b>✏️ sᴇᴛ ᴜsᴇʀɴᴀᴍᴇ ʀᴇᴘʟᴀᴄᴇʀ</b>.\n"
            "• Send your handle: <code>@SkinetVerse</code>\n"
            "• Any competitor handle like <code>@OtherSeller</code> is instantly converted to <code>@SkinetVerse</code>!\n\n"
            "<b>3️⃣ External Link Remover:</b>\n"
            "• Tap <b>🔗 ʟɪɴᴋs: [ON/OFF]</b> to eliminate all <code>t.me/...</code> and web URLs.\n\n"
            "<b>4️⃣ Link Replacer:</b>\n"
            "• Tap <b>✏️ sᴇᴛ ʟɪɴᴋ ʀᴇᴘʟᴀᴄᴇʀ</b>.\n"
            "• Send your channel link: <code>https://t.me/SkinetVerse</code>\n"
            "• Automatically redirects all external links in captions to your channel!\n\n"
            "<b>5️⃣ Hidden Link Sanitizer:</b>\n"
            "• Strips sneaky embedded links like <code>[Click Here](https://competitor.com)</code> or <code>&lt;a href='...'&gt;</code>.\n\n"
            "<b>6️⃣ Custom Word Replacements:</b>\n"
            "• Tap <b>🔤 ᴀᴅᴅ ᴡᴏʀᴅ ʀᴇᴘʟᴀᴄᴇᴍᴇɴᴛ</b>.\n"
            "• Send rule as <code>old_word:new_word</code> (e.g. <code>PW:SkinetVerse</code>)."
        ),
        "action_btn": InlineKeyboardButton("🛠 ᴏᴘᴇɴ sᴋɪɴᴇᴛ ᴍᴏᴅɪғɪᴇʀ", callback_data="settings#ftm")
    },
    11: {
        "title": "🔢 11. ᴀʟᴘʜᴀ ᴍᴏᴅᴇ & sᴋɪᴘ ᴍᴇssᴀɢᴇs",
        "short": "ᴀʟᴘʜᴀ & sᴋɪᴘ",
        "text": (
            "<b><u>📚 MODULE 11: MESSAGE SKIPPING & PARTIAL FORWARDS</u></b>\n\n"
            "Need to resume a forward task or skip promotional messages at the beginning of a channel?\n\n"
            "<b>🔢 How Skip Messages Works:</b>\n"
            "• When launching <code>/forward</code>, the bot prompts:\n"
            "  <i>'sᴇᴛ ɴᴏ. ᴏғ ᴍᴇssᴀɢᴇs ᴛᴏ sᴋɪᴘ'</i>\n"
            "• If you enter <code>0</code>, forwarding starts from the very beginning.\n"
            "• If you enter <code>50</code>, the first 50 messages are skipped, and the bot begins copying from message 51!\n\n"
            "<b>🎯 Practical Use Cases:</b>\n"
            "• <b>Resume Interrupted Tasks:</b> If 100 lectures were copied earlier, enter <code>100</code> to continue seamlessly.\n"
            "• <b>Bypass Intro Ads:</b> Skip intro advertisements and welcome messages.\n"
            "• <b>Direct Range Alternative:</b> Use <code>/fwd &lt;link_51&gt; &lt;link_200&gt;</code> for exact boundary targeting."
        ),
        "action_btn": InlineKeyboardButton("⚙️ sᴘᴇᴇᴅ sᴇᴛᴛɪɴɢs", callback_data="settings#speed")
    },
    12: {
        "title": "👤 12. ᴜsᴇʀʙᴏᴛ ᴘʀɪᴠᴀᴛᴇ ᴄʜᴀɴɴᴇʟ ʟᴏɢɪɴ",
        "short": "ᴜsᴇʀʙᴏᴛ ᴘʀɪᴠᴀᴛᴇ ʟᴏɢɪɴ",
        "text": (
            "<b><u>📚 MODULE 12: USERBOT PRIVATE CHANNEL LOGIN</u></b>\n\n"
            "Normal Telegram bots cannot see or join private channels unless invited as admin. A <b>UserBot</b> allows forwarding from ANY channel you have access to!\n\n"
            "<b>🔐 How to Login Your UserBot:</b>\n"
            "<b>1.</b> Run <code>/settings</code> ➔ <b>🤖 ʙᴏᴛs</b>.\n"
            "<b>2.</b> Tap <b>✚ ʟᴏɢɪɴ ᴜsᴇʀ ʙᴏᴛ ✚</b>.\n"
            "<b>3.</b> Enter your phone number with country code (e.g. <code>+919876543210</code>).\n"
            "<b>4.</b> Check your Telegram app for the official login code and send it (with spaces between digits, e.g. <code>1 2 3 4 5</code>).\n"
            "<b>5.</b> If you have 2-Factor Authentication enabled, enter your password when prompted.\n\n"
            "🛡 <b>Privacy & Security:</b>\n"
            "• Your session runs securely in-memory and is never shared.\n"
            "• You can forward from any restricted or private channel seamlessly!"
        ),
        "action_btn": InlineKeyboardButton("🤖 ᴜsᴇʀʙᴏᴛ sᴇᴛᴜᴘ", callback_data="settings#bots")
    }
}

def tutorial_menu_keyboard():
    buttons = []
    keys = list(TUTORIAL_MODULES.keys())
    for i in range(0, len(keys), 2):
        row = [
            InlineKeyboardButton(TUTORIAL_MODULES[keys[i]]["title"], callback_data=f"tutorial#mod_{keys[i]}")
        ]
        if i + 1 < len(keys):
            row.append(
                InlineKeyboardButton(TUTORIAL_MODULES[keys[i+1]]["title"], callback_data=f"tutorial#mod_{keys[i+1]}")
            )
        buttons.append(row)
    
    buttons.append([
        InlineKeyboardButton("🎓 ᴄᴏᴜʀsᴇ sᴇʟʟᴇʀ ⚡️", callback_data="settings#courseseller"),
        InlineKeyboardButton("🛠 sᴋɪɴᴇᴛ ᴍᴏᴅɪғɪᴇʀ 🛠", callback_data="settings#ftm")
    ])
    buttons.append([
        InlineKeyboardButton("• ʙᴀᴄᴋ ᴛᴏ ᴍᴀɪɴ", callback_data="back"),
        InlineKeyboardButton("❌ ᴄʟᴏsᴇ", callback_data="close_btn")
    ])
    return InlineKeyboardMarkup(buttons)

def tutorial_page_keyboard(mod_id: int):
    nav_row = []
    if mod_id > 1:
        nav_row.append(InlineKeyboardButton("⬅️ ᴘʀᴇᴠɪᴏᴜs", callback_data=f"tutorial#mod_{mod_id - 1}"))
    nav_row.append(InlineKeyboardButton("📚 ᴀʟʟ ᴛᴏᴘɪᴄs", callback_data="tutorial#menu"))
    if mod_id < len(TUTORIAL_MODULES):
        nav_row.append(InlineKeyboardButton("ɴᴇxᴛ ➡️", callback_data=f"tutorial#mod_{mod_id + 1}"))
    
    buttons = [nav_row]
    action = TUTORIAL_MODULES[mod_id].get("action_btn")
    if action:
        buttons.append([action])
    buttons.append([
        InlineKeyboardButton("• ʙᴀᴄᴋ ᴛᴏ ᴍᴇɴᴜ", callback_data="back"),
        InlineKeyboardButton("❌ ᴄʟᴏsᴇ", callback_data="close_btn")
    ])
    return InlineKeyboardMarkup(buttons)


#===================Commands===================#

@Client.on_message(filters.private & filters.command(['tutorial', 'guide']))
async def tutorial_cmd(client: Client, message: Message):
    text = (
        "<blockquote><b>📚 <u>sᴋɪɴᴇᴛ ᴠᴇʀsᴇ ᴍᴀsᴛᴇʀ ᴛᴜᴛᴏʀɪᴀʟ ʜᴜʙ</u></b></blockquote>\n\n"
        "Welcome to the official interactive knowledge base for <b>Skinet Verse Forward Bot</b>.\n"
        "Master channel cloning, Skinet text & media sanitization, course automation, and private channel forwarding!\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "👇 <b>Select any module below to start learning:</b>"
    )
    await message.reply_text(
        text,
        reply_markup=tutorial_menu_keyboard(),
        disable_web_page_preview=True,
        quote=True
    )

@Client.on_message(filters.private & filters.command(['skinet', 'modifier', 'ftm']))
async def ftm_cmd(client: Client, message: Message):
    mod = TUTORIAL_MODULES[10]
    await message.reply_text(
        mod["text"],
        reply_markup=tutorial_page_keyboard(10),
        disable_web_page_preview=True,
        quote=True
    )

@Client.on_message(filters.command(['courseseller', 'seller', 'course', 'courses']))
async def seller_cmd(client: Client, message: Message):
    from plugins.settings import course_seller_text, course_seller_buttons
    from plugins.test import get_configs
    user_id = message.from_user.id if message.from_user else message.chat.id
    configs = await get_configs(user_id)
    await message.reply_text(
        course_seller_text(configs),
        reply_markup=course_seller_buttons(configs),
        quote=True
    )


#===================Callback Queries===================#

@Client.on_callback_query(filters.regex(r'^tutorial'))
async def tutorial_callback(bot: Client, query: CallbackQuery):
    data = query.data.split("#")
    action = data[1] if len(data) > 1 else "menu"

    if action == "menu":
        text = (
            "<blockquote><b>📚 <u>sᴋɪɴᴇᴛ ᴠᴇʀsᴇ ᴍᴀsᴛᴇʀ ᴛᴜᴛᴏʀɪᴀʟ ʜᴜʙ</u></b></blockquote>\n\n"
            "Welcome to the official interactive knowledge base for <b>Skinet Verse Forward Bot</b>.\n"
            "Master channel cloning, Skinet text & media sanitization, course automation, and private channel forwarding!\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "👇 <b>Select any module below to start learning:</b>"
        )
        await query.message.edit_text(
            text,
            reply_markup=tutorial_menu_keyboard(),
            disable_web_page_preview=True
        )

    elif action.startswith("mod_"):
        try:
            mod_id = int(action.replace("mod_", ""))
        except ValueError:
            mod_id = 1
        
        mod_data = TUTORIAL_MODULES.get(mod_id, TUTORIAL_MODULES[1])
        await query.message.edit_text(
            mod_data["text"],
            reply_markup=tutorial_page_keyboard(mod_id),
            disable_web_page_preview=True
        )
