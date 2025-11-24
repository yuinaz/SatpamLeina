
import asyncio, types, logging, time
log = logging.getLogger("preflight.fake")

class FakeUser:
    def __init__(self, user_id=1, name="Owner"):
        self.id = int(user_id)
        self.name = name
        self.bot = False
    async def send(self, *args, **kwargs):
        return True

class FakeTextChannel:
    def __init__(self, id=123, name="log-botphising", guild=None):
        self.id = int(id); self.name = name; self.guild = guild
    async def send(self, *args, **kwargs): return True
    async def create_thread(self, *args, **kwargs): return self

class FakeGuild:
    def __init__(self, id=761163966030151701, channels=1):
        self.id = int(id)
        self.text_channels = [FakeTextChannel(1400375184048787566, "log-botphising", self)]
        self._stickers = []
        self.emojis = []
    async def fetch_stickers(self): return list(self._stickers)
    def get_channel(self, ch_id):
        for c in self.text_channels:
            if c.id == int(ch_id): return c
        return None

class FakeMember(FakeUser):
    def __init__(self, user_id=2, name="Member", roles=None):
        super().__init__(user_id, name)
        self.roles = roles or []
        class _Perms:
            administrator = True
        self.guild_permissions = _Perms()

class FakeDMChannel:
    def __init__(self): pass

class FakeAppCmdTree:
    async def sync(self, *args, **kwargs): return True

class FakeBot:
    def __init__(self):
        self.cogs = {}
        self.guilds = [FakeGuild()]
        self.loop = asyncio.get_event_loop()
        self.user = FakeUser(1399565852264628235, "SatpamLeina")
        self.tree = FakeAppCmdTree()

    def get_cog(self, name): return self.cogs.get(name)

    async def add_cog(self, cog):
        # Mimic discord.py 2.x where add_cog is awaitable in setup()
        self.cogs[cog.__class__.__name__] = cog
        return True

    async def add_view(self, *args, **kwargs):
        return True

    async def reload_extension(self, extname): return True
    def get_user(self, uid): return FakeUser(uid, "Owner")
    async def fetch_user(self, uid): return FakeUser(uid, "Owner")

    async def _emit_on_ready(self):
        for cog in list(self.cogs.values()):
            f = getattr(cog, "on_ready", None)
            if f and asyncio.iscoroutinefunction(f):
                try:
                    await f()
                except TypeError:
                    pass
        return True
