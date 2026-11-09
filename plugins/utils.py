import asyncio
import time as tm
from database import db 
from .test import parse_buttons

async def auto_delete(message, delay=5):
    """Wait for delay seconds, then delete the message cleanly."""
    if not message:
        return
    try:
        if delay and delay > 0:
            await asyncio.sleep(delay)
        if hasattr(message, "delete"):
            await message.delete()
    except Exception:
        pass

STATUS = {}

class STS:
    def __init__(self, id):
        self.id = id
        self.data = STATUS
    
    def verify(self):
        return self.data.get(self.id)
    
    def store(self, From, to, skip, limit, ranges=None, worker=None):
        total_count = sum((end - start + 1) for start, end in ranges) if ranges else limit
        initial_fetched = 0 if ranges else skip
        self.data[self.id] = {
            "FROM": From,
            'TO': to,
            'total_files': 0,
            'skip': skip,
            'limit': limit,
            'fetched': initial_fetched,
            'filtered': 0,
            'deleted': 0,
            'duplicate': 0,
            'total': total_count,
            'start': 0,
            'ranges': ranges,
            'worker': worker,
            'last_flood': 0,
            'floodwaits': 0
        }
        self.get(full=True)
        return STS(self.id)
        
    def get(self, value=None, full=False):
        values = self.data.get(self.id)
        if not values:
            return None
        if not full:
           return values.get(value)
        for k, v in values.items():
            setattr(self, k, v)
        return self

    def add(self, key=None, value=1, time=False):
        if time:
          return self.data[self.id].update({'start': tm.time()})
        current_val = self.get(key) or 0
        self.data[self.id].update({key: current_val + value}) 
    
    def divide(self, no, by):
       by = 1 if int(by) == 0 else by 
       return int(no) / by 
    
    async def get_data(self, user_id):
        # 1. Check if a specific worker was selected during setup
        worker = self.get('worker')
        if worker:
            bot = worker
        else:
            from_chat = self.get('FROM')
            bot = await db.get_worker_for_chat(user_id, from_chat, is_source=True)
            if not bot:
                bot = await db.get_bot(user_id, prefer_userbot=True)
        k, filters = self, await db.get_filters(user_id)
        size, configs = None, await db.get_configs(user_id)
        if configs['duplicate']:
           duplicate = [configs['db_uri'], self.TO]
        else:
           duplicate = False
        button = parse_buttons(configs['button'] if configs['button'] else '')
        if configs['file_size'] != 0:
            size = [configs['file_size'], configs['size_limit']]
        return bot, configs['caption'], configs['forward_tag'], {'chat_id': k.FROM, 'limit': k.limit, 'offset': k.skip, 'filters': filters,
                'keywords': configs['keywords'], 'media_size': size, 'extensions': configs['extension'], 'skip_duplicate': duplicate}, configs['protect'], button        