"""
plugins/verify.py
─────────────────
Next-Generation Cryptographic Token Verification & Shortener Monetization System
Integrated for Skinet Verse Ultra Forward Bot.

Features:
  1. Multi-Step Chains (1-Step, 2-Step, 3-Step)
  2. Cryptographic HMAC-SHA256 Token Binding (anti-tamper, anti-share, anti-replay)
  3. Single-Use Nonce Consumption & Purging
  4. Multi-Provider Shortener Integration (Shareus, AdLinkFly, Droplink, GP Links, etc.)
  5. Fallback Resiliency (Direct Telegram deep-link if shortener API fails)
  6. Admin Dynamic Runtime Configuration (/setverify)
  7. High-Aesthetic ZSRCBOT / Skinet Verse Blockquote UI
  8. Admin Bypass & Referral VIP Pass Integration
"""

import hashlib
import hmac
import html
import logging
import secrets
import time
from datetime import datetime, timedelta

import aiohttp
from pyrogram import Client, filters, enums
from pyrogram.types import InlineKeyboardButton, Message, CallbackQuery
from buttons import StyledMarkup as InlineKeyboardMarkup, btn, btn_url, row, markup, colored_markup

from config import Config
from database import db

logger = logging.getLogger(__name__)

# ── In-Memory Active Tokens ──────────────────────────────────────────
# { token: {"user_id": int, "step": int, "nonce": str, "created": float, "expires": float} }
_VERIFY_TOKENS: dict = {}

# ── In-Memory Verification Cache (user_id -> expires_timestamp) ─────
_VERIFIED_CACHE: dict = {}

# ── Rate Limiter (user_id -> [timestamps]) ──────────────────────────
_RATE_LIMIT: dict = {}
_RATE_LIMIT_MAX = 10         # max token generations per window
_RATE_LIMIT_WINDOW = 3600    # 1 hour

_PURGE_COUNTER = 0
_PURGE_INTERVAL = 30


def _purge_expired():
    """Prune expired tokens, stale cache records, and rate-limiting history."""
    global _PURGE_COUNTER
    _PURGE_COUNTER += 1
    if _PURGE_COUNTER < _PURGE_INTERVAL:
        return
    _PURGE_COUNTER = 0
    now = time.time()
    for tok in [k for k, v in _VERIFY_TOKENS.items() if v["expires"] < now]:
        _VERIFY_TOKENS.pop(tok, None)
    for uid in [k for k, v in _VERIFIED_CACHE.items() if v < now]:
        _VERIFIED_CACHE.pop(uid, None)
    cutoff = now - _RATE_LIMIT_WINDOW
    for uid in list(_RATE_LIMIT.keys()):
        _RATE_LIMIT[uid] = [t for t in _RATE_LIMIT[uid] if t > cutoff]
        if not _RATE_LIMIT[uid]:
            _RATE_LIMIT.pop(uid, None)


# ── Cryptographic Signature Engine ───────────────────────────────────

def _get_hmac_secret() -> bytes:
    key_material = f"SKINET_VERIFY_SIGNER:{Config.BOT_TOKEN}:{Config.API_HASH}"
    return hashlib.sha256(key_material.encode()).digest()


def _sign_token(user_id: int, step: int, nonce: str, timestamp: int) -> str:
    secret = _get_hmac_secret()
    payload = f"{user_id}:{step}:{nonce}:{timestamp}".encode()
    return hmac.new(secret, payload, hashlib.sha256).hexdigest()[:24]


def _verify_signature(user_id: int, step: int, nonce: str, timestamp: int, signature: str) -> bool:
    expected = _sign_token(user_id, step, nonce, timestamp)
    return hmac.compare_digest(expected, signature)


