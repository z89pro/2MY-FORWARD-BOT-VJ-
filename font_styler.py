"""
font_styler.py — Universal Unicode Small Caps Engine for Skinet Verse
──────────────────────────────────────────────────────────────────────
Transforms all Latin text across messages, prompts, notifications,
and inline buttons into aesthetic Unicode Small Caps font.

Strictly protects:
  1. HTML tags (<...>, <blockquote>, <b>, <i>, <u>, <a>, etc.)
  2. Code and pre blocks (<code>...</code>, <pre>...</pre>)
  3. Python format placeholders ({...}, {botname}, {0:.2f}, etc.)
  4. Telegram bot commands (/start, /forward, /help, /config, etc.)
  5. URLs and deep-links (https://..., http://..., t.me/..., tg://...)
  6. Telegram user/channel mentions (@username)
  7. HTML entities (&amp;, &lt;, &gt;, etc.)
"""

import re
import functools
import logging
from typing import Optional, Any
from pyrogram import Client
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

logger = logging.getLogger("FontStyler")

# ── Small Caps Character Map ──────────────────────────────────────────
SMALL_CAPS_MAP = {
    'a': 'ᴀ', 'b': 'ʙ', 'c': 'ᴄ', 'd': 'ᴅ', 'e': 'ᴇ', 'f': 'ғ', 'g': 'ɢ',
    'h': 'ʜ', 'i': 'ɪ', 'j': 'ᴊ', 'k': 'ᴋ', 'l': 'ʟ', 'm': 'ᴍ', 'n': 'ɴ',
    'o': 'ᴏ', 'p': 'ᴘ', 'q': 'ǫ', 'r': 'ʀ', 's': 's', 't': 'ᴛ', 'u': 'ᴜ',
    'v': 'ᴠ', 'w': 'ᴡ', 'x': 'x', 'y': 'ʏ', 'z': 'ᴢ',
    'A': 'ᴀ', 'B': 'ʙ', 'C': 'ᴄ', 'D': 'ᴅ', 'E': 'ᴇ', 'F': 'ғ', 'G': 'ɢ',
    'H': 'ʜ', 'I': 'ɪ', 'J': 'ᴊ', 'K': 'ᴋ', 'L': 'ʟ', 'M': 'ᴍ', 'N': 'ɴ',
    'O': 'ᴏ', 'P': 'ᴘ', 'Q': 'ǫ', 'R': 'ʀ', 'S': 's', 'T': 'ᴛ', 'U': 'ᴜ',
    'V': 'ᴠ', 'W': 'ᴡ', 'X': 'x', 'Y': 'ʏ', 'Z': 'ᴢ',
}

# Tokens that must NEVER be mutated
TOKEN_PATTERN = re.compile(
    r'(<[^>]+>|'
    r'\{[a-zA-Z0-9_:., ]*\}|'
    r'https?://[^\s<>\'\",]+|'
    r'(?<![a-zA-Z0-9_])t\.me/[^\s<>\'\",]+|'
    r'(?<![a-zA-Z0-9_])tg://[^\s<>\'\",]+|'
    r'(?<![a-zA-Z0-9_<])/[a-zA-Z0-9_]+|'
    r'(?<![a-zA-Z0-9_])@[a-zA-Z0-9_]+|'
    r'&[a-zA-Z0-9#]+;)'
)

CODE_BLOCK_PATTERN = re.compile(r'(<(?:code|pre)[^>]*>.*?</(?:code|pre)>)', re.DOTALL | re.IGNORECASE)


def _transform_plain_chunk(text: str) -> str:
    """Transform text chunks while protecting tokens."""
    tokens = TOKEN_PATTERN.split(text)
    out = []
    for i, tok in enumerate(tokens):
        if i % 2 == 1:
            # Protected token: preserve exact bytes
            out.append(tok)
        else:
            # Plain text: map Latin alphabets to small caps
            out.append(''.join(SMALL_CAPS_MAP.get(c, c) for c in tok))
    return ''.join(out)


def to_small_caps(html_text: Optional[str]) -> str:
    """
    Convert HTML or plain text to small caps, protecting HTML tags, code blocks,
    format specifiers, URLs, and bot commands.
    """
    if not html_text or not isinstance(html_text, str):
        return "" if html_text is None else str(html_text)

    # Protect entire <pre> and <code> blocks from modification
    code_parts = CODE_BLOCK_PATTERN.split(html_text)
    out_parts = []
    for i, part in enumerate(code_parts):
        if i % 2 == 1:
            # Code/Pre block: preserve untouched
            out_parts.append(part)
        else:
            out_parts.append(_transform_plain_chunk(part))
    return ''.join(out_parts)


