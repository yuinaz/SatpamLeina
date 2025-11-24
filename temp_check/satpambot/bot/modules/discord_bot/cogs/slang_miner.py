from discord.ext import commands
import re, logging

from ..helpers.phrasebook import Phrasebook

log = logging.getLogger(__name__)
_token_re = re.compile(r"""(?:(?<=\s)|^)([a-zA-Z0-9_]{3,15})(?=\s|$)""")

class SlangMiner(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.pb = Phrasebook()

    @commands.Cog.listener()
    async def on_message(self, m):
        if m.author.bot or not m.content:
            return
        for tok in _token_re.findall(m.content.lower()):
            if any(c.isdigit() for c in tok):
                continue
            self.pb.add_slang(tok)
        self.pb.save()
async def setup(bot):
    await bot.add_cog(SlangMiner(bot))