def _generate_step_token(user_id: int, step: int, timeout_mins: int) -> str:
    nonce = secrets.token_hex(6)
    timestamp = int(time.time())
    sig = _sign_token(user_id, step, nonce, timestamp)
    token = f"s{step}_{nonce}_{timestamp}_{sig}"

    _VERIFY_TOKENS[token] = {
        "user_id": user_id,
        "step": step,
        "nonce": nonce,
        "created": timestamp,
        "expires": timestamp + (timeout_mins * 60),
    }

    # Evict older tokens for the same user at this step
    for old_tok in [
        k for k, v in _VERIFY_TOKENS.items()
        if v["user_id"] == user_id and v["step"] == step and k != token
    ]:
        _VERIFY_TOKENS.pop(old_tok, None)

    _purge_expired()
    return token


# ── Shortener API Resolver ───────────────────────────────────────────

async def _call_shortener_api(domain: str, api_key: str, long_url: str) -> str | None:
    """Invokes third-party shortener API or returns None on failure."""
    if not domain or not api_key:
        return None

    clean_domain = domain.lower().replace("https://", "").replace("http://", "").rstrip("/")

    # 1. Shareus API format
    if "shareus" in clean_domain:
        endpoint = f"https://api.shareus.io/shortLink?token={api_key}&format=json&link={long_url}"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(endpoint, timeout=aiohttp.ClientTimeout(total=8)) as resp:
                    if resp.status == 200:
                        data = await resp.json(content_type=None)
                        if isinstance(data, dict):
                            return data.get("shortenedUrl") or data.get("shortLink") or data.get("link")
        except Exception as e:
            logger.debug(f"shareus call failed: {e}")
        return None

    # 2. Standard AdLinkFly / Instalinks / Generic Shortener APIs
    # Try different query parameter conventions used by various shortener scripts
    for param_name in ("api", "token", "api_key", "key"):
        endpoint = f"https://{clean_domain}/api?{param_name}={api_key}&url={long_url}"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(endpoint, timeout=aiohttp.ClientTimeout(total=8)) as resp:
                    if resp.status == 200:
                        try:
                            data = await resp.json(content_type=None)
                            if isinstance(data, dict):
                                res = (
                                    data.get("shortenedUrl")
                                    or data.get("shortLink")
                                    or data.get("short_url")
                                    or data.get("short")
                                    or data.get("result")
                                    or data.get("url")
                                    or data.get("shortlink")
                                )
                                if isinstance(res, str) and res.startswith("http"):
                                    return res
                                if isinstance(data.get("data"), dict):
                                    d_url = (
                                        data["data"].get("url")
                                        or data["data"].get("short_url")
                                        or data["data"].get("shortenedUrl")
                                    )
                                    if isinstance(d_url, str) and d_url.startswith("http"):
                                        return d_url
                        except Exception:
                            pass
                        text = (await resp.text()).strip()
                        if text.startswith("http://") or text.startswith("https://"):
                            return text
        except Exception as e:
            logger.debug(f"shortener {clean_domain} with param {param_name} failed: {e}")

    return None


async def _resolve_short_url(bot_username: str, token: str, step: int, cfg: dict) -> tuple[str, str]:
    """Resolves shortened URL or falls back to direct Telegram deep link."""
    deep_link = f"https://t.me/{bot_username}?start=vrf_{token}"

    shorteners = []
    if cfg.get("shortener_url") and cfg.get("shortener_api"):
        shorteners.append((cfg["shortener_url"], cfg["shortener_api"]))
    if cfg.get("shortener_url2") and cfg.get("shortener_api2"):
        shorteners.append((cfg["shortener_url2"], cfg["shortener_api2"]))
    if cfg.get("shortener_url3") and cfg.get("shortener_api3"):
        shorteners.append((cfg["shortener_url3"], cfg["shortener_api3"]))

    if not shorteners:
        return deep_link, "direct"

    # Select shortener according to step
    idx = (step - 1) % len(shorteners)
    domain, api_key = shorteners[idx]
    short_url = await _call_shortener_api(domain, api_key, deep_link)

    if short_url:
        return short_url, domain

    # Fallback to remaining shorteners
    for d, k in shorteners:
        if d == domain:
            continue
        short_url = await _call_shortener_api(d, k, deep_link)
        if short_url:
            return short_url, d

    # Ultimate fallback: direct link so user is never stuck
    return deep_link, "direct (fallback)"


# ── Gate Evaluation ──────────────────────────────────────────────────