def style_button(text: Optional[str]) -> str:
    """Convert button text to small caps, preserving emojis, badges, and symbols."""
    if not text or not isinstance(text, str):
        return "" if text is None else str(text)
    return ''.join(SMALL_CAPS_MAP.get(c, c) for c in text)


def _sanitize_btn(b):
    if hasattr(b, "text") and b.text:
        b.text = style_button(b.text)
    if hasattr(b, "callback_data") and b.callback_data is not None:
        if isinstance(b.callback_data, str):
            b_raw = b.callback_data.encode("utf-8", "replace")
            if len(b_raw) > 64:
                b.callback_data = b_raw[:64].decode("utf-8", "ignore")
        elif isinstance(b.callback_data, bytes) and len(b.callback_data) > 64:
            b.callback_data = b.callback_data[:64]
    return b


def style_reply_markup(markup_obj: Any) -> Any:
    """Style all buttons inside an InlineKeyboardMarkup or ReplyKeyboardMarkup and ensure callback_data <= 64 bytes."""
    if not markup_obj:
        return markup_obj

    if isinstance(markup_obj, InlineKeyboardMarkup):
        new_keyboard = []
        for row in getattr(markup_obj, "inline_keyboard", []):
            new_row = []
            for b in row:
                new_row.append(_sanitize_btn(b))
            new_keyboard.append(new_row)
        markup_obj.inline_keyboard = new_keyboard

        if hasattr(markup_obj, "_spec_rows"):
            for r in markup_obj._spec_rows:
                for b in r:
                    _sanitize_btn(b)

        return markup_obj

    if isinstance(markup_obj, ReplyKeyboardMarkup):
        new_keyboard = []
        for row in getattr(markup_obj, "keyboard", []):
            new_row = []
            for b in row:
                if isinstance(b, KeyboardButton) and b.text:
                    b.text = style_button(b.text)
                elif isinstance(b, str):
                    b = style_button(b)
                new_row.append(b)
            new_keyboard.append(new_row)
        markup_obj.keyboard = new_keyboard
        return markup_obj

    return markup_obj


# ── Global Pyrogram Client Interceptor ───────────────────────────────
_PATCHED = False

