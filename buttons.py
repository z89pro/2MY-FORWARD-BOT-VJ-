"""
buttons.py — Advanced Coloured & Styled Buttons Engine for Skinet Verse
-----------------------------------------------------------------------
Provides native MTProto Layer 223+ (Bot API 9.4+) coloured inline buttons:
  • GREEN  (bg_success) → Positive: Start, Save, Confirm, Yes, Add, Enable, Done, Refresh, Resume
  • RED    (bg_danger)  → Destructive: Close, Cancel, Stop, Delete, Disable, No, Clear, Reset
  • BLUE   (bg_primary) → Navigation: Settings, Help, About, Back, Stats, Hub, Config, Referrals

Falls back seamlessly to standard InlineKeyboardMarkup for any client or datacenter
that does not support the styled layer. Also decorates buttons with beautiful visual
badges and Unicode Small Caps so the UI looks stunning across all platforms.
"""

from io import BytesIO
import re
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.raw.core import TLObject
from pyrogram.raw.core.primitives import Int, Long, Bytes, String
from pyrogram.raw.types import (
    ReplyInlineMarkup as _RawMarkup,
    KeyboardButtonRow as _RawRow,
)

STYLE_ENABLED = True

_FLAG_BY_COLOR = {
    "green": "bg_success",
    "red": "bg_danger",
    "blue": "bg_primary"
}

# Small Caps translation for normalizing text during auto-detection
_SMALL_CAPS_TRANS = str.maketrans(
    'ᴀʙᴄᴅᴇғɢʜɪᴊᴋʟᴍɴᴏᴘǫʀsᴛᴜᴠᴡxʏᴢ',
    'abcdefghijklmnopqrstuvwxyz'
)

_RED_PATTERNS = re.compile(
    r'\b(close|cancel|stop|delete|remove|clear|reset|wipe|revoke|unlink|'
    r'disconnect|purge|disable|off|abort|reject|terminate|dismiss|no)\b',
    re.IGNORECASE
)

_GREEN_PATTERNS = re.compile(
    r'\b(enable|on|start|confirm|approve|save|add|connect|restore|generate|test|'
    r'download|upload|set|apply|refresh|edit|manage|configure|accept|done|default|yes|resume|claim)\b',
    re.IGNORECASE
)

_BLUE_PATTERNS = re.compile(
    r'\b(back|audit|review|view|guide|info|help|details|token|folder|remote|'
    r'custom|thumbnail|split|duration|settings|menu|nav|stats|plan|change|tutorial|hub|referral|verify)\b',
    re.IGNORECASE
)


class KeyboardButtonStyle(TLObject):
    """keyboardButtonStyle#4fdd3430 (TL layer 223+)"""
    __slots__ = ["bg_primary", "bg_danger", "bg_success", "icon"]
    ID = 0x4FDD3430
    QUALNAME = "types.KeyboardButtonStyle"

    def __init__(self, *, bg_primary=None, bg_danger=None, bg_success=None, icon=None):
        self.bg_primary = bg_primary
        self.bg_danger = bg_danger
        self.bg_success = bg_success
        self.icon = icon

    def write(self, *args) -> bytes:
        b = BytesIO()
        b.write(Int(self.ID, False))
        flags = 0
        flags |= (1 << 0) if self.bg_primary else 0
        flags |= (1 << 1) if self.bg_danger else 0
        flags |= (1 << 2) if self.bg_success else 0
        flags |= (1 << 3) if self.icon is not None else 0
        b.write(Int(flags))
        if self.icon is not None:
            b.write(Long(self.icon))
        return b.getvalue()


