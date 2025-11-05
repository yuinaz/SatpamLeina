
import asyncio, importlib, json, sys, types
from _smoke_common import ensure_sys_path, load_overrides, export_env_if_any

root = ensure_sys_path()
export_env_if_any()

class DummyLoop:
    def create_task(self, coro):
        return asyncio.get_event_loop().create_task(coro)

class DummyBot:
    def __init__(self):
        self.cogs = {}
        self.loop = DummyLoop()
        self.guilds = []

    async def add_cog(self, cog):
        name = getattr(cog, "__cog_name__", cog.__class__.__name__)
        self.cogs[name] = cog

    async def wait_until_ready(self):
        await asyncio.sleep(0)

class DummyAuthor:
    def __init__(self):
        self.bot = False
        self.id = 42
        self.name = "smoke-user"

class DummyChannel:
    def __init__(self, id_val: int):
        self.id = id_val
        self.name = f"chan-{id_val}"

class DummyMessage:
    def __init__(self, ch_id: int, content="smoke passive probe"):
        self.author = DummyAuthor()
        self.channel = DummyChannel(ch_id)
        self.content = content
        self.attachments = []
        self.guild = types.SimpleNamespace(id=999, name="SMOKE-GUILD")

doc, used = load_overrides()
env = doc.get("env", {}) if isinstance(doc, dict) else {}
catmap = env.get("HOTENV_CATEGORY_MAP_JSON", "{}")
try:
    cat = json.loads(catmap) if isinstance(catmap, str) else (catmap or {})
except Exception:
    cat = {}

xp_modules = list(cat.get("XP / LADDER", [])) if isinstance(cat, dict) else []
if not xp_modules:
    xp_modules = [
        "satpambot.bot.modules.discord_bot.cogs.a08_xp_event_bridge_overlay",
        "satpambot.bot.modules.discord_bot.cogs.a08f_passive_to_bot_bridge_overlay",
        "satpambot.bot.modules.discord_bot.cogs.a08_xp_stage_recompute_overlay",
        "satpambot.bot.modules.discord_bot.cogs.a09_leina_xp_status_embed_overlay",
        "satpambot.bot.modules.discord_bot.cogs.a09_work_xp_overlay",
    ]

async def load_cog(bot, modname):
    try:
        m = importlib.import_module(modname)
    except Exception as e:
        print("[SKIP import]", modname, "|", repr(e)); return False
    setup = getattr(m, "setup", None)
    if not setup or not asyncio.iscoroutinefunction(setup):
        print("[SKIP no-setup]", modname); return False
    try:
        await setup(bot)
        print("[OK loaded]", modname); return True
    except Exception as e:
        print("[FAIL setup]", modname, "|", repr(e)); return False

async def main():
    # pick a likely-allowed XP channel; fallback to an ID from your notes
    test_ch = int(env.get("XP_TEST_CHANNEL_ID", "1293200121063936052"))
    bot = DummyBot()
    # gate overlay first, so wrappers hook properly
    try:
        gate = importlib.import_module("satpambot.bot.modules.discord_bot.cogs.a00_channel_policy_gate_overlay")
        await gate.setup(bot)
        print("[OK] channel-policy gate overlay loaded")
    except Exception as e:
        print("[WARN] channel-policy overlay not loaded:", repr(e))

    loaded = 0
    for mod in xp_modules:
        ok = await load_cog(bot, mod)
        if ok: loaded += 1

    msg = DummyMessage(test_ch)
    ok_handlers = 0; err_handlers = 0; skipped = 0
    for name, cog in list(bot.cogs.items()):
        mod = getattr(cog, "__module__", "").lower()
        if any(k in mod for k in ("xp","learn","neuro","passive","observer","miner")):
            fn = getattr(cog, "on_message", None)
            if callable(fn):
                try:
                    await fn(msg)
                    ok_handlers += 1
                except Exception as e:
                    print("[ERR handler]", name, "->", repr(e)); err_handlers += 1
            else:
                skipped += 1

    print("[REPORT] loaded:", loaded, "ok_handlers:", ok_handlers, "err_handlers:", err_handlers, "skipped:", skipped)
    if ok_handlers >= 1 and err_handlers == 0:
        return 0
    return 2

if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
