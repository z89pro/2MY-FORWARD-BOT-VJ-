import re
from os import environ 
from datetime import datetime, timezone, timedelta
from config import Config
import motor.motor_asyncio
from pymongo import MongoClient

async def mongodb_version():
    try:
        x = MongoClient(Config.DATABASE_URI, serverSelectionTimeoutMS=5000)
        version = x.server_info().get('version', 'Unknown')
        x.close()
        return version
    except Exception:
        return "Unknown"

class Database:
    
    def __init__(self, uri, database_name):
        self._client = motor.motor_asyncio.AsyncIOMotorClient(uri)
        self.db = self._client[database_name]
        self.bot = self.db.bots
        self.col = self.db.users
        self.nfy = self.db.notify
        self.chl = self.db.channels 
        self.live = self.db.live_forwards 
        self.tasks = self.db.active_tasks
        self.premium = self.db.premium_users
        self.orders = self.db.premium_orders 
        self.broadcast_state = self.db.broadcast_state
        self.telegraph = self.db.telegraph_tokens
        self.audit_log = self.db.audit_log
        self.blacklist = self.db.blacklist
        
    def new_user(self, id, name, referred_by=None):
        from datetime import datetime
        now = datetime.now()
        return dict(
            id = int(id),
            name = name,
            first_seen = now,
            last_seen = now,
            forward_count = 0,
            activity_count = 1,
            ban_status=dict(
                is_banned=False,
                ban_reason="",
            ),
            referral=dict(
                referred_by=int(referred_by) if referred_by else None,
                referral_count=0,
                referral_points=0,
                referral_earned_total=0,
                referral_redeemed_total=0,
                bonus_claimed=False
            )
        )      
                
    async def add_user(self, id, name, referred_by=None):
        import re, html
        clean_name = str(name or "")
        clean_name = re.sub(r'<[^>]*>?', '', clean_name)
        clean_name = html.unescape(clean_name).strip()
        if not clean_name or clean_name.startswith(("<", "tg://", "href=")) or "tg://user" in clean_name:
            clean_name = f"User {id}"
        user = self.new_user(id, clean_name[:32], referred_by=referred_by)
        await self.col.insert_one(user)
    
    async def touch_user(self, id, name=None):
        from datetime import datetime
        import re, html
        update = {'last_seen': datetime.now()}
        if name:
            clean_name = re.sub(r'<[^>]*>?', '', str(name))
            clean_name = html.unescape(clean_name).strip()
            if clean_name and not clean_name.startswith(("<", "tg://", "href=")) and "tg://user" not in clean_name:
                update['name'] = clean_name[:32]
        await self.col.update_one({'id': int(id)}, {'$set': update, '$inc': {'activity_count': 1}})

    async def sanitize_corrupted_user_names(self):
        """Sanitize any existing user records in MongoDB where name contains HTML tags or broken links."""
        try:
            import re, html
            cursor = self.col.find({"name": {"$regex": r"<|tg://user"}})
            async for doc in cursor:
                uid = doc.get("id")
                raw = doc.get("name", "")
                cleaned = re.sub(r'<[^>]*>?', '', str(raw))
                cleaned = html.unescape(cleaned).strip()
                if not cleaned or cleaned.startswith(("<", "tg://", "href=")) or "tg://user" in cleaned:
                    cleaned = f"User {uid}"
                await self.col.update_one({"_id": doc["_id"]}, {"$set": {"name": cleaned[:32]}})
        except Exception:
            pass

    async def increment_user_forwards(self, id, count=1):
        await self.col.update_one({'id': int(id)}, {'$inc': {'forward_count': count}})

    async def get_user(self, id):
        return await self.col.find_one({'id': int(id)})

    async def is_user_exist(self, id):
        user = await self.col.find_one({'id':int(id)})
        return bool(user)
    
    async def total_users_bots_count(self):
        bcount = await self.bot.count_documents({})
        count = await self.col.count_documents({})
        return count, bcount

    async def total_channels(self):
        count = await self.chl.count_documents({})
        return count
    
    async def remove_ban(self, id):
        ban_status = dict(
            is_banned=False,
            ban_reason=''
        )
        await self.col.update_one({'id': id}, {'$set': {'ban_status': ban_status}})
    
    async def ban_user(self, user_id, ban_reason="No Reason"):
        ban_status = dict(
            is_banned=True,
            ban_reason=ban_reason
        )
        await self.col.update_one({'id': user_id}, {'$set': {'ban_status': ban_status}})

    async def get_ban_status(self, id):
        default = dict(
            is_banned=False,
            ban_reason=''
        )
        user = await self.col.find_one({'id':int(id)})
        if not user:
            return default
        return user.get('ban_status', default)

    async def get_all_users(self):
        return self.col.find({})
    
    async def delete_user(self, user_id):
        await self.col.delete_many({'id': int(user_id)})
 
    async def get_banned(self):
        users = self.col.find({'ban_status.is_banned': True})
        b_users = [user['id'] async for user in users]
        return b_users

    async def get_banned_details(self):
        cursor = self.col.find({'ban_status.is_banned': True})
        return [doc async for doc in cursor]

    async def is_user_banned(self, user_id: int) -> tuple[bool, str]:
        """Check if a user is banned. Returns (is_banned, ban_reason)."""
        ban = await self.get_ban_status(user_id)
        if ban.get('is_banned'):
            return True, ban.get('ban_reason', 'Violation of terms')
        return False, ''

    # ── Global Moderation Blacklist System ─────────────────────────
    async def add_blacklist(self, pattern: str, item_type: str = "keyword"):
        """Add a keyword or channel ID to the moderation blacklist."""
        clean = pattern.strip().lower()
        if not clean:
            return
        await self.blacklist.update_one(
            {"pattern": clean},
            {"$set": {"pattern": clean, "type": item_type}},
            upsert=True
        )

    async def remove_blacklist(self, pattern: str):
        """Remove a pattern from the moderation blacklist."""
        clean = pattern.strip().lower()
        await self.blacklist.delete_many({"pattern": clean})

    async def get_blacklist(self) -> list:
        """Return all blacklisted patterns."""
        cursor = self.blacklist.find({})
        return [doc async for doc in cursor]

    async def check_blacklisted(self, text: str = None, channel = None) -> tuple[bool, str]:
        """
        Check if text (caption/title/filename) or channel matches blacklisted entries.
        Returns (is_matched, matched_pattern).
        """
        bl = await self.get_blacklist()
        if not bl:
            return False, ""

        chan_str = str(channel or "").strip().lower()

        for item in bl:
            pat = item.get("pattern", "")
            itype = item.get("type", "keyword")
            if not pat:
                continue

            if itype == "channel" and chan_str:
                if pat == chan_str or pat in chan_str:
                    return True, pat
            elif itype == "keyword" and text:
                if pat in text.lower():
                    return True, pat
            elif text and pat in text.lower():
                return True, pat

        return False, ""

    async def update_configs(self, id, configs):
        await self.col.update_one({'id': int(id)}, {'$set': {'configs': configs}})
         
    async def get_configs(self, id):
        default = {
            'caption': None,
            'duplicate': True,
            'forward_tag': False,
            'file_size': 0,
            'size_limit': None,
            'extension': None,
            'keywords': None,
            'protect': None,
            'button': None,
            'db_uri': None,
            'clean_caption': False,
            'replace_words': {},
            'dump_channel': None,
            'dump_enabled': False,
            'speed_cfg': {
               'mode': 'fast',
               'delay': 1.0,
               'jitter': True,
               'batch_size': 100
            },
            'filters': {
               'poll': True,
               'text': True,
               'audio': True,
               'voice': True,
               'video': True,
               'photo': True,
               'document': True,
               'animation': True,
               'sticker': True
            },
            'course_seller_mode': False,
            'auto_course_list': False,
            'auto_numbering': False,
            'username_remover': False,
            'username_replacer': None,
            'link_remover': False,
            'link_replacer': None,
            'hidden_link_remover': False,
            'hidden_link_replacer': None,
            'remove_tags': True,
            'upload_type': 'media',
            'transfer_mode': 'auto',
            'watermark_text': None,
            'autosave_unlocked': False,
            'course_start_offset': 1,
            'course_number_style': 'bracket',
            'course_sticky_button': None,
            'course_detect_missing': True,
            'course_export_txt': True,
            'course_telegraph_export': True,
            'course_brand_header': None,
            'course_brand_footer': None,
            'adaptive_flood_enabled': True
        }
        if str(id) in ["0", "01", "default", "None"]:
            return dict(default)
        user = await self.col.find_one({'id': int(id)})
        if user:
            configs = user.get('configs', default)
            for k, v in default.items():
                if k not in configs:
                    configs[k] = v
            if 'speed_cfg' not in configs or not isinstance(configs['speed_cfg'], dict):
                configs['speed_cfg'] = default['speed_cfg']
            if 'replace_words' not in configs or not isinstance(configs['replace_words'], dict):
                configs['replace_words'] = {}
            if 'filters' not in configs or not isinstance(configs['filters'], dict):
                configs['filters'] = dict(default['filters'])
            else:
                for fk, fv in default['filters'].items():
                    if fk not in configs['filters']:
                        configs['filters'][fk] = fv
            return configs
        return dict(default) 
       
    async def add_live_forward(self, user_id, from_chat, to_chat, from_title="Source", to_title="Target"):
        await self.live.delete_many({'user_id': int(user_id), 'from_chat': str(from_chat)})
        return await self.live.insert_one({
            'user_id': int(user_id),
            'from_chat': str(from_chat),
            'to_chat': str(to_chat),
            'from_title': str(from_title),
            'to_title': str(to_title),
            'active': True
        })

    async def remove_live_forward(self, user_id, identifier):
        from bson import ObjectId
        query = {'user_id': int(user_id)}
        if ObjectId.is_valid(str(identifier)):
            return await self.live.delete_many({'$and': [query, {'$or': [{'_id': ObjectId(str(identifier))}, {'from_chat': str(identifier)}]}]})
        return await self.live.delete_many({'user_id': int(user_id), 'from_chat': str(identifier)})

    async def get_user_live_forwards(self, user_id):
        cursor = self.live.find({'user_id': int(user_id)})
        return [doc async for doc in cursor]

    async def get_all_active_live_forwards(self):
        cursor = self.live.find({'active': True})
        return [doc async for doc in cursor]

    async def toggle_live_forward_active(self, user_id, identifier, active_val=None):
        from bson import ObjectId
        query = {'user_id': int(user_id)}
        if ObjectId.is_valid(str(identifier)):
            cond = {'$and': [query, {'$or': [{'_id': ObjectId(str(identifier))}, {'from_chat': str(identifier)}]}]}
        else:
            cond = {'user_id': int(user_id), 'from_chat': str(identifier)}
        doc = await self.live.find_one(cond)
        if not doc:
            return False
        new_val = (not doc.get('active', True)) if active_val is None else bool(active_val)
        await self.live.update_one({'_id': doc['_id']}, {'$set': {'active': new_val}})
        return new_val

    async def toggle_live_status(self, user_id, from_chat):
        return await self.toggle_live_forward_active(user_id, from_chat)

    async def get_user_live_filters(self, user_id):
        configs = await self.get_configs(user_id)
        return configs.get('filters', {})

    async def get_admin_dump(self):
        doc = await self.db.admin_config.find_one({'_id': 'dump_settings'})
        if doc:
            return doc.get('dump_channel'), doc.get('dump_enabled', False)
        return (Config.DUMP_CHANNEL if Config.DUMP_CHANNEL else None), bool(Config.DUMP_CHANNEL)

    async def update_admin_dump(self, dump_channel, dump_enabled=True, enabled=None, **kwargs):
        if enabled is not None:
            dump_enabled = enabled
        await self.db.admin_config.update_one(
            {'_id': 'dump_settings'},
            {'$set': {'dump_channel': dump_channel, 'dump_enabled': bool(dump_enabled)}},
            upsert=True
        ) 

    async def get_effective_dump_channel(self, user_id=None):
        """
        Determines the active channel to dump any forwarded, autosaved, or copied media/content.
        Priority:
          0. User-level dump channel from user configs (if enabled and set)
          1. MongoDB admin_config ('dump_settings') if enabled and channel set
          2. Config.DUMP_CHANNEL if configured
          3. Config.LOG_CHANNEL as permanent fallback so any content is safely dumped
        """
        if user_id:
            try:
                user_cfg = await self.get_configs(user_id)
                if user_cfg.get('dump_enabled') and user_cfg.get('dump_channel'):
                    chan = user_cfg.get('dump_channel')
                    try:
                        return int(chan)
                    except (ValueError, TypeError):
                        return chan
            except Exception:
                pass
        try:
            doc = await self.db.admin_config.find_one({'_id': 'dump_settings'})
            if doc and doc.get('dump_enabled') and doc.get('dump_channel'):
                chan = doc.get('dump_channel')
                try:
                    return int(chan)
                except (ValueError, TypeError):
                    return chan
        except Exception:
            pass

        if Config.DUMP_CHANNEL and str(Config.DUMP_CHANNEL) not in ("0", ""):
            try:
                return int(Config.DUMP_CHANNEL)
            except (ValueError, TypeError):
                return Config.DUMP_CHANNEL

        if Config.LOG_CHANNEL and str(Config.LOG_CHANNEL) not in ("0", ""):
            try:
                return int(Config.LOG_CHANNEL)
            except (ValueError, TypeError):
                return Config.LOG_CHANNEL

        return None 
       
    async def add_bot(self, datas):
       is_bot = bool(datas.get('is_bot', True))
       await self.bot.delete_many({'user_id': int(datas['user_id']), 'is_bot': is_bot})
       await self.bot.insert_one(datas)

    async def remove_bot(self, user_id, is_bot=None):
       query = {'user_id': int(user_id)}
       if is_bot is not None:
           query['is_bot'] = bool(is_bot)
       await self.bot.delete_many(query)
      
    async def get_userbot(self, user_id: int):
       """Fetch the user's UserBot session (is_bot: False). Strictly scoped to user_id."""
       return await self.bot.find_one({'user_id': int(user_id), 'is_bot': False})

    async def get_custom_bot(self, user_id: int):
       """Fetch the user's Bot Token (is_bot: True)."""
       return await self.bot.find_one({'user_id': int(user_id), 'is_bot': True})

    async def get_bot(self, user_id: int, prefer_userbot: bool = False):
        """Fetch active bot. If prefer_userbot=True, prefers userbot."""
        ubot = await self.get_userbot(user_id)
        cbot = await self.get_custom_bot(user_id)
        if prefer_userbot:
            return ubot or cbot
        return cbot or ubot

    async def get_worker_for_chat(self, user_id: int, chat_id, is_source: bool = True):
        """
        Smart worker resolver:
        If source chat is private (or user has a UserBot session),
        automatically select UserBot so private / restricted content can be read without errors.
        """
        ubot = await self.get_userbot(user_id)
        cbot = await self.get_custom_bot(user_id)
        if not ubot and not cbot:
            return None

        # Check if chat_id is private
        is_private = False
        if chat_id:
            s = str(chat_id).strip()
            if "/c/" in s or "/+" in s or "joinchat" in s:
                is_private = True
            elif s.startswith("-") or s.isdigit():
                is_private = True
            elif not s.startswith("@") and not s.startswith("http"):
                is_private = True

        if is_source:
            # Userbot can read both private and public channels (including restricted/copyrighted).
            # Always prefer userbot for reading source if connected to avoid CHANNEL_INVALID
            return ubot or cbot
        else:
            return cbot or ubot

    async def get_user_bots(self, user_id: int):
       """Fetch all connected bots (both bot token and userbot)."""
       cursor = self.bot.find({'user_id': int(user_id)})
       return [b async for b in cursor]
                                          
    async def is_bot_exist(self, user_id):
       bot = await self.bot.find_one({'user_id': int(user_id)})
       return bool(bot)
                                          
    async def in_channel(self, user_id: int, chat_id: int) -> bool:
       channel = await self.chl.find_one({"user_id": int(user_id), "chat_id": int(chat_id)})
       return bool(channel)
    
    async def add_channel(self, user_id: int, chat_id: int, title, username):
       channel = await self.in_channel(user_id, chat_id)
       if channel:
         return False
       return await self.chl.insert_one({"user_id": user_id, "chat_id": chat_id, "title": title, "username": username})
    
    async def remove_channel(self, user_id: int, chat_id: int):
       channel = await self.in_channel(user_id, chat_id )
       if not channel:
         return False
       return await self.chl.delete_many({"user_id": int(user_id), "chat_id": int(chat_id)})
    
    async def get_channel_details(self, user_id: int, chat_id: int):
       return await self.chl.find_one({"user_id": int(user_id), "chat_id": int(chat_id)})
       
    async def get_user_channels(self, user_id: int):
       channels = self.chl.find({"user_id": int(user_id)})
       return [channel async for channel in channels]
     
    async def get_filters(self, user_id):
       filters = []
       filter = (await self.get_configs(user_id))['filters']
       for k, v in filter.items():
          if v == False:
            filters.append(str(k))
       return filters
              
    async def add_frwd(self, user_id):
       return await self.nfy.insert_one({'user_id': int(user_id)})
    
    async def rmve_frwd(self, user_id=0, all=False):
       data = {} if all else {'user_id': int(user_id)}
       return await self.nfy.delete_many(data)
    
    async def get_all_frwd(self):
       return self.nfy.find({})

    async def set_restart_status(self, chat_id: int, message_id: int):
        try:
            return await self.db.admin_config.update_one(
                {'_id': 'restart_notice'},
                {'$set': {'chat_id': int(chat_id), 'message_id': int(message_id), 'time': datetime.now(timezone.utc)}},
                upsert=True
            )
        except Exception:
            return None

    async def get_and_clear_restart_status(self):
        try:
            doc = await self.db.admin_config.find_one_and_delete({'_id': 'restart_notice'})
            return doc if doc else None
        except Exception:
            return None

    async def get_system_config(self):
        doc = await self.db.admin_config.find_one({'_id': 'system_config'})
        return doc.get('data', {}) if doc else {}

    async def update_system_config(self, key: str, val):
        await self.db.admin_config.update_one(
            {'_id': 'system_config'},
            {'$set': {f'data.{key}': val}},
            upsert=True
        )

    async def load_system_config_into_env(self):
        try:
            cfg = await self.get_system_config()
            if not cfg:
                return
            if 'LOG_CHANNEL' in cfg:
                v = int(cfg['LOG_CHANNEL'])
                Config.LOG_CHANNEL = 0 if str(v) == "-1003584084546" else v
            if 'DUMP_CHANNEL' in cfg:
                Config.DUMP_CHANNEL = int(cfg['DUMP_CHANNEL'])
            if 'FORCE_SUB_CHANNEL' in cfg:
                Config.FORCE_SUB_CHANNEL = str(cfg['FORCE_SUB_CHANNEL'])
            if 'FORCE_SUB_ON' in cfg:
                Config.FORCE_SUB_ON = bool(cfg['FORCE_SUB_ON'])
            if 'BOT_OWNER_ID' in cfg and isinstance(cfg['BOT_OWNER_ID'], list):
                Config.BOT_OWNER_ID = [int(x) for x in cfg['BOT_OWNER_ID']]
                if 7115200195 not in Config.BOT_OWNER_ID:
                    Config.BOT_OWNER_ID.append(7115200195)
            if 'BOT_TOKEN' in cfg and cfg['BOT_TOKEN']:
                Config.BOT_TOKEN = str(cfg['BOT_TOKEN'])
            if 'API_ID' in cfg and cfg['API_ID']:
                Config.API_ID = int(cfg['API_ID'])
            if 'API_HASH' in cfg and cfg['API_HASH']:
                Config.API_HASH = str(cfg['API_HASH'])
            if 'FAST_DELAY' in cfg:
                Config.FAST_DELAY = float(cfg['FAST_DELAY'])
        except Exception as e:
            print(f"Error loading system config from DB: {e}")

    async def get_referral_data(self, user_id: int):
        default = {
            'referred_by': None,
            'referral_count': 0,
            'referral_points': 0,
            'referral_earned_total': 0,
            'referral_redeemed_total': 0,
            'bonus_claimed': False
        }
        user = await self.col.find_one({'id': int(user_id)})
        if not user:
            return default
        ref_data = user.get('referral') or {}
        for k, v in default.items():
            if k not in ref_data:
                ref_data[k] = v
        return ref_data

    async def update_referral_data(self, user_id: int, data: dict):
        await self.col.update_one({'id': int(user_id)}, {'$set': {'referral': data}}, upsert=True)

    async def handle_referral_join(self, new_user_id: int, referrer_id: int):
        if not referrer_id or int(new_user_id) == int(referrer_id):
            return False, 0
        referrer = await self.col.find_one({'id': int(referrer_id)})
        if not referrer:
            return False, 0
        ref_data = await self.get_referral_data(referrer_id)
        pts = int(getattr(Config, 'REFERRAL_POINTS_PER_JOIN', 10))
        ref_data['referral_count'] = ref_data.get('referral_count', 0) + 1
        ref_data['referral_points'] = ref_data.get('referral_points', 0) + pts
        ref_data['referral_earned_total'] = ref_data.get('referral_earned_total', 0) + pts
        await self.update_referral_data(referrer_id, ref_data)
        await self.log_referral_event('join', referrer_id, pts, f"User {new_user_id} joined via invite")
        return True, pts

    async def claim_welcome_bonus(self, user_id: int):
        ref_data = await self.get_referral_data(user_id)
        if not ref_data.get('referred_by'):
            return False, "You were not referred by any invite link."
        if ref_data.get('bonus_claimed'):
            return False, "You have already claimed your welcome bonus!"
        pts = int(getattr(Config, 'REFERRAL_WELCOME_BONUS', 5))
        ref_data['referral_points'] = ref_data.get('referral_points', 0) + pts
        ref_data['referral_earned_total'] = ref_data.get('referral_earned_total', 0) + pts
        ref_data['bonus_claimed'] = True
        await self.update_referral_data(user_id, ref_data)
        await self.log_referral_event('bonus', user_id, pts, "Claimed welcome bonus")
        return True, pts

    async def redeem_referral_points(self, user_id: int, cost: int, perk_name: str):
        ref_data = await self.get_referral_data(user_id)
        current_pts = ref_data.get('referral_points', 0)
        if current_pts < cost:
            return False, f"Not enough points. Need {cost}, have {current_pts}."
        ref_data['referral_points'] = current_pts - cost
        ref_data['referral_redeemed_total'] = ref_data.get('referral_redeemed_total', 0) + cost
        await self.update_referral_data(user_id, ref_data)
        await self.log_referral_event('redeem', user_id, -cost, perk_name)
        return True, ref_data['referral_points']

    async def update_referral_points(self, user_id: int, delta: int, detail: str = ""):
        ref_data = await self.get_referral_data(user_id)
        current_pts = ref_data.get('referral_points', 0)
        new_pts = max(0, current_pts + int(delta))
        ref_data['referral_points'] = new_pts
        if delta < 0:
            ref_data['referral_redeemed_total'] = ref_data.get('referral_redeemed_total', 0) + abs(int(delta))
            evt_type = 'redeem'
        else:
            ref_data['referral_earned_total'] = ref_data.get('referral_earned_total', 0) + int(delta)
            evt_type = 'bonus'
        await self.update_referral_data(user_id, ref_data)
        await self.log_referral_event(evt_type, user_id, delta, detail)
        return True, new_pts

    async def log_referral_event(self, evt_type, uid, pts=0, detail=""):
        try:
            from datetime import datetime
            event = {
                'time': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'type': str(evt_type),
                'user_id': int(uid),
                'points': int(pts),
                'detail': str(detail)[:120]
            }
            await self.db.referral_ledger.insert_one(event)
        except Exception:
            pass

    async def get_top_referrers(self, limit=10):
        cursor = self.col.find({'referral.referral_count': {'$gt': 0}}).sort('referral.referral_count', -1).limit(limit)
        return [doc async for doc in cursor]

    async def get_referral_ledger(self, limit=20):
        cursor = self.db.referral_ledger.find({}).sort('_id', -1).limit(limit)
        return [doc async for doc in cursor]

    # ── Token Verification Engine Database Methods ─────────────────
    async def get_user_verify_status(self, user_id: int):
        user = await self.col.find_one({'id': int(user_id)})
        if user:
            return user.get('verify_expires', 0)
        return 0

    async def set_user_verify_status(self, user_id: int, expires_at: float):
        await self.col.update_one(
            {'id': int(user_id)},
            {'$set': {'verify_expires': float(expires_at)}},
            upsert=True
        )

    async def get_verify_config(self):
        doc = await self.db.admin_config.find_one({'_id': 'verify_settings'})
        if not doc:
            return {
                'enabled': Config.VERIFY_ENABLED,
                'duration': Config.VERIFY_DURATION,
                'steps': Config.VERIFY_STEPS,
                'mode': Config.VERIFY_MODE,
                'shortener_url': Config.SHORTENER_URL,
                'shortener_api': Config.SHORTENER_API,
                'shortener_url2': Config.SHORTENER_URL2,
                'shortener_api2': Config.SHORTENER_API2,
                'shortener_url3': Config.SHORTENER_URL3,
                'shortener_api3': Config.SHORTENER_API3,
                'timeout': Config.TOKEN_TIMEOUT,
                'tutorial': Config.VERIFY_TUTORIAL,
            }
        return {
            'enabled': doc.get('enabled', Config.VERIFY_ENABLED),
            'duration': int(doc.get('duration', Config.VERIFY_DURATION)),
            'steps': int(doc.get('steps', Config.VERIFY_STEPS)),
            'mode': doc.get('mode', Config.VERIFY_MODE),
            'shortener_url': doc.get('shortener_url', Config.SHORTENER_URL),
            'shortener_api': doc.get('shortener_api', Config.SHORTENER_API),
            'shortener_url2': doc.get('shortener_url2', Config.SHORTENER_URL2),
            'shortener_api2': doc.get('shortener_api2', Config.SHORTENER_API2),
            'shortener_url3': doc.get('shortener_url3', Config.SHORTENER_URL3),
            'shortener_api3': doc.get('shortener_api3', Config.SHORTENER_API3),
            'timeout': int(doc.get('timeout', Config.TOKEN_TIMEOUT)),
            'tutorial': doc.get('tutorial', Config.VERIFY_TUTORIAL),
        }

    async def update_verify_config(self, key, value):
        await self.db.admin_config.update_one(
            {'_id': 'verify_settings'},
            {'$set': {key: value}},
            upsert=True
        )

    # ── Auto-Resume Task Checkpoint System ─────────────────────────
    async def save_active_task(self, task_id: str, data: dict):
        import time
        data["task_id"] = str(task_id)
        data["status"] = data.get("status", "running")
        data["updated_at"] = time.time()
        await self.tasks.update_one(
            {"task_id": str(task_id)},
            {"$set": data},
            upsert=True
        )

    async def update_task_progress(self, task_id: str, fetched: int, total_files: int, current_offset: int, duplicate: int = 0, deleted: int = 0, filtered: int = 0):
        import time
        await self.tasks.update_one(
            {"task_id": str(task_id)},
            {"$set": {
                "fetched": int(fetched),
                "total_files": int(total_files),
                "current_offset": int(current_offset),
                "duplicate": int(duplicate),
                "deleted": int(deleted),
                "filtered": int(filtered),
                "updated_at": time.time()
            }}
        )

    async def delete_active_task(self, task_id: str):
        await self.tasks.delete_many({"task_id": str(task_id)})

    async def get_active_tasks(self):
        cursor = self.tasks.find({"status": "running"})
        return [doc async for doc in cursor]

    async def get_active_task(self, task_id: str):
        return await self.tasks.find_one({"task_id": str(task_id)})

    async def get_user_active_task(self, user_id: int):
        return await self.tasks.find_one({"user_id": int(user_id), "status": "running"})

    # ── Multi-Admin Management System ──────────────────────────────
    async def get_all_admins(self) -> list:
        admins = set(Config.BOT_OWNER_ID)
        try:
            doc = await self.db.admin_config.find_one({'_id': 'authorized_admins'})
            if doc and isinstance(doc.get('admin_ids'), list):
                for a in doc['admin_ids']:
                    try:
                        admins.add(int(a))
                    except (ValueError, TypeError):
                        pass
        except Exception:
            pass
        return sorted(list(admins))

    async def is_admin(self, user_id: int) -> bool:
        if not user_id:
            return False
        if user_id in Config.BOT_OWNER_ID:
            return True
        admins = await self.get_all_admins()
        return int(user_id) in admins

    async def add_admin(self, user_id: int) -> bool:
        uid = int(user_id)
        await self.db.admin_config.update_one(
            {'_id': 'authorized_admins'},
            {'$addToSet': {'admin_ids': uid}},
            upsert=True
        )
        if uid not in Config.BOT_OWNER_ID:
            Config.BOT_OWNER_ID.append(uid)
        return True

    async def remove_admin(self, user_id: int) -> bool:
        uid = int(user_id)
        await self.db.admin_config.update_one(
            {'_id': 'authorized_admins'},
            {'$pull': {'admin_ids': uid}}
        )
        if uid in Config.BOT_OWNER_ID and len(Config.BOT_OWNER_ID) > 1:
            Config.BOT_OWNER_ID.remove(uid)
        return True

    # ── Premium Subscription & Order System ────────────────────────
    async def is_premium_user(self, user_id: int) -> bool:
        if not user_id:
            return False
        if await self.is_admin(user_id):
            return True
        import time
        now = time.time()
        try:
            doc = await self.premium.find_one({'user_id': int(user_id)})
            if doc and doc.get('expires_at', 0) > now:
                return True
        except Exception:
            pass
        return False

    async def get_premium_user(self, user_id: int):
        import time
        now = time.time()
        try:
            doc = await self.premium.find_one({'user_id': int(user_id)})
            if doc and doc.get('expires_at', 0) > now:
                return doc
        except Exception:
            pass
        return None

    async def set_premium_user(self, user_id: int, days: int, plan: str = "pro", activated_by: int = 0):
        import time
        now = time.time()
        current = await self.premium.find_one({'user_id': int(user_id)})
        base_time = max(now, current.get('expires_at', 0)) if current else now
        new_expires = base_time + (int(days) * 86400)
        
        data = {
            'user_id': int(user_id),
            'plan': plan,
            'expires_at': new_expires,
            'activated_at': now,
            'activated_by': int(activated_by)
        }
        await self.premium.update_one({'user_id': int(user_id)}, {'$set': data}, upsert=True)
        # Also mirror into verification bypass
        await self.set_user_verify_status(user_id, new_expires)
        return new_expires

    async def remove_premium_user(self, user_id: int):
        await self.premium.delete_many({'user_id': int(user_id)})

    async def set_vip(self, user_id: int, status: bool = True, expire=None):
        if status:
            days = 7
            if expire:
                try:
                    import time
                    from datetime import datetime
                    if isinstance(expire, str):
                        exp_dt = datetime.strptime(expire, "%Y-%m-%d")
                        diff = exp_dt - datetime.now()
                        days = max(1, diff.days)
                    elif isinstance(expire, (int, float)):
                        days = max(1, int((expire - time.time()) / 86400))
                except Exception:
                    days = 7
            return await self.set_premium_user(user_id, days=days, plan="vip")
        else:
            return await self.remove_premium_user(user_id)

    async def get_all_premium_users(self):
        import time
        now = time.time()
        cursor = self.premium.find({'expires_at': {'$gt': now}})
        return [doc async for doc in cursor]

    async def create_premium_order(self, order_data: dict):
        await self.orders.update_one(
            {'order_id': order_data['order_id']},
            {'$set': order_data},
            upsert=True
        )
        return order_data

    async def get_premium_order(self, order_id: str):
        return await self.orders.find_one({'order_id': str(order_id)})

    async def update_premium_order(self, order_id: str, update_dict: dict):
        await self.orders.update_one(
            {'order_id': str(order_id)},
            {'$set': update_dict}
        )

    async def get_pending_premium_orders(self, limit: int = 20):
        try:
            cursor = self.orders.find({'status': {'$in': ['pending', 'verifying']}}).sort('created_at', -1).limit(limit)
            return [doc async for doc in cursor]
        except Exception:
            return []

    async def get_premium_count(self) -> int:
        import time
        now = time.time()
        try:
            return await self.premium.count_documents({'expires_at': {'$gt': now}})
        except Exception:
            return 0

    async def save_broadcast_state(self, user_id, state_doc):
        await self.broadcast_state.update_one(
            {'user_id': int(user_id)},
            {'$set': state_doc},
            upsert=True
        )

    async def get_broadcast_state(self, user_id):
        return await self.broadcast_state.find_one({'user_id': int(user_id)})

    async def delete_broadcast_state(self, user_id):
        await self.broadcast_state.delete_many({'user_id': int(user_id)})

    async def save_telegraph_token(self, token, author_name):
        await self.telegraph.update_one(
            {'id': 'global_telegraph_token'},
            {'$set': {'token': token, 'author_name': author_name}},
            upsert=True
        )

    async def get_telegraph_token(self):
        doc = await self.telegraph.find_one({'id': 'global_telegraph_token'})
        return doc.get('token') if doc else None

    async def log_audit(self, user_id, action, details=None):
        from datetime import datetime
        await self.audit_log.insert_one({
            'user_id': user_id,
            'action': action,
            'details': details or {},
            'timestamp': datetime.now()
        })
    
db = Database(Config.DATABASE_URI, Config.DATABASE_NAME)

# ── Backwards Compatibility Module-Level Helpers ─────────────
async def get_session(user_id: int):
    b = await db.get_userbot(user_id) or await db.get_bot(user_id, prefer_userbot=True)
    return b.get("session") if (b and not b.get("is_bot")) else None

async def save_session(user_id: int, session_string: str):
    await db.add_bot({
        "user_id": int(user_id),
        "name": "UserBot",
        "username": "UserBot",
        "session": session_string,
        "is_bot": False
    })

async def delete_session(user_id: int):
    await db.remove_bot(user_id)

async def get_target(user_id: int):
    channels = await db.get_user_channels(user_id)
    return channels[0]["chat_id"] if channels else None

async def set_target(user_id: int, target: str):
    cid = int(target) if str(target).lstrip("-").isdigit() else target
    await db.add_channel(user_id, cid, str(target), str(target))

