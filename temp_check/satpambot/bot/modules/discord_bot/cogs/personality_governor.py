from discord.ext import commands
import json, os, logging

log = logging.getLogger(__name__)
FILE = "data/personality.json"

_DEFAULT = {
    "tsundere_level": 0.6,
    "laugh": "www",
    "languages": ["id","en","jp-romaji","zh"],
    "mood_bias": {"ceria":0.5,"normal":0.4,"sedih":0.1},
}

class PersonalityGovernor(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.state = dict(_DEFAULT)
        self._load()

    def _load(self):
        if os.path.exists(FILE):
            try:
                self.state.update(json.load(open(FILE,"r",encoding="utf-8")))
            except Exception:
                log.warning("personality: failed to load; using defaults")

    def _save(self):
        os.makedirs(os.path.dirname(FILE), exist_ok=True)
        json.dump(self.state, open(FILE,"w",encoding="utf-8"), ensure_ascii=False, indent=2)
async def setup(bot):
    await bot.add_cog(PersonalityGovernor(bot))