def patch_pyrogram_font():
    """
    Monkey-patches Pyrogram Client message methods so that all outgoing messages,
    media captions, alerts, and inline button markups are automatically styled in
    Small Caps across the entire application.
    """
    global _PATCHED
    if _PATCHED:
        return
    _PATCHED = True

    # 0. Patch Pyrogram Str.__getitem__ to eliminate UnicodeDecodeError on UTF-16 surrogates
    try:
        from pyrogram.types.messages_and_media.message import Str
        import pyrogram.parser.utils as parser_utils

        def safe_str_getitem(self, item):
            try:
                return parser_utils.remove_surrogates(parser_utils.add_surrogates(self)[item])
            except (UnicodeDecodeError, Exception):
                return str(self)[item]

        Str.__getitem__ = safe_str_getitem
    except Exception:
        pass

    # 1. Client.send_message
    orig_send_message = Client.send_message

    @functools.wraps(orig_send_message)
    async def hooked_send_message(self, *args, **kwargs):
        new_args = list(args)
        if len(new_args) > 1 and isinstance(new_args[1], str):
            new_args[1] = to_small_caps(new_args[1])
        elif "text" in kwargs and isinstance(kwargs["text"], str):
            kwargs["text"] = to_small_caps(kwargs["text"])

        if "reply_markup" in kwargs and kwargs["reply_markup"]:
            kwargs["reply_markup"] = style_reply_markup(kwargs["reply_markup"])
        return await orig_send_message(self, *new_args, **kwargs)

    Client.send_message = hooked_send_message

    # 2. Client.edit_message_text
    orig_edit_message_text = Client.edit_message_text

    @functools.wraps(orig_edit_message_text)
    async def hooked_edit_message_text(self, *args, **kwargs):
        new_args = list(args)
        if len(new_args) >= 3 and isinstance(new_args[2], str):
            new_args[2] = to_small_caps(new_args[2])
        elif len(new_args) == 2 and isinstance(new_args[1], str):
            new_args[1] = to_small_caps(new_args[1])
        elif "text" in kwargs and isinstance(kwargs["text"], str):
            kwargs["text"] = to_small_caps(kwargs["text"])

        if "reply_markup" in kwargs and kwargs["reply_markup"]:
            kwargs["reply_markup"] = style_reply_markup(kwargs["reply_markup"])
        return await orig_edit_message_text(self, *new_args, **kwargs)

    Client.edit_message_text = hooked_edit_message_text

    # 3. Media senders
    media_methods = [
        "send_photo", "send_video", "send_document",
        "send_audio", "send_animation", "send_voice"
    ]
    for method_name in media_methods:
        orig_fn = getattr(Client, method_name, None)
        if not orig_fn:
            continue

        def _make_media_hook(fn):
            @functools.wraps(fn)
            async def hooked_media(self, *args, **kwargs):
                if "caption" in kwargs and kwargs["caption"] and isinstance(kwargs["caption"], str):
                    kwargs["caption"] = to_small_caps(kwargs["caption"])
                if "reply_markup" in kwargs and kwargs["reply_markup"]:
                    kwargs["reply_markup"] = style_reply_markup(kwargs["reply_markup"])
                return await fn(self, *args, **kwargs)
            return hooked_media

        setattr(Client, method_name, _make_media_hook(orig_fn))

    # 4. Client.edit_message_caption
    orig_edit_caption = getattr(Client, "edit_message_caption", None)
    if orig_edit_caption:
        @functools.wraps(orig_edit_caption)
        async def hooked_edit_caption(self, *args, **kwargs):
            new_args = list(args)
            if len(new_args) >= 3 and isinstance(new_args[2], str):
                new_args[2] = to_small_caps(new_args[2])
            elif "caption" in kwargs and kwargs["caption"] and isinstance(kwargs["caption"], str):
                kwargs["caption"] = to_small_caps(kwargs["caption"])
            if "reply_markup" in kwargs and kwargs["reply_markup"]:
                kwargs["reply_markup"] = style_reply_markup(kwargs["reply_markup"])
            return await orig_edit_caption(self, *new_args, **kwargs)
        Client.edit_message_caption = hooked_edit_caption

    # 5. Client.edit_message_reply_markup
    orig_edit_reply_markup = getattr(Client, "edit_message_reply_markup", None)
    if orig_edit_reply_markup:
        @functools.wraps(orig_edit_reply_markup)
        async def hooked_edit_reply_markup(self, *args, **kwargs):
            if "reply_markup" in kwargs and kwargs["reply_markup"]:
                kwargs["reply_markup"] = style_reply_markup(kwargs["reply_markup"])
            return await orig_edit_reply_markup(self, *args, **kwargs)
        Client.edit_message_reply_markup = hooked_edit_reply_markup

    # 6. Client.answer_callback_query
    orig_answer_callback = getattr(Client, "answer_callback_query", None)
    if orig_answer_callback:
        @functools.wraps(orig_answer_callback)
        async def hooked_answer_callback(self, *args, **kwargs):
            new_args = list(args)
            if len(new_args) > 1 and isinstance(new_args[1], str):
                new_args[1] = to_small_caps(new_args[1])
            elif "text" in kwargs and kwargs["text"] and isinstance(kwargs["text"], str):
                kwargs["text"] = to_small_caps(kwargs["text"])
            return await orig_answer_callback(self, *new_args, **kwargs)
        Client.answer_callback_query = hooked_answer_callback

    # 7. Client.ask
    orig_ask = getattr(Client, "ask", None)
    if orig_ask:
        @functools.wraps(orig_ask)
        async def hooked_ask(self, *args, **kwargs):
            new_args = list(args)
            if len(new_args) > 1 and isinstance(new_args[1], str):
                new_args[1] = to_small_caps(new_args[1])
            elif "text" in kwargs and isinstance(kwargs["text"], str):
                kwargs["text"] = to_small_caps(kwargs["text"])
            if "reply_markup" in kwargs and kwargs["reply_markup"]:
                kwargs["reply_markup"] = style_reply_markup(kwargs["reply_markup"])
            return await orig_ask(self, *new_args, **kwargs)
        Client.ask = hooked_ask

    logger.info("✅ Universal Small Caps font engine initialized and patched into Pyrogram Client.")
