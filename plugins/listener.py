"""
plugins/listener.py — Universal Pyrogram Interactive Listener & Ask Engine for Skinet_Verse_Forward_Bot.
Attaches .listen() and .ask() to Client and Chat, and sanitizes quote/disable_web_page_preview keywords.
"""
import asyncio
import logging
from pyrogram import Client, StopPropagation
from pyrogram.handlers import MessageHandler
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


# 1. Incoming Message Dispatcher for interactive listeners (runs at highest priority group -100)
async def _listener_dispatcher(client, message):
    # Ignore outgoing messages sent by the bot or account itself
    if getattr(message, "outgoing", False):
        return
    from_user = getattr(message, "from_user", None)
    if from_user and getattr(from_user, "is_self", False):
        return
    if hasattr(client, "me") and client.me and from_user and from_user.id == client.me.id:
        return

    chat_id = getattr(getattr(message, "chat", None), "id", None)
    user_id = getattr(from_user, "id", None) if from_user else None
    if not chat_id:
        return

    # Check matching listener keys: (chat_id, user_id) or (chat_id, None)
    for key in ((chat_id, user_id), (chat_id, None)):
        if key in _ACTIVE_FUTURES:
            fut, flt = _ACTIVE_FUTURES[key]
            if flt is not None:
                try:
                    match = flt(client, message)
                    if asyncio.iscoroutine(match):
                        match = await match
                except Exception:
                    match = False
                if not match:
                    continue

            _ACTIVE_FUTURES.pop(key, None)
            if not fut.done():
                fut.set_result(message)
            raise StopPropagation


def _ensure_listener_registered(client):
    if not getattr(client, "_listener_handler_registered", False):
        client.add_handler(MessageHandler(_listener_dispatcher), group=-100)
        client._listener_handler_registered = True


# 2. Attach .listen() to Client
async def client_listen(self, chat_id, filters=None, timeout=None, user_id=None):
    _ensure_listener_registered(self)
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
    except Exception:
        _ACTIVE_FUTURES.pop(key, None)
        raise

Client.listen = client_listen


# 3. Attach .ask() to Client
async def client_ask(self, *args, **kwargs):
    kwargs.pop("quote", None)
    if kwargs.pop("disable_web_page_preview", None):
        kwargs["link_preview_options"] = LinkPreviewOptions(is_disabled=True)

    chat_id = None
    if args:
        chat_id = args[0]
        args = args[1:]
    elif "chat_id" in kwargs:
        chat_id = kwargs.pop("chat_id")

    text = None
    if args:
        text = args[0]
        args = args[1:]
    elif "text" in kwargs:
        text = kwargs.pop("text")

    filters = kwargs.pop("filters", None)
    timeout = kwargs.pop("timeout", None)
    user_id = kwargs.pop("user_id", None)

    _ensure_listener_registered(self)

    loop = asyncio.get_running_loop()
    fut = loop.create_future()
    key = (chat_id, user_id) if user_id else (chat_id, None)
    _ACTIVE_FUTURES[key] = (fut, filters)

    try:
        if text is not None:
            await self.send_message(chat_id, text, *args, **kwargs)
        elif "text" in kwargs:
            t = kwargs.pop("text")
            await self.send_message(chat_id, t, *args, **kwargs)
    except Exception:
        _ACTIVE_FUTURES.pop(key, None)
        raise

    try:
        if timeout:
            return await asyncio.wait_for(fut, timeout=timeout)
        return await fut
    except asyncio.TimeoutError:
        _ACTIVE_FUTURES.pop(key, None)
        raise pyrogram.errors.ListenerTimeout(f"Listen operation timed out after {timeout}s.")
    except Exception:
        _ACTIVE_FUTURES.pop(key, None)
        raise

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
