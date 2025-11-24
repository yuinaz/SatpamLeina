
"""
Smoke helpers: provide DummyBot and retrofit utilities for thin testing without Discord.
"""
import types, asyncio

class DummyLoop:
    def create_task(self, coro): 
        return asyncio.get_event_loop().create_task(coro)

class DummyUser:
    id = 1234567890

class DummyBot:
    def __init__(self):
        self.user = DummyUser()
        self.guilds = []
        self.loop = DummyLoop()
    def get_channel(self, *args, **kwargs): return None
    async def fetch_channel(self, *args, **kwargs): return None
    async def wait_until_ready(self): return True
    async def add_cog(self, cog): return True

def retrofit(bot):
    """Ensure a skinny bot instance has the APIs our cogs expect."""
    setattr(bot, "get_all_channels", lambda: [])
    setattr(bot, "get_channel", getattr(bot, "get_channel", lambda *a, **k: None))
    setattr(bot, "get_user", lambda *a, **k: None)
    setattr(bot, "fetch_user", lambda *a, **k: None)
    return bot
