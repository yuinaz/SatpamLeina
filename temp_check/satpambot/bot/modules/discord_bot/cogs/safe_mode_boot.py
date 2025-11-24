from discord.ext import commands
import os, json, time, logging

log = logging.getLogger(__name__)

BOOT_FILE = "data/runtime_boot.json"
FLAGS_FILE = "data/runtime_flags.json"

class SafeModeBoot(commands.Cog):
    """Deteksi crash-loop dan aktifkan safe-mode minimal."""
    def __init__(self, bot):
        self.bot = bot

    @staticmethod
    def _touch_boot():
        os.makedirs("data", exist_ok=True)
        now = int(time.time())
        try:
            doc = json.load(open(BOOT_FILE,"r"))
        except Exception:
            doc = {"boots":[]}
        doc["boots"] = [ts for ts in doc.get("boots",[]) if now-ts < 600]
        doc["boots"].append(now)
        json.dump(doc, open(BOOT_FILE,"w"))
        safe = len(doc["boots"]) >= 3
        try:
            flags = json.load(open(FLAGS_FILE,"r"))
        except Exception:
            flags = {}
        flags["SAFE_MODE"] = safe
        json.dump(flags, open(FLAGS_FILE,"w"))
        return safe

    @commands.Cog.listener()
    async def on_ready(self):
        safe = self._touch_boot()
        if safe:
            log.warning("[safe-mode] aktif: terlalu sering restart.")
async def setup(bot):
    await bot.add_cog(SafeModeBoot(bot))