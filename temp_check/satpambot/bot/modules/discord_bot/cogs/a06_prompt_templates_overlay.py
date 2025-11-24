
from discord.ext import commands
"""a06_prompt_templates_overlay.py (v8.2)"""
import os, time, logging, threading

DEFAULT_PATH = "satpambot/config/prompts/system.md"
POLL_SEC = int(os.getenv("PROMPT_POLL_SEC", "5"))
log = logging.getLogger(__name__)

class PromptKeeper:
    def __init__(self, path):
        self.path = os.getenv("SYSTEM_PROMPT_PATH", path)
        self._mt = 0; self._txt = ""; t = threading.Thread(target=self._watch, daemon=True); t.start()
        self._load(force=True)
    def _load(self, force=False):
        try:
            st = os.stat(self.path)
            if force or st.st_mtime > self._mt:
                with open(self.path, "r", encoding="utf-8") as f: self._txt = f.read()
                self._mt = st.st_mtime; log.info("[prompt] reloaded from %s", self.path)
        except FileNotFoundError: log.warning("[prompt] file not found: %s", self.path)
        except Exception as e: log.warning("[prompt] load failed: %r", e)
    def _watch(self):
        while True: time.sleep(POLL_SEC); self._load()
    def get(self): return self._txt

class PromptTemplatesOverlay(commands.Cog):
    def __init__(self, bot): self.bot = bot; self.keeper = PromptKeeper(DEFAULT_PATH)
    def get_system_prompt(self): return self.keeper.get()
async def setup(bot): await bot.add_cog(PromptTemplatesOverlay(bot))
def setup(bot):
    try:
        import asyncio
        if asyncio.get_event_loop().is_running():
            return asyncio.create_task(bot.add_cog(PromptTemplatesOverlay(bot)))
    except Exception: pass
    return bot.add_cog(PromptTemplatesOverlay(bot))