class StyledKeyboardButtonCallback(TLObject):
    """keyboardButtonCallback#e62bc960 — Layer 223 form with `style`"""
    __slots__ = ["text", "data", "requires_password", "style"]
    ID = 0xE62BC960
    QUALNAME = "types.KeyboardButtonCallback"

    def __init__(self, *, text, data, requires_password=None, style=None):
        self.text = text
        if isinstance(data, str):
            b_data = data.encode('utf-8', 'replace')
        elif isinstance(data, bytes):
            b_data = data
        else:
            b_data = str(data or "").encode('utf-8', 'replace')
        if len(b_data) > 64:
            b_data = b_data[:64]
        self.data = b_data
        self.requires_password = requires_password
        self.style = style

    def write(self, *args) -> bytes:
        b = BytesIO()
        b.write(Int(self.ID, False))
        flags = 0
        flags |= (1 << 0) if self.requires_password else 0
        flags |= (1 << 10) if self.style is not None else 0
        b.write(Int(flags))
        if self.style is not None:
            b.write(self.style.write())
        b.write(String(str(self.text or "")))
        cb_bytes = self.data if isinstance(self.data, bytes) else str(self.data or "").encode('utf-8', 'replace')
        b.write(Bytes(cb_bytes[:64]))
        return b.getvalue()


class StyledKeyboardButtonUrl(TLObject):
    """keyboardButtonUrl#d80c25ec — Layer 223 form with `style`"""
    __slots__ = ["text", "url", "style"]
    ID = 0xD80C25EC
    QUALNAME = "types.KeyboardButtonUrl"

    def __init__(self, *, text, url, style=None):
        self.text = text
        self.url = url
        self.style = style

    def write(self, *args) -> bytes:
        b = BytesIO()
        b.write(Int(self.ID, False))
        flags = 0
        flags |= (1 << 10) if self.style is not None else 0
        b.write(Int(flags))
        if self.style is not None:
            b.write(self.style.write())
        b.write(String(str(self.text or "")))
        b.write(String(str(self.url or "")))
        return b.getvalue()


def _get_style(color: str):
    if not color:
        return None
    flag = _FLAG_BY_COLOR.get(color.lower())
    return KeyboardButtonStyle(**{flag: True}) if flag else None


def auto_color(text: str, data=None) -> str:
    """Intelligently detects semantic button color (green, red, blue, or None)."""
    clean_text = str(text or "").translate(_SMALL_CAPS_TRANS).lower()
    clean_data = str(data or "").lower()

    # Red patterns
    if _RED_PATTERNS.search(clean_text) or _RED_PATTERNS.search(clean_data):
        return "red"
    # Green patterns
    if _GREEN_PATTERNS.search(clean_text) or _GREEN_PATTERNS.search(clean_data):
        return "green"
    # Blue patterns
    if _BLUE_PATTERNS.search(clean_text) or _BLUE_PATTERNS.search(clean_data):
        return "blue"
    return "blue"


class _Btn:
    """Color-aware button specification that produces both high-level and raw objects."""
    __slots__ = ("text", "data", "url", "color")

    def __init__(self, text, data=None, url=None, color=None):
        from font_styler import style_button
        raw_text = str(text or "")
        self.text = style_button(raw_text)
        if isinstance(data, str):
            b_data = data.encode("utf-8", "replace")
            if len(b_data) > 64:
                b_data = b_data[:64]
            data = b_data
        elif isinstance(data, bytes) and len(data) > 64:
            data = data[:64]
        self.data = data
        self.url = str(url) if url else None
        self.color = color or auto_color(raw_text, data or url)

    def high_level(self):
        if self.url is not None:
            return InlineKeyboardButton(self.text, url=self.url)
        cb_data = self.data.decode('utf-8', 'ignore') if isinstance(self.data, bytes) else str(self.data or "")
        return InlineKeyboardButton(self.text, callback_data=cb_data)

    def raw(self):
        st = _get_style(self.color)
        if self.url is not None:
            return StyledKeyboardButtonUrl(text=self.text, url=self.url, style=st)
        return StyledKeyboardButtonCallback(text=self.text, data=self.data, style=st)