async def is_user_verified(user_id: int) -> bool:
    """
    Returns True if user has active verification, VIP referral pass, or admin bypass.
    """
    # 1. Admin & Premium Bypass
    if await db.is_admin(user_id) or await db.is_premium_user(user_id):
        return True

    # 2. Config check
    cfg = await db.get_verify_config()
    if not cfg.get("enabled", True):
        return True

    # If verification is enabled but no shorteners or APIs are configured, pass freely
    has_shortener = bool(
        (cfg.get("shortener_url") and cfg.get("shortener_api"))
        or (cfg.get("shortener_url2") and cfg.get("shortener_api2"))
        or (cfg.get("shortener_url3") and cfg.get("shortener_api3"))
    )
    if not has_shortener:
        return True

    _purge_expired()
    now = time.time()

    # 3. In-memory fast cache
    cached = _VERIFIED_CACHE.get(user_id)
    if cached and cached > now:
        return True

    # 4. MongoDB user verification record
    try:
        expires = await db.get_user_verify_status(user_id)
        if expires and float(expires) > now:
            _VERIFIED_CACHE[user_id] = float(expires)
            return True
    except Exception:
        pass

    # 5. Referral VIP perk bypass
    try:
        ref_data = await db.get_referral_data(user_id)
        vip_until = ref_data.get("vip_until", 0)
        if vip_until and float(vip_until) > now:
            _VERIFIED_CACHE[user_id] = float(vip_until)
            return True
    except Exception:
        pass

    return False


def get_remaining_verify_time(user_id: int) -> int:
    """Returns seconds remaining for user verification, or 0 if expired."""
    now = time.time()
    cached = _VERIFIED_CACHE.get(user_id, 0)
    if cached > now:
        return int(cached - now)
    return 0


# ── UI Card Builders ─────────────────────────────────────────────────

def _build_progress_bar(step: int, total: int) -> str:
    filled = "🟩" * step
    empty = "⬜" * (total - step)
    return f"[{filled}{empty}] Step {step} of {total}"


def _build_verify_card(step: int, total_steps: int, duration_hours: int, domain: str, timeout_mins: int) -> str:
    progress = _build_progress_bar(step, total_steps)
    return (
        "<blockquote><b>🛡️ <u>sᴋɪɴᴇᴛ ᴠᴇʀsᴇ — ᴠᴇʀɪғɪᴄᴀᴛɪᴏɴ ʀᴇǫᴜɪʀᴇᴅ</u></b></blockquote>\n\n"
        "To maintain lightning transfer speeds and prevent automated flood abuse, "
        "please verify to unlock your <b>Free Unlimited Access Pass</b>!\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📊 <b>ᴘʀᴏɢʀᴇss:</b> <code>{progress}</code>\n"
        f"⏱️ <b>ᴘᴀss ᴠᴀʟɪᴅɪᴛʏ:</b> <code>{duration_hours} Hours</code>\n"
        f"🌐 <b>sʜᴏʀᴛᴇɴᴇʀ:</b> <code>{domain}</code>\n"
        f"⏳ <b>ʟɪɴᴋ ᴛɪᴍᴇᴏᴜᴛ:</b> <code>{timeout_mins} Minutes</code>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "👇 <i>Click the button below, complete the step in your browser, and you will be redirected back automatically!</i>"
    )


def _build_success_card(user_id: int, total_steps: int, duration_hours: int, expiry_str: str) -> str:
    return (
        "<blockquote><b>🎉 <u>ᴠᴇʀɪғɪᴄᴀᴛɪᴏɴ sᴜᴄᴄᴇssғᴜʟ!</u></b></blockquote>\n\n"
        f"<b>Congratulations! Your {duration_hours}-Hour Unlimited Pass is now active.</b>\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 <b>ᴜsᴇʀ ɪᴅ:</b> <code>{user_id}</code>\n"
        f"✅ <b>sᴛᴇᴘs ᴄᴏᴍᴘʟᴇᴛᴇᴅ:</b> <code>{total_steps}/{total_steps}</code>\n"
        f"⚡️ <b>sᴛᴀᴛᴜs:</b> <code>🟢 VIP Access Granted</code>\n"
        f"⏳ <b>ᴇxᴘɪʀᴇs ᴏɴ:</b> <code>{expiry_str}</code>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "🚀 <i>You can now use /forward, /fwd, /autosave, and all advanced features without limits!</i>"
    )


