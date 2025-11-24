#!/usr/bin/env python3
import os, sys, types, asyncio, importlib, pathlib

ROOT = pathlib.Path(__file__).resolve().parent
REPO_ROOT = ROOT if (ROOT / "satpambot").exists() else ROOT.parent
if str(REPO_ROOT) not in sys.path: sys.path.insert(0, str(REPO_ROOT))
# --- Smoketest guard: force local KV (ignore Upstash) so this test runs offline.
# This prevents the Cog from calling the real Upstash if your shell already exports UPSTASH_*.
os.environ.pop("UPSTASH_REDIS_REST_URL", None)
os.environ.pop("UPSTASH_REDIS_REST_TOKEN", None)

def ensure_discord_stubs():
    try:
        import discord; from discord.ext import commands, tasks  # noqa
        return
    except Exception:
        pass
    discord = types.ModuleType("discord"); sys.modules["discord"] = discord
    class User: 
        def __init__(self): self.sent=[]
        async def send(self, text): self.sent.append(text)
    discord.User=User
    class TextChannel:
        def __init__(self): self.sent=[]
        async def send(self, text): self.sent.append(text)
    discord.TextChannel=TextChannel
    ext = types.ModuleType("discord.ext"); sys.modules["discord.ext"] = ext
    commands = types.ModuleType("commands"); sys.modules["discord.ext.commands"] = commands
    tasks = types.ModuleType("tasks"); sys.modules["discord.ext.tasks"] = tasks
    class _Cog: pass
    def _listener(*args, **kwargs):
        def deco(fn): return fn
        return deco
    _Cog.listener = staticmethod(_listener)
    commands.Cog=_Cog
    class Context: pass
    commands.Context = Context
    class Bot:
        def __init__(self): pass
    commands.Bot = Bot
    def command(*args, **kwargs):
        def deco(fn): return fn
        return deco
    commands.command = command
    def loop(**kw):
        def deco(fn): return fn
        return deco
    tasks.loop = loop

class DummyUser:
    def __init__(self): self.sent=[]
    async def send(self, text): self.sent.append(text)

class DummyChannel:
    def __init__(self): self.sent=[]
    async def send(self, text): self.sent.append(text)

class DummyBot:
    def __init__(self, user=None, ch=None):
        self._user=user or DummyUser()
        self._ch=ch or DummyChannel()
        self._memkv={}
    def get_user(self, _id): return self._user
    def get_channel(self, _id): return self._ch

async def main():
    ensure_discord_stubs()
    mod = importlib.import_module("satpambot.bot.modules.discord_bot.cogs.xp_chaining_overlay")
    os.environ["XP_CHAIN_ENABLE"]="1"
    os.environ["XP_MAGANG_DONE_KEY"]="leina:xp:magang:done"
    os.environ["XP_PHASE_KEY"]="leina:xp:phase"
    os.environ["XP_NOTIFY_KEY"]="leina:xp:last_notify_ms"
    os.environ["OWNER_USER_ID"]="1234567890"
    bot = DummyBot()
    cog = mod.XPChainingOverlay(bot)
    bot._memkv["leina:xp:magang:done"]="1"
    bot._memkv["leina:xp:phase"]="MAGANG"
    await cog._tick_once()
    phase = bot._memkv.get("leina:xp:phase")
    print("DEBUG after tick:", {"phase": phase, "dm_count": len(bot._user.sent)})
    assert phase=="KERJA", f"phase didn't change -> {phase}"
    assert len(bot._user.sent)==1, f"expected 1 DM, got {len(bot._user.sent)}"
    await cog._tick_once()
    assert len(bot._user.sent)==1, "should not spam duplicate DM"
    print("XP chain smoketest OK: 1 notify, no duplicates.")

if __name__=="__main__":
    asyncio.run(main())