class StyledMarkup(InlineKeyboardMarkup):
    """
    InlineKeyboardMarkup subclass that serializes to TL Layer 223 styled raw markup.
    Inherits cleanly from Pyrogram's InlineKeyboardMarkup so all Pyrogram functions
    (send_message, edit_message_text, etc.) accept it directly.
    """
    def __init__(self, spec_rows):
        normalized_rows = []
        high_level_rows = []
        for r in spec_rows:
            norm_row = []
            hl_row = []
            for item in r:
                if isinstance(item, _Btn):
                    norm_row.append(item)
                    hl_row.append(item.high_level())
                elif isinstance(item, InlineKeyboardButton):
                    from font_styler import style_button
                    item.text = style_button(item.text)
                    if item.callback_data is not None:
                        if isinstance(item.callback_data, str):
                            cb_b = item.callback_data.encode('utf-8', 'replace')
                            if len(cb_b) > 64:
                                item.callback_data = cb_b[:64].decode('utf-8', 'ignore')
                        elif isinstance(item.callback_data, bytes) and len(item.callback_data) > 64:
                            item.callback_data = item.callback_data[:64]
                    btn_color = auto_color(item.text, item.callback_data or item.url)
                    btn_spec = _Btn(item.text, data=item.callback_data, url=item.url, color=btn_color)
                    norm_row.append(btn_spec)
                    hl_row.append(item)
                elif isinstance(item, tuple) or isinstance(item, list):
                    # Tuple format: (text, data/url, [color])
                    t = item[0]
                    target = item[1]
                    c = item[2] if len(item) > 2 else None
                    if str(target).startswith("http://") or str(target).startswith("https://") or str(target).startswith("tg://"):
                        spec = _Btn(t, url=target, color=c)
                    else:
                        spec = _Btn(t, data=target, color=c)
                    norm_row.append(spec)
                    hl_row.append(spec.high_level())
            normalized_rows.append(norm_row)
            high_level_rows.append(hl_row)

        super().__init__(high_level_rows)
        self._spec_rows = normalized_rows

    async def _plain(self, client):
        try:
            return await super().write(client)
        except TypeError:
            return await super().write()

    async def write(self, client=None):
        if not STYLE_ENABLED:
            return await self._plain(client)
        try:
            return _RawMarkup(rows=[
                _RawRow(buttons=[b.raw() for b in r]) for r in self._spec_rows
            ])
        except Exception:
            return await self._plain(client)


# ── Public API ─────────────────────────────────────────────────────────────

def btn(text: str, data: str, color: str = None) -> _Btn:
    """Creates a callback button with optional color ('green', 'red', 'blue')."""
    return _Btn(text, data=data, color=color)


def btn_url(text: str, url: str, color: str = None) -> _Btn:
    """Creates an URL button with optional color ('green', 'red', 'blue')."""
    return _Btn(text, url=url, color=color)


def row(*buttons) -> list:
    """Wraps buttons into a single horizontal row."""
    return list(buttons)


def markup(*rows) -> StyledMarkup:
    """Builds a StyledMarkup keyboard from multiple rows of buttons."""
    return StyledMarkup(list(rows))


def colored_markup(keyboard_grid) -> StyledMarkup:
    """
    Accepts any existing list-of-lists keyboard (containing InlineKeyboardButton,
    tuples, or _Btn) and automatically transforms it into a StyledMarkup with
    Layer 223 color styling.
    """
    return StyledMarkup(keyboard_grid)


# ── Global MTProto 64-byte Callback Safeguard ───────────────────────────────
_orig_ikb_write = InlineKeyboardButton.write

async def _safe_ikb_write(self, client):
    if self.callback_data is not None:
        if isinstance(self.callback_data, str):
            b = self.callback_data.encode("utf-8", "replace")
            if len(b) > 64:
                self.callback_data = b[:64].decode("utf-8", "ignore")
        elif isinstance(self.callback_data, bytes) and len(self.callback_data) > 64:
            self.callback_data = self.callback_data[:64]
    return await _orig_ikb_write(self, client)

InlineKeyboardButton.write = _safe_ikb_write