# ── Prompt Dispatcher ────────────────────────────────────────────────

async def send_verify_prompt(client: Client, message: Message, user_id: int, step: int = 1):
    """Generates token and presents the verification card with interactive buttons."""
    # Rate limiting
    now = time.time()
    user_hits = [t for t in _RATE_LIMIT.get(user_id, []) if t > now - _RATE_LIMIT_WINDOW]
    if len(user_hits) >= _RATE_LIMIT_MAX:
        await message.reply_text(
            "<blockquote><b>⚠️ <u>ᴠᴇʀɪғɪᴄᴀᴛɪᴏɴ ʀᴀᴛᴇ ʟɪᴍɪᴛ</u></b></blockquote>\n\n"
            "You have generated too many verification links recently. Please wait a few minutes before trying again."
        )
        return
    user_hits.append(now)
    _RATE_LIMIT[user_id] = user_hits

    cfg = await db.get_verify_config()
    total_steps = max(1, cfg.get("steps", 1))
    step = min(max(1, step), total_steps)
    timeout = cfg.get("timeout", 30)
    duration = cfg.get("duration", 24)

    token = _generate_step_token(user_id, step, timeout)
    bot_user = await client.get_me()
    short_url, domain = await _resolve_short_url(bot_user.username, token, step, cfg)

    card = _build_verify_card(step, total_steps, duration, domain, timeout)

    step_btn_text = f"⚡ ᴠᴇʀɪғʏ sᴛᴇᴘ {step} ⚡" if total_steps > 1 else "⚡ ᴠᴇʀɪғʏ ɴᴏᴡ ⚡"
    keyboard = [
        [InlineKeyboardButton(step_btn_text, url=short_url)],
    ]
    if cfg.get("tutorial"):
        keyboard.append([InlineKeyboardButton("❓ ʜᴏᴡ ᴛᴏ ᴠᴇʀɪғʏ (ᴛᴜᴛᴏʀɪᴀʟ)", url=cfg["tutorial"])])
    
    keyboard.append([
        InlineKeyboardButton("🎁 ʀᴇғᴇʀ & ᴇᴀʀɴ ғʀᴇᴇ ᴘᴀss", callback_data="referral#main"),
        InlineKeyboardButton("🔄 ᴄʜᴇᴄᴋ sᴛᴀᴛᴜs", callback_data=f"verify#check_{user_id}")
    ])

    await message.reply_text(
        card,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=enums.ParseMode.HTML,
        disable_web_page_preview=True
    )


# ── Callback Handler (/start vrf_<token>) ────────────────────────────

