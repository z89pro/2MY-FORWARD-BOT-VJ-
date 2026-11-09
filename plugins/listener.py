"""
plugins/listener.py — Universal Pyrogram Interactive Listener & Ask Engine for Skinet_Verse_Forward_Bot.
Attaches .listen() and .ask() to Client and Chat, and sanitizes quote/disable_web_page_preview keywords.
"""
import asyncio
import logging
from pyrogram import Client, StopPropagation
from pyrogram.types import Message, Chat, LinkPreviewOptions
import pyrogram.errors

logger = logging.getLogger("ListenerEngine")

# Listener registry: key -> (Future, filters)
_ACTIVE_FUTURES = {}

# Ensure ListenerTimeout exists in pyrogram.errors
if not hasattr(pyrogram.errors, "ListenerTimeout"):
    class ListenerTimeout(asyncio.TimeoutError):
        """Raised when a listen or ask call times out."""
        pass
    pyrogram.errors.ListenerTimeout = ListenerTimeout

# 1. Hook Message._parse to intercept messages for waiting listeners
_orig_parse = getattr(Message, "_parse", None)

@staticmethod
async def _custom_listener_parse(client, message, users, chats, *args, **kwargs):
    msg = await _orig_parse(client, message, users, chats, *args, **kwargs)
    if not msg:
        return msg

    chat_id = getattr(getattr(msg, "chat", None), "id", None)
    user_id = getattr(getattr(msg, "from_user", None), "id", None)

    for key in ((chat_id, user_id), (chat_id, None)):
        if key in _ACTIVE_FUTURES:
            fut, flt = _ACTIVE_FUTURES[key]
            if flt is not None:
                try:
                    match = flt(client, msg)
                    if asyncio.iscoroutine(match):
                        match = await match
                except Exception:
                    match = False
                if not match:
                    continue  # Filter did not match, keep listening

            _ACTIVE_FUTURES.pop(key, None)
            if not fut.done():
                fut.set_result(msg)
            raise StopPropagation

    return msg

if _orig_parse and not getattr(_orig_parse, "_is_custom_listener", False):
    _custom_listener_parse._is_custom_listener = True
    Message._parse = _custom_listener_parse


# 2. Attach .listen() to Client
async def client_listen(self, chat_id, filters=None, timeout=None, user_id=None):
    loop = asyncio.get_running_loop()
    fut = loop.create_future()
    key = (chat_id, user_id) if user_id else (chat_id, None)
    _ACTIVE_FUTURES[key] = (fut, filters)
    try:
        if timeout:
            return await asyncio.wait_for(fut, timeout=timeout)
        return await fut
    except asyncio.TimeoutError:
        _ACTIVE_FUTURES.pop(key, None)
        raise pyrogram.errors.ListenerTimeout(f"Listen operation timed out after {timeout}s.")

Client.listen = client_listen


# 3. Attach .ask() to Client
async def client_ask(self, chat_id, text=None, filters=None, timeout=None, user_id=None, *args, **kwargs):
    kwargs.pop("quote", None)
    if kwargs.pop("disable_web_page_preview", None):
        kwargs["link_preview_options"] = LinkPreviewOptions(is_disabled=True)

    if text is not None:
        await self.send_message(chat_id, text, *args, **kwargs)
    elif "text" in kwargs:
        t = kwargs.pop("text")
        await self.send_message(chat_id, t, *args, **kwargs)

    return await self.listen(chat_id, filters=filters, timeout=timeout, user_id=user_id)

Client.ask = client_ask


# 4. Attach .listen() and .ask() to Chat
async def chat_listen(self, filters=None, timeout=None, *args, **kwargs):
    return await self._client.listen(self.id, filters=filters, timeout=timeout, *args, **kwargs)

async def chat_ask(self, text=None, filters=None, timeout=None, *args, **kwargs):
    return await self._client.ask(self.id, text=text, filters=filters, timeout=timeout, *args, **kwargs)

Chat.listen = chat_listen
Chat.ask = chat_ask


# 5. Sanitize Message.reply and Message.reply_text kwargs (pop quote & convert disable_web_page_preview)
_orig_reply = Message.reply
async def _safe_reply(self, *args, **kwargs):
    kwargs.pop("quote", None)
    if kwargs.pop("disable_web_page_preview", None):
        kwargs["link_preview_options"] = LinkPreviewOptions(is_disabled=True)
    return await _orig_reply(self, *args, **kwargs)

Message.reply = _safe_reply

_orig_reply_text = Message.reply_text
async def _safe_reply_text(self, *args, **kwargs):
    kwargs.pop("quote", None)
    if kwargs.pop("disable_web_page_preview", None):
        kwargs["link_preview_options"] = LinkPreviewOptions(is_disabled=True)
    return await _orig_reply_text(self, *args, **kwargs)

Message.reply_text = _safe_reply_text

logger.info("✅ Universal Interactive Listener (.ask / .listen) initialized successfully.")
