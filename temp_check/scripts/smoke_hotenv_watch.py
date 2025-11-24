
import os, sys, types, importlib, asyncio, json, time
from pathlib import Path

# auto root
SCRIPT = Path(__file__).resolve()
def _find_root(p: Path) -> Path:
    q = p
    for _ in range(8):
        if (q/"satpambot").is_dir():
            return q
        q = q.parent
    return Path.cwd()
ROOT = _find_root(SCRIPT.parent)
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# stubs
discord_mod = types.ModuleType("discord")
discord_mod.ext = types.ModuleType("ext")
commands_mod = types.ModuleType("discord.ext.commands")
class Cog:
    @classmethod
    def listener(cls, *a, **k):
        def deco(fn): return fn
        return deco
class Bot:
    def __init__(self): self._events=[]
    def dispatch(self, evt, *args): self._events.append((evt,)+args)
    @property
    def loop(self): return asyncio.get_event_loop()
commands_mod.Cog = Cog
commands_mod.Bot = Bot
discord_mod.ext.commands = commands_mod
sys.modules["discord"] = discord_mod
sys.modules["discord.ext"] = discord_mod.ext
sys.modules["discord.ext.commands"] = commands_mod

from importlib import import_module

async def main():
    # prepare a temp overrides file
    tmp = SCRIPT.parent / "tmp_overrides.json"
    tmp.write_text('{"ok":1}', encoding="utf-8")
    os.environ["HOTENV_WATCH_ENABLE"] = "1"
    os.environ["HOTENV_WATCH_INTERVAL_MS"] = "200"
    os.environ["HOTENV_DEBOUNCE_MS"] = "100"
    os.environ["HOTENV_FILE"] = str(tmp)
    mod = import_module("satpambot.bot.modules.discord_bot.cogs.a00_hotenv_watch_overrides_overlay")
    bot = Bot()
    cog = mod.HotenvWatchOverrides(bot)
    await asyncio.sleep(0.5)  # prime
    # mutate file
    tmp.write_text('{"ok":2}', encoding="utf-8")
    await asyncio.sleep(0.6)  # wait beyond debounce
    assert any(e[0]=="hotenv_reload" for e in bot._events), f"no hotenv_reload fired: {bot._events}"
    print("[SMOKE] hotenv_watch: PASS")

if __name__=="__main__":
    asyncio.run(main())