async def handle_verify_callback(client: Client, message: Message, raw_token: str) -> bool:
    """Validates verification callback token from /start vrf_<token>."""
    cfg = await db.get_verify_config()

    token = raw_token
    for pfx in ("vrf_", "verify_"):
        if token.startswith(pfx):
            token = token[len(pfx):]
            break

    user_id = message.from_user.id if message.from_user else 0
    if not user_id:
        return False

    # Token structure: s{step}_{nonce}_{timestamp}_{sig}
    parts = token.split("_")
    if len(parts) != 4 or not parts[0].startswith("s"):
        await message.reply_text(
            "<blockquote><b>❌ <u>ɪɴᴠᴀʟɪᴅ ᴛᴏᴋᴇɴ ғᴏʀᴍᴀᴛ</u></b></blockquote>\n\n"
            "The verification link appears malformed or expired. Please generate a fresh link using /verify."
        )
        return False

    try:
        step = int(parts[0][1:])
        nonce = parts[1]
        timestamp = int(parts[2])
        sig = parts[3]
    except Exception:
        await message.reply_text("<b>❌ Invalid token structure. Please use /verify.</b>")
        return False

    # HMAC Signature Integrity Check
    if not _verify_signature(user_id, step, nonce, timestamp, sig):
        logger.warning(f"Verify HMAC forged or signature mismatch for UID {user_id}")
        await message.reply_text(
            "<blockquote><b>🚫 <u>ᴛᴏᴋᴇɴ ᴠᴇʀɪғɪᴄᴀᴛɪᴏɴ ғᴀɪʟᴇᴅ</u></b></blockquote>\n\n"
            "This link was signed for a different account or has been tampered with. Links cannot be shared across users."
        )
        return False

    # In-memory single-use token consumption
    tok_data = _VERIFY_TOKENS.get(token)
    if not tok_data:
        await message.reply_text(
            "<blockquote><b>⚠️ <u>ʟɪɴᴋ ᴇxᴘɪʀᴇᴅ ᴏʀ ᴀʟʀᴇᴀᴅʏ ᴜsᴇᴅ</u></b></blockquote>\n\n"
            "This verification link has already been consumed or timed out. Send /verify to get a new one."
        )
        return False

    if tok_data["user_id"] != user_id:
        await message.reply_text("<b>🚫 This verification link belongs to another user.</b>")
        return False

    if tok_data["expires"] < time.time():
        _VERIFY_TOKENS.pop(token, None)
        await message.reply_text("<b>⏳ This verification link has expired. Send /verify to generate a fresh link.</b>")
        return False

    # Consume token immediately (prevents replay)
    _VERIFY_TOKENS.pop(token, None)

    total_steps = max(1, cfg.get("steps", 1))

    # Multi-Step Chain Progression
    if step < total_steps:
        next_step = step + 1
        await message.reply_text(
            f"<blockquote><b>✅ <u>sᴛᴇᴘ {step}/{total_steps} ᴄᴏᴍᴘʟᴇᴛᴇᴅ!</u></b></blockquote>\n\n"
            f"Great job! Please complete the final <b>Step {next_step}</b> below to activate your pass."
        )
        await send_verify_prompt(client, message, user_id, step=next_step)
        return False

    # Final Step Complete! Grant Duration
    duration_hours = cfg.get("duration", 24)
    expires_at = time.time() + (duration_hours * 3600)

    await db.set_user_verify_status(user_id, expires_at)
    _VERIFIED_CACHE[user_id] = expires_at

    expiry_dt = datetime.now() + timedelta(hours=duration_hours)
    expiry_str = expiry_dt.strftime("%d %b %Y, %I:%M %p")

    card = _build_success_card(user_id, total_steps, duration_hours, expiry_str)
    start_btn = InlineKeyboardMarkup([
        [InlineKeyboardButton("🚀 sᴛᴀʀᴛ ғᴏʀᴡᴀʀᴅɪɴɢ", callback_data="settings#main")],
        [InlineKeyboardButton("🎁 ʀᴇғᴇʀ & ᴇᴀʀɴ", callback_data="referral#main")]
    ])
    await message.reply_text(card, reply_markup=start_btn, parse_mode=enums.ParseMode.HTML)
    return True


# ── Commands & Callbacks ─────────────────────────────────────────────

@Client.on_message(filters.private & filters.command("verify"))
async def verify_command(bot: Client, message: Message):
    user_id = message.from_user.id
    verified = await is_user_verified(user_id)
    if verified:
        rem_sec = get_remaining_verify_time(user_id)
        if rem_sec > 0:
            hrs = rem_sec // 3600
            mins = (rem_sec % 3600) // 60
            exp_text = f"{hrs}h {mins}m remaining"
        else:
            exp_text = "Permanent VIP / Admin Access"

        card = (
            "<blockquote><b>🛡️ <u>sᴋɪɴᴇᴛ ᴠᴇʀsᴇ — ᴠᴇʀɪғɪᴄᴀᴛɪᴏɴ sᴛᴀᴛᴜs</u></b></blockquote>\n\n"
            f"👤 <b>ᴜsᴇʀ:</b> {message.from_user.first_name}\n"
            f"🆔 <b>ᴜsᴇʀ ɪᴅ:</b> <code>{user_id}</code>\n"
            f"⚡️ <b>sᴛᴀᴛᴜs:</b> <code>🟢 Fully Verified</code>\n"
            f"⏳ <b>ᴠᴀʟɪᴅɪᴛʏ:</b> <code>{exp_text}</code>\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "✅ <i>All forwarding and AutoSave pipelines are completely unlocked!</i>"
        )
        return await message.reply_text(
            card,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🚀 sᴛᴀʀᴛ ғᴏʀᴡᴀʀᴅɪɴɢ", callback_data="settings#main")],
                [InlineKeyboardButton("🎁 ʀᴇғᴇʀ & ᴇᴀʀɴ", callback_data="referral#main")]
            ]),
            quote=True
        )

    await send_verify_prompt(bot, message, user_id, step=1)


@Client.on_message(filters.private & filters.command("setverify"))
async def setverify_command(bot: Client, message: Message):
    user_id = message.from_user.id
    if not await db.is_admin(user_id):
        return await message.reply_text("⛔ <b>This command is restricted to Bot Administrators only.</b>", quote=True)

    args = (message.text or message.caption or "").split()[1:]
    cfg = await db.get_verify_config()

    if not args or args[0].lower() in ("status", "info"):
        status_txt = "🟢 ᴇɴᴀʙʟᴇᴅ" if cfg.get("enabled") else "🔴 ᴅɪsᴀʙʟᴇᴅ"
        s1 = f"{cfg.get('shortener_url', 'None')} (API: {'Set' if cfg.get('shortener_api') else 'None'})"
        s2 = f"{cfg.get('shortener_url2', 'None')} (API: {'Set' if cfg.get('shortener_api2') else 'None'})"
        s3 = f"{cfg.get('shortener_url3', 'None')} (API: {'Set' if cfg.get('shortener_api3') else 'None'})"

        text = (
            "<blockquote><b>⚙️ <u>ᴛᴏᴋᴇɴ ᴠᴇʀɪғɪᴄᴀᴛɪᴏɴ — ᴀᴅᴍɪɴ ᴄᴏɴᴛʀᴏʟ</u></b></blockquote>\n\n"
            f"• <b>sᴛᴀᴛᴜs:</b> <code>{status_txt}</code>\n"
            f"• <b>ᴘᴀss ᴅᴜʀᴀᴛɪᴏɴ:</b> <code>{cfg.get('duration', 24)} Hours</code>\n"
            f"• <b>ᴠᴇʀɪғɪᴄᴀᴛɪᴏɴ sᴛᴇᴘs:</b> <code>{cfg.get('steps', 1)} Step(s)</code>\n"
            f"• <b>ʟɪɴᴋ ᴛɪᴍᴇᴏᴜᴛ:</b> <code>{cfg.get('timeout', 30)} Minutes</code>\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"<b>Shortener 1:</b> <code>{s1}</code>\n"
            f"<b>Shortener 2:</b> <code>{s2}</code>\n"
            f"<b>Shortener 3:</b> <code>{s3}</code>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "<b><u>Available Configuration Commands:</u></b>\n"
            "• <code>/setverify on</code> — Enable verification gate\n"
            "• <code>/setverify off</code> — Disable verification gate\n"
            "• <code>/setverify time &lt;hours&gt;</code> — Set pass duration (e.g. 24)\n"
            "• <code>/setverify steps &lt;1|2|3&gt;</code> — Set number of shortener steps\n"
            "• <code>/setverify s1 &lt;domain&gt; &lt;api_key&gt;</code> — Configure Shortener 1\n"
            "• <code>/setverify s2 &lt;domain&gt; &lt;api_key&gt;</code> — Configure Shortener 2\n"
            "• <code>/setverify s3 &lt;domain&gt; &lt;api_key&gt;</code> — Configure Shortener 3\n"
            "• <code>/setverify give &lt;user_id&gt; &lt;hours&gt;</code> — Grant free pass to user\n"
            "• <code>/setverify reset &lt;user_id&gt;</code> — Revoke user verification"
        )
        return await message.reply_text(text, quote=True)

    sub = args[0].lower()

    if sub == "on":
        await db.update_verify_config("enabled", True)
        return await message.reply_text("✅ <b>Token verification gate has been ENABLED!</b>", quote=True)

    elif sub == "off":
        await db.update_verify_config("enabled", False)
        return await message.reply_text("🛑 <b>Token verification gate has been DISABLED!</b>", quote=True)

    elif sub == "time":
        if len(args) < 2 or not args[1].isdigit():
            return await message.reply_text("<b>Usage:</b> <code>/setverify time 24</code> (in hours)", quote=True)
        hours = int(args[1])
        await db.update_verify_config("duration", hours)
        return await message.reply_text(f"✅ <b>Pass duration set to {hours} Hours!</b>", quote=True)

    elif sub == "steps":
        if len(args) < 2 or not args[1].isdigit() or int(args[1]) not in (1, 2, 3):
            return await message.reply_text("<b>Usage:</b> <code>/setverify steps 1</code> (1, 2, or 3)", quote=True)
        steps = int(args[1])
        await db.update_verify_config("steps", steps)
        return await message.reply_text(f"✅ <b>Verification steps set to {steps}!</b>", quote=True)

    elif sub in ("s1", "s2", "s3"):
        if len(args) < 3:
            return await message.reply_text(f"<b>Usage:</b> <code>/setverify {sub} shareus.io my_api_key</code>", quote=True)
        domain, api_key = args[1].strip(), args[2].strip()
        idx_suffix = "" if sub == "s1" else sub[-1]
        await db.update_verify_config(f"shortener_url{idx_suffix}", domain)
        await db.update_verify_config(f"shortener_api{idx_suffix}", api_key)
        return await message.reply_text(f"✅ <b>Shortener {sub.upper()} set to:</b> <code>{domain}</code>", quote=True)

    elif sub == "give":
        if len(args) < 3 or not args[1].lstrip("-").isdigit() or not args[2].isdigit():
            return await message.reply_text("<b>Usage:</b> <code>/setverify give &lt;user_id&gt; &lt;hours&gt;</code>", quote=True)
        target_uid = int(args[1])
        hours = int(args[2])
        expires_at = time.time() + (hours * 3600)
        await db.set_user_verify_status(target_uid, expires_at)
        _VERIFIED_CACHE[target_uid] = expires_at
        return await message.reply_text(f"✅ <b>Granted {hours}h verification pass to user <code>{target_uid}</code>!</b>", quote=True)

    elif sub == "reset":
        if len(args) < 2 or not args[1].lstrip("-").isdigit():
            return await message.reply_text("<b>Usage:</b> <code>/setverify reset &lt;user_id&gt;</code>", quote=True)
        target_uid = int(args[1])
        await db.set_user_verify_status(target_uid, 0)
        _VERIFIED_CACHE.pop(target_uid, None)
        return await message.reply_text(f"✅ <b>Verification pass revoked for user <code>{target_uid}</code>.</b>", quote=True)

    await message.reply_text("❓ <b>Unknown argument. Type <code>/setverify</code> for help.</b>", quote=True)


@Client.on_callback_query(filters.regex(r"^verify#check_(\d+)"))
async def verify_check_callback(bot: Client, query: CallbackQuery):
    user_id = int(query.data.split("_")[1])
    if query.from_user.id != user_id:
        return await query.answer("⚠️ This is not your verification prompt!", show_alert=True)

    verified = await is_user_verified(user_id)
    if verified:
        await query.answer("🎉 Verification verified! Access granted.", show_alert=True)
        try:
            await query.message.delete()
        except Exception:
            pass
        return await bot.send_message(
            user_id,
            "<blockquote><b>🎉 <u>ᴀᴄᴄᴇss ɢʀᴀɴᴛᴇᴅ!</u></b></blockquote>\n\n"
            "Your pass is active! You can now use all forward commands.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🚀 sᴛᴀʀᴛ ғᴏʀᴡᴀʀᴅɪɴɢ", callback_data="settings#main")]
            ])
        )

    await query.answer("❌ You haven't completed the verification step yet! Complete the link above.", show_alert=True)
